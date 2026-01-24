# SPDX-License-Identifier: MIT

import argparse
import json
import os
import sys
import time
import ee
from dotenv import load_dotenv

POLL_INTERVAL_SECONDS = 15

ERROR_MSG = (
    "ERROR: Unable to monitor the Google Earth Engine task.\n"
    "Please check your GEE credentials and the provided task ID, then try again."
)

SUCCESS_MSG = (
    "\nSUCCESS: Google Earth Engine task completed successfully.\n"
)


def init_gee() -> None:
    load_dotenv()

    gee_key_json = os.getenv("GEE_PRIVATE_KEY_JSON")
    if not gee_key_json:
        raise RuntimeError("GEE_PRIVATE_KEY_JSON not set")

    key_dict = json.loads(gee_key_json)

    credentials = ee.ServiceAccountCredentials(
        key_dict["client_email"],
        key_data=json.dumps(key_dict),
    )

    ee.Initialize(credentials)


def wait_for_task(gee_task_id: str) -> None:
    while True:
        statuses = ee.data.getTaskStatus(gee_task_id)

        if not statuses:
            raise RuntimeError(f"Task '{gee_task_id}' not found")

        status = statuses[0]
        state = status.get("state")

        print(f"[GEE] task={gee_task_id} state={state}")

        if state == "COMPLETED":
            return

        if state in ("FAILED", "CANCELLED"):
            error = status.get("error_message", "Unknown error")
            raise RuntimeError(f"Task failed: {error}")

        time.sleep(POLL_INTERVAL_SECONDS)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Monitor a Google Earth Engine task until completion"
    )
    parser.add_argument("--gee-task-id", required=True)
    args = parser.parse_args()

    init_gee()

    wait_for_task(args.gee_task_id)

    print(SUCCESS_MSG)


if __name__ == "__main__":
    try:
        main()
    except Exception:
        print(ERROR_MSG, file=sys.stderr)
        sys.exit(2)
