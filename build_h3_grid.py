"""Build an H3 resolution-7/resolution-8 pilot grid from one GeoJSON boundary.

Example:
    python build_h3_grid.py --boundary maps/chuong_duong_boundary.geojson \
        --ward "Chương Dương" \
        --output data/processed/pilots/chuong_duong/cells.parquet
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import h3
import pandas as pd


def load_single_geometry(path: Path) -> dict:
    with path.open(encoding="utf-8") as boundary_file:
        document = json.load(boundary_file)

    if document.get("type") == "FeatureCollection":
        features = document.get("features", [])
        if len(features) != 1:
            raise ValueError(f"Expected one boundary feature in {path}; found {len(features)}.")
        geometry = features[0].get("geometry")
    elif document.get("type") == "Feature":
        geometry = document.get("geometry")
    else:
        geometry = document

    if not isinstance(geometry, dict) or geometry.get("type") not in {"Polygon", "MultiPolygon"}:
        raise ValueError("Boundary must be a GeoJSON Polygon or MultiPolygon.")
    return geometry


def polygon_to_cells(geometry: dict, resolution: int) -> set[str]:
    """Use the H3 GeoJSON-compatible API, with a clear error for old releases."""
    if not hasattr(h3, "geo_to_cells"):
        raise RuntimeError("h3-py >= 4 is required. Reinstall with: conda install -c conda-forge h3-py")
    return h3.geo_to_cells(geometry, resolution)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--boundary", type=Path, required=True)
    parser.add_argument("--ward", required=True, help="Current 2025 ward/commune name.")
    parser.add_argument("--district", default=None, help="Legacy district label; omit for the new two-level geography.")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument(
        "--geometry-output",
        type=Path,
        help="Optional GeoJSON of H3 polygons for visual QA in QGIS.",
    )
    parser.add_argument("--resolutions", type=int, nargs="+", default=[7, 8])
    args = parser.parse_args()

    geometry = load_single_geometry(args.boundary)
    records: list[dict[str, object]] = []
    for resolution in args.resolutions:
        if resolution < 0 or resolution > 15:
            raise ValueError(f"Invalid H3 resolution: {resolution}")
        for cell in sorted(polygon_to_cells(geometry, resolution)):
            lat, lon = h3.cell_to_latlng(cell)
            records.append(
                {
                    "h3_index": cell,
                    "resolution": resolution,
                    "centroid_lat": lat,
                    "centroid_lon": lon,
                    "district": args.district,
                    "ward": args.ward,
                }
            )

    cells = pd.DataFrame(
        records,
        columns=["h3_index", "resolution", "centroid_lat", "centroid_lon", "district", "ward"],
    )
    if cells.empty:
        raise ValueError("The boundary generated zero H3 cells. Check the boundary CRS and geometry.")
    if cells["h3_index"].duplicated().any():
        raise ValueError("Duplicate H3 indexes generated.")

    args.output.parent.mkdir(parents=True, exist_ok=True)
    cells.to_parquet(args.output, index=False, compression="zstd")

    if args.geometry_output:
        geometry_features = []
        for row in cells.itertuples(index=False):
            ring = [[lon, lat] for lat, lon in h3.cell_to_boundary(row.h3_index)]
            ring.append(ring[0])
            geometry_features.append(
                {
                    "type": "Feature",
                    "properties": {
                        "h3_index": row.h3_index,
                        "resolution": row.resolution,
                        "ward": row.ward,
                    },
                    "geometry": {"type": "Polygon", "coordinates": [ring]},
                }
            )
        args.geometry_output.parent.mkdir(parents=True, exist_ok=True)
        with args.geometry_output.open("w", encoding="utf-8", newline="\n") as geometry_file:
            json.dump({"type": "FeatureCollection", "features": geometry_features}, geometry_file, ensure_ascii=False)
            geometry_file.write("\n")

    counts = cells.groupby("resolution").size().to_dict()
    # Keep output ASCII-only to work in the default Windows console code page.
    print(f"Created {args.output}")
    if args.geometry_output:
        print(f"Created {args.geometry_output} for QGIS QA")
    print(f"Rows: {len(cells)}; cells_by_resolution: {counts}")


if __name__ == "__main__":
    main()
