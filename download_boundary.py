# Script tải ranh giới Hà Nội


# Đảm bảo UTF-8 cho stdout trên Windows
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

os.makedirs("data/raw/osm", exist_ok=True)
output_path = "data/raw/osm/hanoi_boundary.geojson"

print("[INFO] Dang tai ranh gioi hanh chinh Ha Noi tu geoBoundaries / GitHub...")

url = "https://github.com/wmgeolab/geoBoundaries/raw/9469f09/releaseData/gbOpen/VNM/ADM1/geoBoundaries-VNM-ADM1.geojson"

try:
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"})
    with urllib.request.urlopen(req) as resp:
        data = json.loads(resp.read().decode("utf-8"))
    
    # Lọc lấy riêng Hà Nội
    hanoi_features = [
        f for f in data["features"]
        if any(name in f["properties"].get("shapeName", "") for name in ["Ha Noi", "Hà Nội", "Hanoi"])
    ]
    
    if not hanoi_features:
        raise ValueError("Khong tim thay ranh gioi Ha Noi trong du lieu!")
    
    hanoi_geojson = {
        "type": "FeatureCollection",
        "features": hanoi_features
    }
    
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(hanoi_geojson, f, ensure_ascii=False, indent=2)
        
    print(f"[SUCCESS] DA LUU THANH CONG ranh gioi Ha Noi tai: {output_path}")

except Exception as e:
    print(f"[ERROR] Gap loi khi tai: {e}")