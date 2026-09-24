# Kết quả mẫu Track B — Phường Xuân Phương (để đối chiếu)

> **Tài liệu tham chiếu:** [`docs/chuong_duong_track_b_pilot_guide.md`](chuong_duong_track_b_pilot_guide.md) & [`docs/track_b_guide.md`](track_b_guide.md)  
> **Địa bàn:** Phường Xuân Phương (`ward_id = 00622`)  
> **Mục đích:** Tài liệu này cung cấp **kết quả THẬT và đầy đủ nhất** sau khi chạy xong toàn bộ pipeline Track B trên Phường Xuân Phương (bao gồm cả dữ liệu thời tiết 7 năm 2019–2025). Dùng tài liệu này để đối chiếu cấu trúc cột, kiểu dữ liệu, các giá trị thực tế và file QA khi triển khai trên các xã/phường khác.

---

## 1. Toàn bộ cấu trúc file kết quả sau khi hoàn thành

```text
data/processed/pilots/xuan_phuong/
├── cells.parquet                    # sau bước B2 — chỉ có lưới H3 thô (15 ô)
├── cells_geometry.geojson           # hình lục giác, dùng để xem trên QGIS
├── cells_b4.parquet                 # + đặc trưng đường bộ (B4)
├── cells_b4_qa.json                 # QA log kiểm tra hình học và giao lộ B4
├── cells_b5.parquet                 # + dân số WorldPop & OSM POI (B5)
├── cells_b5_qa.json                 # QA log kiểm tra dân số & POI B5
├── cells_b3.parquet                 # ⭐ BẢNG ĐẶC TRƯNG TỔNG HỢP CUỐI CÙNG (19 cột, 15 dòng)
├── cell_images/                     # 15 ảnh PNG 224x224 px, tên file = {h3_index}.png
│   ├── 874143693ffffff.png          # Ô Resolution 7
│   ├── 8841436903fffff.png          # Ô Resolution 8
│   ├── 8841436907fffff.png
│   └── ... (12 ảnh res 8 khác)
├── cell_images_contact_sheet.png    # Ảnh ghép toàn bộ 15 ô để kiểm tra trực quan
├── weather.parquet                  # ⭐ DỮ LIỆU THỜI TIẾT 6H ĐỦ 7 NĂM 2019-2025 (153.420 dòng)
└── weather_qa.json                  # QA log kiểm tra độ toàn vẹn thời tiết
```

---

## 2. `cells_b3.parquet` — 19 cột, 15 dòng

### Toàn bộ tên cột (đúng thứ tự và chuẩn schema mục 5 docs/context.md)

```text
h3_index, resolution, centroid_lat, centroid_lon, district, ward,
n_intersections, road_length_primary, road_length_secondary,
road_length_residential, n_traffic_signals, n_crossings, has_major_road,
population, population_density, n_schools, n_hospitals, n_commercial_poi,
image_path
```

### Dòng thật Resolution 7 (ô lớn bao quát toàn phường)

| h3_index | resolution | centroid_lat | centroid_lon | district | ward | n_intersections | road_length_primary | road_length_secondary | road_length_residential | n_traffic_signals | n_crossings | has_major_road | population | population_density | n_schools | n_hospitals | n_commercial_poi |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| `874143693ffffff` | 7 | 21.044021 | 105.740086 | *(trống)* | Xuân Phương | 142 | 3885.43 | 5423.11 | 32135.67 | 11 | 69 | True | 45005.18 | 7960.44 | 11 | 1 | 11 |

### 2 dòng thật tiêu biểu Resolution 8 (ô nhỏ độ phân giải cao)

| h3_index | resolution | centroid_lat | centroid_lon | district | ward | n_intersections | road_length_primary | road_length_secondary | road_length_residential | n_traffic_signals | n_crossings | has_major_road | population | population_density | n_schools | n_hospitals | n_commercial_poi |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| `8841436903fffff` | 8 | 21.027972 | 105.747687 | *(trống)* | Xuân Phương | 16 | 0.0 | 0.0 | 10884.23 | 0 | 105 | False | 1600.85 | 1981.89 | 4 | 0 | 0 |
| `8841436907fffff` | 8 | 21.034822 | 105.753164 | *(trống)* | Xuân Phương | 29 | 0.0 | 3505.13 | 7520.66 | 0 | 1 | True | 4200.11 | 5200.43 | 0 | 1 | 3 |

---

## 3. `weather.parquet` — Thời tiết 6 giờ đủ 7 năm (2019–2025)

* **Số lượng dòng:** 15 ô × 10.228 khung giờ = **153.420 dòng** (100% đầy đủ, không thiếu 1 khung giờ nào).
* **Khoảng thời gian:** `2019-01-01T00:00:00+07:00` đến `2025-12-31T18:00:00+07:00`.
* **Schema:** 7 cột chuẩn: `h3_index`, `time_bin`, `temp_mean`, `precipitation_sum`, `visibility_min`, `wind_speed_max`, `humidity_mean`.

### 3 dòng dữ liệu thật đầu tiên của ô `874143693ffffff`

