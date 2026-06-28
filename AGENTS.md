# Repository Guidelines

## Project Structure & Module Organization

This repository is a local investment-news dashboard with no build step and no third-party Python dependencies.

- `index.html` is the single-page browser dashboard.
- `server.py` serves the dashboard and exposes `/api/refresh`.
- `scripts/fetch.py` reads `sources.json`, fetches RSS/Atom items, filters them, and writes `data.js`.
- `scripts/digest.py` enriches `data.js` with LLM-generated Chinese key points and translations.
- `scripts/llm.py` centralizes `claude-cli` and OpenAI-compatible API calls.
- `sources.json` defines sectors, sources, fetch windows, and redline keywords.
- `llm.config.json` selects the LLM provider. Do not commit real API keys.
- `docs/screenshot.png` is the README/dashboard screenshot.

There is no dedicated `tests/` directory; validate changes with the commands below.

## Build, Test, and Development Commands

- `python server.py` starts the local dashboard on `http://localhost:8793`.
- `python server.py 9000` starts it on a custom port.
- `python scripts/fetch.py` regenerates `data.js` from configured sources.
- `python scripts/digest.py` adds LLM summaries/translations to `data.js`.
- `python -m py_compile server.py scripts/*.py` checks Python syntax without running network or LLM calls.

Use `python` or `python3` according to your environment. Refreshes require internet access; `digest.py` also requires Claude CLI login or an API provider.

## Coding Style & Naming Conventions

Keep Python compatible with Python 3.7+ and the standard library. Match the existing compact style: module-level constants in `UPPER_CASE`, helpers in `snake_case`, and JSON keys in lower snake case where practical. Avoid hand-editing generated `data.js` except for controlled fixtures or emergency corrections.

For frontend changes, keep the dashboard self-contained in `index.html` unless a clear maintenance need justifies splitting files.

## Testing Guidelines

Before opening a PR, run `python -m py_compile server.py scripts/*.py`. For source or pipeline changes, run `python scripts/fetch.py` and inspect `data.js` for valid payload structure. For UI/server changes, run `python server.py`, open the dashboard, and verify refresh behavior if `/api/refresh` changed.

## Commit & Pull Request Guidelines

Recent commits use Conventional Commit-style prefixes such as `feat:`, `fix:`, and `docs:`. Follow that pattern with concise, imperative summaries, for example `fix: preserve source URLs during digest`.

Pull requests should describe the user-facing change, list validation commands, and note LLM/provider assumptions. Include screenshots for visible dashboard changes. Mention `sources.json` updates separately so reviewers can assess source quality and compliance filtering.

## Security & Configuration Tips

Keep API keys in environment variables such as `LLM_API_KEY`, not in `llm.config.json`. Respect source terms of service, avoid high-frequency refresh loops, and preserve the project's local-only data model.
