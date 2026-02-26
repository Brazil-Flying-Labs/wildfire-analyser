# SPDX-License-Identifier: MIT
#
# GCS helpers for burn trend outputs.

import os
import json
import shutil
import subprocess
from urllib.parse import quote

import requests
from google.auth.transport.requests import Request
from google.oauth2 import service_account


def _upload_with_gcs_api_bytes(data: bytes, bucket: str, object_name: str) -> None:
    key_json = os.getenv("GEE_PRIVATE_KEY_JSON")
    if not key_json:
        raise RuntimeError("GEE_PRIVATE_KEY_JSON not set")

    try:
        key_info = json.loads(key_json)
    except Exception as exc:
        raise RuntimeError("GEE_PRIVATE_KEY_JSON is not valid JSON") from exc

    credentials = service_account.Credentials.from_service_account_info(
        key_info,
        scopes=["https://www.googleapis.com/auth/devstorage.read_write"],
    )
    credentials.refresh(Request())
    token = credentials.token
    if not token:
        raise RuntimeError("Failed to obtain GCS access token")

    name = quote(object_name, safe="")
    url = f"https://storage.googleapis.com/upload/storage/v1/b/{bucket}/o?uploadType=media&name={name}"
    response = requests.post(
        url,
        data=data,
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/octet-stream",
        },
        timeout=120,
    )

    if response.status_code >= 300:
        raise RuntimeError(
            f"GCS API upload failed ({response.status_code}): {response.text[:300]}"
        )


def upload_file_to_gcs(local_path: str, bucket: str, object_name: str) -> dict:
    if not bucket:
        raise RuntimeError("GCS bucket not provided")

    if shutil.which("gsutil") is not None:
        target = f"gs://{bucket}/{object_name}"
        subprocess.run(["gsutil", "cp", local_path, target], check=True)
    else:
        with open(local_path, "rb") as fp:
            _upload_with_gcs_api_bytes(fp.read(), bucket, object_name)

    return {
        "url": f"https://storage.googleapis.com/{bucket}/{object_name}",
    }


def upload_bytes_to_gcs(data: bytes, bucket: str, object_name: str) -> dict:
    if not bucket:
        raise RuntimeError("GCS bucket not provided")

    _upload_with_gcs_api_bytes(data, bucket, object_name)

    return {
        "url": f"https://storage.googleapis.com/{bucket}/{object_name}",
    }
