"""Data loading for the wind forecast decision support app.

This is the only module in the project that reads files from disk. It loads
the raw JSON produced by ``scripts/fetch_data.py`` and parses the ISO-8601
UTC timestamps into timezone-aware ``datetime`` objects so that every
downstream module works with proper datetimes instead of strings.

The data directory is resolved from the ``DATA_DIR`` environment variable.
When unset it defaults to the ``data/`` folder next to the repository root,
located relative to this file (no hard-coded absolute paths).
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

# This file lives at backend/app/loader.py, so the repo root is two parents up.
_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
_DEFAULT_DATA_DIR = _REPO_ROOT / "data"


def _data_dir() -> Path:
    """Return the directory containing the JSON data files.

    Honours the ``DATA_DIR`` environment variable; falls back to the
    repository-root ``data/`` folder resolved relative to this file.
    """
    env = os.environ.get("DATA_DIR")
    if env:
        return Path(env)
    return _DEFAULT_DATA_DIR


@dataclass(frozen=True)
class ActualsRow:
    """One 30-minute actual generation reading (FUELHH, fuelType=WIND)."""

    startTime: datetime  # e.g. 2025-12-31T00:00:00Z
    generation: float  # MW
    settlementDate: str
    settlementPeriod: int
    fuelType: str


@dataclass(frozen=True)
class ForecastRow:
    """One hourly forecast reading (WINDFOR)."""

    publishTime: datetime
    startTime: datetime
    generation: float  # MW


def _parse_utc(value: str) -> datetime:
    """Parse an ISO-8601 UTC timestamp into a timezone-aware datetime.

    Handles the trailing ``Z`` suffix used by Elexon data.
    """
    text = value.strip()
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    dt = datetime.fromisoformat(text)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def _load_json(filename: str) -> list[dict]:
    """Read and JSON-parse a data file from the data directory."""
    path = _data_dir() / filename
    with open(path, "r", encoding="utf-8") as fh:
        data = json.load(fh)
    if not isinstance(data, list):
        raise ValueError(f"{filename}: expected a JSON list, got {type(data).__name__}")
    return data


def load_actuals() -> list[ActualsRow]:
    """Load ``actuals.json`` into a list of :class:`ActualsRow`.

    The file is expected to contain FUELHH rows for fuelType=WIND. Rows whose
    ``fuelType`` is not WIND are skipped, since they are outside the scope of
    this app (see SPEC.md).
    """
    rows: list[ActualsRow] = []
    for raw in _load_json("actuals.json"):
        if raw.get("fuelType") != "WIND":
            continue
        rows.append(
            ActualsRow(
                startTime=_parse_utc(raw["startTime"]),
                generation=float(raw["generation"]),
                settlementDate=str(raw["settlementDate"]),
                settlementPeriod=int(raw["settlementPeriod"]),
                fuelType=str(raw["fuelType"]),
            )
        )
    return rows


def load_forecasts() -> list[ForecastRow]:
    """Load ``forecasts.json`` into a list of :class:`ForecastRow`.

    Every row is parsed; the caller is responsible for filtering by horizon
    and publish time (see :mod:`decision`).
    """
    rows: list[ForecastRow] = []
    for raw in _load_json("forecasts.json"):
        rows.append(
            ForecastRow(
                publishTime=_parse_utc(raw["publishTime"]),
                startTime=_parse_utc(raw["startTime"]),
                generation=float(raw["generation"]),
            )
        )
    return rows