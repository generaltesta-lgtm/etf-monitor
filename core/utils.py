"""Shared utilities for ETF Monitor."""

from datetime import datetime, timezone
from typing import Union

import pytz

ROME_TZ = pytz.timezone("Europe/Rome")


def rome_now() -> datetime:
    """Return the current time in Europe/Rome timezone."""
    return datetime.now(ROME_TZ)


def fmt_rome(dt: Union[datetime, None]) -> str:
    """Format a datetime object in Rome timezone for display.

    If the datetime is naive or in UTC, it is converted to Rome time.
    Returns 'N/A' if dt is None.
    """
    if dt is None:
        return "N/A"
    if isinstance(dt, str):
        return dt
    try:
        if dt.tzinfo is None or dt.tzinfo.utcoffset(dt) is None:
            dt = dt.replace(tzinfo=timezone.utc)
        rome_dt = dt.astimezone(ROME_TZ)
        return rome_dt.strftime("%H:%M:%S")
    except Exception:
        return str(dt)


def fmt_rome_date(dt: Union[datetime, None], fmt: str = "%Y-%m-%d %H:%M") -> str:
    """Format a datetime in Rome timezone with a custom format string."""
    if dt is None:
        return "N/A"
    try:
        if dt.tzinfo is None or dt.tzinfo.utcoffset(dt) is None:
            dt = dt.replace(tzinfo=timezone.utc)
        rome_dt = dt.astimezone(ROME_TZ)
        return rome_dt.strftime(fmt)
    except Exception:
        return str(dt)