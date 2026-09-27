"""Batch job that produces timestamped JSON result files."""

import json
from datetime import datetime, timezone
from pathlib import Path
from random import randint
from time import sleep

DEFAULT_RESULTS_TO_KEEP = 7
RESULTS_TO_KEEP_ENV_NAME = "RESULTS_TO_KEEP"
RESULTS_DIRECTORY = Path("/tmp/agent-results")
RESULT_FILE_PREFIX = "result-at-"
RESULT_FILE_GLOB = f"{RESULT_FILE_PREFIX}*.json"


def load_results_to_keep() -> int:
    """Load the configured number of result files to keep."""
    env_path = Path.cwd() / ".env"
    if not env_path.exists():
        return DEFAULT_RESULTS_TO_KEEP

    for line in env_path.read_text(encoding="utf-8").splitlines():
        stripped_line = line.strip()
        if not stripped_line or stripped_line.startswith("#"):
            continue

        key, separator, value = stripped_line.partition("=")
        if key.strip() != RESULTS_TO_KEEP_ENV_NAME or not separator:
            continue

        try:
            parsed_value = int(value.strip())
        except ValueError:
            return DEFAULT_RESULTS_TO_KEEP

        return parsed_value if parsed_value > 0 else DEFAULT_RESULTS_TO_KEEP

    return DEFAULT_RESULTS_TO_KEEP


def prune_old_results(results_to_keep: int) -> None:
    """Delete result files that exceed the configured retention limit."""
    result_files = sorted(
        RESULTS_DIRECTORY.glob(RESULT_FILE_GLOB),
        key=lambda path: path.name,
        reverse=True,
    )
    for result_file in result_files[results_to_keep:]:
        result_file.unlink()


def main() -> None:
    """Run the batch job and write its JSON result file."""
    print("Hello, world!")
    sleep_seconds = randint(2, 10)
    sleep(sleep_seconds)
    results_to_keep = load_results_to_keep()
    RESULTS_DIRECTORY.mkdir(parents=True, exist_ok=True)

    result_timestamp = datetime.now().strftime("%Y%m%dT%H%M%S")
    result_path = RESULTS_DIRECTORY / f"{RESULT_FILE_PREFIX}{result_timestamp}.json"
    result_payload = {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "sleep_seconds": sleep_seconds,
    }
    result_path.write_text(json.dumps(result_payload), encoding="utf-8")
    prune_old_results(results_to_keep)


if __name__ == "__main__":
    main()
