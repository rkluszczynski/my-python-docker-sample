# Python Batch Agent Sample

This repository contains a small Python application composed of:

1. a batch job that prints `Hello, world!`, waits for a random number of seconds, and writes a JSON result file
2. a FastAPI server that starts the batch job asynchronously and exposes status and result endpoints
3. a Docker setup for running the HTTP server on port `9000`

## Repository structure

```text
.
├── Dockerfile
├── README.md
├── requirements.txt
└── src
    ├── execute_batch.py
    └── execute_server.py
```

## Batch job

`src/execute_batch.py`:

- prints `Hello, world!`
- sleeps for a random time from 2 to 10 seconds
- writes a JSON file to `/tmp/agent-results`
- keeps only the newest result files according to `RESULTS_TO_KEEP`

Example result file:

```json
{
  "created_at": "20260927T001559",
  "sleep_seconds": 9
}
```

## Configuration

The application reads an optional `.env` file from the working directory.

Supported variable:

```env
RESULTS_TO_KEEP=7
```

If the variable is missing or invalid, the default value `7` is used.

## HTTP API

The FastAPI server is defined in `src/execute_server.py`.

### `GET /status`

Returns the current server and agent state.

### `POST /start`

Starts the batch job in a background thread.

- returns `202 Accepted` when the job starts
- returns `406 Not Acceptable` when a job is already running

### `GET /results`

Returns a list of available JSON result files.

### `GET /results/{file_name}`

Downloads a single JSON result file.

## Running locally

```bash
python3 -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
python -m uvicorn src.execute_server:app --host 0.0.0.0 --port 9000
```

## Running with Docker

```bash
docker build -t python-batch-agent .
docker run --rm -p 9000:9000 python-batch-agent
```
