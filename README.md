HAC hackathon

API Data source: https://clinicaltrials.gov/data-api/api

Tech Stack:
- Python 3
- LangGraph - Agent workflow orchestration
- Streamlit - UI
- Agent Model - MiniMax
- Supabase - Database and storage

# Directory Layout

```
.
├── app.py                 # Main Streamlit application entry point
├── components/            # Streamlit UI components
│   ├── chat_panel.py     # Chat interface for querying analysis
│   ├── dashboard.py      # Main dashboard visualizations
│   ├── progress.py       # Progress tracking UI
│   ├── search_form.py    # Search form for trial queries
│   └── trial_table.py    # Data table for displaying trials
├── graph/                 # LangGraph pipeline definitions
│   ├── chat.py           # Chat node for Q&A functionality
│   ├── pipeline.py       # Main LangGraph workflow
│   └── state.py          # State definitions for the graph
├── services/              # Backend services and clients
│   ├── aggregator.py     # Aggregates insights from trials
│   ├── ct_client.py      # ClinicalTrials.gov API client
│   ├── llm.py            # LLM integration (MiniMax)
│   └── supabase_client.py # Supabase database client
├── prompts/               # LLM prompt templates
│   ├── chat_system.py    # System prompts for chat
│   └── extraction.py     # Prompts for data extraction
├── gather-data/           # Standalone data gathering tool
│   └── main.py           # CLI: python main.py --disease "NSCLC" --status ALL
└── tests/                 # Unit and integration tests
```

# Dev

## Setup

1. Install uv (if not already installed):
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

2. Sync dependencies:
```bash
uv sync
```

3. Configure environment variables:
```bash
cp .env.example .env
# Edit .env with your API keys
```

4. Run the Streamlit app:
```bash
uv run streamlit run app.py
```

# Deploy

