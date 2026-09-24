# Tổng Hợp & So Sánh Triển Khai Track B — Dữ Liệu Không Gian (CrashFormer Hà Nội)

> **Mục đích tài liệu:** Đối chiếu toàn diện giữa cách tiếp cận ban đầu (cũ) và cách tiếp cận chuẩn hóa của Lead (mới), nêu rõ các cải tiến kỹ thuật vượt trội và hướng dẫn từng bước quy trình thực thi mới.

---

## PHẦN 1: Điểm Khác Nhau Giữa Cách Cũ và Cách Mới

| Hạng mục so sánh | Cách tiếp cận cũ (Initial Approach) | Cách tiếp cận mới của Lead (Sample Standard) |
|---|---|---|
| **1. Cơ chế Render Ảnh (B3)** | **Dùng Web Tile qua mạng (`contextily` / CartoDB)**.<br>Tải từng mảnh ảnh bitmap từ server bên thứ ba về ghép lại. | **Vẽ vector trực tiếp (Direct Vector Rendering)** từ file `.osm.pbf` local bằng `osmium` + `shapely` + `matplotlib`. |
| **2. Sự phụ thuộc kết nối** | Phải kết nối Internet liên tục, dễ bị timeout, lỗi mạng, rate-limit khi render hàng nghìn ô. | **Hoàn toàn Offline 100%**, xử lý trực tiếp trên đĩa cứng, tốc độ render cực nhanh và ổn định tuyệt đối. |
| **3. Màu sắc & Phân cấp nét đường** | Nét đường đồng nhất hoặc phụ thuộc style cố định của CartoDB, độ tương phản thấp. | **Quy chuẩn màu sắc & độ dày nét riêng biệt (`ROAD_STYLE`)**:<br>• Đỏ (`#d73027`): Motorway<br>• Cam (`#fc8d59`, `#fdae61`): Trunk & Primary<br>• Vàng (`#fee08b`, `#f6e8c3`): Secondary & Tertiary<br>• Trắng (`#ffffff`): Đường dân sinh/nội bộ |
| **4. Các lớp đối tượng không gian** | Dễ lẫn chi tiết thừa hoặc thiếu khối nhà do phụ thuộc tile server. | Phân lớp hiển thị chính xác theo độ sâu (`zorder`):<br>1. Mặt nước (Sông/Hồ): `#9ecae1` (`zorder=1`)<br>2. Khối nhà (Buildings): `#bdbdbd` (`zorder=2`)<br>3. Mạng lưới đường: Theo `ROAD_STYLE` (`zorder=3`)<br>4. Nền ảnh: Xám nhạt `#edf1f4` |
| **5. Cơ chế kiểm tra ảnh (Visual QA)** | Chỉ lưu từng file ảnh riêng lẻ trong thư mục, muốn kiểm tra phải mở từng file. | Tự động ghép 12 ảnh đầu tiên ($4 \times 3$) thành file **`cell_images_contact_sheet.png`** để review bằng mắt trong 3 giây. |
| **6. Địa giới hành chính** | Dùng ranh giới quận/huyện cũ hoặc tự vẽ bounding box thủ công. | Dùng bộ **126 xã/phường chuẩn địa giới Hà Nội 2025** (`hanoi_wards_2025.geojson`), gán `ward_id` mã số định danh duy nhất. |
| **7. Quản lý Pipeline & Dữ liệu** | Các script chạy độc lập, thiếu tham số dòng lệnh chuẩn, gán cứng đường dẫn. | Chuẩn hóa CLI (`argparse`) với cờ tham số nhất quán (`--pbf`, `--cells`, `--cell-geometry`, `--output`). |
| **8. Báo cáo chất lượng tự động (QA)** | Không có file kiểm định dữ liệu trung gian. | Mỗi bước (B4, B5) đều tự động sinh file **`*_qa.json`** ghi lại thống kê số dòng, min/max, cảnh báo độ chồng lấn lưới H3. |

---

## PHẦN 2: Những Cải Tiến Vượt Bậc Mà Cách Mới Mang Lại

### 1. Độc lập 100% với Internet & Tối ưu hiệu năng
* Không còn rủi ro bị chặn IP (như lỗi `ConnectionResetError: 10054` từ máy chủ OSM/Nominatim).
* Tốc độ render hàng nghìn ảnh tăng gấp 10–20 lần vì không tốn thời gian tải HTTP request cho từng tile bản đồ.

