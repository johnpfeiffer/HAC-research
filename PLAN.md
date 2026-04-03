# Clinical Trials Investment Analysis Dashboard

## Context

Investment funds need a tool to analyze clinical trial data from ClinicalTrials.gov and extract actionable investment insights. Currently, analysts must manually sift through hundreds of trials per disease area. This dashboard automates that process: user enters a disease keyword, system fetches all relevant trials, LangGraph fan-out spawns a subagent per trial to extract structured insights, aggregated data populates dashboards and feeds a chatbot for investment Q&A.

**API:** ClinicalTrials.gov v2 (`https://clinicaltrials.gov/api/v2`). No auth required. ~50 req/min rate limit. Token-based pagination (`pageToken`). Max 1000 results per page.

**Constraints:** Cap at 100 trials per search. User can filter by date range to narrow results before processing.

---

## Tech Stack

| Layer | Choice | Why |
|-------|--------|-----|
| Language | **Python 3.11+** | Specified by user |
| Agent Orchestration | **LangGraph** | `Send` API enables dynamic fan-out (one subagent per trial), reducers auto-aggregate results |
| UI | **Streamlit** | Rapid prototyping, built-in chat UI (`st.chat_message`), native charting |
| LLM | **MiniMax-M2.7** (via `ChatOpenAI` with `base_url="https://api.minimax.io/v1"`) | Latest model, OpenAI-compatible API, function calling, 200K+ context |
| Database | **Supabase** (PostgreSQL) | Also serves as LangGraph checkpointer via `PostgresSaver` |

---

## Architecture

```
                    Streamlit UI
                        |
              LangGraph StateGraph
             /          |          \
     Fetch Trials   Fan-Out (Send)   Chatbot
         |          /    |    \         |
    CT.gov API   Agent Agent Agent   MiniMax
                   \    |    /
                  Aggregate Node
                        |
                    Supabase DB
```

**Data Flow:**
1. User enters disease keyword in Streamlit
2. LangGraph `fetch_trials` node calls ClinicalTrials.gov API (paginated)
3. `distribute_trials` node returns `Send("analyze_trial", {...})` for each trial — LangGraph runs these in parallel
4. Each `analyze_trial` subagent calls MiniMax to extract structured insights (via function calling)
5. `aggregate_results` node collects all insights (via `operator.add` reducer), computes summary stats, stores to Supabase
6. Dashboard renders charts from aggregated data
7. Chat uses aggregated insights as context for MiniMax-powered Q&A

---

## LangGraph Graph Design

```python
# State definitions
class TrialState(TypedDict):
    """State for individual trial processing (fan-out)"""
    trial_data: dict        # Single trial JSON from CT.gov

class OverallState(TypedDict):
    """Main graph state"""
    disease_keyword: str
    search_session_id: str
    raw_trials: list[dict]                              # All fetched trials
    insights: Annotated[list[dict], operator.add]        # Aggregated from subagents
    aggregate: dict                                      # Summary stats
    chat_history: list[dict]                             # Conversation messages
    chat_response: str                                   # Latest response

# Graph nodes:
# 1. fetch_trials      — paginate CT.gov API, populate raw_trials
# 2. distribute_trials — return [Send("analyze_trial", {trial}) for each trial]
# 3. analyze_trial     — call MiniMax with structured extraction prompt, return insight
# 4. aggregate_results — compute stats from insights[], store to Supabase
# 5. chat_node         — build context from aggregate + insights, call MiniMax

# Edges:
# START -> fetch_trials -> distribute_trials -> analyze_trial(s) -> aggregate_results -> END
# (Chat is a separate invocation reusing stored state)
```

**Key pattern — the `Send` fan-out:**
```python
def distribute_trials(state: OverallState):
    return [
        Send("analyze_trial", {"trial_data": trial})
        for trial in state["raw_trials"]
    ]
```
Each `Send` creates a parallel execution. The `Annotated[list[dict], operator.add]` reducer on `insights` auto-concatenates all results.

---

## Folder Structure

