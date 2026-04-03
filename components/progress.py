"""Processing progress display component."""

import streamlit as st
from services.supabase_client import get_client, get_session


def render_progress(session_id: str) -> bool:
    """
    Render a progress bar for the current session.

    Returns True when processing is complete.
    """
    sb = get_client()
    session = get_session(sb, session_id)

    status = session.get("status", "FETCHING")
    total = session.get("total_trials") or 0
    processed = session.get("processed_trials") or 0

    if status == "FETCHING":
        st.info("Fetching trials from ClinicalTrials.gov...")
        st.progress(0.0)
        return False

    if status == "PROCESSING":
        progress = processed / total if total > 0 else 0
        st.info(f"Analyzing trials with AI... ({processed}/{total})")
        st.progress(progress)
        return False

    if status == "COMPLETED":
        st.success(f"Analysis complete! {total} trials processed.")
        return True

    if status == "FAILED":
        st.error("Processing failed. Please try again.")
        return True

    return False
