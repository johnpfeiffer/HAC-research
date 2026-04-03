"""LangGraph state definitions."""

import operator
from typing import Annotated, TypedDict


class TrialState(TypedDict):
    """State for individual trial processing (fan-out)."""
    trial_data: dict  # Single trial JSON from CT.gov
    session_id: str
    trial_db_id: str  # UUID from Supabase trials table


class OverallState(TypedDict):
    """Main graph state."""
    disease_keyword: str
    search_session_id: str
    status_filter: str
    phase_filter: list[str]
    date_range: tuple[str, str] | None
    max_results: int
    raw_trials: list[dict]
    insights: Annotated[list[dict], operator.add]  # Aggregated from subagents
    aggregate: dict  # Summary stats
    chat_history: list[dict]  # Conversation messages
    chat_response: str  # Latest response
