# ADR-001: Python batch agent with FastAPI control server

- **Status:** Accepted
- **Date:** 2026-09-27

## Context

We need a small, containerized Python service that runs a batch job on demand,
reports its status over HTTP, and exposes the JSON results produced by the job.
Only one batch run may be active at a time. The number of stored results must be
limited and configurable.

## Decision

Implement the project with Python 3.14, FastAPI, and Uvicorn. The batch logic
lives in a plain Python module that can also be run standalone. The HTTP server
imports and runs the batch in a background thread. The Docker image runs the
server directly with Uvicorn (no shell wrapper script).

## Requirements per file

The following requirements are sufficient to recreate the project from scratch.

### `src/execute_batch.py` — batch job

1. Module docstring in English.
2. Constants:
   - `DEFAULT_RESULTS_TO_KEEP = 7`
   - `RESULTS_TO_KEEP_ENV_NAME = "RESULTS_TO_KEEP"`
   - `RESULTS_DIRECTORY = Path("/tmp/agent-results")`
   - `RESULT_FILE_PREFIX = "result-at-"`
   - `RESULT_FILE_GLOB = "result-at-*.json"`
3. `load_results_to_keep() -> int`:
   - Reads `.env` from the current working directory using only the standard
     library (no `python-dotenv`).
   - Ignores empty lines and lines starting with `#`.
   - Returns the integer value of `RESULTS_TO_KEEP`.
   - Returns `7` if the file does not exist, the key is missing, the value is not
     an integer, or the value is `<= 0`.
4. `prune_old_results(results_to_keep: int) -> None`:
   - Sorts `result-at-*.json` files in `RESULTS_DIRECTORY` by name, newest first
     (the timestamp format makes lexicographic order chronological).
   - Deletes every file beyond the newest `results_to_keep`.
5. `main() -> None`:
   - Prints exactly `Hello, world!`.
   - Draws a random integer of seconds from 2 to 10 (inclusive) and sleeps.
   - Creates `RESULTS_DIRECTORY` if missing.
   - Writes `result-at-<YYYYMMDDTHHMMSS>.json` (local time, e.g.
     `result-at-20260927T001423.json`) with the content:
     ```json
     {"created_at": "20260927T001423", "sleep_seconds": 7}
     ```
   - Prunes old results after writing.
6. Runnable standalone: `if __name__ == "__main__": main()`.

### `src/execute_server.py` — FastAPI server

1. Module docstring in English; imports `main` and `RESULTS_DIRECTORY` from
   `src.execute_batch` (the app is started from the repository root as
   `src.execute_server:app`).
2. Module-level state:
   - `SERVER_STARTED_AT` — UTC ISO 8601 timestamp captured at import time.
   - `agent_started_at`, `agent_finished_at` — `str | None`.
   - `batch_lock` — `threading.Lock` guaranteeing a single active batch run.
   - `state_lock` — `threading.Lock` protecting the timestamps.
3. Background execution: `run_batch()` calls `main()` and, in `finally`, sets
   `agent_started_at = None`, `agent_finished_at = <UTC now>` and releases
   `batch_lock`.
4. Endpoints (all responses are JSON unless a file is downloaded):

   | Method | Path | Success | Errors |
   |---|---|---|---|
   | `GET` | `/status` | `200` with `server_started_at`, `agent_started_at`, `agent_finished_at`, `agent_status` (`running` / `idle`) | — |
   | `POST` | `/start` | `202` with `{"status": "agent started"}` | `406` with `{"error": "agent is already running"}` |
   | `GET` | `/results` | `200` with `{"results": [{"file_name", "download_url"}]}`, newest first | — |
   | `GET` | `/results/{result_file_name}` | `200`, file download, `application/json` | `400` invalid name (path traversal or not `.json`), `404` not found |

5. `/start` acquires `batch_lock` non-blocking, sets `agent_started_at` to UTC
   now, clears `agent_finished_at`, and starts a daemon `Thread`.
6. Endpoints returning different response classes (`JSONResponse` or
   `FileResponse`) must **not** use a union return annotation — FastAPI would
   try to build a Pydantic response model and fail at startup. Omit the
   annotation or use `response_model=None`.

### `requirements.txt`

Pinned, direct dependencies only (Starlette comes transitively with FastAPI and
must not be listed or imported directly):

```text
fastapi==0.116.1
uvicorn==0.35.0
```

### `Dockerfile`

1. Base image `python:3.14-slim`, `WORKDIR /app`.
2. Copy `requirements.txt` first and install with `--no-cache-dir` (layer
   caching), then copy `src/`.
3. `EXPOSE 9000`.
4. `CMD ["python", "-m", "uvicorn", "src.execute_server:app", "--host", "0.0.0.0", "--port", "9000"]`.
5. `.env` is not baked into the image; mount it to `/app/.env` to override
   `RESULTS_TO_KEEP`.

### `build_and_run_image.sh`

Helper script that stops/removes the previous container, builds the image
`python-docker-sample:latest`, and runs it mapping host port `9011` to
container port `9000`.

### `.env` (optional, not committed)

```env
RESULTS_TO_KEEP=5
```

### `.gitignore`

Standard Python ignores: bytecode, build artifacts, virtual environments,
test/lint caches, `.env*`, IDE files (`.idea/`, `.vscode/`, `*.iml`),
`.DS_Store`, and local `result-at-*.json` artifacts.

### `README.md`

English description of the repository: purpose, structure, batch behaviour,
configuration, HTTP API, and how to run locally and with Docker.

## Consequences

- **Positive:** minimal dependencies, simple deployment, single-run guarantee
  without external infrastructure.
- **Negative:** state is in-memory and per-process — running Uvicorn with
  multiple workers breaks the single-run guarantee and status reporting; results
  in `/tmp` are lost when the container is removed unless a volume is mounted.
