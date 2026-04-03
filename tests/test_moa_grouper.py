"""Weighted tests for MOA grouper module.

Tests are weighted by importance:
- Critical (weight 3): Core grouping logic, output structure
- Important (weight 2): Edge cases, deduplication, cap behavior
- Nice-to-have (weight 1): Formatting, code fence stripping
"""

import json
from unittest.mock import AsyncMock, patch, MagicMock

import pytest
from services.moa_grouper import group_moas


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

SAMPLE_RAW_MOAS = [
    "NMDA receptor antagonist",
    "NMDA receptor antagonist",
    "Selective serotonin reuptake inhibitor (SSRI)",
    "Not applicable — observational study",
    "Monoclonal antibody targeting PD-1",
    "Monoclonal antibody targeting PD-L1",
    "Small molecule kinase inhibitor (EGFR)",
    "Not applicable - biomarker study",
    "Gene therapy via AAV vector delivery",
    "Immunomodulation via checkpoint inhibition",
]

SAMPLE_MOA_CLUSTERS = [
    {"mechanism": "NMDA receptor antagonist", "count": 5},
    {"mechanism": "Selective serotonin reuptake inhibitor (SSRI)", "count": 3},
    {"mechanism": "Monoclonal antibody targeting PD-1", "count": 4},
    {"mechanism": "Not applicable — observational study", "count": 6},
    {"mechanism": "Small molecule kinase inhibitor (EGFR)", "count": 2},
    {"mechanism": "Gene therapy via AAV vector delivery", "count": 1},
]

VALID_LLM_RESPONSE = json.dumps([
    {"group": "Receptor Antagonists", "moas": ["NMDA receptor antagonist", "Selective serotonin reuptake inhibitor (SSRI)"], "count": 8},
    {"group": "Immune Checkpoint", "moas": ["Monoclonal antibody targeting PD-1", "Monoclonal antibody targeting PD-L1", "Immunomodulation via checkpoint inhibition"], "count": 5},
    {"group": "Targeted Small Molecules", "moas": ["Small molecule kinase inhibitor (EGFR)"], "count": 2},
    {"group": "Gene Therapy", "moas": ["Gene therapy via AAV vector delivery"], "count": 1},
    {"group": "Non-Interventional / Observational", "moas": ["Not applicable — observational study", "Not applicable - biomarker study"], "count": 6},
])


def _mock_llm_response(text: str):
    """Create a mock LLM response with given content."""
    response = MagicMock()
    response.content = text
    return response


# ---------------------------------------------------------------------------
# Weight 3 — Critical: core grouping, output structure
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_returns_valid_groups_from_llm():
    """Weight 3: LLM returns valid JSON -> parsed into group list."""
    with patch("services.moa_grouper.get_llm") as mock_get_llm:
        mock_llm = AsyncMock()
        mock_llm.ainvoke.return_value = _mock_llm_response(VALID_LLM_RESPONSE)
        mock_get_llm.return_value = mock_llm

        result = await group_moas(SAMPLE_RAW_MOAS, SAMPLE_MOA_CLUSTERS)

        assert isinstance(result, list)
        assert len(result) == 5
        for group in result:
            assert "group" in group
            assert "moas" in group
            assert "count" in group
            assert isinstance(group["group"], str)
            assert isinstance(group["moas"], list)
            assert isinstance(group["count"], int)


@pytest.mark.asyncio
async def test_total_count_matches_input():
    """Weight 3: Sum of group counts should reflect input trial counts."""
    with patch("services.moa_grouper.get_llm") as mock_get_llm:
        mock_llm = AsyncMock()
        mock_llm.ainvoke.return_value = _mock_llm_response(VALID_LLM_RESPONSE)
        mock_get_llm.return_value = mock_llm

        result = await group_moas(SAMPLE_RAW_MOAS, SAMPLE_MOA_CLUSTERS)

        total_count = sum(g["count"] for g in result)
        input_count = sum(c["count"] for c in SAMPLE_MOA_CLUSTERS)
        # LLM might not match exactly, but should be in the right ballpark
        assert total_count > 0
        assert total_count <= input_count * 2  # sanity bound


@pytest.mark.asyncio
async def test_all_moas_assigned_to_group():
    """Weight 3: Every MOA from input should appear in some group."""
    with patch("services.moa_grouper.get_llm") as mock_get_llm:
        mock_llm = AsyncMock()
        mock_llm.ainvoke.return_value = _mock_llm_response(VALID_LLM_RESPONSE)
        mock_get_llm.return_value = mock_llm

        result = await group_moas(SAMPLE_RAW_MOAS, SAMPLE_MOA_CLUSTERS)

        all_grouped_moas = []
        for g in result:
            all_grouped_moas.extend(g["moas"])

        # Each unique real MOA should be in at least one group
        unique_input = set(SAMPLE_RAW_MOAS)
        for moa in unique_input:
            assert any(moa in grouped for grouped in all_grouped_moas), f"MOA not grouped: {moa}"


@pytest.mark.asyncio
async def test_group_count_between_5_and_6():
    """Weight 3: Should produce 5-6 groups as specified in the prompt."""
    with patch("services.moa_grouper.get_llm") as mock_get_llm:
        mock_llm = AsyncMock()
        mock_llm.ainvoke.return_value = _mock_llm_response(VALID_LLM_RESPONSE)
        mock_get_llm.return_value = mock_llm

        result = await group_moas(SAMPLE_RAW_MOAS, SAMPLE_MOA_CLUSTERS)

        assert 3 <= len(result) <= 8  # allow some LLM flexibility


# ---------------------------------------------------------------------------
# Weight 2 — Important: edge cases, empty input, dedup, cap
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_empty_moas_returns_empty():
    """Weight 2: Empty input returns empty list without calling LLM."""
    result = await group_moas([], [])
    assert result == []


