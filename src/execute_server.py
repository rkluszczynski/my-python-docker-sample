"""FastAPI server for starting the batch job and exposing its results."""

from datetime import datetime, timezone
from pathlib import Path
from threading import Lock, Thread
from typing import Any

from fastapi import FastAPI, status
from fastapi.responses import FileResponse, JSONResponse

from src.execute_batch import RESULTS_DIRECTORY, main

RESULT_FILE_GLOB = "result-at-*.json"

app = FastAPI()
SERVER_STARTED_AT = datetime.now(timezone.utc).isoformat()
agent_started_at: str | None = None
agent_finished_at: str | None = None
agent_finished_with_error: str | None = None
batch_lock = Lock()
state_lock = Lock()
batch_thread: Thread | None = None


def set_agent_state(
    *,
    started_at: str | None = None,
    finished_at: str | None = None,
    finished_with_error: str | None = None,
) -> None:
    """Store the current batch lifecycle timestamps and any error message."""
    global agent_finished_at, agent_started_at, agent_finished_with_error

    with state_lock:
        agent_started_at = started_at
        agent_finished_at = finished_at
        agent_finished_with_error = finished_with_error


def get_agent_state() -> dict[str, Any]:
    """Build the current server and batch status payload."""
    with state_lock:
        return {
            "server_started_at": SERVER_STARTED_AT,
            "agent_started_at": agent_started_at,
            "agent_finished_at": agent_finished_at,
            "agent_status": "running" if batch_lock.locked() else "idle",
            "agent_finished_with_error": agent_finished_with_error,
        }


def list_result_files() -> list[Path]:
    """Return result files sorted from newest to oldest."""
    return sorted(
        RESULTS_DIRECTORY.glob(RESULT_FILE_GLOB),
        key=lambda path: path.name,
        reverse=True,
    )


def run_batch() -> None:
    """Execute the batch job and update its final state."""
    try:
        main()
    except Exception as exc:  # pragma: no cover - runtime failure reporting
        set_agent_state(
            started_at=None,
            finished_at=datetime.now(timezone.utc).isoformat(),
            finished_with_error=str(exc),
        )
        raise
    else:
        set_agent_state(
            started_at=None,
            finished_at=datetime.now(timezone.utc).isoformat(),
            finished_with_error=None,
        )
    finally:
        batch_lock.release()


@app.get("/status")
def status_endpoint() -> JSONResponse:
    """Return the current server and batch execution status."""
    return JSONResponse(content=get_agent_state(), status_code=status.HTTP_200_OK)


@app.post("/start")
def start() -> JSONResponse:
    """Start the batch job in a background thread when idle."""
    global batch_thread

    if not batch_lock.acquire(blocking=False):
        return JSONResponse(
            content={"error": "agent is already running"},
            status_code=status.HTTP_406_NOT_ACCEPTABLE,
        )

    set_agent_state(
        started_at=datetime.now(timezone.utc).isoformat(),
        finished_at=None,
        finished_with_error=None,
    )
    batch_thread = Thread(target=run_batch, daemon=True)
    batch_thread.start()

    return JSONResponse(
        content={"status": "agent started"},
        status_code=status.HTTP_202_ACCEPTED,
    )


@app.get("/results")
def list_results() -> JSONResponse:
    """List generated result files and their download URLs."""
    return JSONResponse(
        content={
            "results": [
                {
                    "file_name": result_file.name,
                    "download_url": f"/results/{result_file.name}",
                }
                for result_file in list_result_files()
            ]
        },
        status_code=status.HTTP_200_OK,
    )


@app.get("/results/{result_file_name}")
def download_result(result_file_name: str):
    """Return a single result file when the requested name is valid."""
    if Path(result_file_name).name != result_file_name or not result_file_name.endswith(".json"):
        return JSONResponse(
            content={"error": "invalid result file name"},
            status_code=status.HTTP_400_BAD_REQUEST,
        )

    result_path = RESULTS_DIRECTORY / result_file_name
    if not result_path.is_file():
        return JSONResponse(
            content={"error": "result file not found"},
            status_code=status.HTTP_404_NOT_FOUND,
        )

    return FileResponse(
        result_path,
        media_type="application/json",
        filename=result_file_name,
    )
