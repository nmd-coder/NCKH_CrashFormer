# Báo Cáo Tổng Kết Toàn Diện Track B — Dữ Liệu Không Gian (Spatial Pipeline)
## Dự Án Nghiên Cứu Khoa Học Sinh Viên: Mô Hình Dự Đoán Tai Nạn Giao Thông CrashFormer Hà Nội

> **Địa bàn thử nghiệm (Pilot):** Phường Xuân Phương (`ward_id = 00622`) & Xã Chương Dương (`ward_id = 10237`)  
> **Tài liệu tham chiếu:** `docs/context.md`, `docs/track_b_guide.md`, `docs/chuong_duong_track_b_pilot_guide.md`  
> **Thời gian hoàn thành:** 09/2026

---

## MỤC LỤC

1. [Tổng Quan Đề Tài & Phạm Vi Track B](#1-tổng-quan-đề-tài--phạm-vi-track-b)
2. [Mô Tả & Trình Bày Chi Tiết Quy Trình Triển Khai (Từng Bước B0 — B6)](#2-mô-tả--trình-bày-chi-tiết-quy-trình-triển-khai-từng-bước-b0--b6)
3. [Tổng Hợp Quá Trình: Thành Quả Đạt Được & Các Vấn Đề Đã Khắc Phục](#3-tổng-hợp-quá-trình-thành-quả-đạt-được--các-vấn-đề-đã-khắc-phục)
4. [Báo Cáo Tóm Tắt Kết Quả Nghiệm Thu (Executive Summary Báo Cáo Lead)](#4-báo-cáo-tóm-tắt-kết-quả-nghiệm-thu-executive-summary-báo-cáo-lead)
5. [Hướng Dẫn Quy Trình Thực Hiện Cho Các Xã/Phường Tiếp Theo](#5-hướng-dẫn-quy-trình-thực-hiện-cho-các-xãphường-tiếp-theo)

---

## 1. Tổng Quan Đề Tài & Phạm Vi Track B

### 1.1. Bối cảnh và Mục tiêu
Đề tài nghiên cứu xây dựng mô hình dự đoán nguy cơ tai nạn giao thông đa phương thức cho TP. Hà Nội dựa trên kiến trúc **CrashFormer (UrbanAI/SIGSPATIAL 2023)**. Trong đó, **Track B (Dữ liệu không gian)** đóng vai trò tạo lập toàn bộ nguồn dữ liệu đầu vào cho các khối kiến trúc nơ-ron:
* **Image Encoder (Visual Attention Network - VAN):** Học các đặc trưng hình thái học, cấu trúc hình học mạng lưới đường, sông ngòi, công trình qua ảnh bản đồ $224 \times 224\text{ px}$.
* **Data Encoder (Nhân khẩu & Hạ tầng):** Mật độ dân số từ ảnh raster WorldPop 100m và các điểm thu hút giao thông (POI: trường học, bệnh viện, khu thương mại).
* **Baseline số học (Không dùng ảnh):** Đặc trưng hình học đường bộ dạng số (chiều dài đường theo cấp, nút giao, đèn tín hiệu) dùng để chứng minh sự đóng góp của module thị giác máy tính.
* **Contextual Features:** Chuỗi thời gian thời tiết theo khung 6 giờ từ Open-Meteo / ERA5.

### 1.2. Sơ đồ luồng dữ liệu (Data Pipeline Architecture)

```
                            ┌──► B6: Thời tiết 6h (2019-2025) ──► weather.parquet
                            │
maps/hanoi.osm.pbf ─────────┼──► B4: Đặc trưng đường bộ ────────┐
                            │                                   │
maps/hanoi_wards_2025 ──────┼──► B2: Lưới Uber H3 (Res 7 & 8) ──┴──► B5: Dân số & POI ──► B3: Render Vector ──► cells_b3.parquet (19 cột)
(126 xã/phường 2025)        │
                            └────────────────────────────────────────────────────────► cell_images/*.png & contact_sheet.png
```

---

## 2. Mô Tả & Trình Bày Chi Tiết Quy Trình Triển Khai (Từng Bước B0 — B6)

### 🔹 BƯỚC 0: Khởi Tạo Môi Trường GIS & Công Cụ Cốt Lõi
* **Mục tiêu:** Cài đặt các thư viện địa lý không gian (GIS) và công cụ C++ trên Windows để đảm bảo xử lý hình học đa giác, đọc file raster vệ tinh và cắt file OSM siêu tốc.
* **Công cụ cài đặt:** `geopandas`, `rasterio`, `rasterstats`, `h3`, `osmnx`, `pyarrow`, `osmium-tool`, `contextily`, `matplotlib`, `pyproj`, `shapely`.
* **Lệnh cài đặt:**
  ```powershell
  conda activate nckh_spatial
  pip install geopandas shapely rasterio rasterstats pyarrow osmnx h3 requests contextily matplotlib Pillow pyyaml osmium pyproj netCDF4 xarray
  conda install -c conda-forge osmium-tool -y
  ```

---

### 🔹 BƯỚC B1: Tải & Cắt Dữ Liệu Bản Đồ OpenStreetMap (OSM)
* **Mục tiêu:** Tải file dữ liệu toàn quốc `vietnam-latest.osm.pbf` (~600MB–1GB) từ Geofabrik và dùng `osmium` cắt riêng bản đồ TP. Hà Nội và ranh giới các xã/phường mục tiêu mà không gây tràn RAM (OOM).
* **Input:** `maps/hanoi_boundary.geojson`, `maps/xuan_phuong_boundary.geojson`.
* **Lệnh thực thi:**
  ```powershell
  # 1. Cắt OSM toàn Hà Nội từ file Việt Nam
  osmium extract --strategy=complete_ways -p maps/hanoi_boundary.geojson data/raw/osm/vietnam-latest.osm.pbf -o data/raw/osm/hanoi.osm.pbf --overwrite

  # 2. Cắt OSM riêng cho Phường Xuân Phương (ward_id = 00622)
  python extract_ward_boundary.py --ward-id 00622 --output maps/xuan_phuong_boundary.geojson
  osmium extract --strategy=complete_ways -p maps/xuan_phuong_boundary.geojson data/raw/osm/hanoi.osm.pbf -o maps/xuan_phuong.osm.pbf --overwrite
  ```
* **Output:** `data/raw/osm/hanoi.osm.pbf` (21.8 MB), `maps/xuan_phuong.osm.pbf` (~210 KB).

---

### 🔹 BƯỚC B2: Sinh Lưới Ô Lục Giác Uber H3 (Resolution 7 & 8)
* **Mục tiêu:** Phủ lưới ô lục giác theo chuẩn không gian Uber H3 lên ranh giới địa lý của xã/phường.
  * **Resolution 7:** Ô lớn $\approx 5.16\text{ km}^2$ (toàn thành phố).
  * **Resolution 8:** Ô nhỏ $\approx 0.74\text{ km}^2$ (nội thành, mật độ cao).
* **Script:** `build_h3_grid.py`
* **Lệnh thực thi:**
  ```powershell
  python build_h3_grid.py --boundary maps/xuan_phuong_boundary.geojson --ward "Xuân Phương" --output data/processed/pilots/xuan_phuong/cells.parquet --geometry-output data/processed/pilots/xuan_phuong/cells_geometry.geojson
  ```
* **Output:**
  * `cells.parquet`: Bảng khung H3 (chứa `h3_index`, `resolution`, `centroid_lat`, `centroid_lon`, `district`, `ward`).
  * `cells_geometry.geojson`: File hình học các đa giác lục giác để kiểm tra trực quan trên phần mềm QGIS.

---

### 🔹 BƯỚC B4: Trích Xuất Đặc Trưng Mạng Lưới Đường Bộ Dạng Số
* **Mục tiêu:** Trích xuất các thuộc tính hình học và cấu trúc hạ tầng từ file OSM PBF làm baseline so sánh với mô hình ảnh.
* **Quy chuẩn kỹ thuật:** Chiều dài đường được tính theo hệ mét phẳng UTM Zone 48N (`EPSG:32648`), tuyệt đối không tính trên độ WGS84.
* **Script:** `build_road_features.py`
* **Lệnh thực thi:**
  ```powershell
  python build_road_features.py --pbf maps/xuan_phuong.osm.pbf --cells data/processed/pilots/xuan_phuong/cells.parquet --cell-geometry data/processed/pilots/xuan_phuong/cells_geometry.geojson --output data/processed/pilots/xuan_phuong/cells_b4.parquet --qa-output data/processed/pilots/xuan_phuong/cells_b4_qa.json
  ```
* **Output:** `cells_b4.parquet` (bổ sung các cột: `road_length_primary`, `road_length_secondary`, `road_length_residential`, `n_intersections`, `n_traffic_signals`, `n_crossings`, `has_major_road`) + `cells_b4_qa.json`.

---

### 🔹 BƯỚC B5: Tích Hợp Dân Số WorldPop và Điểm Quan Tâm (POI)
* **Mục tiêu:** Tính tổng dân số, mật độ dân số từ file raster WorldPop 100m (`vnm_ppp_2020_100m.tif`) bằng Zonal Statistics; đếm số lượng trường học (`n_schools`), bệnh viện (`n_hospitals`), và TTTM/chợ (`n_commercial_poi`) từ OSM.
* **Quy chuẩn kỹ thuật:** Bắt buộc kiểm tra khớp hệ tọa độ CRS (`assert src.crs == EPSG:4326`) giữa raster và polygon vector trước khi tính tổng.
* **Script:** `build_population_poi_features.py`
* **Lệnh thực thi:**
  ```powershell
  python build_population_poi_features.py --cells data/processed/pilots/xuan_phuong/cells_b4.parquet --cell-geometry data/processed/pilots/xuan_phuong/cells_geometry.geojson --population-raster data/raw/worldpop/vnm_ppp_2020_100m.tif --pbf maps/xuan_phuong.osm.pbf --output data/processed/pilots/xuan_phuong/cells_b5.parquet --qa-output data/processed/pilots/xuan_phuong/cells_b5_qa.json
  ```
* **Output:** `cells_b5.parquet` (bổ sung các cột: `population`, `population_density`, `n_schools`, `n_hospitals`, `n_commercial_poi`) + `cells_b5_qa.json`.

---

### 🔹 BƯỚC B3: Render Ảnh Bản Đồ Vector $224 \times 224\text{ px}$ Cho Image Encoder (VAN)
* **Mục tiêu:** Vẽ trực tiếp vector các lớp đối tượng từ file OSM PBF thành các file ảnh PNG chuẩn $224 \times 224\text{ px}$, điền cột `image_path` vào bảng dữ liệu và tạo file `cell_images_contact_sheet.png` để review nhanh.
* **3 Nguyên tắc vàng bắt buộc:**
  1. **Cố định mức Zoom (Fixed Projected Extent):** Toàn bộ ô cùng resolution có chung một kích thước nhìn theo mét (Res 7: bán kính crop ~1400m; Res 8: bán kính crop ~550m).
  2. **TẮT HOÀN TOÀN NHÃN CHỮ (100% No Text/Labels):** Đảm bảo mô hình học cấu trúc hình học mạng lưới đường, không học đọc chữ.
  3. **Quy chuẩn màu sắc & lớp đối tượng (`ROAD_STYLE`):**
     * Đỏ (`#d73027`): Motorway
     * Cam (`#fc8d59`, `#fdae61`): Trunk & Primary
     * Vàng (`#fee08b`, `#f6e8c3`): Secondary & Tertiary
     * Trắng (`#ffffff`): Đường dân sinh
     * Mặt nước (`water`): `#9ecae1` (`zorder=1`)
     * Khối nhà (`buildings`): `#bdbdbd` (`zorder=2`)
     * Màu nền: `#edf1f4`
* **Script:** `render_cell_images.py`
* **Lệnh thực thi:**
  ```powershell
  python render_cell_images.py --pbf maps/xuan_phuong.osm.pbf --cells data/processed/pilots/xuan_phuong/cells_b5.parquet --cell-geometry data/processed/pilots/xuan_phuong/cells_geometry.geojson --image-dir data/processed/pilots/xuan_phuong/cell_images --output data/processed/pilots/xuan_phuong/cells_b3.parquet --contact-sheet data/processed/pilots/xuan_phuong/cell_images_contact_sheet.png
  ```
* **Output:** Thư mục ảnh `cell_images/<h3_index>.png`, ảnh tổng hợp `cell_images_contact_sheet.png`, và **bảng cuối cùng hoàn chỉnh `cells_b3.parquet` (19 cột)**.

---

### 🔹 BƯỚC B6: Thu Thập & Tổng Hợp Dữ Liệu Thời Tiết (2019 — 2025)
* **Mục tiêu:** Thu thập dữ liệu khí tượng lịch sử theo giờ từ Open-Meteo / ERA5 cho toàn bộ giai đoạn nghiên cứu 2019–2025 và gộp về 4 khung 6 giờ/ngày (`0h`, `6h`, `12h`, `18h`).
* **Quy tắc gộp dữ liệu:**
  * 🌧️ `precipitation_sum`: **TỔNG (Sum)**
  * 🌫️ `visibility_min`: **GIÁ TRỊ THẤP NHẤT (Min)** (để `null` chuẩn do giới hạn dữ liệu tái phân tích ERA5)
  * 🌡️ `temp_mean`, 💧 `humidity_mean`: **TRUNG BÌNH (Mean)**
  * 💨 `wind_speed_max`: **MAX**
* **Script:** `collect_weather.py`
* **Lệnh thực thi:**
  ```powershell
  python collect_weather.py --cells data/processed/pilots/xuan_phuong/cells.parquet --output data/processed/pilots/xuan_phuong/weather.parquet --start-date 2019-01-01 --end-date 2025-12-31
  ```
* **Output:** `weather.parquet` (153.420 dòng cho 15 ô $\times$ 10.228 khung 6h) + `weather_qa.json`.

---

## 3. Tổng Hợp Quá Trình: Thành Quả Đạt Được & Các Vấn Đề Đã Khắc Phục

### 3.1. Bảng So Sánh Cách Tiếp Cận Cũ vs Cách Tiếp Cận Mới Chuẩn Hóa Của Lead

| Hạng mục so sánh | Cách tiếp cận cũ (Initial Approach) | Cách tiếp cận mới của Lead (Sample Standard) |
|---|---|---|
| **Cơ chế Render Ảnh (B3)** | Tải mảnh ảnh Web Tile trực tuyến từ CartoDB qua mạng. | **Direct Vector Rendering:** Đọc và vẽ vector trực tiếp từ PBF local bằng `osmium` + `shapely` + `matplotlib`. |
| **Sự phụ thuộc Internet** | Cần Internet liên tục; dễ lỗi timeout/chặn kết nối khi tải nhiều. | **Hoàn toàn Offline 100%**, tốc độ render cực nhanh, ổn định tuyệt đối. |
| **Phân cấp màu đường** | Đường nét mờ nhạt, phụ thuộc style mặc định của Web Tile. | Phân cấp màu sắc & độ dày nét theo chuẩn khoa học (`ROAD_STYLE`). |
| **Lớp địa vật** | Dễ lẫn chi tiết thừa hoặc thiếu khối nhà. | Tách rõ 3 lớp đối tượng theo chiều sâu: Nước $\rightarrow$ Nhà $\rightarrow$ Đường sá. |
| **Visual QA** | Lưu ảnh rời rạc, khó kiểm tra chất lượng. | Tự động tạo bảng ghép 12 ảnh **`contact_sheet.png`** để review trong 3s. |
| **Địa giới hành chính** | Dùng quận/huyện cũ hoặc tự tạo bounding box. | Áp dụng bộ **126 xã/phường Hà Nội địa giới 2025** có `ward_id` duy nhất. |
| **Kiểm định dữ liệu (QA)** | Không có file log số liệu trung gian. | Mỗi bước đều tự sinh file **`*_qa.json`** kiểm tra số dòng, min/max, cảnh báo. |

---

### 3.2. Nhật Ký Xử Lý & Khắc Phục Các Lỗi Kỹ Thuật Thực Tế (Troubleshooting Log)

Trong quá trình triển khai, toàn bộ các lỗi phát sinh đã được phát hiện và xử lý dứt điểm:

1. **Lỗi `Conda Solving Environment` bị treo:**
   * *Nguyên nhân:* Bộ giải cổ điển của Conda bị lặp đệ quy khi phân giải xung đột giữa kênh `defaults` và `conda-forge`.
   * *Khắc phục:* Chuyển sang cài đặt thư viện bằng `pip` với pre-compiled wheels trong môi trường ảo `nckh_spatial` (thời gian cài đặt giảm từ 30 phút xuống còn 30 giây).
2. **Lỗi ngắt kết nối mạng `ConnectionResetError: [WinError 10054]`:**
   * *Nguyên nhân:* Máy chủ OpenStreetMap Nominatim chặn kết nối IP khi dùng `osmnx.geocode_to_gdf()`.
   * *Khắc phục:* Thay thế bằng nguồn ranh giới chính thức `maps/hanoi_wards_2025.geojson` kết hợp script `extract_ward_boundary.py` sử dụng `ward_id` nội bộ.
3. **Lỗi bảng mã console Windows `UnicodeEncodeError: 'charmap' codec can't encode \u23f3`:**
   * *Nguyên nhân:* PowerShell trên Windows dùng bảng mã `cp1252` gây lỗi khi in emoji hoặc ký tự tiếng Việt có dấu.
   * *Khắc phục:* Cấu hình `sys.stdout.reconfigure(encoding='utf-8')` và chuẩn hóa thông báo log ASCII.
4. **Lỗi API H3 v4.x `AttributeError: module 'h3' has no attribute 'geojson_to_geometry'`:**
   * *Nguyên nhân:* Thư viện `h3-py` phiên bản 4.x thay đổi tên hàm hình học so với bản v3.
   * *Khắc phục:* Cập nhật mã nguồn sang hàm chuẩn `h3.geo_to_cells(geometry, resolution)`.
5. **Lỗi thiếu engine Parquet `ImportError: Unable to find a usable engine ('pyarrow')`:**
   * *Nguyên nhân:* Môi trường Python thiếu thư viện backend xử lý file Parquet.
   * *Khắc phục:* Cài đặt bổ sung `pyarrow` với chuẩn nén `zstd`.
6. **Lỗi thiếu biến tầm nhìn `visibility` trong API thời tiết:**
   * *Nguyên nhân:* Dữ liệu khí tượng tái phân tích toàn cầu ECMWF ERA5 không có biến tầm nhìn ngang bề mặt dạng lưới vi mô.
   * *Khắc phục:* Giữ nguyên cột `visibility_min` với giá trị `null` theo đúng nguyên tắc trung thực khoa học (Mục 8 `context.md`); sử dụng cặp biến đại diện `humidity_mean` và `precipitation_sum` làm proxy khi huấn luyện mô hình.

---

## 4. Báo Cáo Tóm Tắt Kết Quả Nghiệm Thu (Executive Summary Báo Cáo Lead)

### 📊 Bảng Nghiệm Thu Phường Xuân Phương (`ward_id = 00622`)

```text
========================================================================================
                      BÁO CÁO NGHIỆM THU TRACK B: PHƯỜNG XUÂN PHƯƠNG
========================================================================================
1. KHÔNG GIAN VÀ LƯỚI H3:
   - Tổng số ô H3: 15 ô (1 ô Resolution 7: 874143693ffffff; 14 ô Resolution 8)
   - File hình học QGIS: data/processed/pilots/xuan_phuong/cells_geometry.geojson

2. ĐẶC TRƯNG ĐƯỜNG BỘ & DÂN SỐ / POI (cells_b3.parquet):
   - Số cột: 19 / 19 cột (Khớp 100% schema Mục 5 docs/context.md)
   - Số dòng: 15 dòng
   - Tỷ lệ ô có Dân số hợp lệ (>= 0): 100.0%
   - Tỷ lệ ô có Ảnh bản đồ 224x224 px tồn tại: 100.0% (15/15 ảnh)
   - File Contact Sheet: data/processed/pilots/xuan_phuong/cell_images_contact_sheet.png

3. CHUỖI THỜI GIAN THỜI TIẾT 2019 - 2025 (weather.parquet):
   - Số cột: 7 / 7 cột (Khớp 100% schema Mục 5 docs/context.md)
   - Tổng số bản ghi (ô x khung 6h): 153.420 dòng (15 ô x 10.228 khung 6h)
   - Khoảng thời gian: 2019-01-01T00:00:00+07:00 -> 2025-12-31T18:00:00+07:00 (7 năm trọn vẹn)
   - Độ toàn vẹn dữ liệu: 100% không có lỗ hổng trên toàn bộ các biến lõi
========================================================================================
KẾT LUẬN: ĐÁP ỨNG 100% TẤT CẢ TIÊU CHÍ ĐẦU RA THEO MỤC 7 DOCS/CONTEXT.MD!
========================================================================================
```

---

## 5. Hướng Dẫn Quy Trình Thực Hiện Cho Các Xã/Phường Tiếp Theo

Khi tiếp tục thực hiện cho bất kỳ xã/phường nào khác trong 126 xã/phường Hà Nội:

1. **Tra cứu mã `ward_id`** của xã/phường trong file `maps/hanoi_wards_2025.geojson`.
2. **Chạy chuỗi 7 lệnh chuẩn hóa** (Ví dụ cho xã mới có mã `<ward_id>` và tên `<ten_xa>`):

```powershell
# Bước 1: Trích xuất ranh giới
python extract_ward_boundary.py --ward-id <ward_id> --output maps/<ten_xa>_boundary.geojson

# Bước 2: Cắt dữ liệu OSM
osmium extract --strategy=complete_ways -p maps/<ten_xa>_boundary.geojson data/raw/osm/hanoi.osm.pbf -o maps/<ten_xa>.osm.pbf --overwrite

# Bước 3: Sinh lưới H3
python build_h3_grid.py --boundary maps/<ten_xa>_boundary.geojson --ward "<Ten_Xa>" --output data/processed/pilots/<ten_xa>/cells.parquet --geometry-output data/processed/pilots/<ten_xa>/cells_geometry.geojson

# Bước 4: Trích xuất đặc trưng đường bộ
python build_road_features.py --pbf maps/<ten_xa>.osm.pbf --cells data/processed/pilots/<ten_xa>/cells.parquet --cell-geometry data/processed/pilots/<ten_xa>/cells_geometry.geojson --output data/processed/pilots/<ten_xa>/cells_b4.parquet

# Bước 5: Tích hợp dân số & POI
python build_population_poi_features.py --cells data/processed/pilots/<ten_xa>/cells_b4.parquet --cell-geometry data/processed/pilots/<ten_xa>/cells_geometry.geojson --population-raster data/raw/worldpop/vnm_ppp_2020_100m.tif --pbf maps/<ten_xa>.osm.pbf --output data/processed/pilots/<ten_xa>/cells_b5.parquet

# Bước 6: Render ảnh bản đồ vector 224x224 & Contact sheet
python render_cell_images.py --pbf maps/<ten_xa>.osm.pbf --cells data/processed/pilots/<ten_xa>/cells_b5.parquet --cell-geometry data/processed/pilots/<ten_xa>/cells_geometry.geojson --image-dir data/processed/pilots/<ten_xa>/cell_images --output data/processed/pilots/<ten_xa>/cells_b3.parquet --contact-sheet data/processed/pilots/<ten_xa>/cell_images_contact_sheet.png

# Bước 7: Tải chuỗi thời tiết 2019-2025
python collect_weather.py --cells data/processed/pilots/<ten_xa>/cells.parquet --output data/processed/pilots/<ten_xa>/weather.parquet --start-date 2019-01-01 --end-date 2025-12-31
```
