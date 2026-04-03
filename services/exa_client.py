"""Exa AI client service for market research queries."""

import os
from typing import Optional

from dotenv import load_dotenv
from exa_py import Exa

load_dotenv()


def get_exa_client() -> Optional[Exa]:
    """Return an Exa client if API key is available."""
    api_key = os.getenv("EXA_API_KEY")
    if not api_key:
        return None
    return Exa(api_key=api_key)


def search_market_data(
    query: str,
    num_results: int = 10,
    use_autoprompt: bool = True,
) -> list[dict]:
    """
    Search for market data using Exa AI.

    Args:
        query: Search query string
        num_results: Number of results to return (default: 10)
        use_autoprompt: Whether to use Exa's autoprompt feature for better results

    Returns:
        List of result dictionaries with title, url, score, and published_date
    """
    client = get_exa_client()
    if not client:
        return []

    try:
        result = client.search(
            query,
            type="auto",
            num_results=num_results,
            use_autoprompt=use_autoprompt,
        )

        return [
            {
                "title": r.title,
                "url": r.url,
                "score": r.score,
                "published_date": getattr(r, "published_date", None),
            }
            for r in result.results
        ]
    except Exception as e:
        print(f"Exa search error: {e}")
        return []


def search_with_contents(
    query: str,
    num_results: int = 5,
    use_autoprompt: bool = True,
) -> list[dict]:
    """
    Search for market data with full text content.

    Args:
        query: Search query string
        num_results: Number of results to return (default: 5)
        use_autoprompt: Whether to use Exa's autoprompt feature

    Returns:
        List of result dictionaries with title, url, score, and text content
    """
    client = get_exa_client()
    if not client:
        return []

    try:
        result = client.search_and_contents(
            query,
            type="auto",
            num_results=num_results,
            use_autoprompt=use_autoprompt,
            text={"max_characters": 2000},
        )

        return [
            {
                "title": r.title,
                "url": r.url,
                "score": r.score,
                "text": getattr(r, "text", ""),
                "published_date": getattr(r, "published_date", None),
            }
            for r in result.results
        ]
    except Exception as e:
        print(f"Exa search with contents error: {e}")
        return []
