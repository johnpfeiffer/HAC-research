"""Tests for ClinicalTrials.gov API client."""

import asyncio
import json
from unittest.mock import AsyncMock, patch, MagicMock

import pytest
from services.ct_client import CTClient, parse_trial


# ---------------------------------------------------------------------------
# Sample API response fixtures
# ---------------------------------------------------------------------------

SAMPLE_STUDY = {
    "protocolSection": {
        "identificationModule": {
            "nctId": "NCT00000001",
            "briefTitle": "Test Trial for Drug X",
        },
        "statusModule": {
            "overallStatus": "RECRUITING",
            "startDateStruct": {"date": "2024-01-15"},
            "completionDateStruct": {"date": "2025-06-30"},
        },
        "designModule": {
            "phases": ["PHASE2"],
            "enrollmentInfo": {"count": 150, "type": "ESTIMATED"},
        },
        "sponsorCollaboratorsModule": {
            "leadSponsor": {"name": "Acme Pharma", "class": "INDUSTRY"},
        },
        "conditionsModule": {
            "conditions": ["Lung Cancer", "Non-Small Cell Lung Cancer"],
        },
    },
    "hasResults": False,
}

SAMPLE_API_RESPONSE = {
    "totalCount": 1,
    "studies": [SAMPLE_STUDY],
}


# ---------------------------------------------------------------------------
# parse_trial tests
# ---------------------------------------------------------------------------

def test_parse_trial_basic():
    result = parse_trial(SAMPLE_STUDY)
    assert result["nct_id"] == "NCT00000001"
    assert result["brief_title"] == "Test Trial for Drug X"
    assert result["phase"] == "PHASE2"
    assert result["overall_status"] == "RECRUITING"
    assert result["enrollment_count"] == 150
    assert result["enrollment_type"] == "ESTIMATED"
    assert result["sponsor_name"] == "Acme Pharma"
    assert result["sponsor_class"] == "INDUSTRY"
    assert result["has_results"] is False
    assert result["start_date"] == "2024-01-15"
    assert result["completion_date"] == "2025-06-30"
    assert "Lung Cancer" in result["conditions"]
    assert result["raw_json"] == SAMPLE_STUDY


def test_parse_trial_missing_fields():
    minimal = {"protocolSection": {}, "hasResults": True}
    result = parse_trial(minimal)
    assert result["nct_id"] is None
    assert result["phase"] is None
    assert result["has_results"] is True
    assert result["conditions"] == []


# ---------------------------------------------------------------------------
# CTClient.search tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_search_single_page():
    client = CTClient()
    mock_response = MagicMock()
    mock_response.json.return_value = SAMPLE_API_RESPONSE
    mock_response.raise_for_status = MagicMock()

    with patch("services.ct_client.httpx.AsyncClient") as MockClient:
        mock_instance = AsyncMock()
        mock_instance.get.return_value = mock_response
        mock_instance.__aenter__ = AsyncMock(return_value=mock_instance)
        mock_instance.__aexit__ = AsyncMock(return_value=False)
        MockClient.return_value = mock_instance

        results = await client.search("lung cancer", max_results=10)
        assert len(results) == 1
        assert results[0]["protocolSection"]["identificationModule"]["nctId"] == "NCT00000001"


@pytest.mark.asyncio
async def test_search_respects_max_results():
    client = CTClient()
    many_studies = {"studies": [SAMPLE_STUDY] * 50, "nextPageToken": "abc"}

    mock_response = MagicMock()
    mock_response.json.return_value = many_studies
    mock_response.raise_for_status = MagicMock()

    with patch("services.ct_client.httpx.AsyncClient") as MockClient:
        mock_instance = AsyncMock()
        mock_instance.get.return_value = mock_response
        mock_instance.__aenter__ = AsyncMock(return_value=mock_instance)
        mock_instance.__aexit__ = AsyncMock(return_value=False)
        MockClient.return_value = mock_instance

        results = await client.search("lung cancer", max_results=20)
        assert len(results) == 20
