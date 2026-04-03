"""Supabase client with CRUD helpers for all tables."""

import os
from typing import Optional

from dotenv import load_dotenv
from supabase import create_client, Client

load_dotenv()


def get_client() -> Client:
    """Return a Supabase client."""
    return create_client(
        os.getenv("SUPABASE_URL", ""),
        os.getenv("SUPABASE_KEY", ""),
    )


# ---------------------------------------------------------------------------
# Search sessions
# ---------------------------------------------------------------------------

def create_session(client: Client, disease_keyword: str, filters: Optional[dict] = None) -> dict:
    """Create a new search session and return the row."""
    row = {"disease_keyword": disease_keyword, "status": "FETCHING"}
    if filters:
        row["filters"] = filters
    return client.table("search_sessions").insert(row).execute().data[0]


def update_session(client: Client, session_id: str, **fields) -> dict:
    return (
        client.table("search_sessions")
        .update(fields)
        .eq("id", session_id)
        .execute()
        .data[0]
    )


def get_session(client: Client, session_id: str) -> dict:
    return (
        client.table("search_sessions")
        .select("*")
        .eq("id", session_id)
        .single()
        .execute()
        .data
    )


def list_sessions(client: Client, limit: int = 10) -> list[dict]:
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
        return []
    rows = [{**t, "session_id": session_id} for t in trials]
    all_data = []
    # Insert in batches of 20 to avoid payload limits
    for i in range(0, len(rows), 20):
        batch = rows[i : i + 20]
        result = client.table("trials").insert(batch).execute().data
        all_data.extend(result)
    return all_data


def get_trials(client: Client, session_id: str) -> list[dict]:
    return (
        client.table("trials")
        .select("*")
        .eq("session_id", session_id)
        .execute()
        .data
    )


# ---------------------------------------------------------------------------
# Trial insights
# ---------------------------------------------------------------------------

def insert_insight(client: Client, insight: dict) -> dict:
    """Insert a single trial insight row."""
    return client.table("trial_insights").insert(insight).execute().data[0]


def get_insights(client: Client, session_id: str) -> list[dict]:
    return (
        client.table("trial_insights")
        .select("*")
        .eq("session_id", session_id)
        .execute()
        .data
    )


# ---------------------------------------------------------------------------
# Chat messages
# ---------------------------------------------------------------------------

def insert_message(client: Client, session_id: str, role: str, content: str) -> dict:
    return (
        client.table("chat_messages")
        .insert({"session_id": session_id, "role": role, "content": content})
        .execute()
        .data[0]
    )


def get_messages(client: Client, session_id: str) -> list[dict]:
    return (
        client.table("chat_messages")
        .select("*")
        .eq("session_id", session_id)
        .order("created_at")
        .execute()
        .data
    )
