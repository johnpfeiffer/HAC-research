"""Addressable market analysis component using Exa AI."""

import streamlit as st
from services.exa_client import get_exa_client, search_market_data, search_with_contents


MARKET_QUERY_TEMPLATES = [
    "{disease} market size forecast 2025",
    "{disease} patient population prevalence global",
    "{disease} drug market revenue analysis",
    "{disease} treatment landscape competitive analysis",
    "{disease} unmet medical need market opportunity",
]


def render_addressable_market(session_id: str, aggregate: dict, trials: list[dict]):
    """Render addressable market analysis using Exa AI."""
    st.subheader("Addressable Market Analysis")

    # Check if Exa is configured
    client = get_exa_client()
    if not client:
        st.error("Exa AI is not configured. Please add EXA_API_KEY to your .env file.")
        st.info("The Exa API is used to search for market research, patient population data, and competitive intelligence.")
        return

    # Get disease keyword from session
    from services.supabase_client import get_client, get_session
    sb = get_client()
    session = get_session(sb, session_id)
    disease_keyword = session.get("disease_keyword", "")

    if not disease_keyword:
        st.warning("No disease keyword found for this session.")
        return

    st.markdown(f"**Analyzing market for:** `{disease_keyword}`")
    st.divider()

    # --- Quick Stats Overview ---
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Total Trials", aggregate.get("total_trials", 0))
    with col2:
        st.metric("Industry Sponsored", aggregate.get("industry_trials", 0))
    with col3:
        total_enrollment = aggregate.get("total_enrollment", 0)
        st.metric("Total Enrollment", f"{total_enrollment:,}" if total_enrollment else "N/A")

    st.divider()

    # --- Search Interface ---
    st.markdown("### 🔍 Market Intelligence Search")

    # Suggested searches
    st.markdown("**Suggested searches:**")
    cols = st.columns(3)
    for i, template in enumerate(MARKET_QUERY_TEMPLATES):
        query = template.format(disease=disease_keyword)
        col = cols[i % 3]
        if col.button(query, key=f"market_search_{i}", use_container_width=True):
            st.session_state["market_query"] = query
            st.rerun()

    # Custom search
    custom_query = st.text_input(
        "Or enter a custom search query:",
        placeholder=f"e.g., {disease_keyword} emerging therapies 2025",
        value=st.session_state.get("market_query", ""),
    )

    num_results = st.slider("Number of results", min_value=3, max_value=15, value=8)

    search_button = st.button("Search Market Data", type="primary")

    # Execute search
    if search_button and custom_query:
        st.session_state["market_query"] = custom_query
        st.session_state["last_results"] = None  # Clear previous results

    query_to_search = st.session_state.get("market_query", "")

    if query_to_search:
        # Cache results in session state to avoid re-running
        cache_key = f"results_{hash(query_to_search)}_{num_results}"

        if cache_key not in st.session_state:
            with st.spinner(f"Searching for: {query_to_search}..."):
                results = search_market_data(
                    query_to_search,
                    num_results=num_results,
                    use_autoprompt=True,
                )
                st.session_state[cache_key] = results
        else:
            results = st.session_state[cache_key]

        if results:
            st.success(f"Found {len(results)} results")
            st.divider()

            # Display results
            st.markdown("### 📊 Search Results")

            for i, result in enumerate(results, 1):
                with st.container():
                    col_rank, col_content = st.columns([0.5, 9.5])

                    with col_rank:
                        st.markdown(f"**#{i}**")
                        if result.get("score"):
                            st.caption(f"Score: {result['score']:.3f}")

                    with col_content:
                        st.markdown(f"**[{result['title']}]({result['url']})**")

                        if result.get("published_date"):
                            st.caption(f"📅 Published: {result['published_date']}")

                        # Add "Get Summary" button for each result
                        if st.button(f"Get Summary", key=f"summary_{i}"):
                            with st.spinner("Fetching content..."):
                                detailed = search_with_contents(
                                    result['url'],
                                    num_results=1,
                                    use_autoprompt=False,
                                )
                                if detailed and detailed[0].get("text"):
                                    with st.expander("📄 Content Summary", expanded=True):
                                        text = detailed[0]["text"]
                                        # Truncate if too long
                                        if len(text) > 2000:
                                            text = text[:2000] + "..."
                                        st.markdown(text)
                                else:
                                    st.warning("Could not fetch content for this URL.")

                    st.divider()

        elif query_to_search:
            st.warning("No results found. Try a different query.")

    # --- Market Context from Trials ---
    st.divider()
    st.markdown("### 💡 Trial-Based Market Context")

    # Show top sponsors (these are the market players)
    col_left, col_right = st.columns(2)

    with col_left:
        st.markdown("**Key Market Players**")
        top_sponsors = aggregate.get("top_sponsors", [])
        if top_sponsors:
            for sponsor in top_sponsors[:8]:
                st.markdown(f"- **{sponsor['name']}** ({sponsor['count']} trials)")
        else:
            st.info("No sponsor data available.")

    with col_right:
        st.markdown("**Top Investigated Drugs**")
        top_drugs = aggregate.get("top_drugs", [])
        if top_drugs:
            for drug in top_drugs[:8]:
                st.markdown(f"- **{drug['name']}** ({drug['count']} trials)")
        else:
            st.info("No drug data available.")

    # Investment signals distribution
    st.markdown("**Investment Signal Distribution**")
    signal_dist = aggregate.get("signal_distribution", {})
    if signal_dist:
        col_pos, col_neu, col_neg, col_insuff = st.columns(4)
        col_pos.metric("🟢 Positive", signal_dist.get("POSITIVE", 0))
        col_neu.metric("🟡 Neutral", signal_dist.get("NEUTRAL", 0))
        col_neg.metric("🔴 Negative", signal_dist.get("NEGATIVE", 0))
        col_insuff.metric("⚪ Insufficient Data", signal_dist.get("INSUFFICIENT_DATA", 0))
    else:
        st.info("No signal distribution data.")

    # Market opportunity insights
    st.divider()
    st.markdown("### 🎯 Market Opportunity Insights")

    with st.expander("View Analysis", expanded=False):
        insights = []

        # Analyze trial phase distribution
        phase_dist = aggregate.get("phase_distribution", {})
        late_stage = phase_dist.get("PHASE3", 0) + phase_dist.get("PHASE4", 0)
        total = aggregate.get("total_trials", 0)

        if late_stage > 0 and total > 0:
            late_pct = (late_stage / total) * 100
            insights.append(
                f"**Late-stage pipeline:** {late_stage} Phase 3/4 trials ({late_pct:.0f}% of total) "
                f"indicate near-term market potential."
            )

        # Analyze investment signals
        positive_signals = signal_dist.get("POSITIVE", 0)
        if positive_signals > 0 and total > 0:
            pos_pct = (positive_signals / total) * 100
            insights.append(
                f"**Positive signals:** {positive_signals} trials ({pos_pct:.0f}%) show positive investment signals, "
                f"suggesting viable therapeutic opportunities."
            )

        # Enrollment as market indicator
        total_enrollment = aggregate.get("total_enrollment", 0)
        if total_enrollment > 1000:
            insights.append(
                f"**Large patient pool:** {total_enrollment:,} patients enrolled across trials "
                f"indicates significant clinical development investment."
            )

        # Industry interest
        industry_trials = sum(
            1 for t in trials if t.get("sponsor_class") == "INDUSTRY"
        )
        if industry_trials > 0 and total > 0:
            ind_pct = (industry_trials / total) * 100
            insights.append(
                f"**Commercial interest:** {industry_trials} industry-sponsored trials ({ind_pct:.0f}%) "
                f"demonstrates strong market validation."
            )

        if insights:
            for insight in insights:
                st.markdown(f"- {insight}")
        else:
            st.info("Insufficient data for market opportunity analysis.")
