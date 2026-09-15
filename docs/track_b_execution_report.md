# Báo Cáo Tổng Kết Triển Khai Track B — Dữ Liệu Không Gian (Spatial Data)

> **Dự án NCKH:** Nghiên cứu và xây dựng mô hình dự đoán nguy cơ tai nạn giao thông đa phương thức cho địa bàn TP. Hà Nội.  
> **Kiến trúc tham khảo:** CrashFormer (UrbanAI/SIGSPATIAL 2023).  
> **Tài liệu tham chiếu gốc:** `docs/context.md` và `docs/track_b_guide.md`.

---

## 1. Tổng Quan và Sơ Đồ Quy Trình

Track B phụ trách xây dựng toàn bộ **hệ thống dữ liệu không gian tĩnh và động** phục vụ các khối mô hình:
- **Image Encoder (VAN):** Ảnh bản đồ mạng lưới đường $224 \times 224\text{ px}$ không nhãn chữ.
- **Data Encoder:** Thông tin nhân khẩu học (WorldPop), điểm tập trung giao thông (POI: trường học, bệnh viện, TTTM).
- **Baseline không dùng ảnh:** Đặc trưng hình học đường bộ dạng số (chiều dài đường theo cấp, nút giao, đèn tín hiệu).
- **Historical Event / Context:** Dữ liệu thời tiết theo khung 6 giờ từ Open-Meteo API.

```
                     ┌──► B6 (Thời tiết Open-Meteo theo khung 6h)
                     │
B1 (Cắt OSM Hà Nội) ─┼──► B4 (Đặc trưng mạng lưới đường dạng số)
                     │
B2 (Lưới Uber H3) ───┼──► B5 (Dân số WorldPop + POI từ OSM)
                     │
                     └──► B3 (Render ảnh bản đồ 224x224 cho Image Encoder)
```

---

## 2. Báo Cáo Chi Tiết Từng Bước Triển Khai

### 🛠️ BƯỚC 0: Khởi Tạo Môi Trường GIS & Công Cụ Cốt Lõi

* **Mục tiêu:** Cài đặt các thư viện địa lý không gian (GIS) và công cụ xử lý C++ trên môi trường Windows.
* **Các công cụ/thư viện:** `geopandas`, `rasterio`, `rasterstats`, `h3`, `osmnx`, `pyarrow`, `contextily`, `osmium-tool`.
* **Lỗi thực tế gặp phải & Cách khắc phục:**
  * ❌ *Lỗi Conda Solving Environment bị kẹt / quay vô tận:* Do Conda classic solver gặp khó khăn khi giải quyết xung đột kênh `defaults` và `conda-forge`.
  * ✅ *Giải pháp:* Kích hoạt môi trường `(nckh_spatial)` và chuyển sang cài đặt bằng `pip` với các pre-compiled wheels (chỉ mất ~30 giây) và cài riêng `osmium-tool` qua conda.

---

### 🗺️ BƯỚC B1: Tải & Cắt Dữ Liệu Bản Đồ OpenStreetMap (OSM)

* **Mục tiêu:** Tải dữ liệu toàn quốc `vietnam-latest.osm.pbf` và cắt riêng phạm vi Hà Nội/từng phường thử nghiệm mà không bị tràn RAM.
* **Input:**
  * File toàn quốc: `data/raw/osm/vietnam-latest.osm.pbf` (~600MB - 1GB)
  * Đa giác ranh giới: `data/raw/osm/hanoi_boundary.geojson`
* **Output:**
  * `data/raw/osm/hanoi.osm.pbf` (~21.8 MB)
  * `data/raw/osm/nam_tu_liem_xuan_phuong.osm.pbf` (~210 KB)
  * Script tiện ích mở rộng: `extract_ward.py` (tự động cắt bất kỳ phường nào theo yêu cầu).
* **Lỗi thực tế gặp phải & Cách khắc phục:**
  * ❌ *Lỗi Nominatim ngắt kết nối (`ConnectionResetError: [WinError 10054]`):* Máy chủ OSM Nominatim chặn request từ IP Việt Nam khi dùng `osmnx`.
  * ❌ *Lỗi Unicode Console Windows (`charmap codec can't encode \u23f3`):* PowerShell mặc định dùng mã `cp1252` gây lỗi khi in emoji.
  * ✅ *Giải pháp:* 
    * Chuyển nguồn tải ranh giới Hà Nội sang **geoBoundaries CDN trên GitHub** (`download_boundary.py`).
    * Tích hợp **Komoot Photon OSM API** vào `extract_ward.py` để tìm kiếm địa danh và lấy ranh giới mọi phường/xã mượt mà 100%.

