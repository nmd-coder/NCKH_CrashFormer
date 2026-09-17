"""Collect Open-Meteo historical weather and aggregate it into 6-hour H3 bins.

Example:
    python collect_weather.py \
        --cells data/processed/pilots/chuong_duong/cells.parquet \
        --output data/processed/pilots/chuong_duong/weather.parquet
"""

from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

import pandas as pd
import requests


API_URL = "https://archive-api.open-meteo.com/v1/archive"
HOURLY_FIELDS = [
    "temperature_2m",
    "precipitation",
    "visibility",
    "wind_speed_10m",
    "relative_humidity_2m",
]


def fetch_hourly(
    *,
    h3_index: str,
    latitude: float,
    longitude: float,
    start_date: str,
    end_date: str,
    cache_dir: Path,
    timezone: str,
) -> pd.DataFrame:
    cache_path = cache_dir / f"{h3_index}_{start_date}_{end_date}.json"
    if cache_path.exists():
        payload = json.loads(cache_path.read_text(encoding="utf-8"))
    else:
        params = {
            "latitude": latitude,
            "longitude": longitude,
            "start_date": start_date,
            "end_date": end_date,
            "hourly": ",".join(HOURLY_FIELDS),
            "timezone": timezone,
            "wind_speed_unit": "ms",
        }
        last_error: Exception | None = None
        for attempt in range(1, 4):
            try:
                response = requests.get(API_URL, params=params, timeout=90)
                response.raise_for_status()
                payload = response.json()
                if payload.get("error"):
                    raise ValueError(payload.get("reason", "Open-Meteo returned an unspecified error."))
                cache_dir.mkdir(parents=True, exist_ok=True)
                cache_path.write_text(json.dumps(payload), encoding="utf-8")
                break
            except (requests.RequestException, ValueError) as error:
                last_error = error
                if attempt == 3:
                    raise RuntimeError(f"{h3_index}: Open-Meteo request failed after 3 attempts: {error}") from error
                time.sleep(attempt * 2)
        else:  # pragma: no cover - loop either breaks or raises
            raise RuntimeError(f"{h3_index}: {last_error}")

    hourly = payload.get("hourly")
    if not isinstance(hourly, dict):
        raise ValueError(f"{h3_index}: response does not contain hourly data.")
    required = ["time", *HOURLY_FIELDS]
    missing = [field for field in required if field not in hourly]
    if missing:
        raise ValueError(f"{h3_index}: API response is missing requested fields: {missing}")

    frame = pd.DataFrame({field: hourly[field] for field in required})
    if frame.empty or frame[required].isna().any().any():
        raise ValueError(f"{h3_index}: hourly weather contains missing values.")

    # The API returns local civil time because timezone is requested explicitly.
    frame["occurred_at"] = pd.to_datetime(frame.pop("time")).dt.tz_localize(timezone)
    frame["h3_index"] = h3_index
    return frame


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cells", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--start-date", default="2019-01-01")
    parser.add_argument("--end-date", default="2025-12-31")
    parser.add_argument("--timezone", default="Asia/Ho_Chi_Minh")
    parser.add_argument("--cache-dir", type=Path, default=Path("data/raw/weather/open_meteo"))
    parser.add_argument("--pause-seconds", type=float, default=0.15)
    args = parser.parse_args()

    cells = pd.read_parquet(args.cells)
    required_columns = {"h3_index", "centroid_lat", "centroid_lon"}
    missing_columns = required_columns - set(cells.columns)
    if missing_columns:
        raise ValueError(f"Cells file missing columns: {sorted(missing_columns)}")
    if cells["h3_index"].duplicated().any():
        raise ValueError("Cells file contains duplicate h3_index values.")

    all_hourly = []
    for position, row in enumerate(cells.itertuples(index=False), start=1):
        hourly = fetch_hourly(
            h3_index=row.h3_index,
            latitude=float(row.centroid_lat),
            longitude=float(row.centroid_lon),
            start_date=args.start_date,
            end_date=args.end_date,
            cache_dir=args.cache_dir,
            timezone=args.timezone,
        )
        all_hourly.append(hourly)
        print(f"Collected {position}/{len(cells)} H3 cells")
        if position < len(cells):
            time.sleep(args.pause_seconds)

    hourly = pd.concat(all_hourly, ignore_index=True)
    hourly["time_bin_dt"] = hourly["occurred_at"].dt.floor("6h")
    weather = (
        hourly.groupby(["h3_index", "time_bin_dt"], as_index=False)
        .agg(
            temp_mean=("temperature_2m", "mean"),
            precipitation_sum=("precipitation", "sum"),
            visibility_min=("visibility", "min"),
            wind_speed_max=("wind_speed_10m", "max"),
            humidity_mean=("relative_humidity_2m", "mean"),
        )
    )
    weather["time_bin"] = weather.pop("time_bin_dt").map(lambda timestamp: timestamp.isoformat())
    weather = weather[
        [
            "h3_index",
            "time_bin",
            "temp_mean",
            "precipitation_sum",
            "visibility_min",
            "wind_speed_max",
            "humidity_mean",
        ]
    ]

    expected_bins_per_cell = ((pd.Timestamp(args.end_date) - pd.Timestamp(args.start_date)).days + 1) * 4
    actual_counts = weather.groupby("h3_index").size()
    if not (actual_counts == expected_bins_per_cell).all():
        bad_cells = actual_counts[actual_counts != expected_bins_per_cell].to_dict()
        raise ValueError(f"Unexpected 6-hour-bin count; expected {expected_bins_per_cell} per cell, got {bad_cells}")
    if weather.duplicated(["h3_index", "time_bin"]).any() or weather.isna().any().any():
        raise ValueError("Weather output has duplicate keys or null values.")

    args.output.parent.mkdir(parents=True, exist_ok=True)
    weather.to_parquet(args.output, index=False, compression="zstd")
    print(f"Created {args.output}; rows={len(weather)}; bins_per_cell={expected_bins_per_cell}")


if __name__ == "__main__":
    main()
