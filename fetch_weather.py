import os
import sys
import requests
import pandas as pd
import numpy as np

# Thiết lập UTF-8 cho Windows Terminal
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

def fetch_weather_for_cells(cells_parquet: str, output_parquet: str, start_date: str = "2023-01-01", end_date: str = "2023-01-07"):
    """
    Tải và tổng hợp thời tiết theo khung 6h cho các ô H3
    (Mặc định demo 1 tuần để chạy thử, khi làm toàn bộ đổi sang 2019-2025)
    """
    print(f"\n==========================================")
    print(f"🌦️ Đang đọc danh sách ô từ: {cells_parquet}")
    print(f"📅 Khoảng thời gian: {start_date} đến {end_date}")
    print(f"==========================================")
    
    if not os.path.exists(cells_parquet):
        print(f"❌ Không tìm thấy file: {cells_parquet}")
        return

    df_cells = pd.read_parquet(cells_parquet)
    print(f"👉 Tổng số ô cần lấy thời tiết: {len(df_cells)}")
    
    all_weather_records = []
    
    # Duyệt qua từng ô H3
    for idx, row in df_cells.iterrows():
        cell_id = row["h3_index"]
        lat = row["centroid_lat"]
        lon = row["centroid_lon"]
        
        print(f"[{idx+1}/{len(df_cells)}] Đang tải thời tiết cho ô {cell_id} (Lat: {lat:.4f}, Lon: {lon:.4f})...")
        
        # Gọi Open-Meteo Historical Weather API (Miễn phí, không cần API Key)
        url = "https://archive-api.open-meteo.com/v1/archive"
        params = {
            "latitude": lat,
            "longitude": lon,
            "start_date": start_date,
            "end_date": end_date,
            "hourly": "temperature_2m,relative_humidity_2m,precipitation,visibility,wind_speed_10m",
            "timezone": "Asia/Bangkok"
        }
        
        try:
            res = requests.get(url, params=params, timeout=30)
            if res.status_code != 200:
                print(f"  ⚠️ Lỗi HTTP {res.status_code}, bỏ qua ô này.")
                continue
            
            data = res.json()
            hourly = data.get("hourly", {})
            
            # Tạo DataFrame theo giờ
            df_hourly = pd.DataFrame({
                "time": pd.to_datetime(hourly["time"]),
                "temperature": hourly.get("temperature_2m"),
                "humidity": hourly.get("relative_humidity_2m"),
                "precipitation": hourly.get("precipitation"),
                "visibility": hourly.get("visibility"),
                "wind_speed": hourly.get("wind_speed_10m")
            })
            
            # Gộp về khung 6 giờ (0h, 6h, 12h, 18h)
            df_hourly.set_index("time", inplace=True)
            df_6h = df_hourly.resample("6h").agg({
                "temperature": "mean",        # temp_mean
                "precipitation": "sum",       # precipitation_sum
                "visibility": "min",          # visibility_min (điều kiện xấu nhất)
                "wind_speed": "max",          # wind_speed_max
                "humidity": "mean"            # humidity_mean
            }).reset_index()
            
            # Đổi tên cột chuẩn schema mục 5 docs/context.md
            df_6h.rename(columns={
                "time": "time_bin",
                "temperature": "temp_mean",
                "precipitation": "precipitation_sum",
                "visibility": "visibility_min",
                "wind_speed": "wind_speed_max",
                "humidity": "humidity_mean"
            }, inplace=True)
            
            df_6h["h3_index"] = cell_id
            all_weather_records.append(df_6h)
            
        except Exception as e:
            print(f"  ❌ Lỗi khi lấy ô {cell_id}: {e}")
            
    if not all_weather_records:
        print("❌ Không có dữ liệu thời tiết nào được thu thập!")
        return
        
    df_weather_all = pd.concat(all_weather_records, ignore_index=True)
    
    # Sắp xếp lại thứ tự cột chuẩn
    cols_order = ["h3_index", "time_bin", "temp_mean", "precipitation_sum", "visibility_min", "wind_speed_max", "humidity_mean"]
    df_weather_all = df_weather_all[cols_order]
    
    os.makedirs(os.path.dirname(output_parquet), exist_ok=True)
    df_weather_all.to_parquet(output_parquet, index=False)
    
    print(f"\n🎉 HOÀN THÀNH B6!")
    print(f"📊 Tổng số bản ghi thời tiết (ô × khung 6h): {len(df_weather_all)}")
    print(f"📁 Đã lưu file tại: {output_parquet}")
    print(f"\n👀 Xem trước 5 dòng đầu:")
    print(df_weather_all.head())

if __name__ == "__main__":
    in_cells = "data/processed/cells_xp.parquet"
    out_weather = "data/processed/weather_xp.parquet"
    
    if len(sys.argv) > 1:
        in_cells = sys.argv[1]
    if len(sys.argv) > 2:
        out_weather = sys.argv[2]
        
    fetch_weather_for_cells(in_cells, out_weather, start_date="2023-03-01", end_date="2023-03-07")