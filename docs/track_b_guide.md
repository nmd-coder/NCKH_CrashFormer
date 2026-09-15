# Hướng dẫn Track B — Dữ liệu không gian

> **Phạm vi:** tài liệu này chỉ nói về Track B (dữ liệu không gian: OSM, lưới H3,
> ảnh bản đồ, đặc trưng đường, dân số, thời tiết). Track A (crawl tin tức, NLP,
> geocoding) xem ở `docs/context.md`.
>
> **Cách đọc:** mỗi bước ghi rõ Input (cần gì trước khi bắt đầu) và Output (ra
> file gì, cột gì) để người làm biết chính xác điểm bắt đầu và điểm kết thúc,
> và người review biết kiểm tra cái gì.
>
> Track B **độc lập hoàn toàn với Track A** — không cần chờ crawl tin tức xong
> mới bắt đầu.

---

## Sơ đồ phụ thuộc giữa các bước

```
B1 (OSM extract) ──┬──► B3 (ảnh bản đồ)
                    ├──► B4 (đặc trưng đường)
                    └──► B5 (POI: trường học/bệnh viện)

B2 (lưới H3) ───────┬──► B3, B4, B5 (đều cần lưới ô trước)
                     └──► B6 (chỉ cần tâm ô)

B5 (dân số) cần thêm raster WorldPop/GHS-POP — tải độc lập, không phụ thuộc B1/B2
```

Thứ tự làm hợp lý nếu chỉ có 1 người: **B1 → B2 → B6 → B4 → B5 → B3** (để B3
cuối vì cần B4 kiểm tra sơ dữ liệu đường trước khi mất công render ảnh hàng loạt).
Nếu có 2 người, B3/B4/B5/B6 làm song song được sau khi B1+B2 xong.

---

## B1. Tải và cắt dữ liệu OSM Hà Nội

**Input:**
- Không có (đây là điểm bắt đầu của toàn bộ Track B)

**Output:**
- File `hanoi.osm.pbf` — dữ liệu OSM đã cắt riêng phạm vi Hà Nội, dùng làm input
  cho B2 (gián tiếp), B3, B4, B5.

**Các bước:**
1. Tải `vietnam-latest.osm.pbf` từ Geofabrik (~500MB-1GB).
2. Lấy ranh giới hành chính Hà Nội (`hanoi_boundary.geojson`) — trích từ relation
   `admin_level=4` của Hà Nội trên OSM, hoặc từ GADM.
3. Cắt bằng `osmium`:
   ```bash
   osmium extract -p hanoi_boundary.geojson vietnam-latest.osm.pbf -o hanoi.osm.pbf
   ```

**Công cụ:** `osmium-tool` (CLI, cài qua conda/apt).

**⚠️ Lưu ý bắt buộc:** KHÔNG đọc toàn bộ file PBF gốc vào RAM bằng thư viện
Python (ví dụ đọc thẳng vào GeoDataFrame) — file gốc quá lớn. `osmium` xử lý
theo kiểu streaming, chạy được với RAM thấp.

**Độ khó:** Thấp. Rủi ro chính là boundary sai (thiếu ngoại thành) hoặc tải
nhầm phiên bản PBF cũ.

---

## B2. Sinh lưới H3 (resolution 7 + resolution 8)

**Input:**
- `hanoi_boundary.geojson` (ranh giới Hà Nội — có thể lấy độc lập với B1, không
  bắt buộc phải chờ cắt xong PBF)
- Ranh giới quận/huyện/phường/xã (để gán `district`/`ward`)

**Output:**
- Khung ban đầu của `cells.parquet` với các cột: `h3_index` (khóa), `resolution`,
  `centroid_lat`, `centroid_lon`, `district`, `ward`

**Các bước:**
1. Sinh lưới bằng `h3-py`:
   ```python
   import h3
   cells_r7 = h3.polygon_to_cells(hanoi_boundary, res=7)
   cells_r8 = h3.polygon_to_cells(hanoi_boundary, res=8)
   ```
2. Với mỗi ô, tính tâm bằng `h3.cell_to_latlng(h3_index)` → `centroid_lat`, `centroid_lon`.
3. Gán `district`/`ward` bằng spatial join (`geopandas.sjoin`) giữa tâm ô và
   ranh giới hành chính.

