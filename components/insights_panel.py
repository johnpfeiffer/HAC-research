"""Always-visible insights panel: headline pick, investor/patient/pharma insights, opportunities."""

import logging

import streamlit as st

logger = logging.getLogger(__name__)


def render_insights_panel(aggregate: dict, trials: list[dict], insights: list[dict]):
    """Render all insights in a single top-down layout above the tabs."""
    if not aggregate:
        return

    logger.debug("Rendering insights panel")

    # --- Headline: Most Investable Company ---
    most = aggregate.get("most_investable", {})
    if most:
        st.markdown(
            f'<div style="background:linear-gradient(135deg,#1a1a2e,#16213e);padding:24px 32px;'
            f'border-radius:12px;margin-bottom:16px;">'
            f'<p style="color:#8892b0;font-size:14px;margin:0 0 4px 0;">MOST INVESTABLE</p>'
            f'<p style="color:#e6f1ff;font-size:32px;font-weight:700;margin:0 0 8px 0;">{most["company"]}</p>'
            f'<p style="color:#a8b2d1;font-size:16px;margin:0;">{most.get("reason", "")}</p>'
            f'</div>',
            unsafe_allow_html=True,
        )

    # --- Investor Insights ---
    st.markdown("### Investor Insights")
    _render_investor(aggregate, insights)

    st.divider()

    # --- Patient Insights ---
    st.markdown("### Patient Insights")
    _render_patient(aggregate, trials, insights)

    st.divider()

    # --- Big Pharma Insights ---
    st.markdown("### Big Pharma Insights")
    _render_pharma(aggregate, trials, insights)

    st.divider()

    # --- Opportunity Analysis ---
    st.markdown("### Opportunity Analysis")
    _render_opportunities(aggregate)


def _render_investor(aggregate: dict, insights: list[dict]):
    total = aggregate.get("total_trials", 0)
    pos = aggregate.get("positive_signals", 0)
    neg = aggregate.get("negative_signals", 0)
    with_results = aggregate.get("trials_with_results", 0)
    unique_sponsors = aggregate.get("unique_sponsors", 0)
    phase_dist = aggregate.get("phase_distribution", {})
    late_stage = phase_dist.get("PHASE3", 0) + phase_dist.get("PHASE4", 0)

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Positive Signals", pos)
    c2.metric("Late-Stage (Ph3/4)", late_stage)
    c3.metric("With Results", with_results)
    c4.metric("Unique Sponsors", unique_sponsors)

    points = []
    if total > 0:
        hit_rate = pos / total * 100
        points.append(f"**Signal hit rate:** {hit_rate:.0f}% of trials show positive investment signals ({pos}/{total})")
    if late_stage > 0:
        points.append(f"**Late-stage pipeline:** {late_stage} trials in Phase 3/4 — nearer to potential market")
    elif total > 0:
        points.append("**No late-stage trials** — entirely early-stage pipeline, higher risk profile")
    if with_results > 0:
        points.append(f"**Data availability:** {with_results} trials have published results for due diligence")
    concentration = aggregate.get("top_sponsors", [])
    if concentration and concentration[0]["count"] > total * 0.3:
        points.append(f"**Concentration risk:** {concentration[0]['name']} holds {concentration[0]['count']}/{total} trials")
    elif unique_sponsors > 5:
        points.append(f"**Competitive space:** {unique_sponsors} unique sponsors — diversified interest")
    top_drugs = aggregate.get("top_drugs", [])
    if top_drugs:
        points.append(f"**Leading candidates:** {', '.join(d['name'] for d in top_drugs[:3])}")
    pos_trials = [i for i in insights if i.get("investment_signal") == "POSITIVE"]
    if pos_trials:
        points.append(f"**Actionable leads:** {len(pos_trials)} trials warrant deeper analysis")

    for p in points:
        st.markdown(f"- {p}")


def _render_patient(aggregate: dict, trials: list[dict], insights: list[dict]):
    status_dist = aggregate.get("status_distribution", {})
    recruiting = status_dist.get("RECRUITING", 0) + status_dist.get("NOT_YET_RECRUITING", 0)
    total_enrollment = aggregate.get("total_enrollment", 0)

    c1, c2, c3 = st.columns(3)
    c1.metric("Recruiting Trials", recruiting)
    c2.metric("Total Enrollment", f"{total_enrollment:,}")
    c3.metric("Total Trials", aggregate.get("total_trials", 0))

    points = []
    if recruiting > 0:
        points.append(f"**{recruiting} trials actively recruiting** — patients may be eligible to enroll")
    else:
        points.append("**No trials currently recruiting** in this search")
    phase_dist = aggregate.get("phase_distribution", {})
    phase3_4 = phase_dist.get("PHASE3", 0) + phase_dist.get("PHASE4", 0)
    if phase3_4 > 0:
        points.append(f"**{phase3_4} late-stage trials** (Phase 3/4) — treatments closer to approval")
    if insights:
        neg_safety = sum(1 for i in insights if "concern" in (i.get("safety_summary") or "").lower())
        safe_count = len(insights) - neg_safety
        points.append(f"**Safety profile:** {safe_count}/{len(insights)} analyzed trials show manageable safety")
    top_drugs = aggregate.get("top_drugs", [])
    if top_drugs:
        points.append(f"**Drugs under investigation:** {', '.join(d['name'] for d in top_drugs[:5])}")
    sc = aggregate.get("sponsor_class_distribution", {})
    nih = sc.get("NIH", 0) + sc.get("OTHER_GOV", 0)
    industry = sc.get("INDUSTRY", 0)
    if nih > 0:
        points.append(f"**{nih} publicly-funded trials** (NIH/government) alongside {industry} industry-sponsored")

    for p in points:
        st.markdown(f"- {p}")


