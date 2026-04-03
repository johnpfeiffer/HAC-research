"""Sortable and filterable trial list component."""

import streamlit as st
import pandas as pd


def render_trial_table(trials: list[dict], insights: list[dict]):
    """Render a filterable trial table with expandable details."""
    if not trials:
        st.info("No trials to display.")
        return

    # Build insight lookup
    insight_map = {i.get("trial_id"): i for i in insights}

    # Build display dataframe
    rows = []
    for t in trials:
        ins = insight_map.get(t["id"], {})
        rows.append({
            "NCT ID": t.get("nct_id", ""),
            "Title": t.get("brief_title", ""),
            "Phase": t.get("phase", "N/A"),
            "Status": t.get("overall_status", "N/A"),
            "Sponsor": t.get("sponsor_name", "N/A"),
            "Sponsor Class": t.get("sponsor_class", "N/A"),
            "Enrollment": t.get("enrollment_count") or 0,
            "Has Results": "Yes" if t.get("has_results") else "No",
            "Signal": ins.get("investment_signal", "N/A"),
            "Drugs": ", ".join(ins.get("drug_names") or []) or "N/A",
        })

    df = pd.DataFrame(rows).fillna("N/A")

    # Filters
    st.subheader("Trial Details")
    filter_col1, filter_col2, filter_col3 = st.columns(3)

    with filter_col1:
        phase_filter = st.multiselect(
            "Filter by phase",
            options=sorted(df["Phase"].unique().tolist()),
            key="trial_phase_filter",
        )
    with filter_col2:
        signal_filter = st.multiselect(
            "Filter by signal",
            options=sorted(df["Signal"].unique().tolist()),
            key="trial_signal_filter",
        )
    with filter_col3:
        sponsor_filter = st.multiselect(
            "Filter by sponsor class",
            options=sorted(df["Sponsor Class"].unique().tolist()),
            key="trial_sponsor_filter",
        )

    filtered = df.copy()
    if phase_filter:
        filtered = filtered[filtered["Phase"].isin(phase_filter)]
    if signal_filter:
        filtered = filtered[filtered["Signal"].isin(signal_filter)]
    if sponsor_filter:
        filtered = filtered[filtered["Sponsor Class"].isin(sponsor_filter)]

    st.dataframe(
        filtered,
        width="stretch",
        hide_index=True,
        column_config={
            "Title": st.column_config.TextColumn(width="large"),
            "Enrollment": st.column_config.NumberColumn(format="%d"),
        },
    )

    # Expandable detail for each trial
    st.subheader("Trial Insights")
    for _, row in filtered.iterrows():
        nct_id = row["NCT ID"]
        matching_trial = next((t for t in trials if t.get("nct_id") == nct_id), None)
        if not matching_trial:
            continue
        ins = insight_map.get(matching_trial["id"], {})
        if not ins:
            continue

        with st.expander(f"{nct_id} — {row['Title'][:60]}..."):
            col1, col2 = st.columns(2)
            with col1:
                st.markdown(f"**Signal:** {ins.get('investment_signal', 'N/A')}")
                st.markdown(f"**Drugs:** {', '.join(ins.get('drug_names') or [])}")
                st.markdown(f"**Mechanism:** {ins.get('mechanism_of_action', 'N/A')}")
                st.markdown(f"**Efficacy:** {ins.get('efficacy_summary', 'N/A')}")
            with col2:
                st.markdown(f"**Safety:** {ins.get('safety_summary', 'N/A')}")
                st.markdown(f"**Rationale:** {ins.get('investment_rationale', 'N/A')}")
                st.markdown(f"**Competitive:** {ins.get('competitive_notes', 'N/A')}")
                st.markdown(f"**Serious AEs:** {ins.get('serious_ae_count', 0)}")