```
HAC-research/
├── requirements.txt
├── .env.example                     # MINIMAX_API_KEY, SUPABASE_URL, SUPABASE_KEY
├── app.py                           # Streamlit entry point
├── graph/
│   ├── __init__.py
│   ├── state.py                     # TypedDict state definitions
│   ├── pipeline.py                  # Main StateGraph: fetch -> distribute -> analyze -> aggregate
│   └── chat.py                      # Chat graph (separate invocation with stored context)
├── services/
│   ├── __init__.py
│   ├── ct_client.py                 # ClinicalTrials.gov API client (httpx, pagination, rate limiting)
│   ├── llm.py                       # MiniMax LLM setup (ChatOpenAI with custom base_url)
│   ├── supabase_client.py           # Supabase client + helpers (store/retrieve sessions, trials, insights)
│   └── aggregator.py                # Compute aggregate stats from insight list
├── prompts/
│   ├── __init__.py
│   ├── extraction.py                # Trial insight extraction system prompt + function schema
│   └── chat_system.py               # Chat system prompt (investment analyst role)
├── components/
│   ├── __init__.py
│   ├── search_form.py               # Streamlit search input component
│   ├── progress.py                  # Processing progress display
│   ├── dashboard.py                 # Charts: phase pie, status bar, sponsor table, signal breakdown
│   ├── trial_table.py               # Sortable/filterable trial list
│   └── chat_panel.py                # Chat interface using st.chat_message
└── tests/
    ├── test_ct_client.py
    ├── test_pipeline.py
    └── test_aggregator.py
```

---

## Data Models

### Supabase Tables

**search_sessions**
| Column | Type | Notes |
|--------|------|-------|
| id | uuid (PK) | Default: gen_random_uuid() |
| disease_keyword | text | User input |
| status | text | FETCHING / PROCESSING / COMPLETED / FAILED |
| total_trials | int | |
| processed_trials | int | Default: 0 |
| created_at | timestamptz | |

**trials**
| Column | Type | Notes |
|--------|------|-------|
| id | uuid (PK) | |
| session_id | uuid (FK) | -> search_sessions |
| nct_id | text | |
| raw_json | jsonb | Full CT.gov response |
| brief_title | text | |
| phase | text | PHASE1, PHASE2, PHASE3, etc. |
| overall_status | text | RECRUITING, COMPLETED, etc. |
| enrollment_count | int | |
| enrollment_type | text | ACTUAL / ESTIMATED |
| sponsor_name | text | |
| sponsor_class | text | NIH / INDUSTRY / OTHER |
| has_results | boolean | |
| start_date | date | |
| completion_date | date | |
| conditions | jsonb | Array of condition strings |

**trial_insights**
| Column | Type | Notes |
|--------|------|-------|
| id | uuid (PK) | |
| trial_id | uuid (FK) | -> trials |
| session_id | uuid (FK) | -> search_sessions (for fast queries) |
| drug_names | jsonb | ["Azacitidine", ...] |
| drug_types | jsonb | ["DRUG", "BIOLOGICAL", ...] |
| mechanism_of_action | text | LLM-extracted |
| primary_endpoints | jsonb | [{measure, timeFrame, result}] |
| secondary_endpoints | jsonb | [{measure, timeFrame, result}] |
| efficacy_summary | text | 1-2 sentences |
| safety_summary | text | 1-2 sentences |
| serious_ae_count | int | |
| other_ae_count | int | |
| top_adverse_events | jsonb | [{term, count, severity}] |
| investment_signal | text | POSITIVE / NEUTRAL / NEGATIVE / INSUFFICIENT_DATA |
| investment_rationale | text | 2-3 sentences |
| competitive_notes | text | |

**chat_messages**
| Column | Type | Notes |
|--------|------|-------|
| id | uuid (PK) | |
| session_id | uuid (FK) | -> search_sessions |
| role | text | user / assistant |
| content | text | |
| created_at | timestamptz | |

---

## MiniMax Integration

```python
# services/llm.py
from langchain_openai import ChatOpenAI

def get_llm(temperature: float = 0) -> ChatOpenAI:
    return ChatOpenAI(
        model="MiniMax-M2.7",
        base_url="https://api.minimax.io/v1",
        api_key=os.getenv("MINIMAX_API_KEY"),
        temperature=temperature,
    )
```

