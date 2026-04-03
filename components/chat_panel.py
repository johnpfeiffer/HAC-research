"""Chat interface component using st.chat_message."""

import asyncio

import streamlit as st
from graph.chat import chat as chat_fn
from services.supabase_client import get_client, get_messages


SUGGESTED_QUESTIONS = [
    "Which Phase 3 trials have positive investment signals?",
    "What are the main safety concerns across these trials?",
    "Which sponsors are most active in this space?",
    "Summarize the competitive landscape for the top drugs.",
    "Which trials have the strongest efficacy data?",
]


def render_chat_panel(session_id: str, aggregate: dict):
    """Render the chat interface for investment Q&A."""
    st.subheader("Investment Q&A")

    # Load existing messages
    sb = get_client()
    messages = get_messages(sb, session_id)

    # Display chat history
    for msg in messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    # Suggested questions (only show if no messages yet)
    if not messages:
        st.markdown("**Suggested questions:**")
        cols = st.columns(2)
        for i, q in enumerate(SUGGESTED_QUESTIONS):
            col = cols[i % 2]
            if col.button(q, key=f"suggested_{i}"):
                st.session_state["pending_question"] = q
                st.rerun()

    # Check for pending question from suggested buttons
    pending = st.session_state.pop("pending_question", None)

    # Chat input
    user_input = st.chat_input("Ask about these clinical trials...")

    question = pending or user_input
    if question:
        # Show user message
        with st.chat_message("user"):
            st.markdown(question)

        # Get response
        with st.chat_message("assistant"):
            with st.spinner("Thinking..."):
                response = asyncio.run(chat_fn(session_id, question, aggregate))
            st.markdown(response)
