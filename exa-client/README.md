# Exa Client

Search the web using the [Exa API](https://exa.ai/).

## Setup

```bash
cd exa-client
uv sync
```

Ensure `EXA_API_KEY` is set in the root `.env` file.

## Usage

```bash
uv run python main.py "What's the addressable market for Hutchinson's disease"
uv run python main.py --num-results 5 "Stargardt disease gene therapy"
```

Results are printed and saved to `SAVED/`.
