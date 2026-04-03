"""Main LangGraph pipeline: fetch -> distribute -> analyze -> aggregate."""

import asyncio
import json

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


# ---------------------------------------------------------------------------
# Nodes
# ---------------------------------------------------------------------------

async def fetch_trials(state: OverallState) -> dict:
    """Fetch trials from ClinicalTrials.gov and store in Supabase."""
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
        update_session(sb, session_id, status="COMPLETED", total_trials=0)
        return {"raw_trials": []}

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

    return {"raw_trials": raw_trials}


def distribute_trials(state: OverallState) -> list[Send]:
    """Fan-out: create a Send for each trial to process in parallel."""
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
            # skip malformed non-string values
        elif expected_type is list:
            if isinstance(val, list):
                insight_row[col] = [
                    item if isinstance(item, dict) else item
                    for item in val
                ]
            # skip malformed non-list values

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

    return {"insights": [stored]}


async def aggregate_results(state: OverallState) -> dict:
    """Compute aggregate stats and mark session complete."""
    sb = get_client()
    session_id = state["search_session_id"]

    from services.supabase_client import get_trials, get_insights
    trials = get_trials(sb, session_id)
    insights = get_insights(sb, session_id)

    agg = aggregate_insights(insights, trials)

    update_session(sb, session_id, status="COMPLETED")

    return {"aggregate": agg}


# ---------------------------------------------------------------------------
# Graph construction
# ---------------------------------------------------------------------------

def build_pipeline() -> StateGraph:
    """Build and compile the main analysis pipeline."""
    graph = StateGraph(OverallState)

    graph.add_node("fetch_trials", fetch_trials)
    graph.add_node("analyze_trial", analyze_trial)
    graph.add_node("aggregate_results", aggregate_results)

    graph.add_edge(START, "fetch_trials")
    graph.add_conditional_edges("fetch_trials", distribute_trials)
    graph.add_edge("analyze_trial", "aggregate_results")
    graph.add_edge("aggregate_results", END)

    return graph.compile()
