# Python Batch Agent Sample

This repository contains a small Python service composed of:

1. a batch job that prints `Hello, world!`, waits for a random number of seconds, and writes a JSON result file,
2. a FastAPI server that starts the batch job in a background thread and exposes status and result endpoints,
3. a Docker setup for running the HTTP server on port `9000`.

## Repository structure

```text
.
├── ADR.md
├── CLAUDE.md
├── Dockerfile
├── README.md
├── build_and_run_image.sh
├── requirements.txt
├── src
│   ├── execute_batch.py
│   └── execute_server.py
└── .gitignore
```

## Batch job

`src/execute_batch.py`:

- prints exactly `Hello, world!`
- sleeps for a random time from 2 to 10 seconds
- creates `/tmp/agent-results` if it does not exist
- writes a JSON file to `/tmp/agent-results`
- keeps only the newest result files according to `RESULTS_TO_KEEP`
- reads an optional `.env` file from the current working directory

Example result file written by the batch job:

```json
{
  "created_at": "2026-09-27T00:15:59.123456+00:00",
  "sleep_seconds": 9
}
```

The file name format is `result-at-YYYYMMDDTHHMMSS.json`, while the `created_at` field is a UTC ISO 8601 timestamp. The retention limit defaults to `7` when the environment variable is missing or invalid.

## Configuration

The application reads an optional `.env` file from the working directory.

Supported variable:

```env
RESULTS_TO_KEEP=7
```

If the variable is missing, invalid, or not greater than zero, the default value `7` is used.

## HTTP API

The FastAPI server is defined in `src/execute_server.py` and is meant to be started from the repository root as `src.execute_server:app`.

### `GET /status`

Returns the current server and agent state:

```json
{
  "server_started_at": "2026-09-27T00:00:00+00:00",
  "agent_started_at": "2026-09-27T00:15:40+00:00",
  "agent_finished_at": null,
  "agent_status": "running",
  "agent_finished_with_error": null
}
```

If the batch exits with an exception, `agent_finished_with_error` contains the exception message and `agent_finished_at` is set to the UTC completion time.

### `POST /start`

Starts the batch job in a background thread.

- returns `202 Accepted` with `{"status": "agent started"}` when the job starts
- returns `406 Not Acceptable` with `{"error": "agent is already running"}` when a job is already active

### `GET /results`

Returns a JSON object with a list of generated result files, ordered newest first:

```json
{
  "results": [
    {
      "file_name": "result-at-20260927T001559.json",
      "download_url": "/results/result-at-20260927T001559.json"
    }
  ]
}
```

### `GET /results/{file_name}`

Downloads a single JSON result file when the name is valid.

- returns `400 Bad Request` with `{"error": "invalid result file name"}` for path traversal attempts or names not ending in `.json`
- returns `404 Not Found` with `{"error": "result file not found"}` when the file does not exist

## Running locally

From the repository root:

```bash
python3 -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
python -m uvicorn src.execute_server:app --host 0.0.0.0 --port 9000
```

## Running with Docker

```bash
docker build -t python-docker-sample .
docker run --rm -p 9000:9000 python-docker-sample
```

A helper script is also available:

```bash
./build_and_run_image.sh
```

It stops the previous container, builds the image as `python-docker-sample:latest`, and runs it on host port `9011` mapped to container port `9000`.
