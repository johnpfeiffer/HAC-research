"""Competitive dynamics dashboard component."""

import streamlit as st
import plotly.express as px
import plotly.figure_factory as ff
import pandas as pd


def render_competitive(aggregate: dict, trials: list[dict], insights: list[dict]):
    """Render competitive dynamics dashboard."""
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

    # --- Row 4: MOA groups (LLM-condensed) + raw MOA clusters ---
    st.subheader("Mechanisms of Action")
    col5, col6 = st.columns(2)

    with col5:
        st.markdown("**Grouped (AI-synthesized)**")
        moa_groups = aggregate.get("moa_groups", [])
        if moa_groups:
            df = pd.DataFrame(moa_groups)
            if "group" in df.columns and "count" in df.columns:
                fig = px.bar(df, y="group", x="count", orientation="h",
                             color="group", color_discrete_sequence=px.colors.qualitative.Pastel)
                fig.update_layout(
                    yaxis=dict(categoryorder="total ascending"),
                    margin=dict(t=20, b=20, l=10), showlegend=False,
                )
                st.plotly_chart(fig, width="stretch")

                # Show which MOAs are in each group
                for g in moa_groups:
                    with st.expander(f"{g.get('group', 'Unknown')} ({g.get('count', 0)} trials)"):
                        for m in g.get("moas", []):
                            st.markdown(f"- {m}")
            else:
                st.info("MOA grouping data format unexpected.")
        else:
            st.info("No grouped MOA data — will appear on new searches.")

    with col6:
        st.markdown("**Raw Mechanisms (ungrouped)**")
        moa = aggregate.get("moa_clusters", [])
        if moa:
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

    st.divider()

    # --- Row 6: Opportunity analysis ---
    st.subheader("Opportunity Analysis")
    _render_opportunities(aggregate)


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


def _render_opportunities(aggregate: dict):
    """Render opportunity analysis based on gaps in the data."""
    phase_dist = aggregate.get("phase_distribution", {})
    signal_dist = aggregate.get("signal_distribution", {})
    sponsors = aggregate.get("top_sponsors", [])
    moa_clusters = aggregate.get("moa_clusters", [])
    moa_groups = aggregate.get("moa_groups", [])
    progressing = len(aggregate.get("progressing_trials", []))
    declining = len(aggregate.get("declining_trials", []))

    observations = []

    # Phase gap analysis
    late_stage = phase_dist.get("PHASE3", 0) + phase_dist.get("PHASE4", 0)
    early_stage = phase_dist.get("PHASE1", 0) + phase_dist.get("EARLY_PHASE1", 0)
    if late_stage == 0 and early_stage > 0:
        observations.append("No Phase 3/4 trials exist — the space is entirely early-stage, representing high risk but potential first-mover advantage.")
    elif late_stage > 0 and early_stage > late_stage * 2:
        observations.append(f"Pipeline-heavy space: {early_stage} early-stage vs {late_stage} late-stage trials. Many candidates may not advance.")

    # Concentration risk
    if sponsors and sponsors[0]["count"] > aggregate.get("total_trials", 1) * 0.3:
        observations.append(f"**{sponsors[0]['name']}** dominates with {sponsors[0]['count']} trials ({sponsors[0]['count']*100//max(aggregate.get('total_trials',1),1)}% of total). High concentration risk.")

    # Signal balance
    pos = signal_dist.get("POSITIVE", 0)
    neg = signal_dist.get("NEGATIVE", 0)
    if pos > neg * 2 and pos > 3:
        observations.append(f"Strong positive signal density ({pos} positive vs {neg} negative) — multiple viable candidates.")
    elif neg > pos and neg > 3:
        observations.append(f"Challenging space: {neg} negative vs {pos} positive signals. High failure rate suggests difficult biology.")

    # Momentum
    if declining > progressing and declining > 3:
        observations.append(f"More trials declining ({declining}) than progressing ({progressing}). The space may be cooling off.")
    elif progressing > declining * 2:
        observations.append(f"Active space with {progressing} progressing trials — strong current interest.")

    # MOA diversity (use grouped if available)
    moa_count = len(moa_groups) if moa_groups else len(moa_clusters)
    if moa_count >= 5:
        observations.append(f"Diverse approach landscape with {moa_count}+ distinct mechanism categories. No single MOA dominates.")
    elif moa_count == 1:
        name = moa_groups[0]["group"] if moa_groups else (moa_clusters[0]["mechanism"] if moa_clusters else "unknown")
        observations.append(f"Single dominant mechanism: **{name}**. Alternative approaches could be differentiated.")

    # Timeline insights
    starts = aggregate.get("starts_by_year", {})
    if starts:
        years = sorted(starts.keys())
        if len(years) >= 2:
            recent = sum(starts.get(y, 0) for y in years[-2:])
            older = sum(starts.get(y, 0) for y in years[:-2])
            if recent > older and recent > 5:
                observations.append(f"Accelerating interest: {recent} trials started in the last 2 years vs {older} before that.")
            elif older > recent * 2:
                observations.append(f"Activity may be declining: only {recent} recent starts vs {older} historically.")

    if not observations:
        observations.append("Insufficient data to identify clear opportunities. Consider broadening the search.")

    for obs in observations:
        st.markdown(f"- {obs}")
