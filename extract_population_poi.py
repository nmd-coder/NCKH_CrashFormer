import os
import sys
import h3
import rasterio
from rasterstats import zonal_stats
import geopandas as gpd
import pandas as pd
from shapely.geometry import Polygon

# Thiết lập UTF-8 cho Windows Terminal
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

def extract_population_and_poi(pbf_path: str, raster_path: str, cells_parquet: str, output_parquet: str):
    print(f"\n==========================================")
    print(f"👥 Đang trích xuất Dân số & POI")
    print(f"📂 Nguồn OSM: {pbf_path}")
    print(f"🗺️ Nguồn Raster WorldPop: {raster_path}")
    print(f"🔷 Khung ô H3: {cells_parquet}")
    print(f"==========================================")

    if not os.path.exists(cells_parquet) or not os.path.exists(pbf_path):
        print(f"❌ Không tìm thấy file đầu vào!")
        return

    # 1. Đọc bảng ô H3
    df_cells = pd.read_parquet(cells_parquet)
    print(f"👉 Tổng số ô H3: {len(df_cells)}")

    # 2. Xây dựng GeoDataFrame đa giác cho các ô H3
    polygons = []
    for _, row in df_cells.iterrows():
        coords = h3.cell_to_boundary(row["h3_index"])
        polygons.append(Polygon([(lon, lat) for lat, lon in coords]))
    
    gdf_cells = gpd.GeoDataFrame(df_cells, geometry=polygons, crs="EPSG:4326")

    # 3. Tính DÂN SỐ từ Raster WorldPop (Zonal Statistics)
    if os.path.exists(raster_path):
        print("⏳ Đang tính tổng dân số theo từng ô H3 từ WorldPop raster...")
        # Đảm bảo CRS giữa vector và raster khớp nhau (WGS84 EPSG:4326)
        with rasterio.open(raster_path) as src:
            assert str(src.crs).upper() in ["EPSG:4326", "WGS 84", "+PROJ=LONGLAT +DATUM=WGS84 +NO_DEFS"], f"CRS không khớp: {src.crs}"
            
        stats = zonal_stats(gdf_cells["geometry"], raster_path, stats="sum")
        df_cells["population"] = [round(s["sum"] or 0.0, 1) for s in stats]
        
        # Tính diện tích ô (km2) để ra mật độ: Res 7 ~ 5.16 km2, Res 8 ~ 0.74 km2
        # h3.cell_area(res, unit='km^2') trong h3-py
        df_cells["population_density"] = df_cells.apply(
            lambda r: round(r["population"] / (5.16 if r.get("resolution", 8) == 7 else 0.74), 2), axis=1
        )
    else:
        print(f"⚠️ Không tìm thấy raster dân số tại {raster_path}, gán mặc định 0.")
        df_cells["population"] = 0.0
        df_cells["population_density"] = 0.0

    # 4. Trích xuất POI (Trường học, Bệnh viện, Thương mại) từ OSM
    print("⏳ Đang đếm số lượng POI (Trường học, Bệnh viện, TTTM)...")
    try:
        gdf_points = gpd.read_file(pbf_path, layer="points")
        if gdf_points.crs is None:
            gdf_points.set_crs("EPSG:4326", inplace=True)
            
        df_cells["n_schools"] = 0
        df_cells["n_hospitals"] = 0
        df_cells["n_commercial_poi"] = 0

        for idx, row in gdf_cells.iterrows():
            poly = row.geometry
            pts_in_cell = gdf_points[gdf_points.within(poly)]
            
            n_schools = 0
            n_hospitals = 0
            n_comm = 0
            
            for _, pt in pts_in_cell.iterrows():
                other = str(pt.get("other_tags", "")).lower()
                amenity = str(pt.get("amenity", "")).lower()
                shop = str(pt.get("shop", "")).lower()
                
                # Trường học / giáo dục
                if amenity in ["school", "kindergarten", "university", "college"] or "school" in other:
                    n_schools += 1
                # Y tế / bệnh viện
                if amenity in ["hospital", "clinic", "doctors", "pharmacy"] or "hospital" in other:
                    n_hospitals += 1
                # Thương mại / chợ / siêu thị
                if shop != "" or amenity in ["marketplace", "mall", "supermarket"] or "shop" in other:
                    n_comm += 1
                    
            df_cells.at[idx, "n_schools"] = n_schools
            df_cells.at[idx, "n_hospitals"] = n_hospitals
            df_cells.at[idx, "n_commercial_poi"] = n_comm

    except Exception as e:
        print(f"⚠️ Lỗi khi trích xuất POI: {e}")

    # Lưu lại file Parquet
    os.makedirs(os.path.dirname(output_parquet), exist_ok=True)
    df_cells.to_parquet(output_parquet, index=False)

    print(f"\n🎉 HOÀN THÀNH B5!")
    print(f"📁 Đã cập nhật Dân số & POI vào: {output_parquet}")
    print(f"\n👀 Xem trước dữ liệu:")
    print(df_cells[["h3_index", "population", "population_density", "n_schools", "n_hospitals", "n_commercial_poi"]].head())

if __name__ == "__main__":
    in_pbf = "data/raw/osm/nam_tu_liem_xuan_phuong.osm.pbf"
    in_raster = "data/raw/worldpop/vnm_ppp_2020_100m.tif"
    in_cells = "data/processed/cells_xp.parquet"
    out_cells = "data/processed/cells_xp.parquet"

    if len(sys.argv) > 1:
        in_pbf = sys.argv[1]
    if len(sys.argv) > 2:
        in_raster = sys.argv[2]
    if len(sys.argv) > 3:
        in_cells = sys.argv[3]
    if len(sys.argv) > 4:
        out_cells = sys.argv[4]

    extract_population_and_poi(in_pbf, in_raster, in_cells, out_cells)