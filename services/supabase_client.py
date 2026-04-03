"""Supabase client with CRUD helpers for all tables."""

import logging
import os
from typing import Optional

from dotenv import load_dotenv
from supabase import create_client, Client

load_dotenv()

logger = logging.getLogger(__name__)


def get_client() -> Client:
    """Return a Supabase client."""
    logger.debug("Creating Supabase client")
    return create_client(
        os.getenv("SUPABASE_URL", ""),
        os.getenv("SUPABASE_KEY", ""),
    )


# ---------------------------------------------------------------------------
# Search sessions
# ---------------------------------------------------------------------------

def create_session(client: Client, disease_keyword: str, filters: Optional[dict] = None) -> dict:
    """Create a new search session and return the row."""
    logger.info("Creating search session: keyword=%r, filters=%s", disease_keyword, filters)
    row = {"disease_keyword": disease_keyword, "status": "FETCHING"}
    if filters:
        row["filters"] = filters
    result = client.table("search_sessions").insert(row).execute().data[0]
    logger.info("Session created: id=%s", result.get("id"))
    return result


def update_session(client: Client, session_id: str, **fields) -> dict:
    logger.debug("Updating session %s: %s", session_id, fields)
    return (
        client.table("search_sessions")
        .update(fields)
        .eq("id", session_id)
        .execute()
        .data[0]
    )


def get_session(client: Client, session_id: str) -> dict:
    logger.debug("Fetching session %s", session_id)
    return (
        client.table("search_sessions")
        .select("*")
        .eq("id", session_id)
        .single()
        .execute()
        .data
    )


def list_sessions(client: Client, limit: int = 10) -> list[dict]:
    logger.debug("Listing recent sessions (limit=%d)", limit)
    return (
        client.table("search_sessions")
        .select("*")
        .order("created_at", desc=True)
        .limit(limit)
        .execute()
        .data
    )


# ---------------------------------------------------------------------------
# Trials
# ---------------------------------------------------------------------------

def insert_trials(client: Client, session_id: str, trials: list[dict]) -> list[dict]:
    """Bulk-insert parsed trial rows for a session."""
    if not trials:
        logger.warning("insert_trials called with empty list for session %s", session_id)
        return []
    logger.info("Inserting %d trials for session %s", len(trials), session_id)
    rows = [{**t, "session_id": session_id} for t in trials]
    all_data = []
    # Insert in batches of 20 to avoid payload limits
    for i in range(0, len(rows), 20):
        batch = rows[i : i + 20]
        batch_num = i // 20 + 1
        logger.debug("Inserting batch %d (%d rows)", batch_num, len(batch))
        result = client.table("trials").insert(batch).execute().data
        all_data.extend(result)
    logger.info("Inserted %d trial rows total", len(all_data))
    return all_data


def get_trials(client: Client, session_id: str) -> list[dict]:
    logger.debug("Fetching trials for session %s", session_id)
    data = (
        client.table("trials")
        .select("*")
        .eq("session_id", session_id)
        .execute()
        .data
    )
    logger.debug("Retrieved %d trials", len(data))
    return data


# ---------------------------------------------------------------------------
# Trial insights
# ---------------------------------------------------------------------------

def insert_insight(client: Client, insight: dict) -> dict:
    """Insert a single trial insight row."""
    logger.debug("Inserting insight for trial_id=%s", insight.get("trial_id"))
    return client.table("trial_insights").insert(insight).execute().data[0]


def get_insights(client: Client, session_id: str) -> list[dict]:
    logger.debug("Fetching insights for session %s", session_id)
    data = (
        client.table("trial_insights")
        .select("*")
        .eq("session_id", session_id)
        .execute()
        .data
    )
    logger.debug("Retrieved %d insights", len(data))
    return data


# ---------------------------------------------------------------------------
# Chat messages
# ---------------------------------------------------------------------------

def insert_message(client: Client, session_id: str, role: str, content: str) -> dict:
    logger.debug("Inserting %s message for session %s (len=%d)", role, session_id, len(content))
    return (
        client.table("chat_messages")
        .insert({"session_id": session_id, "role": role, "content": content})
        .execute()
        .data[0]
    )


def get_messages(client: Client, session_id: str) -> list[dict]:
    logger.debug("Fetching messages for session %s", session_id)
    data = (
        client.table("chat_messages")
        .select("*")
        .eq("session_id", session_id)
        .order("created_at")
        .execute()
        .data
    )
    logger.debug("Retrieved %d messages", len(data))
    return data
