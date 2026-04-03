"""Sortable and filterable trial list component with patient info and KOLs."""

import logging

import streamlit as st
import pandas as pd

logger = logging.getLogger(__name__)


def _extract_investigators(raw_json: dict) -> list[dict]:
    """Extract investigators from trial raw JSON."""
    protocol = raw_json.get("protocolSection", {})
    contacts = protocol.get("contactsLocationsModule", {})
    officials = contacts.get("overallOfficials", [])
    return [
        {"name": o.get("name", ""), "role": o.get("role", ""), "affiliation": o.get("affiliation", "")}
        for o in officials
    ]


def _extract_eligibility(raw_json: dict) -> dict:
    """Extract eligibility info from trial raw JSON."""
    protocol = raw_json.get("protocolSection", {})
    elig = protocol.get("eligibilityModule", {})
    return {
        "criteria": elig.get("eligibilityCriteria", ""),
        "sex": elig.get("sex", "ALL"),
        "min_age": elig.get("minimumAge", "N/A"),
        "max_age": elig.get("maximumAge", "N/A"),
        "healthy_volunteers": elig.get("healthyVolunteers", False),
    }


def render_trial_table(trials: list[dict], insights: list[dict]):
    """Render a filterable trial table with expandable details."""
    logger.debug("Rendering trial table: %d trials, %d insights", len(trials), len(insights))
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

        with st.expander(f"{nct_id} — {row['Title'][:60]}"):
            # --- Investment Analysis ---
            st.markdown("#### Investment Analysis")
            ic1, ic2 = st.columns(2)
            with ic1:
                signal = ins.get("investment_signal", "N/A") if ins else "N/A"
                signal_colors = {"POSITIVE": "green", "NEGATIVE": "red", "NEUTRAL": "orange", "INSUFFICIENT_DATA": "gray"}
                color = signal_colors.get(signal, "gray")
                st.markdown(f"**Signal:** :{color}[{signal}]")
                st.markdown(f"**Drugs:** {', '.join(ins.get('drug_names') or []) if ins else 'N/A'}")
                st.markdown(f"**Mechanism:** {ins.get('mechanism_of_action', 'N/A') if ins else 'N/A'}")
                st.markdown(f"**Efficacy:** {ins.get('efficacy_summary', 'N/A') if ins else 'N/A'}")
            with ic2:
                st.markdown(f"**Safety:** {ins.get('safety_summary', 'N/A') if ins else 'N/A'}")
                st.markdown(f"**Rationale:** {ins.get('investment_rationale', 'N/A') if ins else 'N/A'}")
                st.markdown(f"**Competitive:** {ins.get('competitive_notes', 'N/A') if ins else 'N/A'}")
                st.markdown(f"**Serious AEs:** {ins.get('serious_ae_count', 0) if ins else 0}")

            # --- Patient Population ---
            st.markdown("#### Patient Population")
            raw_json = matching_trial.get("raw_json", {})
            elig = _extract_eligibility(raw_json)
            patient_pop = ins.get("patient_population", "") if ins else ""

            pc1, pc2 = st.columns(2)
            with pc1:
                if patient_pop:
                    st.markdown(f"**AI Summary:** {patient_pop}")
                st.markdown(f"**Sex:** {elig['sex']}  |  **Age:** {elig['min_age']} — {elig['max_age']}")
                st.markdown(f"**Healthy Volunteers:** {'Yes' if elig['healthy_volunteers'] else 'No'}")
            with pc2:
                criteria_text = elig["criteria"]
                if criteria_text:
                    # Show first 500 chars with option to see full
                    if len(criteria_text) > 500:
                        st.text_area("Eligibility Criteria", criteria_text, height=150, disabled=True, key=f"elig_{nct_id}")
                    else:
                        st.markdown(f"**Criteria:** {criteria_text}")

            # --- Key Opinion Leaders / Investigators ---
            investigators = _extract_investigators(raw_json)
            if investigators:
                st.markdown("#### Key Investigators")
                for inv in investigators:
                    role_label = inv["role"].replace("_", " ").title() if inv["role"] else "Investigator"
                    affil = f" — {inv['affiliation']}" if inv["affiliation"] else ""
                    st.markdown(f"- **{inv['name']}** ({role_label}){affil}")