**Công cụ:** `h3-py`, `geopandas`, `shapely`.

**Độ khó:** Thấp-trung bình. Đây là bước nền cho B3, B4, B5, B6 — ưu tiên làm
sớm nhất có thể sau B1.

---

## B3. Render ảnh bản đồ 224×224/ô (đầu vào Image Encoder)

**Input:**
- `cells.parquet` từ B2 (cần danh sách ô + tọa độ)
- `hanoi.osm.pbf` từ B1 (lớp đường, sông hồ, khối nhà để vẽ)
- Khuyến nghị: chờ B4 xong trước để biết chắc dữ liệu đường đã đúng, tránh
  render hàng loạt rồi phải làm lại

**Output:**
- Thư mục ảnh `data/processed/cell_images/<h3_index>.png` (224×224px)
- Cột `image_path` được điền vào `cells.parquet`

**Ba nguyên tắc bắt buộc — sai một trong ba là hỏng input của mô hình:**
1. **Cùng mức zoom cho mọi ô cùng resolution.** Không để zoom tự động theo
   bounding box — ô ở rìa thành phố (ít điểm mốc) sẽ zoom khác ô trung tâm.
2. **Tắt toàn bộ nhãn chữ** (tên đường, tên địa danh). Nếu để lộ, mô hình học
   "đọc chữ" thay vì học cấu trúc hình học — lỗi kinh điển.
3. **Giữ lớp đường phân cấp, sông hồ, khối nhà** — đủ để mô hình học mật độ và
   hình dạng mạng lưới đường.

**Công cụ:** `contextily` (dễ, cần tìm tile provider không nhãn) hoặc
QGIS/Mapnik (kiểm soát style tốt hơn, cần thiết lập style file riêng lúc đầu).

**Độ khó:** Trung bình-cao. Không khó về thuật toán nhưng dễ sai ở style (quên
tắt nhãn, zoom không nhất quán) mà **không có lỗi nào báo ra** — chỉ phát hiện
khi nhìn ảnh output bằng mắt. Bắt buộc kiểm tra một mẫu nhỏ (~10 ảnh) trước khi
chạy hàng loạt cho toàn bộ lưới.

---

## B4. Đặc trưng đường bộ dạng số (baseline không dùng ảnh)

**Input:**
- `hanoi.osm.pbf` từ B1 (các way có tag `highway=*`, node có `traffic_signals`/`crossing`)
- `cells.parquet` từ B2 (ranh giới từng ô để cắt/đếm theo ô)

**Output:**
- Các cột trong `cells.parquet`: `n_intersections`, `road_length_primary`,
  `road_length_secondary`, `road_length_residential`, `n_traffic_signals`,
  `n_crossings`, `has_major_road`

**Các bước:**
1. Lọc way có tag `highway=*`, phân loại theo cấp (`primary`, `secondary`, `residential`...).
2. Với mỗi ô H3: clip các đường nằm trong ô, tính tổng chiều dài theo từng cấp
   (đơn vị mét, dùng CRS chiếu phẳng phù hợp Việt Nam khi tính độ dài, không
   tính trực tiếp trên tọa độ WGS84).
3. Đếm điểm giao (`n_intersections`): node có ≥3 way `highway` đi qua.
4. Đếm `n_traffic_signals`, `n_crossings` từ node có tag tương ứng.

**Công cụ:** `osmnx` (có sẵn hàm phân tích mạng lưới đường, khuyến nghị) hoặc
tự xử lý bằng `geopandas`.

**Ý nghĩa:** đây không phải đặc trưng phụ — mục đích chính là làm **baseline
không dùng ảnh**, để so sánh và chứng minh Image Encoder (B3) thực sự đóng góp
gì. Nên hoàn thành B4 sớm, song song với B3, không làm sau cho có.

**Độ khó:** Trung bình.

---

## B5. Dân số và điểm quan tâm (POI)

**Input:**
- `cells.parquet` từ B2 (ranh giới từng ô)
- Raster dân số: WorldPop 100m hoặc GHS-POP (tải riêng, **không lấy từ OSM**)
- `hanoi.osm.pbf` từ B1 (để đếm POI: `amenity=school`, `amenity=hospital`, `shop=*`)

