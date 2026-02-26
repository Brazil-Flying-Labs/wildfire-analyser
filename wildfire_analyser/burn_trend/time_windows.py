# SPDX-License-Identifier: MIT
#
# Monthly time window generation utilities.

from datetime import datetime, date
from typing import List, Dict


def _parse_date(value: str) -> date:
    return datetime.strptime(value, "%Y-%m-%d").date()


def month_windows(start_date: str, end_date: str) -> List[Dict[str, str]]:
    start = _parse_date(start_date)
    end = _parse_date(end_date)

    # Normalize to first day of start month
    current = date(start.year, start.month, 1)

    windows = []
    while current <= end:
        if current.month == 12:
            next_month = date(current.year + 1, 1, 1)
        else:
            next_month = date(current.year, current.month + 1, 1)

        windows.append({
            "month": f"{current.year:04d}-{current.month:02d}",
            "start": current.strftime("%Y-%m-%d"),
            "end": next_month.strftime("%Y-%m-%d"),
            "year": current.year,
            "month_num": current.month,
        })

        current = next_month

    return windows
