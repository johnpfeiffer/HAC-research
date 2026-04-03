"""Streamlit search input component with filters."""

import streamlit as st
from datetime import date


def render_search_form() -> dict | None:
    """
    Render the search form. Returns a dict of search params when submitted, else None.
    """
    st.header("Clinical Trial Search")

    with st.form("search_form"):
        disease = st.text_input(
            "Disease / Condition",
            placeholder="e.g. lung cancer, Stargardt disease, azacitidine",
        )

        col1, col2 = st.columns(2)
        with col1:
            phase_options = ["PHASE1", "PHASE2", "PHASE3", "PHASE4", "EARLY_PHASE1", "NA"]
            phases = st.multiselect("Phase filter", options=phase_options)
        with col2:
            status_options = [
                "RECRUITING",
                "COMPLETED",
                "ACTIVE_NOT_RECRUITING",
                "NOT_YET_RECRUITING",
                "TERMINATED",
                "WITHDRAWN",
                "SUSPENDED",
            ]
            status = st.selectbox("Status filter", options=["ALL"] + status_options)

        col3, col4 = st.columns(2)
        with col3:
            start_date = st.date_input("Start date (optional)", value=None)
        with col4:
            end_date = st.date_input("End date (optional)", value=None)

        max_results = st.slider("Max trials to analyze", min_value=5, max_value=100, value=50)

        submitted = st.form_submit_button("Analyze Trials", type="primary")

    if submitted and disease:
        date_range = None
        if start_date and end_date:
            date_range = (start_date.isoformat(), end_date.isoformat())

        return {
            "disease_keyword": disease,
            "phase_filter": phases,
            "status_filter": "" if status == "ALL" else status,
            "date_range": date_range,
            "max_results": max_results,
        }

    if submitted and not disease:
        st.warning("Please enter a disease or condition.")

    return None
