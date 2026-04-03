"""Main LangGraph pipeline: fetch -> distribute -> analyze -> aggregate."""

import asyncio
import json
import logging

from langgraph.graph import StateGraph, START, END
from langgraph.types import Send

from graph.state import OverallState, TrialState
from services.ct_client import CTClient, parse_trial
from services.llm import get_llm
from services.supabase_client import (
    get_client,
    create_session,
    update_session,
    insert_trials,
    insert_insight,
)
from services.aggregator import aggregate_insights
from prompts.extraction import EXTRACTION_SYSTEM_PROMPT, TrialInsight

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Nodes
# ---------------------------------------------------------------------------

async def fetch_trials(state: OverallState) -> dict:
    """Fetch trials from ClinicalTrials.gov and store in Supabase."""
    logger.info("fetch_trials: keyword=%r, max_results=%d", state["disease_keyword"], state.get("max_results", 100))
    client = CTClient()
    studies = await client.search(
        condition=state["disease_keyword"],
        max_results=state.get("max_results", 100),
        status=state.get("status_filter") or None,
        phase=state.get("phase_filter") or None,
        date_range=state.get("date_range"),
    )

    # Parse and store trials
    parsed = [parse_trial(s) for s in studies]
    sb = get_client()

    session_id = state["search_session_id"]

    if not parsed:
        logger.warning("fetch_trials: no trials found for %r", state["disease_keyword"])
        update_session(sb, session_id, status="COMPLETED", total_trials=0)
        return {"raw_trials": []}

    logger.info("fetch_trials: parsed %d trials, storing in Supabase", len(parsed))
    update_session(sb, session_id, status="PROCESSING", total_trials=len(parsed))

    stored_trials = insert_trials(sb, session_id, parsed)

    # Build raw_trials with DB IDs for fan-out
    raw_trials = []
    for trial_row in stored_trials:
        raw_trials.append({
            "trial_db_id": trial_row["id"],
            "nct_id": trial_row["nct_id"],
            "raw_json": trial_row["raw_json"],
        })

    logger.info("fetch_trials: %d trials ready for analysis", len(raw_trials))
    return {"raw_trials": raw_trials}


def distribute_trials(state: OverallState) -> list[Send]:
    """Fan-out: create a Send for each trial to process in parallel."""
    logger.info("distribute_trials: fanning out %d trials", len(state["raw_trials"]))
    return [
        Send(
            "analyze_trial",
            {
                "trial_data": trial["raw_json"],
                "session_id": state["search_session_id"],
                "trial_db_id": trial["trial_db_id"],
            },
        )
        for trial in state["raw_trials"]
    ]


async def analyze_trial(state: TrialState) -> dict:
    """Call MiniMax to extract structured insights for a single trial."""
    nct_id = state.get("trial_data", {}).get("protocolSection", {}).get("identificationModule", {}).get("nctId", "unknown")
    logger.debug("analyze_trial: starting analysis for trial_db_id=%s (nct=%s)", state["trial_db_id"], nct_id)
    try:
        llm = get_llm()
        llm_with_tools = llm.bind_tools([TrialInsight])

        trial_json = json.dumps(state["trial_data"], indent=2, default=str)
        messages = [
            {"role": "system", "content": EXTRACTION_SYSTEM_PROMPT},
            {"role": "user", "content": f"Analyze this clinical trial:\n\n{trial_json}"},
        ]

        response = await llm_with_tools.ainvoke(messages)

        # Extract tool call result
        insight_data = {}
        if response.tool_calls:
            insight_data = response.tool_calls[0]["args"]

        # Schema: column name -> expected type
        COLUMN_TYPES = {
            "drug_names": list,
            "drug_types": list,
            "mechanism_of_action": str,
            "primary_endpoints": list,
            "secondary_endpoints": list,
            "efficacy_summary": str,
            "safety_summary": str,
            "serious_ae_count": int,
            "other_ae_count": int,
            "top_adverse_events": list,
            "investment_signal": str,
            "investment_rationale": str,
            "competitive_notes": str,
            "patient_population": str,
        }

        def _safe_int(v):
            if isinstance(v, int):
                return v
            try:
                return int(str(v).strip().split()[0])
            except (ValueError, TypeError, IndexError):
                return 0

        insight_row = {
            "trial_id": state["trial_db_id"],
            "session_id": state["session_id"],
        }
        for col, expected_type in COLUMN_TYPES.items():
            val = insight_data.get(col)
            if val is None:
                continue
            if expected_type is int:
                insight_row[col] = _safe_int(val)
            elif expected_type is str:
                if isinstance(val, str):
                    insight_row[col] = val
            elif expected_type is list:
                if isinstance(val, list):
                    insight_row[col] = [
                        item if isinstance(item, dict) else item
                        for item in val
                    ]

        sb = get_client()
        stored = insert_insight(sb, insight_row)

        # Update processed count
        from services.supabase_client import get_session
        session = get_session(sb, state["session_id"])
        update_session(
            sb,
            state["session_id"],
            processed_trials=(session.get("processed_trials", 0) or 0) + 1,
        )

        logger.debug("analyze_trial: completed nct=%s signal=%s", nct_id, insight_row.get("investment_signal"))
        return {"insights": [stored]}

    except Exception:
        logger.exception("analyze_trial: failed for trial_db_id=%s (nct=%s)", state["trial_db_id"], nct_id)
        return {"insights": []}


