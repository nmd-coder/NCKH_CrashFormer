"""Build Track B4 road-network features from a local OSM PBF extract.

The input grid geometry must contain one GeoJSON feature per H3 cell.  Lengths
are calculated after projection to UTM zone 48N (metres), never in WGS84.

Example:
    python build_road_features.py ^
      --pbf maps\\chuong_duong.osm.pbf ^
      --cells data\\processed\\pilots\\chuong_duong\\cells.parquet ^
      --cell-geometry data\\processed\\pilots\\chuong_duong\\cells_geometry.geojson ^
      --output data\\processed\\pilots\\chuong_duong\\cells_b4.parquet
"""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path

import osmium
import pandas as pd
from pyproj import Transformer
from shapely.geometry import LineString, Point, shape
from shapely.strtree import STRtree
from shapely.ops import transform


NON_VEHICLE_HIGHWAYS = {
    "bridleway", "bus_stop", "construction", "corridor", "cycleway", "elevator",
    "footway", "path", "pedestrian", "platform", "proposed", "raceway", "steps",
}
ROAD_CLASS = {
    "primary": "road_length_primary",
    "primary_link": "road_length_primary",
    "secondary": "road_length_secondary",
    "secondary_link": "road_length_secondary",
    "residential": "road_length_residential",
}
MAJOR_HIGHWAYS = {"motorway", "motorway_link", "trunk", "trunk_link", "primary", "primary_link", "secondary", "secondary_link"}


class OSMReader(osmium.SimpleHandler):
    def __init__(self) -> None:
        super().__init__()
        self.node_coordinates: dict[int, tuple[float, float]] = {}
        self.road_ways: list[tuple[int, str, list[int]]] = []
        self.road_usage: dict[int, set[int]] = defaultdict(set)
        self.signal_nodes: set[int] = set()
        self.crossing_nodes: set[int] = set()

    def node(self, node: osmium.osm.Node) -> None:
        if node.location.valid():
            self.node_coordinates[node.id] = (node.location.lon, node.location.lat)
        tags = node.tags
        if tags.get("highway") == "traffic_signals":
            self.signal_nodes.add(node.id)
        if tags.get("highway") == "crossing" or "crossing" in tags:
            self.crossing_nodes.add(node.id)

    def way(self, way: osmium.osm.Way) -> None:
        highway = way.tags.get("highway")
        if not highway or highway in NON_VEHICLE_HIGHWAYS:
            return
        refs = [node.ref for node in way.nodes]
        if len(refs) < 2:
            return
        self.road_ways.append((way.id, highway, refs))
        for ref in refs:
            self.road_usage[ref].add(way.id)


def get_cell_geometries(path: Path):
    data = json.loads(path.read_text(encoding="utf-8"))
    features = data.get("features", [])
    records = []
    for feature in features:
        h3_index = feature.get("properties", {}).get("h3_index")
        if not h3_index:
            raise ValueError("Every cell geometry feature needs properties.h3_index.")
        records.append((h3_index, shape(feature["geometry"])))
    if not records:
        raise ValueError(f"No cell features found in {path}")
    return records


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pbf", type=Path, required=True)
    parser.add_argument("--cells", type=Path, required=True)
    parser.add_argument("--cell-geometry", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--qa-output", type=Path)
    args = parser.parse_args()

    cells = pd.read_parquet(args.cells)
    if "h3_index" not in cells or cells["h3_index"].duplicated().any():
        raise ValueError("cells must have a unique h3_index column.")
    cell_records = get_cell_geometries(args.cell_geometry)
    if set(cells["h3_index"]) != {h3_index for h3_index, _ in cell_records}:
        raise ValueError("cells.parquet and cell geometry do not contain the same H3 indexes.")

    to_utm = Transformer.from_crs("EPSG:4326", "EPSG:32648", always_xy=True).transform
    projected_geometries = [transform(to_utm, geometry) for _, geometry in cell_records]
    h3_indexes = [h3_index for h3_index, _ in cell_records]
    tree = STRtree(projected_geometries)
    metrics = {
        h3_index: {
            "n_intersections": 0,
            "road_length_primary": 0.0,
            "road_length_secondary": 0.0,
            "road_length_residential": 0.0,
            "n_traffic_signals": 0,
            "n_crossings": 0,
            "has_major_road": False,
        }
        for h3_index in h3_indexes
    }

    reader = OSMReader()
    reader.apply_file(str(args.pbf))
    missing_way_nodes = 0
    for _, highway, refs in reader.road_ways:
        coordinates = [reader.node_coordinates[ref] for ref in refs if ref in reader.node_coordinates]
        if len(coordinates) != len(refs):
            missing_way_nodes += 1
        if len(coordinates) < 2:
            continue
        road = transform(to_utm, LineString(coordinates))
        metric_name = ROAD_CLASS.get(highway)
        major = highway in MAJOR_HIGHWAYS
        for position in tree.query(road):
            clipped = road.intersection(projected_geometries[position])
            if clipped.is_empty:
                continue
            record = metrics[h3_indexes[position]]
            if metric_name:
                record[metric_name] += float(clipped.length)
            if major and clipped.length > 0:
                record["has_major_road"] = True

    def count_point(node_id: int, field: str) -> None:
        coordinate = reader.node_coordinates.get(node_id)
        if coordinate is None:
            return
        point = transform(to_utm, Point(coordinate))
        for position in tree.query(point):
            if projected_geometries[position].covers(point):
                metrics[h3_indexes[position]][field] += 1

    for node_id, way_ids in reader.road_usage.items():
        if len(way_ids) >= 3:
            count_point(node_id, "n_intersections")
    for node_id in reader.signal_nodes:
        count_point(node_id, "n_traffic_signals")
    for node_id in reader.crossing_nodes:
        count_point(node_id, "n_crossings")

    feature_frame = pd.DataFrame.from_dict(metrics, orient="index").rename_axis("h3_index").reset_index()
    output = cells.merge(feature_frame, on="h3_index", validate="one_to_one")
    for column in ["road_length_primary", "road_length_secondary", "road_length_residential"]:
        output[column] = output[column].round(3)
    output["has_major_road"] = output["has_major_road"].astype(bool)
    b4_columns = [
        "n_intersections",
        "road_length_primary",
        "road_length_secondary",
        "road_length_residential",
        "n_traffic_signals",
        "n_crossings",
        "has_major_road",
    ]
    if output[b4_columns].isna().any().any() or output.duplicated("h3_index").any():
        raise ValueError("B4 feature columns have nulls or duplicate H3 indexes.")

    args.output.parent.mkdir(parents=True, exist_ok=True)
    output.to_parquet(args.output, index=False, compression="zstd")
    qa_path = args.qa_output or args.output.with_name(f"{args.output.stem}_qa.json")
    qa = {
        "source_pbf": str(args.pbf),
        "length_crs": "EPSG:32648 (UTM zone 48N)",
        "h3_cells": len(output),
        "eligible_osm_highway_ways": len(reader.road_ways),
        "ways_with_missing_node_coordinates": missing_way_nodes,
        "total_intersections": int(output["n_intersections"].sum()),
        "total_traffic_signals": int(output["n_traffic_signals"].sum()),
        "total_crossings": int(output["n_crossings"].sum()),
    }
    qa_path.write_text(json.dumps(qa, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Created {args.output}; rows={len(output)}")
    print(f"Created {qa_path}")


if __name__ == "__main__":
    main()
