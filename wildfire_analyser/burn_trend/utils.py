# SPDX-License-Identifier: MIT
#
# Shared helpers for burn trend pipeline.

from datetime import datetime
import uuid


DEFAULT_SCALE = 10


def generate_object_name(prefix: str, start_date: str, end_date: str) -> str:
    ts = datetime.utcnow().strftime("%Y%m%dT%H%M%S")
    uid = uuid.uuid4().hex[:8]
    start_norm = start_date.replace("-", "_")
    end_norm = end_date.replace("-", "_")
    return f"{prefix}_{start_norm}_{end_norm}_{ts}_{uid}"