async def aggregate_results(state: OverallState) -> dict:
    """Compute aggregate stats, group MOAs via LLM, and mark session complete."""
    logger.info("aggregate_results: starting for session %s", state["search_session_id"])
    sb = get_client()
    session_id = state["search_session_id"]

    from services.supabase_client import get_trials, get_insights

    trials = get_trials(sb, session_id)
    insights = get_insights(sb, session_id)
    logger.info("aggregate_results: loaded %d trials, %d insights", len(trials), len(insights))

    agg = aggregate_insights(insights, trials)

    # Determine most investable company via LLM
    try:
        llm = get_llm(temperature=0)
        sponsor_summary = "\n".join(
            f"- {s['name']}: {s['count']} trials"
            for s in agg.get("top_sponsors", [])[:10]
        )
        insight_map = {}
        for i in insights:
            sponsor = None
            for t in trials:
                if t.get("id") == i.get("trial_id"):
                    sponsor = t.get("sponsor_name")
                    break
            if sponsor:
                insight_map.setdefault(sponsor, []).append(i)

        sponsor_details = []
        for sponsor, sponsor_insights in list(insight_map.items())[:10]:
            pos = sum(1 for i in sponsor_insights if i.get("investment_signal") == "POSITIVE")
            neg = sum(1 for i in sponsor_insights if i.get("investment_signal") == "NEGATIVE")
            drugs = set()
            for i in sponsor_insights:
                for d in i.get("drug_names") or []:
                    drugs.add(d)
            sponsor_details.append(
                f"- {sponsor}: {len(sponsor_insights)} trials, {pos} positive/{neg} negative signals, drugs: {', '.join(list(drugs)[:5]) or 'N/A'}"
            )

        prompt = (
            f"Based on this clinical trial data for '{state['disease_keyword']}', identify the single most investable company/sponsor.\n\n"
            f"Sponsor overview:\n{sponsor_summary}\n\n"
            f"Detailed signals:\n" + "\n".join(sponsor_details) + "\n\n"
            f"Phase distribution: {agg.get('phase_distribution', {})}\n"
            f"Signal distribution: {agg.get('signal_distribution', {})}\n\n"
            "Respond in EXACTLY this format, nothing else:\n"
            "COMPANY: <company name>\n"
            "REASON: <1-2 sentence reason why this is the most investable>"
        )
        resp = await llm.ainvoke([{"role": "user", "content": prompt}])
        text = resp.content.strip()
        lines = text.split("\n")
        company = ""
        reason = ""
        for line in lines:
            if line.startswith("COMPANY:"):
                company = line.split(":", 1)[1].strip()
            elif line.startswith("REASON:"):
                reason = line.split(":", 1)[1].strip()
        if company:
            agg["most_investable"] = {"company": company, "reason": reason}
            logger.info("Most investable: %s", company)
    except Exception:
        logger.exception("aggregate_results: most investable determination failed")

    update_session(sb, session_id, status="COMPLETED")
    logger.info("aggregate_results: session %s marked COMPLETED", session_id)

    return {"aggregate": agg}


# ---------------------------------------------------------------------------
# Graph construction
# ---------------------------------------------------------------------------

def build_pipeline() -> StateGraph:
    """Build and compile the main analysis pipeline."""
    logger.info("Building LangGraph pipeline")
    graph = StateGraph(OverallState)

    graph.add_node("fetch_trials", fetch_trials)
    graph.add_node("analyze_trial", analyze_trial)
    graph.add_node("aggregate_results", aggregate_results)

    graph.add_edge(START, "fetch_trials")
    graph.add_conditional_edges("fetch_trials", distribute_trials)
    graph.add_edge("analyze_trial", "aggregate_results")
    graph.add_edge("aggregate_results", END)

    return graph.compile()