**Output:**
- Các cột trong `cells.parquet`: `population`, `population_density`,
  `n_schools`, `n_hospitals`, `n_commercial_poi`

**Các bước:**
1. Tải raster WorldPop/GHS-POP cho khu vực Việt Nam/Hà Nội.
2. Zonal statistics: với mỗi polygon H3, tính tổng dân số trong ô bằng
   `rasterio` + `rasterstats.zonal_stats`.
3. Tính `population_density` = `population` / diện tích ô (diện tích ô H3 theo
   resolution đã biết trước, có thể lấy từ `h3.cell_area`).
4. Đếm POI bằng spatial join giữa điểm OSM (`amenity=school`, `amenity=hospital`,
   `shop=*`) và ranh giới ô.

**⚠️ Điểm dễ sai nhất của cả Track B:** CRS (hệ tọa độ) của raster dân số và
vector lưới H3 **phải khớp nhau** trước khi chạy zonal statistics. Nếu lệch
CRS, kết quả sai nhưng **không báo lỗi gì cả** — chỉ ra số liệu trông hợp lý
nhưng vô nghĩa. Luôn kiểm tra bằng code (`assert raster.crs == cells.crs`),
không chỉ nhìn qua.

**Công cụ:** `rasterio`, `rasterstats`, `geopandas`.

**Độ khó:** Trung bình-cao — rủi ro sai âm thầm (silent failure) cao nhất
trong toàn Track B.

---

## B6. Thời tiết

**Input:**
- `cells.parquet` từ B2 (chỉ cần `centroid_lat`/`centroid_lon` — không cần B1)

**Output:**
- `weather.parquet`, khóa `(h3_index, time_bin)`, các cột: `temp_mean`,
  `precipitation_sum`, `visibility_min`, `wind_speed_max`, `humidity_mean`

**Các bước:**
1. Với mỗi ô (hoặc gộp theo cụm ô gần nhau để giảm số lần gọi API), gọi
   Open-Meteo Historical API theo `centroid_lat`/`centroid_lon`, lấy dữ liệu
   theo giờ, phạm vi thời gian 2019-2025 (khớp mục 4 `context.md`).
2. Gộp về khung 6 giờ theo đúng quy tắc đã chốt:
   - Mưa (`precipitation_sum`): lấy **tổng**
   - Tầm nhìn (`visibility_min`): lấy **min** (điều kiện xấu nhất mới gây tai nạn)
   - Nhiệt độ (`temp_mean`): lấy **trung bình**
   - Gió, độ ẩm: theo quy ước tương tự nhiệt độ (trung bình), trừ khi có lý do khác

**Công cụ:** `requests` (API miễn phí, không cần key), `pandas` (resample theo
khung 6h).

**Độ khó:** Thấp. Đây là bước dễ nhất, ít phụ thuộc nhất — làm được ngay sau
B2, không cần chờ B1 xong hay bất kỳ xử lý OSM nào.

---

## Bảng tổng hợp nhanh

| Bước | Input chính | Output chính | Phụ thuộc | Độ khó |
|---|---|---|---|---|
| B1 | — | `hanoi.osm.pbf` | Không | Thấp |
| B2 | Ranh giới Hà Nội | `cells.parquet` (khung ô + tọa độ) | Có thể song song B1 | Thấp-TB |
| B3 | B1 + B2 | Ảnh PNG 224×224 + cột `image_path` | B1, B2 (nên chờ B4) | TB-Cao |
| B4 | B1 + B2 | Cột đặc trưng đường trong `cells.parquet` | B1, B2 | Trung bình |
| B5 | B2 + raster ngoài + B1 (POI) | Cột dân số + POI trong `cells.parquet` | B1, B2 | TB-Cao |
| B6 | B2 | `weather.parquet` | Chỉ B2 | Thấp |

## Định nghĩa hoàn thành Track B

Theo tiêu chí ở `docs/context.md` mục 7:
- Ô H3 có ảnh bản đồ và dân số: **100%**
- Thời tiết không lỗ hổng: **100%**
- Toàn bộ cột của `cells.parquet` và `weather.parquet` khớp đúng schema mục 5
  của `docs/context.md` — không tự ý đổi tên cột/kiểu dữ liệu.
