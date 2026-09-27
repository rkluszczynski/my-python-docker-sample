# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with
code in this repository.

## Project overview

A containerized Python 3.14 service: a FastAPI server (`src/execute_server.py`)
that starts a batch job (`src/execute_batch.py`) in a background thread, reports
its status, and serves the JSON result files. Full requirements and design
decisions are in `ADR.md` — keep it in sync with any behavioural change.

## Commands

```bash
# Set up the environment
python3 -m venv .venv && . .venv/bin/activate
pip install -r requirements.txt

# Run the server (always from the repository root)
python -m uvicorn src.execute_server:app --host 0.0.0.0 --port 9000

# Run the batch job standalone
python src/execute_batch.py

# Syntax check
python -m compileall src

# Docker
docker build -t python-docker-sample .
docker run --rm -p 9000:9000 python-docker-sample

# Smoke test a running server
curl -i localhost:9000/status
curl -i -X POST localhost:9000/start
curl -i localhost:9000/results
```

There is no test suite or linter configured yet.

## Architecture

- `execute_batch.main()` prints `Hello, world!`, sleeps 2–10 s, writes
  `/tmp/agent-results/result-at-<YYYYMMDDTHHMMSS>.json`, and prunes old results
  to `RESULTS_TO_KEEP` (read from `.env`, default `7`).
- `execute_server` holds in-memory state guarded by two locks:
  `batch_lock` (single active run) and `state_lock` (timestamps).
- Endpoints: `GET /status` (200), `POST /start` (202 / 406 when already
  running), `GET /results` (200), `GET /results/{name}` (200 / 400 / 404).

## Coding guidelines

- Follow the Google Python Style Guide.
- Everything in code is in English: identifiers, docstrings, comments, log and
  error messages, API payloads.
- Every module and function has a short docstring.
- Use type hints; prefer `pathlib.Path` and `datetime` with explicit time zones
  for API timestamps (UTC ISO 8601).
- Keep dependencies minimal and pinned in `requirements.txt`. Do not list or
  import `starlette` directly — use `fastapi` / `fastapi.responses`.
- Do not annotate an endpoint's return type with a union of response classes
  (e.g. `JSONResponse | FileResponse`); FastAPI fails at startup. Omit the
  annotation or pass `response_model=None`.
- Return explicit HTTP status codes via `fastapi.status` constants.
- Validate user-supplied file names to prevent path traversal.
- Imports inside `src/` use the `src.` package prefix because the app is started
  as `src.execute_server:app` from the repository root.
- Keep the Dockerfile running Uvicorn directly (no shell wrapper scripts) and
  keep the server single-process (in-memory state).

## Workflow rules

- Make minimal, focused changes; do not add frameworks or tools unless asked.
- After changes, run `python -m compileall src` and, when dependencies are
  available, start the server and smoke test the affected endpoints.
- Update `README.md` and `ADR.md` when behaviour, endpoints, configuration, or
  files change.
- Never commit `.env` or generated `result-at-*.json` files.
