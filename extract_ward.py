import os
import sys
import subprocess
import unicodedata
import re
import osmnx as ox
import geopandas as gpd

# Thiết lập UTF-8 cho Windows Terminal
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

def slugify(text: str) -> str:
    """Chuyển tên tiếng Việt có dấu sang dạng không dấu (ví dụ: 'Xuân Phương' -> 'xuan_phuong')"""
    text = unicodedata.normalize('NFD', text)
    text = re.sub(r'[\u0300-\u036f]', '', text)
    text = re.sub(r'[^\w\s-]', '', text).strip().lower()
    return re.sub(r'[-\s]+', '_', text)

def extract_ward(ward_name: str, district_name: str = "", input_pbf: str = "data/raw/osm/hanoi.osm.pbf"):
    # 1. Chuẩn hóa tên tìm kiếm
    search_query = ward_name
    if district_name:
        search_query += f", {district_name}"
    search_query += ", Hà Nội, Vietnam"
    
    ward_slug = slugify(ward_name)
    if district_name:
        ward_slug = f"{slugify(district_name)}_{ward_slug}"

    os.makedirs("data/raw/osm", exist_ok=True)
    boundary_path = f"data/raw/osm/{ward_slug}_boundary.geojson"
    output_pbf = f"data/raw/osm/{ward_slug}.osm.pbf"

    print(f"\n==========================================")
    print(f"🔍 Đang tìm ranh giới cho: {search_query}")
    print(f"==========================================")

    # 2. Lấy ranh giới phường từ OpenStreetMap (hỗ trợ nhiều server dự phòng)
    geojson_data = None
    
    # Kênh 1: Komoot Photon OSM API (Cực nhanh, không bị chặn)
    try:
        import urllib.parse
        import urllib.request
        import json
        
        q_encoded = urllib.parse.quote(f"{ward_name} {district_name} Hà Nội")
        photon_url = f"https://photon.komoot.io/api/?q={q_encoded}&limit=5"
        req = urllib.request.Request(photon_url, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            p_data = json.loads(resp.read().decode("utf-8"))
            features = p_data.get("features", [])
            if features:
                # Chọn feature tốt nhất
                feat = features[0]
                extent = feat.get("properties", {}).get("extent")
                coords = feat.get("geometry", {}).get("coordinates")
                
                if extent and len(extent) == 4:
                    min_lon, max_lat, max_lon, min_lat = extent
                elif coords and len(coords) == 2:
                    lon, lat = coords
                    delta = 0.015 # ~1.5km bán kính
                    min_lon, min_lat, max_lon, max_lat = lon - delta, lat - delta, lon + delta, lat + delta
                else:
                    extent = None

                if extent or coords:
                    geojson_data = {
                        "type": "FeatureCollection",
                        "features": [{
                            "type": "Feature",
                            "properties": {"name": f"{ward_name}, {district_name}"},
                            "geometry": {
                                "type": "Polygon",
                                "coordinates": [[
                                    [min_lon, min_lat],
                                    [max_lon, min_lat],
                                    [max_lon, max_lat],
                                    [min_lon, max_lat],
                                    [min_lon, min_lat]
                                ]]
                            }
                        }]
                    }
    except Exception as e:
        print(f"[DEBUG] Kênh Photon thong bao: {e}")

    # Kênh 2 (Dự phòng): OSMnx / Nominatim
    if not geojson_data:
        try:
            ox.settings.user_agent = "nckh_hanoi_research_extractor"
            ox.settings.requests_timeout = 15
            gdf = ox.geocode_to_gdf(search_query)
            gdf.to_file(boundary_path, driver="GeoJSON")
            print(f"✅ Đã lưu ranh giới tại: {boundary_path}")
        except Exception as e:
            print(f"❌ Không tìm thấy ranh giới tự động cho '{search_query}'. Lỗi: {e}")
            return
    else:
        with open(boundary_path, "w", encoding="utf-8") as f:
            json.dump(geojson_data, f, ensure_ascii=False, indent=2)
        print(f"✅ Đã lưu ranh giới tại: {boundary_path}")

    # 3. Kiểm tra file OSM gốc
    if not os.path.exists(input_pbf):
        print(f"❌ Không tìm thấy file gốc: {input_pbf}")
        return

    # 4. Chạy lệnh osmium extract
    print(f"✂️ Đang cắt dữ liệu OSM từ {input_pbf}...")
    cmd = [
        "osmium", "extract",
        "-p", boundary_path,
        input_pbf,
        "-o", output_pbf,
        "--overwrite"
    ]
    
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode == 0:
        file_size_kb = os.path.getsize(output_pbf) / 1024
        print(f"🎉 CẮT THÀNH CÔNG!")
        print(f"📁 File kết quả: {output_pbf} ({file_size_kb:.1f} KB)")
    else:
        print(f"❌ Lỗi khi chạy osmium: {result.stderr}")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        # Nếu truyền tham số từ dòng lệnh: python extract_ward.py "Xuân Phương" "Nam Từ Liêm"
        w_name = sys.argv[1]
        d_name = sys.argv[2] if len(sys.argv) > 2 else ""
        extract_ward(w_name, d_name)
    else:
        # Nếu chạy trực tiếp: hỏi người dùng nhập từ bàn phím
        print("--- CÔNG CỤ CẮT DỮ LIỆU OSM THEO PHƯỜNG HÀ NỘI ---")
        w_name = input("Nhập tên Phường/Xã (ví dụ: Xuân Phương): ").strip()
        d_name = input("Nhập tên Quận/Huyện (ví dụ: Nam Từ Liêm - có thể để trống): ").strip()
        if w_name:
            extract_ward(w_name, d_name)
        else:
            print("Chưa nhập tên phường!")