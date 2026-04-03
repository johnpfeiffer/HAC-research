"""Compute aggregate statistics from a list of trial insights."""

import logging
from collections import Counter

logger = logging.getLogger(__name__)

PROGRESSING_STATUSES = {
    "RECRUITING", "ACTIVE_NOT_RECRUITING", "NOT_YET_RECRUITING",
    "ENROLLING_BY_INVITATION", "AVAILABLE",
}
DECLINING_STATUSES = {
    "TERMINATED", "WITHDRAWN", "SUSPENDED",
}


def aggregate_insights(insights: list[dict], trials: list[dict]) -> dict:
    """
    Build summary stats from insights and trial metadata.

    Returns a dict with distributions and totals suitable for dashboard rendering.
    """
    logger.info("Aggregating insights: %d trials, %d insights", len(trials), len(insights))
    total = len(trials)
    with_results = sum(1 for t in trials if t.get("has_results"))

    # Phase distribution
    phase_counts = Counter(t.get("phase") or "UNKNOWN" for t in trials)

    # Status distribution
    status_counts = Counter(t.get("overall_status") or "UNKNOWN" for t in trials)

    # Sponsor class distribution
    sponsor_class_counts = Counter(t.get("sponsor_class") or "UNKNOWN" for t in trials)

    # Top sponsors by trial count
    sponsor_name_counts = Counter(t.get("sponsor_name") or "UNKNOWN" for t in trials)
    top_sponsors = sponsor_name_counts.most_common(15)

    # Investment signal distribution
    signal_counts = Counter(i.get("investment_signal") or "INSUFFICIENT_DATA" for i in insights)

    # Enrollment totals
    total_enrollment = sum(t.get("enrollment_count") or 0 for t in trials)

    # Drug frequency across insights
    drug_counter: Counter = Counter()
    for i in insights:
        for drug in i.get("drug_names") or []:
            drug_counter[drug] += 1
    top_drugs = drug_counter.most_common(15)

    # --- Competitive dynamics ---
    unique_sponsors = len(set(t.get("sponsor_name") or "UNKNOWN" for t in trials))

    # Trial starts by year
    starts_by_year: Counter = Counter()
    for t in trials:
        sd = t.get("start_date")
        if sd:
            year = str(sd)[:4]
            starts_by_year[year] += 1

    # Trial ends by year
    ends_by_year: Counter = Counter()
    for t in trials:
        cd = t.get("completion_date")
        if cd:
            year = str(cd)[:4]
            ends_by_year[year] += 1

    # Gantt chart data: trials with both start and end dates
    gantt_data = []
    insight_map = {i.get("trial_id"): i for i in insights}
    for t in trials:
        sd = t.get("start_date")
        cd = t.get("completion_date")
        if sd and cd:
            ins = insight_map.get(t.get("id"), {})
            gantt_data.append({
                "nct_id": t.get("nct_id", ""),
                "title": (t.get("brief_title") or "")[:50],
                "start": str(sd),
                "end": str(cd),
                "phase": t.get("phase") or "UNKNOWN",
                "status": t.get("overall_status") or "UNKNOWN",
                "signal": ins.get("investment_signal", "N/A"),
            })

    # Progressing vs declining trials
    progressing = []
    declining = []
    for t in trials:
        status = t.get("overall_status") or ""
        ins = insight_map.get(t.get("id"), {})
        signal = ins.get("investment_signal", "")
        entry = {
            "nct_id": t.get("nct_id"),
            "brief_title": t.get("brief_title"),
            "phase": t.get("phase"),
            "status": status,
            "sponsor": t.get("sponsor_name"),
            "signal": signal,
            "drugs": ", ".join(ins.get("drug_names") or []) or "N/A",
        }
        if status in PROGRESSING_STATUSES:
            progressing.append(entry)
        elif status in DECLINING_STATUSES or signal == "NEGATIVE":
            declining.append(entry)

    # Raw MOA list (for LLM grouping in pipeline)
    raw_moas = []
    for i in insights:
        moa = i.get("mechanism_of_action") or ""
        if moa and moa.lower() not in ("", "unknown", "n/a", "not specified"):
            raw_moas.append(moa)

    # Fallback ungrouped MOA counts
    moa_counter = Counter(raw_moas)

    logger.info(
        "Aggregation complete: %d total, %d with results, %d unique sponsors, %d raw MOAs",
        total, with_results, unique_sponsors, len(raw_moas),
    )

    return {
        "total_trials": total,
        "trials_with_results": with_results,
        "total_enrollment": total_enrollment,
        "phase_distribution": dict(phase_counts),
        "status_distribution": dict(status_counts),
        "sponsor_class_distribution": dict(sponsor_class_counts),
        "top_sponsors": [{"name": n, "count": c} for n, c in top_sponsors],
        "signal_distribution": dict(signal_counts),
        "top_drugs": [{"name": n, "count": c} for n, c in top_drugs],
        "positive_signals": signal_counts.get("POSITIVE", 0),
        "negative_signals": signal_counts.get("NEGATIVE", 0),
        "neutral_signals": signal_counts.get("NEUTRAL", 0),
        # Competitive dynamics
        "unique_sponsors": unique_sponsors,
        "starts_by_year": dict(sorted(starts_by_year.items())),
        "ends_by_year": dict(sorted(ends_by_year.items())),
        "gantt_data": gantt_data,
        "progressing_trials": progressing,
        "declining_trials": declining,
        "moa_clusters": [{"mechanism": m, "count": c} for m, c in moa_counter.most_common(15)],
        "raw_moas": raw_moas,  # for LLM grouping
        "moa_groups": [],  # populated by pipeline after LLM call
    }