### 2. Tối ưu hóa tuyệt đối cho mô hình thị giác (Image Encoder — VAN)
* **Loại bỏ 100% chữ / nhãn:** Đảm bảo mô hình mạng nơ-ron học thuần túy về **hình thái học hình học của mạng lưới giao thông** (mật độ nút giao, độ cong, phân cấp đường lớn - nhỏ) mà không bị "học vẹt" đọc tên đường.
* **Cố định tỷ lệ không gian (Projected Extent):** Toàn bộ các ô ở cùng một resolution có chung đúng một khung nhìn theo hệ mét phẳng UTM Zone 48N (`EPSG:32648`), không bị co dãn tự động.

### 3. Tương thích hoàn toàn với thay đổi địa giới hành chính Hà Nội 2025
* Không còn tình trạng sai lệch dữ liệu do sử dụng phân cấp quận/huyện cũ.
* Bộ dữ liệu 126 xã/phường giúp mô hình bám sát cấu trúc quản lý giao thông đô thị hiện đại của Hà Nội.

### 4. Quy trình kiểm thử chất lượng dữ liệu (QA/QC) chuyên nghiệp
* Cơ chế **Contact Sheet** giúp phát hiện ngay các lỗi hình ảnh (ảnh bị trắng trơn, lệch màu, lỗi crop) trước khi đưa vào huấn luyện mô hình.
* File QA JSON theo dõi sát sao số lượng ô H3, tính hợp lệ của các phép tính độ dài đường và thống kê dân số.

---

## PHẦN 3: Mô Tả Chi Tiết Từng Bước Của Quy Trình Mới

Toàn bộ quy trình mới được thiết kế dạng module hóa tuần tự. Dưới đây là các bước thực hiện chi tiết (ví dụ trên xã Chương Dương `ward_id = 10237` hoặc Phường Xuân Phương `ward_id = 00622`):

```
                       ┌──► B6 (Thời tiết: collect_weather.py / ingest_era5_weather.py)
                       │
maps/hanoi.osm.pbf ────┼──► B4 (Đặc trưng đường: build_road_features.py)
                       │
maps/hanoi_wards_2025 ─┼──► B2 (Lưới H3: build_h3_grid.py) ──► B5 (Dân số/POI: build_population_poi_features.py)
                       │
                       └──► B3 (Render ảnh vector: render_cell_images.py ──► contact_sheet.png)
```

---

### Bước 1: Trích xuất ranh giới xã/phường mục tiêu
* **Script:** `extract_ward_boundary.py`
* **Mục tiêu:** Tách đa giác ranh giới của 1 xã/phường cụ thể từ bộ dữ liệu 126 xã/phường Hà Nội 2025 (`maps/hanoi_wards_2025.geojson`).
* **Lệnh thực thi:**
  ```powershell
  python extract_ward_boundary.py --ward-id 10237 --output maps/chuong_duong_boundary.geojson
  ```
* **Output:** `maps/chuong_duong_boundary.geojson`.

---

### Bước 2: Cắt dữ liệu OpenStreetMap (OSM) cục bộ cho xã/phường
* **Công cụ:** `osmium-tool`
* **Mục tiêu:** Trích xuất toàn bộ mạng lưới đường, sông hồ và khối nhà của riêng xã đó từ file OSM Hà Nội gốc (`data/raw/osm/hanoi.osm.pbf`).
* **Lệnh thực thi:**
  ```powershell
  osmium extract --strategy=complete_ways -p maps/chuong_duong_boundary.geojson data/raw/osm/hanoi.osm.pbf -o maps/chuong_duong.osm.pbf --overwrite
  ```
* **Output:** `maps/chuong_duong.osm.pbf` (dung lượng siêu nhẹ, chỉ ~200KB – 1MB).

---

### Bước 3 (B2): Sinh lưới ô lục giác Uber H3 (Resolution 7 & 8)
* **Script:** `build_h3_grid.py`
* **Mục tiêu:** Phủ các ô lục giác H3 lên ranh giới xã; đồng thời xuất file GeoJSON để có thể mở kiểm tra trực quan trên phần mềm QGIS.
* **Lệnh thực thi:**
  ```powershell
  python build_h3_grid.py --boundary maps/chuong_duong_boundary.geojson --ward "Chương Dương" --output data/processed/pilots/chuong_duong/cells.parquet --geometry-output data/processed/pilots/chuong_duong/cells_geometry.geojson
  ```
