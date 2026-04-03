"""Tests for aggregator module."""

from services.aggregator import aggregate_insights


SAMPLE_TRIALS = [
    {
        "id": "t1",
        "phase": "PHASE2",
        "overall_status": "RECRUITING",
        "sponsor_class": "INDUSTRY",
        "sponsor_name": "Acme",
        "has_results": False,
        "enrollment_count": 100,
    },
    {
        "id": "t2",
        "phase": "PHASE3",
        "overall_status": "COMPLETED",
        "sponsor_class": "INDUSTRY",
        "sponsor_name": "Acme",
        "has_results": True,
        "enrollment_count": 500,
    },
    {
        "id": "t3",
        "phase": "PHASE2",
        "overall_status": "RECRUITING",
        "sponsor_class": "NIH",
        "sponsor_name": "NIH",
        "has_results": False,
        "enrollment_count": 200,
    },
]

SAMPLE_INSIGHTS = [
    {
        "trial_id": "t1",
        "investment_signal": "NEUTRAL",
        "drug_names": ["DrugA"],
    },
    {
        "trial_id": "t2",
        "investment_signal": "POSITIVE",
        "drug_names": ["DrugA", "DrugB"],
    },
    {
        "trial_id": "t3",
        "investment_signal": "INSUFFICIENT_DATA",
        "drug_names": [],
    },
]


def test_aggregate_totals():
    result = aggregate_insights(SAMPLE_INSIGHTS, SAMPLE_TRIALS)
    assert result["total_trials"] == 3
    assert result["trials_with_results"] == 1
    assert result["total_enrollment"] == 800


def test_aggregate_phase_distribution():
    result = aggregate_insights(SAMPLE_INSIGHTS, SAMPLE_TRIALS)
    assert result["phase_distribution"]["PHASE2"] == 2
    assert result["phase_distribution"]["PHASE3"] == 1


def test_aggregate_signal_distribution():
    result = aggregate_insights(SAMPLE_INSIGHTS, SAMPLE_TRIALS)
    assert result["signal_distribution"]["POSITIVE"] == 1
    assert result["signal_distribution"]["NEUTRAL"] == 1
    assert result["positive_signals"] == 1
    assert result["negative_signals"] == 0


def test_aggregate_drug_counts():
    result = aggregate_insights(SAMPLE_INSIGHTS, SAMPLE_TRIALS)
    drugs = {d["name"]: d["count"] for d in result["top_drugs"]}
    assert drugs["DrugA"] == 2
    assert drugs["DrugB"] == 1


def test_aggregate_top_sponsors():
    result = aggregate_insights(SAMPLE_INSIGHTS, SAMPLE_TRIALS)
    sponsors = {s["name"]: s["count"] for s in result["top_sponsors"]}
    assert sponsors["Acme"] == 2
    assert sponsors["NIH"] == 1
