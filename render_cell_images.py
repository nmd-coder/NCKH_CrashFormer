"""Render unlabeled 224px OSM map images for Track B3 H3 cells.

Roads, building footprints and water are drawn from a local PBF, without web
tiles or text labels.  Each H3 resolution uses a single fixed projected extent.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import osmium
import pandas as pd
from PIL import Image
from pyproj import Transformer
from shapely.geometry import LineString, Polygon, shape
from shapely.ops import transform


ROAD_STYLE = {
    "motorway": ("#d73027", 2.2), "trunk": ("#fc8d59", 2.0),
    "primary": ("#fdae61", 1.8), "secondary": ("#fee08b", 1.5),
    "tertiary": ("#f6e8c3", 1.1), "residential": ("#ffffff", 0.65),
    "service": ("#ffffff", 0.45), "unclassified": ("#ffffff", 0.55),
}


class MapReader(osmium.SimpleHandler):
    def __init__(self) -> None:
        super().__init__()
        self.nodes: dict[int, tuple[float, float]] = {}
        self.roads: list[tuple[str, list[tuple[float, float]]]] = []
        self.buildings: list[list[tuple[float, float]]] = []
        self.water: list[list[tuple[float, float]]] = []

    def node(self, node: osmium.osm.Node) -> None:
        if node.location.valid():
            self.nodes[node.id] = (node.location.lon, node.location.lat)

    def way(self, way: osmium.osm.Way) -> None:
        coords = [self.nodes[ref] for ref in (node.ref for node in way.nodes) if ref in self.nodes]
        if len(coords) < 2:
            return
        tags = way.tags
        highway = tags.get("highway")
        if highway:
            style_key = highway.replace("_link", "")
            if style_key in ROAD_STYLE:
                self.roads.append((style_key, coords))
        if len(coords) >= 4 and coords[0] == coords[-1]:
            if "building" in tags:
                self.buildings.append(coords)
            if tags.get("natural") == "water" or tags.get("waterway") in {"riverbank", "dock"} or tags.get("landuse") == "reservoir":
                self.water.append(coords)


def load_cells(path: Path):
    data = json.loads(path.read_text(encoding="utf-8"))
    return [(item["properties"]["h3_index"], item["properties"]["resolution"], shape(item["geometry"])) for item in data["features"]]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pbf", type=Path, required=True)
    parser.add_argument("--cells", type=Path, required=True)
    parser.add_argument("--cell-geometry", type=Path, required=True)
    parser.add_argument("--image-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--contact-sheet", type=Path, required=True)
    args = parser.parse_args()

    cells_frame = pd.read_parquet(args.cells)
    cell_records = load_cells(args.cell_geometry)
    if set(cells_frame.h3_index) != {item[0] for item in cell_records}:
        raise ValueError("cells and cell geometry have different H3 indexes")
    to_utm = Transformer.from_crs("EPSG:4326", "EPSG:32648", always_xy=True).transform
    projected_cells = [(index, resolution, transform(to_utm, geometry)) for index, resolution, geometry in cell_records]
    extents: dict[int, tuple[float, float]] = {}
    for _, resolution, geometry in projected_cells:
        min_x, min_y, max_x, max_y = geometry.bounds
        half_x, half_y = (max_x - min_x) * 0.65, (max_y - min_y) * 0.65
        old = extents.get(resolution, (0.0, 0.0))
        extents[resolution] = (max(old[0], half_x), max(old[1], half_y))

    reader = MapReader()
    reader.apply_file(str(args.pbf))
    roads = [(style, transform(to_utm, LineString(coords))) for style, coords in reader.roads]
    buildings = [transform(to_utm, Polygon(coords)) for coords in reader.buildings]
    water = [transform(to_utm, Polygon(coords)) for coords in reader.water]

    args.image_dir.mkdir(parents=True, exist_ok=True)
    for position, (index, resolution, cell) in enumerate(projected_cells, start=1):
        centre = cell.centroid
        half_x, half_y = extents[resolution]
        fig = plt.figure(figsize=(2.24, 2.24), dpi=100, facecolor="#edf1f4")
        axis = fig.add_axes([0, 0, 1, 1], facecolor="#edf1f4")
        axis.set_xlim(centre.x - half_x, centre.x + half_x)
        axis.set_ylim(centre.y - half_y, centre.y + half_y)
        axis.set_aspect("equal")
        axis.set_axis_off()
        for polygon in water:
            if polygon.bounds[2] >= axis.get_xlim()[0] and polygon.bounds[0] <= axis.get_xlim()[1] and polygon.bounds[3] >= axis.get_ylim()[0] and polygon.bounds[1] <= axis.get_ylim()[1]:
                x, y = polygon.exterior.xy
                axis.fill(x, y, color="#9ecae1", linewidth=0, zorder=1)
        for polygon in buildings:
            if polygon.bounds[2] >= axis.get_xlim()[0] and polygon.bounds[0] <= axis.get_xlim()[1] and polygon.bounds[3] >= axis.get_ylim()[0] and polygon.bounds[1] <= axis.get_ylim()[1]:
                x, y = polygon.exterior.xy
                axis.fill(x, y, color="#bdbdbd", linewidth=0, zorder=2)
        for style, line in roads:
            if line.bounds[2] >= axis.get_xlim()[0] and line.bounds[0] <= axis.get_xlim()[1] and line.bounds[3] >= axis.get_ylim()[0] and line.bounds[1] <= axis.get_ylim()[1]:
                color, width = ROAD_STYLE[style]
                x, y = line.xy
                axis.plot(x, y, color=color, linewidth=width, solid_capstyle="round", zorder=3)
        target = args.image_dir / f"{index}.png"
        fig.savefig(target, dpi=100, facecolor=fig.get_facecolor())
        plt.close(fig)
        print(f"Rendered {position}/{len(projected_cells)}")

    output = cells_frame.copy()
    output["image_path"] = output["h3_index"].map(lambda value: str(args.image_dir / f"{value}.png"))
    output.to_parquet(args.output, index=False, compression="zstd")
    images = [Image.open(args.image_dir / f"{index}.png").convert("RGB") for index, _, _ in projected_cells[:12]]
    sheet = Image.new("RGB", (224 * 4, 224 * 3), "white")
    for position, image in enumerate(images):
        sheet.paste(image, ((position % 4) * 224, (position // 4) * 224))
    args.contact_sheet.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(args.contact_sheet)
    print(f"Created {args.output}; images={len(projected_cells)}")
    print(f"Created {args.contact_sheet}")


if __name__ == "__main__":
    main()