* **Output:**
  * `cells.parquet`: Bảng dữ liệu khung ban đầu (chứa `h3_index`, `resolution`, `centroid_lat`, `centroid_lon`, `ward`).
  * `cells_geometry.geojson`: File hình học các ô lục giác để xem trong QGIS.

---

### Bước 4 (B4): Trích xuất đặc trưng mạng lưới đường bộ dạng số
* **Script:** `build_road_features.py`
* **Mục tiêu:** Tính toán chiều dài các cấp đường (mét) theo hệ chiếu phẳng UTM Zone 48N (`EPSG:32648`), đếm số nút giao (`n_intersections`), số đèn tín hiệu (`n_traffic_signals`), vạch sang đường (`n_crossings`), và cờ đường trục chính (`has_major_road`).
* **Lệnh thực thi:**
  ```powershell
  python build_road_features.py --pbf maps/chuong_duong.osm.pbf --cells data/processed/pilots/chuong_duong/cells.parquet --cell-geometry data/processed/pilots/chuong_duong/cells_geometry.geojson --output data/processed/pilots/chuong_duong/cells_b4.parquet --qa-output data/processed/pilots/chuong_duong/cells_b4_qa.json
  ```
* **Output:** `cells_b4.parquet` và file kiểm định `cells_b4_qa.json`.

---

### Bước 5 (B5): Tích hợp Dân số WorldPop và Điểm quan tâm (POI)
* **Script:** `build_population_poi_features.py`
* **Mục tiêu:** Thống kê tổng dân số và mật độ dân số từ ảnh raster WorldPop 100m (`vnm_ppp_2020_100m.tif`) bằng Zonal Statistics; đếm số lượng trường học (`n_schools`), bệnh viện (`n_hospitals`), và khu thương mại (`n_commercial_poi`) từ file OSM.
* **Lệnh thực thi:**
  ```powershell
  python build_population_poi_features.py --cells data/processed/pilots/chuong_duong/cells_b4.parquet --cell-geometry data/processed/pilots/chuong_duong/cells_geometry.geojson --population-raster data/raw/worldpop/vnm_ppp_2020_100m.tif --pbf maps/chuong_duong.osm.pbf --output data/processed/pilots/chuong_duong/cells_b5.parquet --qa-output data/processed/pilots/chuong_duong/cells_b5_qa.json
  ```
* **Output:** `cells_b5.parquet` và file kiểm định `cells_b5_qa.json`.

---

### Bước 6 (B3): Render ảnh bản đồ Vector OSM $224 \times 224\text{ px}$ chuẩn
* **Script:** `render_cell_images.py`
* **Mục tiêu:** Đọc trực tiếp các đối tượng đường sá, sông hồ, khối nhà từ PBF và vẽ thành các file ảnh PNG chuẩn $224 \times 224\text{ px}$ không nhãn chữ; điền cột `image_path` và tạo bảng ảnh liên hệ `cell_images_contact_sheet.png`.
* **Lệnh thực thi:**
  ```powershell
  python render_cell_images.py --pbf maps/chuong_duong.osm.pbf --cells data/processed/pilots/chuong_duong/cells_b5.parquet --cell-geometry data/processed/pilots/chuong_duong/cells_geometry.geojson --image-dir data/processed/pilots/chuong_duong/cell_images --output data/processed/pilots/chuong_duong/cells_b3.parquet --contact-sheet data/processed/pilots/chuong_duong/cell_images_contact_sheet.png
  ```
* **Output:**
  * Thư mục `cell_images/<h3_index>.png`: Chứa toàn bộ ảnh đầu vào cho mô hình Image Encoder (VAN).
  * `cell_images_contact_sheet.png`: Bảng ghép 12 ảnh đầu tiên để kiểm tra trực quan nhanh.
  * **`cells_b3.parquet`**: **BẢNG CUỐI CÙNG HOÀN CHỈNH** với đầy đủ **19 cột chuẩn** (kết hợp trọn vẹn B2 + B4 + B5 + B3).

---

### Bước 7 (B6): Thu thập và xử lý Dữ liệu Thời tiết
* **Script:** `collect_weather.py` (từ Open-Meteo Historical API) hoặc `ingest_era5_weather.py` (từ file lưới NetCDF4 của ERA5).
* **Mục tiêu:** Lấy dữ liệu nhiệt độ, mưa, gió, độ ẩm, mây và gộp chuẩn theo 4 khung 6 giờ/ngày (`0h`, `6h`, `12h`, `18h` múi giờ `Asia/Bangkok`).
* **Output:** `weather.parquet` với khóa chính `(h3_index, time_bin)`.
