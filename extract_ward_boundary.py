"""Extract one ward/commune feature from the shared Hanoi 2025 GeoJSON."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


SOURCE = Path("maps/hanoi_wards_2025.geojson")


def main() -> None:
    parser = argparse.ArgumentParser()
    selector = parser.add_mutually_exclusive_group(required=True)
    selector.add_argument("--ward", help="Exact value of the 'ward' property.")
    selector.add_argument("--ward-id", help="Exact value of the 'ward_id' property; avoids Windows Unicode input issues.")
    parser.add_argument("--output", required=True, type=Path, help="Output GeoJSON path.")
    args = parser.parse_args()

    with SOURCE.open(encoding="utf-8") as source_file:
        collection = json.load(source_file)

    matches = [
        feature
        for feature in collection.get("features", [])
        if (
            feature.get("properties", {}).get("ward") == args.ward
            if args.ward is not None
            else str(feature.get("properties", {}).get("ward_id")) == args.ward_id
        )
    ]
    if len(matches) != 1:
        selector_name = args.ward if args.ward is not None else args.ward_id
        raise ValueError(f"Expected one matching feature ({selector_name!r}); found {len(matches)}.")

    result = {"type": "FeatureCollection", "features": matches}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8", newline="\n") as output_file:
        json.dump(result, output_file, ensure_ascii=False, separators=(",", ":"))
        output_file.write("\n")

    feature = matches[0]
    # Keep console output ASCII-only so the script also works in the default
    # Windows Anaconda Prompt code page.
    print(f"Created {args.output} (ward_id={feature['properties']['ward_id']}).")


if __name__ == "__main__":
    main()
