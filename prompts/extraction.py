"""Trial insight extraction prompt and Pydantic schema for function calling."""

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Pydantic schema — used with LangChain bind_tools() for structured output
# ---------------------------------------------------------------------------

class Endpoint(BaseModel):
    measure: str = Field(description="Endpoint measure name")
    time_frame: str = Field(default="", description="Time frame for measurement")
    result: str = Field(default="", description="Result summary if available")


class AdverseEvent(BaseModel):
    term: str = Field(description="Adverse event term")
    count: int = Field(default=0, description="Number of occurrences")
    severity: str = Field(default="", description="Severity level")


class TrialInsight(BaseModel):
    """Structured investment insight extracted from a clinical trial."""

    drug_names: list[str] = Field(
        default_factory=list,
        description="Names of drugs/interventions in the trial",
    )
    drug_types: list[str] = Field(
        default_factory=list,
        description="Types: DRUG, BIOLOGICAL, DEVICE, PROCEDURE, etc.",
    )
    mechanism_of_action: str = Field(
        default="",
        description="Mechanism of action of the primary intervention",
    )
    primary_endpoints: list[Endpoint] = Field(
        default_factory=list,
        description="Primary outcome measures",
    )
    secondary_endpoints: list[Endpoint] = Field(
        default_factory=list,
        description="Secondary outcome measures",
    )
    efficacy_summary: str = Field(
        default="",
        description="1-2 sentence summary of efficacy signals",
    )
    safety_summary: str = Field(
        default="",
        description="1-2 sentence summary of safety profile",
    )
    serious_ae_count: int = Field(
        default=0,
        description="Number of serious adverse events reported",
    )
    other_ae_count: int = Field(
        default=0,
        description="Number of other adverse events reported",
    )
    top_adverse_events: list[AdverseEvent] = Field(
        default_factory=list,
        description="Most significant adverse events",
    )
    investment_signal: str = Field(
        default="INSUFFICIENT_DATA",
        description="POSITIVE / NEUTRAL / NEGATIVE / INSUFFICIENT_DATA",
    )
    investment_rationale: str = Field(
        default="",
        description="2-3 sentence investment rationale",
    )
    competitive_notes: str = Field(
        default="",
        description="Notes on competitive landscape from trial context",
    )
    patient_population: str = Field(
        default="",
        description="Target patient population: age range, disease stage, prior treatments, key inclusion criteria. 1-2 sentences.",
    )


# ---------------------------------------------------------------------------
# System prompt
# ---------------------------------------------------------------------------

EXTRACTION_SYSTEM_PROMPT = """\
You are a clinical trials analyst for an investment fund. Analyze this clinical trial \
and extract investment-relevant insights using the provided function.

Focus on:
1. DRUG IDENTIFICATION: Drug names, types, mechanism of action
2. EFFICACY SIGNALS: Primary/secondary endpoints; if results exist, did it meet endpoints?
3. SAFETY PROFILE: Adverse events, serious AE rate, concerning signals
4. INVESTMENT SIGNAL: Rate as POSITIVE (strong efficacy, manageable safety) / NEUTRAL \
(mixed, early stage, inconclusive) / NEGATIVE (failed endpoints, safety concerns, \
terminated) / INSUFFICIENT_DATA
5. COMPETITIVE CONTEXT: Hints about competitive landscape from trial description
6. PATIENT POPULATION: Summarize who this trial targets — age range, disease stage, \
prior treatment requirements, key inclusion/exclusion criteria

Be precise. Use only information present in the trial data. Do not speculate beyond what \
the data supports."""
