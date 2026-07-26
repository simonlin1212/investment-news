# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**Investment News** is a local investment-news dashboard. It fetches 100+ RSS/Atom sources across 12 investment sectors, uses the user's own LLM (Claude Code subscription or OpenAI-compatible API) to generate Chinese "daily key points" and translations, and renders everything in a browser dashboard at `http://localhost:8793`.

**Core principle**: the deliverable is the browser dashboard page — not terminal output, not `data.js`. When the user asks to view news or refresh the dashboard, open `http://localhost:8793` in the browser and direct them there.

## Architecture

```
sources.json ──► scripts/fetch.py ──► data.js ──► scripts/digest.py ──► data.js (enriched)
                                                                                  │
                                                                                  ▼
                                                                       index.html (dashboard)
                                                                                  │
                                                                          server.py:8793
```

- `server.py` — serves the dashboard and exposes `POST/GET /api/refresh` which runs `fetch.py` then `digest.py`
- `scripts/fetch.py` — reads `sources.json`, fetches RSS/Atom, applies compliance filters and time-window, writes `data.js`
- `scripts/digest.py` — calls the LLM to add Chinese key points and translations per sector, writes back to `data.js`
- `scripts/llm.py` — unified LLM entry point (`claude-cli` or OpenAI-compatible API)
- `scripts/build_sources.py` — rebuilds and validates `sources.json` with live liveness checks
- `sources.json` — 12 sectors, 108 sources, fetch windows, and redline keyword filters
- `llm.config.json` — LLM provider selection (`claude-cli` or `api`) and credentials
- `data.js` — generated data file (raw items after fetch; enriched with LLM output after digest)
- `index.html` — single-file browser dashboard (no build step, no dependencies)

## Commands

```bash
# Start the dashboard (always from project root)
python server.py            # port 8793 (default)
python server.py 9000       # custom port

# Fetch raw data
python scripts/fetch.py

# Generate LLM summaries (run after fetch)
python scripts/digest.py

# Syntax check only (no network, no LLM)
python -m py_compile server.py scripts/*.py

# Validate data.js structure after fetch/digest changes
python scripts/fetch.py && python scripts/digest.py && python -c "import json; json.load(open('data.js'))"
```

## Configuration

Edit `llm.config.json` to choose the LLM provider:

- **`claude-cli`** (default, $0) — uses local Claude Code subscription via `claude -p`. Requires `claude login` on the machine. Only works locally.
- **`api`** — OpenAI-compatible API (DeepSeek, OpenAI, SiliconFlow, OpenRouter, etc.). Works on any machine, pay-per-use.

```jsonc
{ "provider": "claude-cli" }
// or
{ "provider": "api", "api": { "base_url": "...", "api_key": "...", "model": "..." } }
```

## Adding / Modifying Sources

Sources are defined in `sources.json` — no code changes needed. Each source entry:
```jsonc
{ "name": "媒体名", "hint": "ai", "type": "rss", "url": "https://example.com/feed" }
```
`hint` maps to a sector: `ai` / `semi` / `robot` / `auto` / `energy` / `bio` / `space` / `security` / `tech` / `consumer` / `macro` / `science`.

Tuning parameters in `sources.json`:
- `fetch.recent_days` — time window (default 7 days, Beijing time)
- `redline_keywords` — compliance blocklist (gambling, prediction markets, crypto, adult; politics/finance are allowed)

## Important Notes

- **Pure standard library** — no `pip install`, no third-party Python packages.
- `claude-cli` mode spawns `claude -p --disallowedTools all`; runs text-only through the subscription.
- Some sectors may gracefully degrade (show news list without key points) if the subscription model refuses certain content. Switching to `api` mode avoids this.
- `data.js` is auto-generated — do not hand-edit except for controlled test fixtures.
- The dashboard is self-contained in `index.html` — do not split it unless a clear maintenance need arises.
- Keep API keys in environment variables (`LLM_API_KEY`), not hardcoded in `llm.config.json`.