def _render_pharma(aggregate: dict, trials: list[dict], insights: list[dict]):
    unique_sponsors = aggregate.get("unique_sponsors", 0)
    phase_dist = aggregate.get("phase_distribution", {})
    moa_clusters = aggregate.get("moa_clusters", [])

    c1, c2, c3 = st.columns(3)
    c1.metric("Competitors", unique_sponsors)
    c2.metric("Distinct Mechanisms", len(moa_clusters))
    c3.metric("Phase 2+ Trials", phase_dist.get("PHASE2", 0) + phase_dist.get("PHASE3", 0) + phase_dist.get("PHASE4", 0))

    points = []
    sponsors = aggregate.get("top_sponsors", [])
    if sponsors:
        points.append(f"**Market leader:** {sponsors[0]['name']} with {sponsors[0]['count']} trials")
        if len(sponsors) > 1:
            points.append(f"**Runner-up:** {sponsors[1]['name']} ({sponsors[1]['count']} trials)")
    if len(moa_clusters) >= 3:
        points.append(f"**Dominant mechanism:** {moa_clusters[0]['mechanism'][:50]} — consider differentiation via novel MOA")
    elif len(moa_clusters) == 1:
        points.append("**Single mechanism space** — first-mover advantage for alternative approaches")
    early = phase_dist.get("PHASE1", 0) + phase_dist.get("EARLY_PHASE1", 0)
    mid = phase_dist.get("PHASE2", 0)
    late = phase_dist.get("PHASE3", 0) + phase_dist.get("PHASE4", 0)
    if early > late * 3 and early > 5:
        points.append(f"**Pipeline-heavy:** {early} early-stage vs {late} late-stage — high attrition expected, partnership opportunities")
    if mid > 0 and late == 0:
        points.append(f"**Phase 2 bottleneck:** {mid} trials in Phase 2, none advanced to Phase 3 — potential licensing targets")
    declining = aggregate.get("declining_trials", [])
    if len(declining) > 3:
        points.append(f"**{len(declining)} terminated/withdrawn trials** — potential asset acquisition or lessons learned")
    progressing = aggregate.get("progressing_trials", [])
    if len(progressing) > 10:
        total_enroll = aggregate.get("total_enrollment", 0)
        points.append(f"**Patient competition:** {len(progressing)} active trials competing for ~{total_enroll:,} patients")

    for p in points:
        st.markdown(f"- {p}")


def _render_opportunities(aggregate: dict):
    phase_dist = aggregate.get("phase_distribution", {})
    signal_dist = aggregate.get("signal_distribution", {})
    sponsors = aggregate.get("top_sponsors", [])
    moa_clusters = aggregate.get("moa_clusters", [])
    progressing = len(aggregate.get("progressing_trials", []))
    declining = len(aggregate.get("declining_trials", []))

    observations = []

    late_stage = phase_dist.get("PHASE3", 0) + phase_dist.get("PHASE4", 0)
    early_stage = phase_dist.get("PHASE1", 0) + phase_dist.get("EARLY_PHASE1", 0)
    if late_stage == 0 and early_stage > 0:
        observations.append("No Phase 3/4 trials exist — entirely early-stage, high risk but potential first-mover advantage.")
    elif late_stage > 0 and early_stage > late_stage * 2:
        observations.append(f"Pipeline-heavy: {early_stage} early-stage vs {late_stage} late-stage. Many may not advance.")

    if sponsors and sponsors[0]["count"] > aggregate.get("total_trials", 1) * 0.3:
        observations.append(f"**{sponsors[0]['name']}** dominates ({sponsors[0]['count']*100//max(aggregate.get('total_trials',1),1)}% of trials). High concentration risk.")

    pos = signal_dist.get("POSITIVE", 0)
    neg = signal_dist.get("NEGATIVE", 0)
    if pos > neg * 2 and pos > 3:
        observations.append(f"Strong positive signal density ({pos} positive vs {neg} negative) — multiple viable candidates.")
    elif neg > pos and neg > 3:
        observations.append(f"Challenging space: {neg} negative vs {pos} positive. High failure rate suggests difficult biology.")

    if declining > progressing and declining > 3:
        observations.append(f"More declining ({declining}) than progressing ({progressing}). Space may be cooling off.")
    elif progressing > declining * 2:
        observations.append(f"Active space with {progressing} progressing trials — strong current interest.")

    if len(moa_clusters) >= 5:
        observations.append(f"Diverse landscape: {len(moa_clusters)}+ distinct mechanisms. No single MOA dominates.")
    elif len(moa_clusters) == 1:
        observations.append(f"Single dominant mechanism: **{moa_clusters[0]['mechanism'][:50]}**. Alternatives could differentiate.")

    starts = aggregate.get("starts_by_year", {})
    if starts:
        years = sorted(starts.keys())
        if len(years) >= 2:
            recent = sum(starts.get(y, 0) for y in years[-2:])
            older = sum(starts.get(y, 0) for y in years[:-2])
            if recent > older and recent > 5:
                observations.append(f"Accelerating: {recent} trials in last 2 years vs {older} before.")
            elif older > recent * 2:
                observations.append(f"Declining activity: only {recent} recent starts vs {older} historically.")

    if not observations:
        observations.append("Insufficient data to identify clear opportunities. Consider broadening the search.")

    for obs in observations:
        st.markdown(f"- {obs}")