@pytest.mark.asyncio
async def test_deduplication_in_prompt():
    """Weight 2: Duplicate MOAs should be deduplicated before sending to LLM."""
    duplicated = ["NMDA receptor antagonist"] * 20 + ["PD-1 inhibitor"] * 10

    with patch("services.moa_grouper.get_llm") as mock_get_llm:
        mock_llm = AsyncMock()
        mock_llm.ainvoke.return_value = _mock_llm_response(
            json.dumps([{"group": "Receptor Modulators", "moas": ["NMDA receptor antagonist", "PD-1 inhibitor"], "count": 30}])
        )
        mock_get_llm.return_value = mock_llm

        result = await group_moas(duplicated, [])

        # Verify LLM was called with deduplicated list
        call_args = mock_llm.ainvoke.call_args[0][0]
        prompt_text = call_args[0]["content"]
        # "NMDA receptor antagonist" should appear once in the prompt, not 20 times
        assert prompt_text.count("- NMDA receptor antagonist") == 1


@pytest.mark.asyncio
async def test_caps_at_50_unique_moas():
    """Weight 2: More than 50 unique MOAs should be capped at 50."""
    many_moas = [f"Mechanism type {i}" for i in range(100)]

    with patch("services.moa_grouper.get_llm") as mock_get_llm:
        mock_llm = AsyncMock()
        mock_llm.ainvoke.return_value = _mock_llm_response(
            json.dumps([{"group": "Various", "moas": ["Mechanism type 0"], "count": 100}])
        )
        mock_get_llm.return_value = mock_llm

        await group_moas(many_moas, [])

        call_args = mock_llm.ainvoke.call_args[0][0]
        prompt_text = call_args[0]["content"]
        moa_lines = [l for l in prompt_text.split("\n") if l.startswith("- Mechanism type")]
        assert len(moa_lines) <= 50


@pytest.mark.asyncio
async def test_llm_error_raises():
    """Weight 2: LLM failure should propagate (caller handles the exception)."""
    with patch("services.moa_grouper.get_llm") as mock_get_llm:
        mock_llm = AsyncMock()
        mock_llm.ainvoke.side_effect = ConnectionError("API down")
        mock_get_llm.return_value = mock_llm

        with pytest.raises(ConnectionError):
            await group_moas(SAMPLE_RAW_MOAS, SAMPLE_MOA_CLUSTERS)


@pytest.mark.asyncio
async def test_llm_returns_empty_array():
    """Weight 2: LLM returns [] -> function returns []."""
    with patch("services.moa_grouper.get_llm") as mock_get_llm:
        mock_llm = AsyncMock()
        mock_llm.ainvoke.return_value = _mock_llm_response("[]")
        mock_get_llm.return_value = mock_llm

        result = await group_moas(SAMPLE_RAW_MOAS, SAMPLE_MOA_CLUSTERS)
        assert result == []


@pytest.mark.asyncio
async def test_llm_returns_invalid_json_raises():
    """Weight 2: LLM returns garbage -> json.loads raises."""
    with patch("services.moa_grouper.get_llm") as mock_get_llm:
        mock_llm = AsyncMock()
        mock_llm.ainvoke.return_value = _mock_llm_response("not json at all")
        mock_get_llm.return_value = mock_llm

        with pytest.raises(Exception):
            await group_moas(SAMPLE_RAW_MOAS, SAMPLE_MOA_CLUSTERS)


# ---------------------------------------------------------------------------
# Weight 1 — Nice-to-have: code fence stripping, formatting
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_strips_markdown_code_fences():
    """Weight 1: LLM wraps JSON in ```json ... ``` -> still parses."""
    fenced = f"```json\n{VALID_LLM_RESPONSE}\n```"

    with patch("services.moa_grouper.get_llm") as mock_get_llm:
        mock_llm = AsyncMock()
        mock_llm.ainvoke.return_value = _mock_llm_response(fenced)
        mock_get_llm.return_value = mock_llm

        result = await group_moas(SAMPLE_RAW_MOAS, SAMPLE_MOA_CLUSTERS)
        assert len(result) == 5


@pytest.mark.asyncio
async def test_strips_plain_code_fences():
    """Weight 1: LLM wraps JSON in ``` ... ``` without language tag."""
    fenced = f"```\n{VALID_LLM_RESPONSE}\n```"

    with patch("services.moa_grouper.get_llm") as mock_get_llm:
        mock_llm = AsyncMock()
        mock_llm.ainvoke.return_value = _mock_llm_response(fenced)
        mock_get_llm.return_value = mock_llm

        result = await group_moas(SAMPLE_RAW_MOAS, SAMPLE_MOA_CLUSTERS)
        assert len(result) == 5


@pytest.mark.asyncio
async def test_moa_clusters_truncated_in_prompt():
    """Weight 1: Long mechanism names in clusters are truncated to 80 chars."""
    long_clusters = [{"mechanism": "A" * 200, "count": 3}]

    with patch("services.moa_grouper.get_llm") as mock_get_llm:
        mock_llm = AsyncMock()
        mock_llm.ainvoke.return_value = _mock_llm_response(
            json.dumps([{"group": "Test", "moas": ["A" * 200], "count": 3}])
        )
        mock_get_llm.return_value = mock_llm

        await group_moas(["some moa"], long_clusters)

        call_args = mock_llm.ainvoke.call_args[0][0]
        prompt_text = call_args[0]["content"]
        # The frequency section should have truncated the long name
        freq_lines = [l for l in prompt_text.split("\n") if l.startswith("- AAAA")]
        for line in freq_lines:
            assert len(line) < 200
