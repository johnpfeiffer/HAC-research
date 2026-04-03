"""Streamlit entry point for Clinical Trials Investment Dashboard."""

import asyncio

import streamlit as st
from dotenv import load_dotenv

load_dotenv()

from components.search_form import render_search_form
from components.progress import render_progress
from components.dashboard import render_dashboard
from components.trial_table import render_trial_table
from components.chat_panel import render_chat_panel
from services.supabase_client import (
    get_client,
    create_session,
    list_sessions,
    get_trials,
    get_insights,
    get_session,
)
from graph.pipeline import build_pipeline


st.set_page_config(
    page_title="Clinical Trials Investment Dashboard",
    page_icon="💊",
    layout="wide",
)

st.title("Clinical Trials Investment Dashboard")

if st.button("New Search", type="secondary"):
    st.session_state["current_session_id"] = None
    st.session_state["pipeline_complete"] = False
    st.session_state["aggregate"] = {}
    st.rerun()

st.divider()


def run_pipeline(search_params: dict, session_id: str, status_container):
    """Run the LangGraph analysis pipeline with live logging."""
    pipeline = build_pipeline()
    initial_state = {
        "disease_keyword": search_params["disease_keyword"],
        "search_session_id": session_id,
        "status_filter": search_params.get("status_filter", ""),
        "phase_filter": search_params.get("phase_filter", []),
        "date_range": search_params.get("date_range"),
        "max_results": search_params.get("max_results", 100),
        "raw_trials": [],
        "insights": [],
        "aggregate": {},
        "chat_history": [],
        "chat_response": "",
    }

    async def _run():
        analyzed_count = 0
        total_trials = 0
        result = None

        async for event in pipeline.astream_events(initial_state, version="v2"):
            kind = event.get("event", "")
            name = event.get("name", "")

            if kind == "on_chain_start" and name == "fetch_trials":
                status_container.update(label="Fetching trials from ClinicalTrials.gov...", state="running")

            elif kind == "on_chain_end" and name == "fetch_trials":
                output = event.get("data", {}).get("output", {})
                raw = output.get("raw_trials", [])
                total_trials = len(raw)
                if total_trials == 0:
                    status_container.write("No trials found for this query.")
                else:
                    status_container.write(f"Fetched **{total_trials}** trials from ClinicalTrials.gov")
                    status_container.update(label=f"Analyzing {total_trials} trials with AI...", state="running")

            elif kind == "on_chain_end" and name == "analyze_trial":
                analyzed_count += 1
                output = event.get("data", {}).get("output", {})
                insights = output.get("insights", [])
                signal = "N/A"
                drugs = "N/A"
                if insights:
                    ins = insights[0]
                    signal = ins.get("investment_signal", "N/A")
                    drugs = ", ".join(ins.get("drug_names") or []) or "N/A"
                status_container.update(
                    label=f"Analyzing trials... ({analyzed_count}/{total_trials})",
                    state="running",
                )
                status_container.write(
                    f"Trial {analyzed_count}/{total_trials} — Signal: **{signal}** | Drugs: {drugs}"
                )

            elif kind == "on_chain_start" and name == "aggregate_results":
                status_container.update(label="Aggregating results...", state="running")

            elif kind == "on_chain_end" and name == "aggregate_results":
                output = event.get("data", {}).get("output", {})
                agg = output.get("aggregate", {})
                pos = agg.get("positive_signals", 0)
                neg = agg.get("negative_signals", 0)
                neu = agg.get("neutral_signals", 0)
                status_container.write(
                    f"Done! Signals: **{pos}** positive, **{neu}** neutral, **{neg}** negative"
                )
                status_container.update(label="Analysis complete!", state="complete")
                result = output

        # If stream ended without aggregate (e.g. 0 trials), get final state
        if result is None:
            result = {"aggregate": {}}
        return result

    return asyncio.run(_run())


# ---------------------------------------------------------------------------
# Session state
# ---------------------------------------------------------------------------
if "current_session_id" not in st.session_state:
    st.session_state["current_session_id"] = None
if "pipeline_complete" not in st.session_state:
    st.session_state["pipeline_complete"] = False
if "aggregate" not in st.session_state:
    st.session_state["aggregate"] = {}

# ---------------------------------------------------------------------------
# Sidebar: recent searches
# ---------------------------------------------------------------------------
with st.sidebar:
    st.header("Recent Searches")
    sb = get_client()
    sessions = list_sessions(sb)
    for s in sessions:
        label = f"{s['disease_keyword']} ({s['status']})"
        if st.button(label, key=f"session_{s['id']}"):
            st.session_state["current_session_id"] = s["id"]
            st.session_state["pipeline_complete"] = s["status"] == "COMPLETED"
            if s["status"] == "COMPLETED":
                trials = get_trials(sb, s["id"])
                insights = get_insights(sb, s["id"])
                from services.aggregator import aggregate_insights
                st.session_state["aggregate"] = aggregate_insights(insights, trials)
            st.rerun()

# ---------------------------------------------------------------------------
# Main content
# ---------------------------------------------------------------------------
session_id = st.session_state["current_session_id"]

if session_id and st.session_state["pipeline_complete"]:
    # Dashboard view
    session = get_session(sb, session_id)
    st.subheader(f"Results: {session['disease_keyword']}")

    trials = get_trials(sb, session_id)
    insights = get_insights(sb, session_id)
    aggregate = st.session_state["aggregate"]

    tab_dashboard, tab_trials, tab_chat = st.tabs(["Dashboard", "Trial Details", "Chat"])

    with tab_dashboard:
        render_dashboard(aggregate, trials, insights)

    with tab_trials:
        render_trial_table(trials, insights)

    with tab_chat:
        render_chat_panel(session_id, aggregate)

elif session_id and not st.session_state["pipeline_complete"]:
    # Processing view — poll for progress
    complete = render_progress(session_id)
    if complete:
        st.session_state["pipeline_complete"] = True
        trials = get_trials(sb, session_id)
        insights = get_insights(sb, session_id)
        from services.aggregator import aggregate_insights
        st.session_state["aggregate"] = aggregate_insights(insights, trials)
        st.rerun()
    else:
        st.button("Refresh", on_click=lambda: None)

else:
    # Search view
    search_params = render_search_form()

    if search_params:
        # Create session and kick off pipeline
        sb = get_client()
        filters = {
            "phase": search_params.get("phase_filter"),
            "status": search_params.get("status_filter"),
            "date_range": search_params.get("date_range"),
        }
        session = create_session(sb, search_params["disease_keyword"], filters)
        session_id = session["id"]

        st.session_state["current_session_id"] = session_id

        with st.status("Starting analysis pipeline...", expanded=True) as status:
            result = run_pipeline(search_params, session_id, status)
            st.session_state["aggregate"] = result.get("aggregate", {})
            st.session_state["pipeline_complete"] = True

        st.rerun()