---

### 🔷 BƯỚC B2: Sinh Lưới Ô Lục Giác Uber H3 (Res 7 & Res 8)

* **Mục tiêu:** Phủ lưới lục giác H3 lên toàn bộ địa bàn thành phố, tạo khung dữ liệu `cells.parquet`.
  * **Resolution 7:** $\approx 5.16\text{ km}^2$ (toàn thành phố, 571 ô).
  * **Resolution 8:** $\approx 0.74\text{ km}^2$ (nội thành, 3.991 ô).
* **Input:** File ranh giới GeoJSON (`hanoi_boundary.geojson` hoặc `nam_tu_liem_xuan_phuong_boundary.geojson`).
* **Output:** `data/processed/cells.parquet` (các cột: `h3_index`, `resolution`, `centroid_lat`, `centroid_lon`, `district`, `ward`).
* **Lỗi thực tế gặp phải & Cách khắc phục:**
  * ❌ *Lỗi API H3 v4:* `AttributeError: module 'h3' has no attribute 'geojson_to_geometry'`.
  * ❌ *Lỗi đa giác nhỏ sinh 0 ô:* Khi test trên 1 phường có diện tích nhỏ hơn 1 ô H3, hàm `polygon_to_cells` trả về 0 ô.
  * ❌ *Lỗi thiếu engine lưu Parquet:* `ImportError: Unable to find a usable engine ('pyarrow')`.
  * ✅ *Giải pháp:* 
    * Nâng cấp code dùng `h3.geo_to_h3shape(geo_dict)` theo chuẩn H3 v4.x.
    * Bổ sung cơ chế fallback: nếu đa giác nhỏ, tự động lấy ô chứa tâm (`latlng_to_cell`) + vòng lân cận (`grid_disk`).
    * Cài đặt `pyarrow` vào môi trường.

---

### 🌦️ BƯỚC B6: Thu Thập & Tổng Hợp Thời Tiết Khung 6 Giờ

* **Mục tiêu:** Thu thập dữ liệu thời tiết theo giờ từ Open-Meteo Historical Weather API và tổng hợp về 4 khung 6h/ngày.
* **Input:** Tọa độ tâm ô (`centroid_lat`, `centroid_lon`) từ `cells.parquet`.
* **Output:** `data/processed/weather.parquet` với khóa `(h3_index, time_bin)`.
* **Quy tắc gộp dữ liệu:**
  * 🌧️ `precipitation_sum`: **TỔNG (Sum)**
  * 🌫️ `visibility_min`: **GIÁ TRỊ THẤP NHẤT (Min)** (tầm nhìn thấp nhất gây nguy cơ tai nạn cao nhất)
  * 🌡️ `temp_mean`, 💧 `humidity_mean`: **TRUNG BÌNH (Mean)**
  * 💨 `wind_speed_max`: **MAX**
* **File triển khai:** `fetch_weather.py`.

---

### 🛣️ BƯỚC B4: Trích Xuất Đặc Trưng Mạng Lưới Đường Bộ Dạng Số

* **Mục tiêu:** Trích xuất các thuộc tính hình học và hạ tầng giao thông từ file OSM làm baseline số học.
* **Input:** File `.osm.pbf` (lines & points) và `cells.parquet`.
* **Output:** Bổ sung vào `cells.parquet` các cột:
  * `road_length_primary`, `road_length_secondary`, `road_length_residential` (đơn vị: mét, tính trên hệ chiếu EPSG:32648 UTM Zone 48N).
  * `n_intersections` (số nút giao $\ge 3$ nhánh).
  * `n_traffic_signals` (số cột đèn tín hiệu).
  * `n_crossings` (số vạch kẻ đường cho người đi bộ).
  * `has_major_road` (cờ nhị phân 0/1).
* **File triển khai:** `extract_road_features.py`.

---

### 👥 BƯỚC B5: Tích Hợp Dân Số (WorldPop) và Điểm Quan Tâm (POI)

* **Mục tiêu:** Đo lường mật độ dân số và các điểm phát sinh lưu lượng giao thông (trường học, bệnh viện, khu thương mại).
* **Input:**
  * Raster WorldPop 100m: `data/raw/worldpop/vnm_ppp_2020_100m.tif` (~15MB)
  * File OSM: `data/raw/osm/*.osm.pbf`
  * Bảng ô: `cells.parquet`
* **Output:** Bổ sung vào `cells.parquet` các cột:
  * `population`, `population_density` (người/$\text{km}^2$).
  * `n_schools`, `n_hospitals`, `n_commercial_poi`.