MiniMax-M2.7 supports OpenAI-compatible function calling, so structured extraction via `bind_tools()` works natively with LangChain's tool abstraction.

---

## Insight Extraction Strategy

Each subagent receives one trial's JSON and uses function calling to return structured output:

**System prompt** (in `prompts/extraction.py`):
```
You are a clinical trials analyst for an investment fund. Analyze this clinical trial 
and extract investment-relevant insights using the provided function.

Focus on:
1. DRUG IDENTIFICATION: Drug names, types, mechanism of action
2. EFFICACY SIGNALS: Primary/secondary endpoints; if results exist, did it meet endpoints?
3. SAFETY PROFILE: Adverse events, serious AE rate, concerning signals
4. INVESTMENT SIGNAL: Rate as POSITIVE (strong efficacy, manageable safety) / NEUTRAL 
   (mixed, early stage, inconclusive) / NEGATIVE (failed endpoints, safety concerns, 
   terminated) / INSUFFICIENT_DATA
5. COMPETITIVE CONTEXT: Hints about competitive landscape from trial description
```

**Function schema** matches the `trial_insights` table columns. MiniMax returns structured JSON via function calling, parsed directly into the Supabase insert.

---

## Chat Context Strategy

System prompt for chatbot:
1. Role: "You are an investment analyst specializing in clinical trial data for pharma/biotech investment decisions."
2. Aggregate stats: phase distribution, status distribution, top drugs, signal counts, enrollment totals
3. Trial index: compact table of all trials (NCT ID, drug, phase, status, signal, 1-line rationale) — ~100 tokens per trial
4. Full insights for high-priority trials (Phase 3, INDUSTRY sponsor, has results, POSITIVE signal)

MiniMax's 200K context handles ~300 trials at full detail or ~1000+ in index-only mode.

---

## Streamlit UI Layout

**Page 1: Search** (`app.py` default view)
- `st.text_input` for disease keyword
- **Date filter**: `st.date_input` for start/end date range (maps to CT.gov `filter.advanced` date params)
- **Phase filter**: `st.multiselect` for trial phases (PHASE1, PHASE2, PHASE3, etc.)
- **Status filter**: `st.multiselect` for trial status (RECRUITING, COMPLETED, etc.)
- Trial cap: fetch up to 100 trials (configurable, hard max to control LLM costs)
- Recent searches from Supabase
- "Analyze" button triggers LangGraph pipeline

**Page 2: Dashboard + Chat** (after processing completes)
- **Left column (60%)**:
  - `st.metric` cards: total trials, trials with results, positive signals
  - `st.plotly_chart` / `st.bar_chart`: phase distribution, status distribution
  - Sponsor breakdown table
  - Investment signal pie chart
  - Sortable trial table with filters (phase, status, signal, sponsor class)
  - Click-to-expand trial detail
- **Right column (40%)**:
  - `st.chat_message` based chat interface
  - Pre-populated suggested questions ("Which Phase 3 trials have positive signals?", "What are the main safety concerns?", "Which sponsors are most active?")
- **Progress bar** during processing (updates via Streamlit rerun pattern)

---

## Implementation Phases

### Phase 1: Foundation + Pipeline
- Project setup: `requirements.txt`, `.env`, Supabase tables
- `services/ct_client.py`: ClinicalTrials.gov fetcher with pagination + rate limiting (httpx)
- `services/llm.py`: MiniMax via ChatOpenAI
- `services/supabase_client.py`: CRUD operations for all tables
- `graph/state.py`: TypedDict state definitions
- `graph/pipeline.py`: LangGraph StateGraph (fetch -> distribute -> analyze -> aggregate)
- `prompts/extraction.py`: Extraction prompt + function schema
- Test: run pipeline for "azacitidine" (~50 trials), verify insights in Supabase

### Phase 2: Streamlit Dashboard
- `app.py`: Search form + session routing
- `components/dashboard.py`: Charts from aggregated data
- `components/trial_table.py`: Sortable trial list
- `components/progress.py`: Processing progress display
- Test: full flow from search to dashboard rendering

