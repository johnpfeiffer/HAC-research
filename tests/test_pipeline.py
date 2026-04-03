"""Tests for LangGraph pipeline structure."""

from graph.pipeline import build_pipeline
from graph.state import OverallState, TrialState


def test_state_definitions():
    """Verify state TypedDicts have required keys."""
    overall_keys = OverallState.__annotations__.keys()
    assert "disease_keyword" in overall_keys
    assert "insights" in overall_keys
    assert "aggregate" in overall_keys
    assert "raw_trials" in overall_keys

    trial_keys = TrialState.__annotations__.keys()
    assert "trial_data" in trial_keys
    assert "session_id" in trial_keys
    assert "trial_db_id" in trial_keys


def test_pipeline_builds():
    """Verify the pipeline compiles without errors."""
    pipeline = build_pipeline()
    assert pipeline is not None
    # The compiled graph should have a graph attribute
    assert hasattr(pipeline, "invoke") or hasattr(pipeline, "ainvoke")
