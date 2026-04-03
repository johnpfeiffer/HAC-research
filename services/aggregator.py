"""Compute aggregate statistics from a list of trial insights."""

from collections import Counter


def aggregate_insights(insights: list[dict], trials: list[dict]) -> dict:
    """
    Build summary stats from insights and trial metadata.

    Returns a dict with distributions and totals suitable for dashboard rendering.
    """
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
    }