### Phase 3: Chat Interface
- `graph/chat.py`: Chat graph node with context builder
- `prompts/chat_system.py`: Investment analyst system prompt
- `components/chat_panel.py`: Streamlit chat UI with streaming
- `services/supabase_client.py`: Chat history persistence
- Test: ask "Which Phase 3 trials show positive efficacy signals?"

### Phase 4: Polish
- Error handling / retry for API failures
- Loading states + empty states
- Filter/sort on trial table
- Export to CSV
- Session management (revisit previous searches)

---

## Key Dependencies

```
# requirements.txt
streamlit>=1.38
langgraph>=0.2
langchain-openai>=0.2
langchain-core>=0.3
httpx>=0.27
supabase>=2.0
plotly>=5.0
python-dotenv>=1.0
pydantic>=2.0
```

---

## Supabase Setup SQL

```sql
-- Run this in Supabase SQL Editor to create all required tables

create table search_sessions (
  id uuid primary key default gen_random_uuid(),
  disease_keyword text not null,
  status text not null default 'FETCHING',
  total_trials int,
  processed_trials int default 0,
  filters jsonb,  -- stores date range, phase, status filters used
  created_at timestamptz default now()
);

create table trials (
  id uuid primary key default gen_random_uuid(),
  session_id uuid references search_sessions(id) on delete cascade,
  nct_id text not null,
  raw_json jsonb not null,
  brief_title text,
  phase text,
  overall_status text,
  enrollment_count int,
  enrollment_type text,
  sponsor_name text,
  sponsor_class text,
  has_results boolean default false,
  start_date date,
  completion_date date,
  conditions jsonb,
  created_at timestamptz default now(),
  unique(session_id, nct_id)
);

create table trial_insights (
  id uuid primary key default gen_random_uuid(),
  trial_id uuid references trials(id) on delete cascade,
  session_id uuid references search_sessions(id) on delete cascade,
  drug_names jsonb,
  drug_types jsonb,
  mechanism_of_action text,
  primary_endpoints jsonb,
  secondary_endpoints jsonb,
  efficacy_summary text,
  safety_summary text,
  serious_ae_count int,
  other_ae_count int,
  top_adverse_events jsonb,
  investment_signal text,
  investment_rationale text,
  competitive_notes text,
  created_at timestamptz default now()
);

create table chat_messages (
  id uuid primary key default gen_random_uuid(),
  session_id uuid references search_sessions(id) on delete cascade,
  role text not null,
  content text not null,
  created_at timestamptz default now()
);

-- Indexes for common queries
create index idx_trials_session on trials(session_id);
create index idx_insights_session on trial_insights(session_id);
create index idx_insights_signal on trial_insights(investment_signal);
create index idx_chat_session on chat_messages(session_id);

-- LangGraph checkpointer tables (PostgresSaver.setup() creates these,
-- but included here for completeness)
create table if not exists checkpoints (
  thread_id text not null,
  checkpoint_id text not null,
  parent_checkpoint_id text,
  type text,
  checkpoint jsonb,
  metadata jsonb,
  created_at timestamptz default now(),
  primary key (thread_id, checkpoint_id)
);

create table if not exists checkpoint_writes (
  thread_id text not null,
  checkpoint_ns text not null default '',
  checkpoint_id text not null,
  task_id text not null,
  idx int not null,
  channel text not null,
  type text,
  blob bytea,
  primary key (thread_id, checkpoint_ns, checkpoint_id, task_id, idx)
);
```

---

## Verification

1. **Unit**: Mock CT.gov responses, verify pagination logic in `ct_client.py`
2. **Integration**: Run pipeline for "azacitidine", verify trials + insights stored in Supabase
3. **LangGraph**: Verify Send fan-out processes N trials in parallel and aggregates correctly
4. **E2E**: `streamlit run app.py` -> search "lung cancer" -> dashboard renders -> chat answers investment questions
5. **Rate limits**: Query with >100 trials, verify no 429 errors from CT.gov or MiniMax
