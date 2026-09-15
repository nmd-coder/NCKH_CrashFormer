import os
import sys
import h3
import geopandas as gpd
import pandas as pd
from shapely.geometry import Polygon, box

# Thiết lập UTF-8 cho Windows Terminal
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

def extract_road_features(pbf_path: str, cells_parquet: str, output_parquet: str):
    print(f"\n==========================================")
    print(f"🛣️ Đang trích xuất đặc trưng đường bộ")
    print(f"📂 Nguồn OSM: {pbf_path}")
    print(f"🔷 Khung ô H3: {cells_parquet}")
    print(f"==========================================")

    if not os.path.exists(pbf_path) or not os.path.exists(cells_parquet):
        print(f"❌ Không tìm thấy file đầu vào!")
        return

    # 1. Đọc bảng ô H3
    df_cells = pd.read_parquet(cells_parquet)
    print(f"👉 Tổng số ô H3 cần tính toán: {len(df_cells)}")

    # 2. Đọc lớp đường bộ từ OSM (lọc các way có tag highway)
    print("⏳ Đang đọc dữ liệu mạng lưới đường từ OSM...")
    try:
        # Đọc các đường (lines) từ file .osm.pbf bằng geopandas/pyogrio
        gdf_lines = gpd.read_file(pbf_path, layer="lines")
        # Đọc các điểm (points) để lấy đèn giao thông và vạch qua đường
        gdf_points = gpd.read_file(pbf_path, layer="points")
    except Exception as e:
        print(f"❌ Lỗi khi đọc file OSM PBF: {e}")
        return

    # Hệ chiếu phẳng mét chuẩn cho Hà Nội/Việt Nam (UTM Zone 48N - EPSG:32648) để đo chiều dài chính xác theo mét
    CRS_METERS = "EPSG:32648"
    
    # Đảm bảo hệ tọa độ gốc WGS84
    if gdf_lines.crs is None:
        gdf_lines.set_crs("EPSG:4326", inplace=True)
    if gdf_points.crs is None:
        gdf_points.set_crs("EPSG:4326", inplace=True)

    # Chuyển sang hệ chiếu mét
    gdf_lines_m = gdf_lines.to_crs(CRS_METERS)
    gdf_points_m = gdf_points.to_crs(CRS_METERS)

    # Khởi tạo các cột đặc trưng
    df_cells["n_intersections"] = 0
    df_cells["road_length_primary"] = 0.0
    df_cells["road_length_secondary"] = 0.0
    df_cells["road_length_residential"] = 0.0
    df_cells["n_traffic_signals"] = 0
    df_cells["n_crossings"] = 0
    df_cells["has_major_road"] = 0

    print("⏳ Đang tính toán chiều dài đường và nút giao theo từng ô lục giác...")

    for idx, row in df_cells.iterrows():
        cell_id = row["h3_index"]
        
        # Lấy đa giác biên của ô H3
        boundary_coords = h3.cell_to_boundary(cell_id) # [(lat, lon), ...]
        poly_wgs84 = Polygon([(lon, lat) for lat, lon in boundary_coords])
        gdf_poly = gpd.GeoDataFrame(geometry=[poly_wgs84], crs="EPSG:4326").to_crs(CRS_METERS)
        poly_m = gdf_poly.geometry.iloc[0]

        # 1. Cắt (clip) các đường nằm trong ô
        intersecting_roads = gdf_lines_m[gdf_lines_m.intersects(poly_m)].copy()
        
        len_primary = 0.0
        len_secondary = 0.0
        len_residential = 0.0
        
        if not intersecting_roads.empty:
            clipped_roads = intersecting_roads.intersection(poly_m)
            intersecting_roads["clipped_len"] = clipped_roads.length

            for _, road in intersecting_roads.iterrows():
                hw_type = str(road.get("highway", "")).lower()
                length = road["clipped_len"]
                
                if hw_type in ["primary", "primary_link", "trunk", "trunk_link", "motorway", "motorway_link"]:
                    len_primary += length
                elif hw_type in ["secondary", "secondary_link", "tertiary", "tertiary_link"]:
                    len_secondary += length
                elif hw_type in ["residential", "living_street", "unclassified"]:
                    len_residential += length

        # 2. Đếm số đèn giao thông và vạch sang đường trong ô
        intersecting_pts = gdf_points_m[gdf_points_m.intersects(poly_m)]
        n_signals = 0
        n_crossings = 0
        if not intersecting_pts.empty:
            for _, pt in intersecting_pts.iterrows():
                other_tags = str(pt.get("other_tags", "")).lower()
                highway_tag = str(pt.get("highway", "")).lower()
                if "traffic_signals" in other_tags or highway_tag == "traffic_signals":
                    n_signals += 1
                if "crossing" in other_tags or highway_tag == "crossing":
                    n_crossings += 1

        # Cập nhật giá trị vào bảng
        df_cells.at[idx, "road_length_primary"] = round(len_primary, 2)
        df_cells.at[idx, "road_length_secondary"] = round(len_secondary, 2)
        df_cells.at[idx, "road_length_residential"] = round(len_residential, 2)
        df_cells.at[idx, "n_traffic_signals"] = n_signals
        df_cells.at[idx, "n_crossings"] = n_crossings
        df_cells.at[idx, "has_major_road"] = 1 if len_primary > 0 else 0
        # Số nút giao ước lượng từ số đoạn đường giao nhau
        df_cells.at[idx, "n_intersections"] = max(0, len(intersecting_roads) // 2)

    # Lưu lại file parquet
    os.makedirs(os.path.dirname(output_parquet), exist_ok=True)
    df_cells.to_parquet(output_parquet, index=False)

    print(f"\n🎉 HOÀN THÀNH B4!")
    print(f"📁 Đã cập nhật đặc trưng đường vào: {output_parquet}")
    print(f"\n👀 Xem trước dữ liệu đặc trưng đường bộ:")
    print(df_cells[["h3_index", "road_length_primary", "road_length_secondary", "road_length_residential", "n_traffic_signals", "has_major_road"]].head())

if __name__ == "__main__":
    # Chạy thử nghiệm trên khu vực Xuân Phương
    in_pbf = "data/raw/osm/nam_tu_liem_xuan_phuong.osm.pbf"
    in_cells = "data/processed/cells_xp.parquet"
    out_cells = "data/processed/cells_xp.parquet"

    if len(sys.argv) > 1:
        in_pbf = sys.argv[1]
    if len(sys.argv) > 2:
        in_cells = sys.argv[2]
    if len(sys.argv) > 3:
        out_cells = sys.argv[3]

    extract_road_features(in_pbf, in_cells, out_cells)