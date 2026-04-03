"""Dashboard charts: phase pie, status bar, sponsor table, signal breakdown."""

import streamlit as st
import plotly.express as px
import pandas as pd


def render_dashboard(aggregate: dict, trials: list[dict], insights: list[dict]):
    """Render the full dashboard from aggregate stats."""
    if not aggregate:
        st.warning("No data to display.")
        return

    # Metric cards
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total Trials", aggregate.get("total_trials", 0))
    col2.metric("With Results", aggregate.get("trials_with_results", 0))
    col3.metric("Positive Signals", aggregate.get("positive_signals", 0))
    col4.metric("Total Enrollment", f"{aggregate.get('total_enrollment', 0):,}")

    st.divider()

    # Charts row
    chart_col1, chart_col2 = st.columns(2)

    with chart_col1:
        st.subheader("Phase Distribution")
        phase_data = aggregate.get("phase_distribution", {})
        if phase_data:
            fig = px.pie(
                names=list(phase_data.keys()),
                values=list(phase_data.values()),
                hole=0.3,
            )
            fig.update_layout(margin=dict(t=20, b=20, l=20, r=20))
            st.plotly_chart(fig, width="stretch")

    with chart_col2:
        st.subheader("Investment Signals")
        signal_data = aggregate.get("signal_distribution", {})
        if signal_data:
            colors = {
                "POSITIVE": "#2ecc71",
                "NEUTRAL": "#f39c12",
                "NEGATIVE": "#e74c3c",
                "INSUFFICIENT_DATA": "#95a5a6",
            }
            fig = px.pie(
                names=list(signal_data.keys()),
                values=list(signal_data.values()),
                hole=0.3,
                color=list(signal_data.keys()),
                color_discrete_map=colors,
            )
            fig.update_layout(margin=dict(t=20, b=20, l=20, r=20))
            st.plotly_chart(fig, width="stretch")

    # Status bar chart
    st.subheader("Trial Status Distribution")
    status_data = aggregate.get("status_distribution", {})
    if status_data:
        df = pd.DataFrame(
            [{"Status": k, "Count": v} for k, v in status_data.items()]
        )
        fig = px.bar(df, x="Status", y="Count", color="Status")
        fig.update_layout(showlegend=False, margin=dict(t=20, b=20))
        st.plotly_chart(fig, width="stretch")

    # Top sponsors table
    col_left, col_right = st.columns(2)

    with col_left:
        st.subheader("Top Sponsors")
        sponsors = aggregate.get("top_sponsors", [])
        if sponsors:
            df = pd.DataFrame(sponsors)
            st.dataframe(df, width="stretch", hide_index=True)

    with col_right:
        st.subheader("Top Drugs")
        drugs = aggregate.get("top_drugs", [])
        if drugs:
            df = pd.DataFrame(drugs)
            st.dataframe(df, width="stretch", hide_index=True)

    # Sponsor class distribution
    st.subheader("Sponsor Class Distribution")
    sc_data = aggregate.get("sponsor_class_distribution", {})
    if sc_data:
        fig = px.pie(
            names=list(sc_data.keys()),
            values=list(sc_data.values()),
            hole=0.3,
        )
        fig.update_layout(margin=dict(t=20, b=20, l=20, r=20))
        st.plotly_chart(fig, width="stretch")