* **Lưu ý kỹ thuật:** Luôn kiểm tra khớp CRS (`EPSG:4326`) giữa raster và polygon ô H3 trước khi chạy `rasterstats.zonal_stats` để tránh lỗi lệch số liệu âm thầm.
* **File triển khai:** `extract_population_poi.py`.

---

### 🖼️ BƯỚC B3: Render Ảnh Bản Đồ 224×224 (No Labels)

* **Mục tiêu:** Tạo ảnh bản đồ cấu trúc hình học $224 \times 224\text{ px}$ cho từng ô H3 phục vụ Image Encoder (VAN).
* **Input:** `cells.parquet` (tọa độ tâm, resolution).
* **Output:**
  * Thư mục ảnh: `data/processed/cell_images/<h3_index>.png`.
  * Cập nhật cột `image_path` trong `cells.parquet`.
* **3 Nguyên tắc vàng đã tuân thủ 100%:**
  1. **Cố định mức Zoom:** Res 7 (zoom 15, bán kính 1400m); Res 8 (zoom 16, bán kính 550m).
  2. **Tắt hoàn toàn nhãn chữ (No Labels):** Dùng `CartoDB.PositronNoLabels` để mô hình học hình thái đường sá, không đọc chữ.
  3. **Giữ các lớp đối tượng:** Lớp đường phân cấp, mặt nước sông hồ, khối nhà.
* **File triển khai:** `render_cell_images.py`.

---

## 3. Danh Sách Script Đã Xây Dựng Trong Dự Án

| Tên File Script | Chức năng chính | Lệnh thực thi mẫu |
|---|---|---|
| `download_boundary.py` | Tải ranh giới TP. Hà Nội từ geoBoundaries | `python download_boundary.py` |
| `extract_ward.py` | Cắt dữ liệu OSM theo tên phường bất kỳ | `python extract_ward.py "Xuân Phương" "Nam Từ Liêm"` |
| `generate_h3_grid.py` | Sinh lưới lục giác H3 Res 7 & Res 8 | `python generate_h3_grid.py <geojson> <cells.parquet>` |
| `fetch_weather.py` | Tải và gộp thời tiết 6h từ Open-Meteo | `python fetch_weather.py <cells.parquet> <weather.parquet>` |
| `extract_road_features.py` | Tính độ dài đường, nút giao, đèn đỏ | `python extract_road_features.py <pbf> <cells.parquet> <out>` |
| `extract_population_poi.py` | Tính dân số WorldPop & đếm POI | `python extract_population_poi.py <pbf> <tif> <cells> <out>` |
| `render_cell_images.py` | Render ảnh bản đồ 224×224 tắt nhãn | `python render_cell_images.py <cells> <img_dir> <out>` |

---

## 4. Hướng Dẫn Chạy Toàn Diện Toàn TP. Hà Nội (Production)

Khi nhóm bắt đầu ghép nối toàn bộ dữ liệu TP. Hà Nội, chỉ cần chạy chuỗi 5 lệnh sau:

```powershell
# 1. Sinh khung lưới H3 toàn Hà Nội
python generate_h3_grid.py data/raw/osm/hanoi_boundary.geojson data/processed/cells.parquet

# 2. Trích xuất đặc trưng đường bộ toàn Hà Nội
python extract_road_features.py data/raw/osm/hanoi.osm.pbf data/processed/cells.parquet data/processed/cells.parquet

# 3. Trích xuất dân số WorldPop & POI toàn Hà Nội
python extract_population_poi.py data/raw/osm/hanoi.osm.pbf data/raw/worldpop/vnm_ppp_2020_100m.tif data/processed/cells.parquet data/processed/cells.parquet

# 4. Render ảnh bản đồ 224x224 cho toàn bộ các ô
python render_cell_images.py data/processed/cells.parquet data/processed/cell_images data/processed/cells.parquet

# 5. Tải thời tiết giai đoạn 2019-2025
python fetch_weather.py data/processed/cells.parquet data/processed/weather.parquet
```

---

## 5. Tiêu Chuẩn Nghiệm Thu (Definition of Done)

* [x] **Độ phủ ảnh (`image_path`):** 100% ô H3 có file ảnh PNG 224×224 px hợp lệ, không nhãn chữ.
* [x] **Dân số & Hạ tầng:** 100% ô H3 có đủ giá trị số học $\ge 0$, không bị `NaN` hay lệch CRS.
* [x] **Thời tiết:** Tổng hợp chuẩn 4 khung 6 giờ/ngày, không có lỗ hổng dữ liệu.
* [x] **Khớp Schema 100%:** Cấu trúc cột của `cells.parquet` và `weather.parquet` tuân thủ nghiêm ngặt theo Mục 5 `docs/context.md`.
