"""Competitive dynamics dashboard component."""

import logging

import streamlit as st
import plotly.express as px
import plotly.figure_factory as ff
import pandas as pd

logger = logging.getLogger(__name__)


def render_competitive(aggregate: dict, trials: list[dict], insights: list[dict]):
    """Render competitive dynamics dashboard."""
    logger.debug("Rendering competitive dashboard: %d trials, %d insights", len(trials), len(insights))
    if not aggregate:
        st.warning("No data to display.")
        return

    # --- Metric cards ---
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Unique Sponsors", aggregate.get("unique_sponsors", 0))
    c2.metric("Total Trials", aggregate.get("total_trials", 0))
    c3.metric("Progressing", len(aggregate.get("progressing_trials", [])))
    c4.metric("Declining", len(aggregate.get("declining_trials", [])))

    st.divider()

    # --- Row 1: Phase bar chart + Sponsor ranking ---
    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Trials by Phase")
        phase_data = aggregate.get("phase_distribution", {})
        if phase_data:
            phase_order = ["EARLY_PHASE1", "PHASE1", "PHASE2", "PHASE3", "PHASE4", "NA", "UNKNOWN"]
            sorted_phases = sorted(phase_data.items(), key=lambda x: phase_order.index(x[0]) if x[0] in phase_order else 99)
            df = pd.DataFrame(sorted_phases, columns=["Phase", "Count"])
            fig = px.bar(df, x="Phase", y="Count", color="Phase",
                         color_discrete_sequence=px.colors.qualitative.Set2)
            fig.update_layout(showlegend=False, margin=dict(t=20, b=20))
            st.plotly_chart(fig, width="stretch")

    with col2:
        st.subheader("Sponsors by Trial Count")
        sponsors = aggregate.get("top_sponsors", [])
        if sponsors:
            df = pd.DataFrame(sponsors)
            fig = px.bar(df, y="name", x="count", orientation="h",
                         color="count", color_continuous_scale="Blues")
            fig.update_layout(
                yaxis=dict(categoryorder="total ascending"),
                margin=dict(t=20, b=20, l=10), showlegend=False,
                coloraxis_showscale=False,
            )
            st.plotly_chart(fig, width="stretch")

    # --- Row 2: Trial starts + ends by year ---
    col3, col4 = st.columns(2)

    with col3:
        st.subheader("Trial Starts by Year")
        starts = aggregate.get("starts_by_year", {})
        if starts:
            df = pd.DataFrame([{"Year": y, "Trials": c} for y, c in starts.items()])
            fig = px.bar(df, x="Year", y="Trials", color="Trials",
                         color_continuous_scale="Viridis")
            fig.update_layout(margin=dict(t=20, b=20), coloraxis_showscale=False)
            st.plotly_chart(fig, width="stretch")

    with col4:
        st.subheader("Trial End Dates by Year")
        ends = aggregate.get("ends_by_year", {})
        if ends:
            df = pd.DataFrame([{"Year": y, "Trials": c} for y, c in ends.items()])
            fig = px.bar(df, x="Year", y="Trials", color="Trials",
                         color_continuous_scale="Magma")
            fig.update_layout(margin=dict(t=20, b=20), coloraxis_showscale=False)
            st.plotly_chart(fig, width="stretch")
        else:
            st.info("No completion date data available.")

    st.divider()

    # --- Row 3: Gantt chart ---
    st.subheader("Trial Timeline (Gantt)")
    _render_gantt(aggregate)

    st.divider()

    # --- Row 4: Raw MOA clusters ---
    st.subheader("Mechanisms of Action")
    moa = aggregate.get("moa_clusters", [])
    if moa:
        for m in moa:
            if len(m["mechanism"]) > 50:
                m["mechanism"] = m["mechanism"][:47] + "..."
        df = pd.DataFrame(moa)
        fig = px.bar(df, y="mechanism", x="count", orientation="h",
                     color="count", color_continuous_scale="Teal")
        fig.update_layout(
            yaxis=dict(categoryorder="total ascending"),
            margin=dict(t=20, b=20, l=10), showlegend=False,
            coloraxis_showscale=False,
        )
        st.plotly_chart(fig, width="stretch")
    else:
        st.info("No mechanism data available.")

    st.divider()

    # --- Row 5: Progressing vs Declining tabs ---
    st.subheader("Trial Momentum")
    tab_prog, tab_decl = st.tabs(["Progressing", "Declining"])

    with tab_prog:
        prog = aggregate.get("progressing_trials", [])
        if prog:
            df = pd.DataFrame(prog)
            df.columns = ["NCT ID", "Title", "Phase", "Status", "Sponsor", "Signal", "Drugs"]
            st.dataframe(df, width="stretch", hide_index=True,
                         column_config={"Title": st.column_config.TextColumn(width="large")})
        else:
            st.info("No progressing trials found.")

    with tab_decl:
        decl = aggregate.get("declining_trials", [])
        if decl:
            df = pd.DataFrame(decl)
            df.columns = ["NCT ID", "Title", "Phase", "Status", "Sponsor", "Signal", "Drugs"]
            st.dataframe(df, width="stretch", hide_index=True,
                         column_config={"Title": st.column_config.TextColumn(width="large")})
        else:
            st.info("No declining trials found.")


def _render_gantt(aggregate: dict):
    """Render a Gantt chart of trial timelines."""
    gantt_data = aggregate.get("gantt_data", [])
    if not gantt_data:
        st.info("No trials with both start and end dates available.")
        return

    # Sort by start date
    gantt_data = sorted(gantt_data, key=lambda x: x["start"])

    # Cap at 50 trials for readability
    if len(gantt_data) > 50:
        st.caption(f"Showing 50 of {len(gantt_data)} trials (sorted by start date)")
        gantt_data = gantt_data[:50]

    # Build dataframe for px.timeline
    rows = []
    for g in gantt_data:
        rows.append({
            "Trial": f"{g['nct_id']}",
            "Start": g["start"],
            "End": g["end"],
            "Phase": g["phase"],
            "Status": g["status"],
            "Signal": g["signal"],
        })

    df = pd.DataFrame(rows)
    df["Start"] = pd.to_datetime(df["Start"], errors="coerce")
    df["End"] = pd.to_datetime(df["End"], errors="coerce")
    df = df.dropna(subset=["Start", "End"])

    if df.empty:
        st.info("No valid date ranges for Gantt chart.")
        return

    phase_colors = {
        "EARLY_PHASE1": "#a6cee3",
        "PHASE1": "#1f78b4",
        "PHASE2": "#b2df8a",
        "PHASE3": "#33a02c",
        "PHASE4": "#ff7f00",
        "NA": "#cab2d6",
        "UNKNOWN": "#999999",
    }

    fig = px.timeline(
        df, x_start="Start", x_end="End", y="Trial",
        color="Phase", color_discrete_map=phase_colors,
        hover_data=["Status", "Signal"],
    )
    fig.update_layout(
        height=max(400, len(df) * 22),
        margin=dict(t=20, b=20, l=10),
        yaxis=dict(autorange="reversed"),
    )
    st.plotly_chart(fig, width="stretch")

