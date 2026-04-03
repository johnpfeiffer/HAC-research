"""Chat graph node for investment Q&A powered by MiniMax."""

from services.llm import get_llm
from services.supabase_client import (
    get_client,
    get_trials,
    get_insights,
    get_messages,
    insert_message,
)
from prompts.chat_system import build_chat_system_prompt


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
    sb = get_client()

    # Save user message
    insert_message(sb, session_id, "user", user_message)

    # Load context
    trials = get_trials(sb, session_id)
    insights = get_insights(sb, session_id)
    history = get_messages(sb, session_id)

    # Build system prompt with full context
    system_prompt = build_chat_system_prompt(aggregate, insights, trials)

    # Build message list
    messages = [{"role": "system", "content": system_prompt}]
    for msg in history:
        messages.append({"role": msg["role"], "content": msg["content"]})

    # Call LLM
    llm = get_llm(temperature=0.3)
    response = await llm.ainvoke(messages)
    assistant_text = response.content

    # Save assistant message
    insert_message(sb, session_id, "assistant", assistant_text)

    return assistant_text
