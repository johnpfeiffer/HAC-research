"""MiniMax LLM setup via LangChain's ChatOpenAI."""

import os

from dotenv import load_dotenv
from langchain_openai import ChatOpenAI

load_dotenv()


def get_llm(temperature: float = 0) -> ChatOpenAI:
    """Return a ChatOpenAI instance configured for MiniMax-M2.7."""
    return ChatOpenAI(
        model="MiniMax-M2.7",
        base_url="https://api.minimax.io/v1",
        api_key=os.getenv("MINIMAX_API_KEY"),
        temperature=temperature,
    )
