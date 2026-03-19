# SPDX-License-Identifier: MIT
# Copyright (C) 2025 Marcelo Camargo.
#
# Google Earth Engine authentication helpers.


import ee
import json
from tempfile import NamedTemporaryFile


def authenticate_gee(gee_key_json: str | None = None) -> None:
    """Authenticate Google Earth Engine using a service account JSON payload."""

    try:
        key_dict = json.loads(gee_key_json)
    except json.JSONDecodeError as e:
        raise ValueError("Invalid GEE_PRIVATE_KEY_JSON format") from e

    try:
        with NamedTemporaryFile(mode="w+", suffix=".json") as f:
            json.dump(key_dict, f)
            f.flush()
            credentials = ee.ServiceAccountCredentials(
                key_dict["client_email"], f.name
            )
            ee.Initialize(credentials)
    except Exception as e:
        raise RuntimeError(
            "Failed to authenticate with Google Earth Engine") from e
