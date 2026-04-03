"""ClinicalTrials.gov API v2 client with pagination and rate limiting.

Uses requests (not httpx) because CT.gov blocks httpx via TLS fingerprinting.
Async methods wrap requests calls with asyncio.to_thread.
"""

import asyncio
import time
from typing import Optional

import requests


BASE_URL = "https://clinicaltrials.gov/api/v2/studies"

# CT.gov allows ~50 req/min
_MIN_REQUEST_INTERVAL = 1.2  # seconds between requests


class CTClient:
    """Client for ClinicalTrials.gov API v2."""

    def __init__(self):
        self._last_request_time: float = 0
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Python-ClinicalTrials-Client/1.0",
        })

    def _throttle_sync(self):
        """Enforce rate limiting between requests (blocking)."""
        elapsed = time.monotonic() - self._last_request_time
        if elapsed < _MIN_REQUEST_INTERVAL:
            time.sleep(_MIN_REQUEST_INTERVAL - elapsed)
        self._last_request_time = time.monotonic()

    def _search_sync(
        self,
        condition: str,
        max_results: int = 100,
        status: Optional[str] = None,
        phase: Optional[list[str]] = None,
        date_range: Optional[tuple[str, str]] = None,
    ) -> list[dict]:
        """Synchronous search with pagination."""
        max_results = min(max_results, 100)
        all_studies: list[dict] = []
        page_token: Optional[str] = None
        page_size = min(max_results, 100)

        params: dict = {
            "query.cond": condition,
            "pageSize": page_size,
            "format": "json",
            "countTotal": "true",
        }

        if status:
            params["filter.overallStatus"] = status
        if phase:
            params["filter.advanced"] = f"AREA[Phase]{' OR '.join(phase)}"
        if date_range:
            start, end = date_range
            date_filter = f"AREA[StartDate]RANGE[{start},{end}]"
            if "filter.advanced" in params:
                params["filter.advanced"] += f" AND {date_filter}"
            else:
                params["filter.advanced"] = date_filter

        while True:
            if page_token:
                params["pageToken"] = page_token

            self._throttle_sync()
            resp = self.session.get(BASE_URL, params=params)
            resp.raise_for_status()
            data = resp.json()

            studies = data.get("studies", [])
            all_studies.extend(studies)

            if len(all_studies) >= max_results:
                all_studies = all_studies[:max_results]
                break

            page_token = data.get("nextPageToken")
            if not page_token:
                break

        return all_studies

    async def search(
        self,
        condition: str,
        max_results: int = 100,
        status: Optional[str] = None,
        phase: Optional[list[str]] = None,
        date_range: Optional[tuple[str, str]] = None,
    ) -> list[dict]:
        """Async wrapper around synchronous search."""
        return await asyncio.to_thread(
            self._search_sync, condition, max_results, status, phase, date_range
        )

    async def get_study(self, nct_id: str) -> dict:
        """Fetch a single study by NCT ID."""
        def _fetch():
            self._throttle_sync()
            resp = self.session.get(f"{BASE_URL}/{nct_id}")
            resp.raise_for_status()
            return resp.json()
        return await asyncio.to_thread(_fetch)


def _normalize_date(date_str: Optional[str]) -> Optional[str]:
    """Normalize partial dates like '2025-12' to '2025-12-01' for Postgres."""
    if not date_str:
        return None
    parts = date_str.split("-")
    if len(parts) == 1:
        return f"{parts[0]}-01-01"
    if len(parts) == 2:
        return f"{parts[0]}-{parts[1]}-01"
    return date_str


def parse_trial(study: dict) -> dict:
    """Extract flat fields from a CT.gov study JSON for the trials table."""
    protocol = study.get("protocolSection", {})
    ident = protocol.get("identificationModule", {})
    status_mod = protocol.get("statusModule", {})
    design = protocol.get("designModule", {})
    sponsor_mod = protocol.get("sponsorCollaboratorsModule", {})
    conditions_mod = protocol.get("conditionsModule", {})
    enrollment_info = design.get("enrollmentInfo", {})
    has_results = study.get("hasResults", False)

    lead_sponsor = sponsor_mod.get("leadSponsor", {})

    phases = design.get("phases", [])
    phase = phases[0] if phases else None

    start_date_struct = status_mod.get("startDateStruct", {})
    completion_date_struct = status_mod.get("completionDateStruct", {})

    return {
        "nct_id": ident.get("nctId"),
        "brief_title": ident.get("briefTitle"),
        "phase": phase,
        "overall_status": status_mod.get("overallStatus"),
        "enrollment_count": enrollment_info.get("count"),
        "enrollment_type": enrollment_info.get("type"),
        "sponsor_name": lead_sponsor.get("name"),
        "sponsor_class": lead_sponsor.get("class"),
        "has_results": has_results,
        "start_date": _normalize_date(start_date_struct.get("date")),
        "completion_date": _normalize_date(completion_date_struct.get("date")),
        "conditions": conditions_mod.get("conditions", []),
        "raw_json": study,
    }
