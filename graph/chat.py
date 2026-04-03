"""Chat graph node for investment Q&A powered by MiniMax."""

import logging

from services.llm import get_llm
from services.supabase_client import (
    get_client,
    get_trials,
    get_insights,
    get_messages,
    insert_message,
)
from prompts.chat_system import build_chat_system_prompt

logger = logging.getLogger(__name__)


async def chat(session_id: str, user_message: str, aggregate: dict) -> str:
    """
    Process a user chat message and return the assistant response.

    Args:
        session_id: The search session ID for context.
        user_message: The user's question.
        aggregate: Pre-computed aggregate stats dict.

    Returns:
        Assistant response string.
    """
    logger.info("Chat request: session=%s, message_len=%d", session_id, len(user_message))
    sb = get_client()

    # Save user message
    insert_message(sb, session_id, "user", user_message)

    # Load context
    trials = get_trials(sb, session_id)
    insights = get_insights(sb, session_id)
    history = get_messages(sb, session_id)
    logger.debug("Chat context: %d trials, %d insights, %d history messages", len(trials), len(insights), len(history))

    # Build system prompt with full context
    system_prompt = build_chat_system_prompt(aggregate, insights, trials)

    # Build message list
    messages = [{"role": "system", "content": system_prompt}]
    for msg in history:
        messages.append({"role": msg["role"], "content": msg["content"]})

    # Call LLM
    logger.debug("Invoking LLM with %d messages", len(messages))
    llm = get_llm(temperature=0.3)
    response = await llm.ainvoke(messages)
    assistant_text = response.content
    logger.info("Chat response generated: len=%d", len(assistant_text))

    # Save assistant message
    insert_message(sb, session_id, "assistant", assistant_text)

    return assistant_text
