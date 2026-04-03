"""Chat system prompt for investment analyst Q&A."""

import logging

logger = logging.getLogger(__name__)


def build_chat_system_prompt(aggregate: dict, insights: list[dict], trials: list[dict]) -> str:
    """
    Build the system prompt for the chat node, injecting aggregate stats
    and a compact trial index as context.
    """
    logger.debug("Building chat system prompt: %d trials, %d insights", len(trials), len(insights))
    # Compact trial index: one line per trial
    trial_lines = []
    insight_map = {i.get("trial_id"): i for i in insights}
    for t in trials:
        tid = t.get("id")
        ins = insight_map.get(tid, {})
        drugs = ", ".join(ins.get("drug_names") or []) or "N/A"
        signal = ins.get("investment_signal", "N/A")
        rationale = (ins.get("investment_rationale") or "")[:80]
        line = (
            f"| {t.get('nct_id','N/A')} | {drugs} | {t.get('phase','N/A')} | "
            f"{t.get('overall_status','N/A')} | {signal} | {rationale} |"
        )
        trial_lines.append(line)

    trial_table = "\n".join(trial_lines) if trial_lines else "No trials available."

    # Build full detail for high-priority trials
    priority_details = []
    for t in trials:
        tid = t.get("id")
        ins = insight_map.get(tid, {})
        if (
            t.get("phase") in ("PHASE3", "PHASE4")
            and t.get("sponsor_class") == "INDUSTRY"
            and t.get("has_results")
            and ins.get("investment_signal") == "POSITIVE"
        ):
            priority_details.append(
                f"### {t.get('nct_id')} — {t.get('brief_title','')}\n"
                f"- Drugs: {', '.join(ins.get('drug_names') or [])}\n"
                f"- Efficacy: {ins.get('efficacy_summary','N/A')}\n"
                f"- Safety: {ins.get('safety_summary','N/A')}\n"
                f"- Rationale: {ins.get('investment_rationale','N/A')}\n"
            )

    priority_section = "\n".join(priority_details) if priority_details else "None identified."

    agg = aggregate or {}

    return f"""\
You are an investment analyst specializing in clinical trial data for pharma/biotech \
investment decisions. Answer questions using the data below.

## Aggregate Statistics
- Total trials: {agg.get('total_trials', 0)}
- Trials with results: {agg.get('trials_with_results', 0)}
- Total enrollment: {agg.get('total_enrollment', 0)}
- Phase distribution: {agg.get('phase_distribution', {})}
- Status distribution: {agg.get('status_distribution', {})}
- Investment signals: {agg.get('signal_distribution', {})}
- Top drugs: {agg.get('top_drugs', [])}
- Top sponsors: {agg.get('top_sponsors', [])}

## Trial Index
| NCT ID | Drugs | Phase | Status | Signal | Rationale |
|--------|-------|-------|--------|--------|-----------|
{trial_table}

## High-Priority Trial Details (Phase 3+, Industry, Has Results, Positive Signal)
{priority_section}

Guidelines:
- Base answers strictly on the provided data.
- When citing trials, include the NCT ID.
- For investment recommendations, clearly state the signal and rationale.
- If data is insufficient to answer, say so explicitly.
"""
