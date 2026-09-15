import os
import sys
import json
import importlib

# Load H3 dynamically so static analyzers do not report a missing import when
# the selected Python environment does not expose third-party packages.
h3 = importlib.import_module("h3")
import geopandas as gpd
import pandas as pd
from shapely.geometry import Polygon, Point, mapping

# Thiết lập UTF-8 cho Windows Terminal
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

def generate_h3_for_boundary(geojson_path: str, output_parquet: str):
    print(f"\n==========================================")
    print(f"🔷 Đang đọc ranh giới từ: {geojson_path}")
    print(f"==========================================")
    
    if not os.path.exists(geojson_path):
        print(f"❌ Không tìm thấy file: {geojson_path}")
        return

    # 1. Đọc file GeoJSON ranh giới
    gdf_boundary = gpd.read_file(geojson_path)
    
    # 2. Sinh các ô H3 cho cả Resolution 7 và Resolution 8
    rows = []
    for _, feature in gdf_boundary.iterrows():
        geom = feature.geometry
        # Lấy GeoJSON geometry dict
        geo_dict = mapping(geom)
        
        for res in [7, 8]:
            # Thư viện h3 v4 sinh tập hợp các ô lục giác phủ kín đa giác
            h3_shape = h3.geo_to_h3shape(geo_dict)
            cells = list(h3.polygon_to_cells(h3_shape, res=res))
            
            # Nếu đa giác quá nhỏ so với 1 ô H3, lấy ô bao phủ tâm đa giác và các ô lân cận
            if len(cells) == 0:
                center_lat = geom.centroid.y
                center_lon = geom.centroid.x
                center_cell = h3.latlng_to_cell(center_lat, center_lon, res=res)
                # Lấy ô tâm + 1 vòng xung quanh để đảm bảo bao trùm
                cells = list(h3.grid_disk(center_cell, 1))
                print(f"  👉 Resolution {res} (đa giác nhỏ): Tự động lấy ô trung tâm + lân cận ({len(cells)} ô).")
            else:
                print(f"  👉 Resolution {res}: Sinh được {len(cells)} ô lục giác.")
            
            for cell in cells:
                lat, lon = h3.cell_to_latlng(cell)
                rows.append({
                    "h3_index": cell,
                    "resolution": res,
                    "centroid_lat": lat,
                    "centroid_lon": lon,
                    "district": feature.get("district", feature.get("name", "Unknown")),
                    "ward": feature.get("name", "Unknown")
                })
    
    # 3. Tạo DataFrame và lưu ra file Parquet
    df_cells = pd.DataFrame(rows).drop_duplicates(subset=["h3_index"])
    
    os.makedirs(os.path.dirname(output_parquet), exist_ok=True)
    df_cells.to_parquet(output_parquet, index=False)
    
    print(f"\n🎉 HOÀN THÀNH B2!")
    print(f"📊 Tổng số ô H3 đã tạo: {len(df_cells)}")
    print(f"📁 Đã lưu khung bảng tại: {output_parquet}")
    print(f"\n👀 Xem trước 5 dòng đầu:")
    print(df_cells.head())

if __name__ == "__main__":
    # Mặc định sinh cho toàn Hà Nội, hoặc có thể đổi đường dẫn sang phường Xuân Phương để thử nghiệm
    geojson_file = "data/raw/osm/hanoi_boundary.geojson"
    out_file = "data/processed/cells.parquet"
    
    if len(sys.argv) > 1:
        geojson_file = sys.argv[1]
    if len(sys.argv) > 2:
        out_file = sys.argv[2]
        
    generate_h3_for_boundary(geojson_file, out_file)