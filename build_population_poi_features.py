"""Build Track B5 population and POI features for an H3 grid.

Population is summed from a WorldPop population-per-pixel GeoTIFF.  The input
cell geometry is GeoJSON/WGS84 and must therefore match a WGS84 raster.

Example:
    python build_population_poi_features.py ^
      --cells data\\processed\\pilots\\chuong_duong\\cells_b4.parquet ^
      --cell-geometry data\\processed\\pilots\\chuong_duong\\cells_geometry.geojson ^
      --population-raster data\\raw\\population\\vnm_ppp_2020_UNadj_constrained.tif ^
      --pbf maps\\chuong_duong.osm.pbf ^
      --output data\\processed\\pilots\\chuong_duong\\cells_b5.parquet
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import h3
import numpy as np
import osmium
import pandas as pd
import rasterio
from rasterio.mask import mask
from pyproj import Transformer
from shapely.geometry import Point, mapping, shape
from shapely.ops import transform
from shapely.strtree import STRtree


class POIReader(osmium.SimpleHandler):
    def __init__(self) -> None:
        super().__init__()
        self.coordinates: dict[int, tuple[float, float]] = {}
        self.poi_nodes: list[tuple[str, int]] = []
        self.poi_ways: list[tuple[str, list[int]]] = []

    @staticmethod
    def category(tags: osmium.osm.TagList) -> str | None:
        if tags.get("amenity") == "school":
            return "n_schools"
        if tags.get("amenity") == "hospital":
            return "n_hospitals"
        if tags.get("shop"):
            return "n_commercial_poi"
        return None

    def node(self, node: osmium.osm.Node) -> None:
        if node.location.valid():
            self.coordinates[node.id] = (node.location.lon, node.location.lat)
        if category := self.category(node.tags):
            self.poi_nodes.append((category, node.id))

    def way(self, way: osmium.osm.Way) -> None:
        if category := self.category(way.tags):
            self.poi_ways.append((category, [node.ref for node in way.nodes]))


def load_cell_geometries(path: Path):
    geojson = json.loads(path.read_text(encoding="utf-8"))
    records = []
    for feature in geojson.get("features", []):
        index = feature.get("properties", {}).get("h3_index")
        if not index:
            raise ValueError("Each cell feature needs properties.h3_index.")
        records.append((index, shape(feature["geometry"])))
    if not records:
        raise ValueError(f"No cell polygons found in {path}")
    return records


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cells", type=Path, required=True)
    parser.add_argument("--cell-geometry", type=Path, required=True)
    parser.add_argument("--population-raster", type=Path, required=True)
    parser.add_argument("--pbf", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--qa-output", type=Path)
    args = parser.parse_args()

    cells = pd.read_parquet(args.cells)
    if "h3_index" not in cells or cells["h3_index"].duplicated().any():
        raise ValueError("cells must have a unique h3_index column.")
    cell_records = load_cell_geometries(args.cell_geometry)
    if set(cells["h3_index"]) != {key for key, _ in cell_records}:
        raise ValueError("cells.parquet and cell geometry must contain the same H3 indexes.")

    populations: dict[str, float] = {}
    with rasterio.open(args.population_raster) as raster:
        if raster.crs is None or raster.crs.to_epsg() != 4326:
            raise ValueError(f"Expected WorldPop raster in EPSG:4326, got {raster.crs}")
        for h3_index, geometry in cell_records:
            values, _ = mask(raster, [mapping(geometry)], crop=True, filled=False)
            valid = values[0].compressed()
            populations[h3_index] = float(valid.sum()) if valid.size else 0.0
        raster_crs = str(raster.crs)
        raster_resolution = [float(raster.res[0]), float(raster.res[1])]

    to_utm = Transformer.from_crs("EPSG:4326", "EPSG:32648", always_xy=True).transform
    projected_cells = [transform(to_utm, geom) for _, geom in cell_records]
    h3_indexes = [key for key, _ in cell_records]
    tree = STRtree(projected_cells)
    poi_metrics = {key: {"n_schools": 0, "n_hospitals": 0, "n_commercial_poi": 0} for key in h3_indexes}

    reader = POIReader()
    reader.apply_file(str(args.pbf))

    def count_poi(category: str, coordinate: tuple[float, float]) -> None:
        point = transform(to_utm, Point(coordinate))
        for position in tree.query(point):
            if projected_cells[position].covers(point):
                poi_metrics[h3_indexes[position]][category] += 1

    skipped_ways = 0
    for category, node_id in reader.poi_nodes:
        coordinate = reader.coordinates.get(node_id)
        if coordinate is not None:
            count_poi(category, coordinate)
    for category, refs in reader.poi_ways:
        coordinates = [reader.coordinates[ref] for ref in refs if ref in reader.coordinates]
        if not coordinates:
            skipped_ways += 1
            continue
        lon = sum(item[0] for item in coordinates) / len(coordinates)
        lat = sum(item[1] for item in coordinates) / len(coordinates)
        count_poi(category, (lon, lat))

    feature_rows = []
    for h3_index in h3_indexes:
        area_km2 = h3.cell_area(h3_index, unit="km^2")
        feature_rows.append(
            {
                "h3_index": h3_index,
                "population": populations[h3_index],
                "population_density": populations[h3_index] / area_km2,
                **poi_metrics[h3_index],
            }
        )
    features = pd.DataFrame(feature_rows)
    output = cells.merge(features, on="h3_index", validate="one_to_one")
    output["population"] = output["population"].round(3)
    output["population_density"] = output["population_density"].round(3)
    b5_columns = ["population", "population_density", "n_schools", "n_hospitals", "n_commercial_poi"]
    if output[b5_columns].isna().any().any() or output.duplicated("h3_index").any():
        raise ValueError("B5 feature columns have nulls or duplicate H3 indexes.")

    args.output.parent.mkdir(parents=True, exist_ok=True)
    output.to_parquet(args.output, index=False, compression="zstd")
    qa_path = args.qa_output or args.output.with_name(f"{args.output.stem}_qa.json")
    qa = {
        "population_raster": str(args.population_raster),
        "population_raster_crs": raster_crs,
        "population_raster_resolution_degrees": raster_resolution,
        "population_value_unit": "people per raster pixel",
        "h3_cells": len(output),
        "total_population_across_cells": float(output["population"].sum()),
        "note_on_total": "H3 resolutions 7 and 8 overlap in this pilot, so this sum is not a physical ward total.",
        "poi_source_pbf": str(args.pbf),
        "poi_node_records": len(reader.poi_nodes),
        "poi_way_records": len(reader.poi_ways),
        "poi_ways_without_coordinates": skipped_ways,
    }
    qa_path.write_text(json.dumps(qa, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Created {args.output}; rows={len(output)}")
    print(f"Created {qa_path}")


if __name__ == "__main__":
    main()
