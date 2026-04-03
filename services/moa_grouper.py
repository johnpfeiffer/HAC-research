"""Group mechanisms of action into broad categories via LLM."""

import json
import logging
import re

from services.llm import get_llm

logger = logging.getLogger(__name__)


async def group_moas(raw_moas: list[str], moa_clusters: list[dict]) -> list[dict]:
    """
    Use LLM to group raw MOA strings into 5-6 broad therapeutic categories.

    Args:
        raw_moas: List of raw MOA strings from insights.
        moa_clusters: List of {"mechanism": str, "count": int} dicts.

    Returns:
        List of {"group": str, "moas": list[str], "count": int} dicts.
        Returns empty list on failure.
    """
    if not raw_moas:
        logger.debug("No raw MOAs to group")
        return []

    logger.info("Grouping %d raw MOAs (%d unique clusters)", len(raw_moas), len(moa_clusters))
    llm = get_llm(temperature=0)

    unique_moas = list(set(raw_moas))[:50]
    moa_list = "\n".join(f"- {m}" for m in unique_moas)
    moa_freq = "\n".join(
        f"- {m['mechanism'][:80]}: {m['count']} trials"
        for m in moa_clusters[:20]
    )

    prompt = (
        "You are a pharmacology expert. Below are mechanisms of action extracted from clinical trials. "
        "Many are verbose descriptions — some say 'not applicable' or 'observational study'.\n\n"
        "Tasks:\n"
        "1. Filter out entries that are not real mechanisms (observational, not applicable, unknown, etc.) — group those as 'Non-Interventional / Observational'\n"
        "2. Group the remaining into 5-6 broad therapeutic mechanism categories with SHORT names (2-4 words each)\n"
        "3. Count how many trials belong to each group based on the frequency data\n\n"
        "Return ONLY a JSON array, no markdown, no explanation:\n"
        '[{"group": "Short Name", "moas": ["moa1", "moa2"], "count": 5}]\n\n'
        f"MOA descriptions:\n{moa_list}\n\n"
        f"Frequency:\n{moa_freq}"
    )

    logger.info(f"moa prompt: {prompt}")
    logger.info("Sending MOA grouping prompt to LLM (%d unique MOAs)", len(unique_moas))
    response = await llm.ainvoke([{"role": "user", "content": prompt}])
    text = (response.content or "").strip()
    logger.info("LLM raw response (%d chars): %s", len(text), text[:500])

    if not text:
        logger.warning("LLM returned empty response for MOA grouping")
        return []

    # Strip markdown code fences if present (```json ... ``` or ``` ... ```)
    fence_match = re.search(r"```(?:json)?\s*\n?(.*?)```", text, re.DOTALL)
    if fence_match:
        text = fence_match.group(1).strip()

    # Try to find a JSON array in the response
    if not text.startswith("["):
        bracket_start = text.find("[")
        if bracket_start != -1:
            text = text[bracket_start:]

    if not text:
        logger.warning("No JSON content found in LLM response")
        return []

    moa_groups = json.loads(text)
    if isinstance(moa_groups, list) and len(moa_groups) > 0:
        logger.info("LLM returned %d MOA groups", len(moa_groups))
        return moa_groups

    logger.warning("LLM returned unexpected MOA grouping format: %s", type(moa_groups).__name__)
    return []
