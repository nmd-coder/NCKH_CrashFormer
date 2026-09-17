"""Convert downloaded ERA5 NetCDF files into Track B 6-hour weather features.

This script is intentionally for a downloaded CDS batch, for example January--
April 2019.  It assigns each H3 cell to its nearest ERA5 grid point, converts
ERA5 units, and aggregates hourly values in Viet Nam local time.

Example:
    python ingest_era5_weather.py ^
      --cells data\\processed\\pilots\\chuong_duong\\cells.parquet ^
      --source-dir data\\raw\\weather\\era5\\chuong_duong\\2019_01_04 ^
      --output data\\processed\\pilots\\chuong_duong\\weather_2019_01_04.parquet
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd
import xarray as xr


LOCAL_TIMEZONE = "Asia/Ho_Chi_Minh"


def open_one(source_dir: Path, marker: str) -> xr.Dataset:
    matches = sorted(source_dir.glob(f"*{marker}*.nc"))
    if len(matches) != 1:
        raise ValueError(f"Expected exactly one '*{marker}*.nc' in {source_dir}; found {len(matches)}")
    return xr.open_dataset(matches[0])


def required(dataset: xr.Dataset, names: set[str], filename_kind: str) -> None:
    missing = names - set(dataset.data_vars)
    if missing:
        raise ValueError(f"{filename_kind} file is missing variables: {sorted(missing)}")


def relative_humidity_percent(temp_c: pd.Series, dewpoint_c: pd.Series) -> pd.Series:
    """Magnus approximation using ERA5 2m temperature and dewpoint."""
    numerator = 17.625 * dewpoint_c / (243.04 + dewpoint_c)
    denominator = 17.625 * temp_c / (243.04 + temp_c)
    return (100 * np.exp(numerator - denominator)).clip(lower=0, upper=100)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cells", type=Path, required=True)
    parser.add_argument("--source-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--qa-output", type=Path)
    args = parser.parse_args()

    cells = pd.read_parquet(args.cells)
    needed_columns = {"h3_index", "centroid_lat", "centroid_lon"}
    if missing := needed_columns - set(cells.columns):
        raise ValueError(f"Cells file is missing: {sorted(missing)}")
    if cells["h3_index"].duplicated().any():
        raise ValueError("Cells file has duplicate h3_index values.")

    instant = open_one(args.source_dir, "stepType-instant")
    accumulation = open_one(args.source_dir, "stepType-accum")
    required(instant, {"t2m", "d2m", "u10", "v10", "tcc"}, "Instantaneous")
    required(accumulation, {"tp"}, "Accumulated")

    instant_frame = instant[["t2m", "d2m", "u10", "v10", "tcc"]].to_dataframe().reset_index()
    accumulation_frame = accumulation[["tp"]].to_dataframe().reset_index()
    join_keys = ["valid_time", "latitude", "longitude"]
    hourly_grid = instant_frame.merge(accumulation_frame[join_keys + ["tp"]], on=join_keys, validate="one_to_one")

    grid_points = hourly_grid[["latitude", "longitude"]].drop_duplicates().to_numpy(dtype=float)
    assignments: list[dict[str, object]] = []
    for cell in cells.itertuples(index=False):
        distances = (grid_points[:, 0] - float(cell.centroid_lat)) ** 2 + (
            grid_points[:, 1] - float(cell.centroid_lon)
        ) ** 2
        latitude, longitude = grid_points[int(np.argmin(distances))]
        assignments.append({"h3_index": cell.h3_index, "latitude": latitude, "longitude": longitude})
    assigned = pd.DataFrame(assignments)

    hourly = assigned.merge(hourly_grid, on=["latitude", "longitude"], validate="many_to_many")
    hourly["occurred_at"] = pd.to_datetime(hourly["valid_time"], utc=True).dt.tz_convert(LOCAL_TIMEZONE)
    hourly["time_bin_dt"] = hourly["occurred_at"].dt.floor("6h")
    hourly["temp_c"] = hourly["t2m"] - 273.15
    hourly["dewpoint_c"] = hourly["d2m"] - 273.15
    hourly["wind_speed_ms"] = np.hypot(hourly["u10"], hourly["v10"])
    hourly["humidity_percent"] = relative_humidity_percent(hourly["temp_c"], hourly["dewpoint_c"])
    hourly["precipitation_mm"] = hourly["tp"] * 1000.0
    hourly["cloud_cover_percent"] = hourly["tcc"] * 100.0

    weather = (
        hourly.groupby(["h3_index", "time_bin_dt"], as_index=False)
        .agg(
            temp_mean=("temp_c", "mean"),
            precipitation_sum=("precipitation_mm", "sum"),
            wind_speed_max=("wind_speed_ms", "max"),
            humidity_mean=("humidity_percent", "mean"),
            cloud_cover_mean=("cloud_cover_percent", "mean"),
        )
        .sort_values(["h3_index", "time_bin_dt"])
    )
    # ERA5 file selected in CDS does not contain visibility.  Keep the agreed
    # schema column, but make the limitation explicit instead of fabricating it.
    weather["visibility_min"] = np.nan
    weather["time_bin"] = weather.pop("time_bin_dt").map(lambda value: value.isoformat())
    weather = weather[
        [
            "h3_index",
            "time_bin",
            "temp_mean",
            "precipitation_sum",
            "visibility_min",
            "wind_speed_max",
            "humidity_mean",
            "cloud_cover_mean",
        ]
    ]
    if weather.duplicated(["h3_index", "time_bin"]).any():
        raise ValueError("Duplicate (h3_index, time_bin) keys were created.")
    if weather.drop(columns="visibility_min").isna().any().any():
        raise ValueError("Unexpected null values in ERA5-derived features.")

    args.output.parent.mkdir(parents=True, exist_ok=True)
    weather.to_parquet(args.output, index=False, compression="zstd")
    qa_path = args.qa_output or args.output.with_name(f"{args.output.stem}_qa.json")
    qa = {
        "source": "ERA5 hourly data on single levels",
        "source_directory": str(args.source_dir),
        "timezone_for_time_bin": LOCAL_TIMEZONE,
        "h3_cells": int(cells.shape[0]),
        "weather_rows": int(weather.shape[0]),
        "time_bin_start": weather["time_bin"].min(),
        "time_bin_end": weather["time_bin"].max(),
        "visibility_min_status": "unavailable_in_selected_ERA5_download; all values are null",
        "nearest_grid_point_assignment": True,
    }
    qa_path.write_text(json.dumps(qa, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Created {args.output}; rows={len(weather)}; cells={len(cells)}")
    print(f"Created {qa_path}")


if __name__ == "__main__":
    main()
