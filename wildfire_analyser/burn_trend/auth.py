# SPDX-License-Identifier: MIT
#
# Google Earth Engine authentication helpers (burn trend).

import json
from tempfile import NamedTemporaryFile
import ee


def authenticate_gee(gee_key_json: str | None) -> None:
    if not gee_key_json:
        raise RuntimeError("GEE_PRIVATE_KEY_JSON not set")

    try:
        key_dict = json.loads(gee_key_json)
    except json.JSONDecodeError as exc:
        raise ValueError("Invalid GEE_PRIVATE_KEY_JSON format") from exc

    try:
        with NamedTemporaryFile(mode="w+", suffix=".json") as handle:
            json.dump(key_dict, handle)
            handle.flush()
            credentials = ee.ServiceAccountCredentials(
                key_dict["client_email"], handle.name
            )
            ee.Initialize(credentials)
    except Exception as exc:
        raise RuntimeError("Failed to authenticate with Google Earth Engine") from exc
