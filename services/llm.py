"""MiniMax LLM setup via LangChain's ChatOpenAI."""

import logging
import os

from dotenv import load_dotenv
from langchain_openai import ChatOpenAI

load_dotenv()

logger = logging.getLogger(__name__)


def get_llm(temperature: float = 0) -> ChatOpenAI:
    """Return a ChatOpenAI instance configured for MiniMax-M2.7."""
    logger.debug("Creating ChatOpenAI instance (model=MiniMax-M2.7-highspeed, temperature=%s)", temperature)
    return ChatOpenAI(
        model="MiniMax-M2.7-highspeed",
        base_url="https://api.minimax.io/v1",
        api_key=os.getenv("MINIMAX_API_KEY"),
        temperature=temperature,
    )