| h3_index | time_bin | temp_mean (°C) | precipitation_sum (mm) | visibility_min | wind_speed_max (m/s) | humidity_mean (%) |
|---|---|---|---|---|---|---|
| `874143693ffffff` | 2019-01-01T00:00:00+07:00 | 9.88 | 0.0 | *(null)* | 3.98 | 60.0 |
| `874143693ffffff` | 2019-01-01T06:00:00+07:00 | 10.33 | 0.0 | *(null)* | 4.43 | 66.5 |
| `874143693ffffff` | 2019-01-01T12:00:00+07:00 | 12.23 | 0.0 | *(null)* | 3.61 | 60.83 |

> **Lưu ý về `visibility_min`:** Giá trị để `null` chuẩn xác theo dữ liệu tái phân tích ERA5 / Open-Meteo do biến tầm nhìn bề mặt không có trong mô hình reanalysis. Không tự ý điền số ảo hay nội suy giả.

---

## 4. Ảnh bản đồ — Direct Vector Rendering (Không dùng Tile mạng)

Toàn bộ 15 ô H3 đều được render trực tiếp từ file vector `maps/xuan_phuong.osm.pbf` qua thư viện `matplotlib` và `shapely`:
* Kích thước cố định: $224 \times 224\text{ px}$, hệ màu RGB chuẩn.
* Nền xám nhạt (`#edf1f4`), sông hồ xanh lam (`#9ecae1`), nhà xám (`#bdbdbd`).
* Mạng lưới đường phân cấp màu:
  * Primary / ĐT70: Màu vàng cam (`#fdae61`).
  * Secondary: Màu vàng nhạt (`#fee08b`).
  * Residential / Đường nội bộ: Màu trắng (`#ffffff`).
* **Không chứa bất kỳ text/nhãn chữ nào trên ảnh** (đáp ứng tiêu chí nạp vào mô hình thị giác Visual Attention Network).

File `cell_images_contact_sheet.png` nằm tại `data/processed/pilots/xuan_phuong/cell_images_contact_sheet.png` hiển thị lưới ghép của toàn bộ 15 ô.

---

## 5. Bảng số liệu tổng hợp đối chiếu — Phường Xuân Phương

| Chỉ số kiểm tra | Giá trị Xuân Phương | Ghi chú kỹ thuật |
|---|---|---|
| **Mã đơn vị hành chính (`ward_id`)** | `00622` | Trích xuất từ `maps/hanoi_wards_2025.geojson` |
| **Số ô Resolution 7** | 1 ô | Phường diện tích nhỏ nằm trọn trong 1 ô res 7 |
| **Số ô Resolution 8** | 14 ô | Phủ kín ranh giới phường và vùng đệm |
| **Tổng số ô H3 (`cells_b3.parquet`)** | 15 ô | 100% có ảnh $224 \times 224\text{ px}$ |
| **Tổng số điểm giao cắt (`n_intersections`)** | 414 giao lộ | Tổng trên các ô (có tính lặp giữa res 7 & 8) |
| **Số ô có đường lớn (`has_major_road = True`)** | 13 / 15 ô | ĐT70 và các trục liên phường |
| **Khoảng dân số (`population`)** | 143.07 — 45.005.18 người | Res 8 nhỏ nhất 143 người, Res 7 toàn phường ~45.005 người |
| **Tổng số dòng thời tiết (`weather.parquet`)** | 153.420 dòng | Đủ 100% 10.228 khung 6h/ô (2019–2025) |
| **Kiểm tra cắt OSM (`ways_with_missing_node_coordinates`)** | **0** | Đạt chuẩn `--strategy=complete_ways` |

---

## 6. Trích lục các file QA JSON tự động

### `cells_b4_qa.json`
```json
{
  "source_pbf": "maps\\xuan_phuong.osm.pbf",
  "length_crs": "EPSG:32648 (UTM zone 48N)",
  "h3_cells": 15,
  "eligible_osm_highway_ways": 1623,
  "ways_with_missing_node_coordinates": 0,
  "total_intersections": 414,
  "total_traffic_signals": 20,
  "total_crossings": 278
}
```

### `cells_b5_qa.json`
```json
{
  "population_raster": "data\\raw\\worldpop\\vnm_ppp_2020_100m.tif",
  "population_raster_crs": "EPSG:4326",
  "h3_cells": 15,
  "total_population_across_cells": 108031.635,
  "note_on_total": "H3 resolutions 7 and 8 overlap in this pilot, so this sum is not a physical ward total.",
  "poi_source_pbf": "maps\\xuan_phuong.osm.pbf",
  "poi_node_records": 29,
  "poi_way_records": 16,
  "poi_ways_without_coordinates": 0
}
```

### `weather_qa.json`
```json
{
  "output_file": "data\\processed\\pilots\\xuan_phuong\\weather.parquet",
  "total_rows": 153420,
  "unique_cells": 15,
  "bins_per_cell": 10228,
  "date_range": ["2019-01-01", "2025-12-31"],
  "visibility_min_status": "present_as_null_in_reanalysis",
  "temp_mean_range": [7.83, 38.87],
  "precipitation_sum_total": 233395.7
}
```
