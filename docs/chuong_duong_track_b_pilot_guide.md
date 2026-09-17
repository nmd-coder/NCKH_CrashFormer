# Track B — Làm theo từng bước (mẫu: xã Chương Dương)

> **Đọc trước khi bắt đầu:** tài liệu này viết cho người **chưa từng làm bước
> nào của Track B**. Mỗi bước đều ghi rõ 3 câu hỏi:
> - **Input lấy ở đâu?** — tải file gì, từ link nào, đặt vào đâu.
> - **Làm như thế nào?** — lệnh gõ chính xác, hoặc click chuột ở đâu trong QGIS.
> - **Output là gì?** — file nào sẽ xuất hiện, bên trong có gì, làm sao biết
>   mình vừa làm đúng chứ không phải làm sai mà không biết.
>
> Bài mẫu dùng xã **Chương Dương** (`ward_id = 10237`). Khi làm xã khác, chỉ
> đổi tên xã và `ward_id`, **giữ nguyên mọi bước còn lại**.
>
> Thư mục gốc của cả dự án luôn là `D:\NCKH`. Mọi lệnh dưới đây giả định bạn
> đang đứng ở thư mục này.

---

## Bước 0 — Cài công cụ (chỉ làm một lần duy nhất)

### 0.1. Cài QGIS

**Input:** trang tải chính thức <https://qgis.org/download/>.
**Làm:** tải bản Windows 64-bit, cài như phần mềm bình thường (Next → Next → Install).
**Output:** một ứng dụng tên **QGIS Desktop** xuất hiện trong Start Menu.
**Kiểm tra:** mở được QGIS, thấy màn hình bản đồ trống là được.

QGIS dùng để **xem** và **chọn ranh giới**. Không dùng QGIS để sửa tay dữ liệu.

### 0.2. Cài Anaconda + Osmium

**Input:** trang tải chính thức <https://www.anaconda.com/download/>.
**Làm:**
1. Cài Anaconda, khi hỏi chọn **Just Me**.
2. Mở **Anaconda Prompt** (tìm trong Start Menu, không dùng CMD thường).
3. Gõ lần lượt:

```cmd
conda create -n osmium -c conda-forge osmium-tool --solver=libmamba -y
conda activate osmium
osmium --version
```

**Output:** dòng lệnh in ra số phiên bản Osmium (ví dụ `osmium 1.19.1`).
**Kiểm tra:** nếu thấy số phiên bản là xong. Nếu báo lỗi "conda không tìm thấy", đóng Anaconda Prompt mở lại từ Start Menu (không dùng cửa sổ CMD cũ).

> Từ giờ, mỗi lần cần cắt file PBF, mở Anaconda Prompt rồi gõ:
> ```cmd
> conda activate osmium
> cd /d D:\NCKH
> ```
> Chỉ gõ đúng 2 dòng này, **không gõ theo phần hiển thị** kiểu `(osmium) D:\NCKH>` — đó là do máy tự in ra, không phải lệnh của bạn.

### 0.3. Cài các thư viện Python cần dùng

**Làm:** mở Anaconda Prompt, gõ:

```cmd
conda activate base
cd /d D:\NCKH
pip install h3 shapely pandas pyarrow netCDF4 pyproj rasterio matplotlib Pillow xarray
```

**Kiểm tra:** không có dòng nào báo `ERROR` màu đỏ ở cuối là được.

---

## Bước 1 — Lấy ranh giới toàn Hà Nội

Mục đích: có 1 file vẽ đúng đường viền thành phố Hà Nội, dùng làm "khuôn" để cắt dữ liệu OSM ở bước sau.

**Input:** file GADM cấp tỉnh/thành của Việt Nam, tải tại:
<https://geodata.ucdavis.edu/gadm/gadm4.1/json/gadm41_VNM_1.json.zip>

**Làm:**
1. Giải nén, copy file `gadm41_VNM_1.json` vào `D:\NCKH\maps\`.
2. Mở QGIS → `Layer` → `Add Layer` → `Add Vector Layer` → chọn file vừa copy.
3. Chuột phải vào layer trong bảng bên trái → `Open Attribute Table`.
4. Trong bảng, bấm nút **Select by Expression**, gõ đúng:
   ```sql
   "GID_1" = 'VNM.27_1'
   ```
   rồi bấm `Select Features`. Đây là mã số riêng của Hà Nội trong bộ GADM.
5. Đóng bảng thuộc tính. Chuột phải layer → `Export` → `Save Selected Features As...`
6. Trong hộp thoại hiện ra, điền đúng:
   - Format: `GeoJSON`
   - File name: `D:\NCKH\maps\hanoi_boundary.geojson`
   - CRS: `EPSG:4326 – WGS 84`
   - Tick chọn **Save only selected features** nếu có ô này.
7. Bấm OK.

**Output:** file `maps\hanoi_boundary.geojson` — chỉ vẽ đúng 1 vùng, là thành phố Hà Nội (cả nội thành lẫn ngoại thành).

**Kiểm tra:** kéo file vừa tạo vào QGIS, chỉ thấy đúng 1 hình dạng Hà Nội hiện ra, không thấy tỉnh nào khác.

---

## Bước 2 — Cắt dữ liệu OSM Việt Nam thành OSM Hà Nội

Mục đích: dữ liệu OSM toàn Việt Nam quá nặng (~300MB+), cắt riêng phần Hà Nội để làm việc cho nhẹ và nhanh.

**Input:** file bản đồ OSM Việt Nam, tải tại
<https://download.geofabrik.de/asia/vietnam.html> (chọn file `.osm.pbf`).

**Làm:**
1. Tải xong, copy vào `D:\NCKH\maps\`, đổi tên theo ngày tải, ví dụ `vietnam-260915.osm.pbf`.
2. **Không mở file này bằng Excel/Notepad/QGIS** — file quá lớn, mở trực tiếp sẽ treo máy. Chỉ dùng Osmium để cắt.
3. Mở Anaconda Prompt:

```cmd
conda activate osmium
cd /d D:\NCKH
osmium extract --strategy=complete_ways -p maps\hanoi_boundary.geojson maps\vietnam-260915.osm.pbf -o maps\hanoi.osm.pbf
osmium fileinfo -e maps\hanoi.osm.pbf
osmium check-refs maps\hanoi.osm.pbf
```

**Output:** file `maps\hanoi.osm.pbf` — nhỏ hơn nhiều so với file gốc (mẫu của nhóm là khoảng 21.8 MB).

**Kiểm tra:** dòng cuối cùng của lệnh `check-refs` phải hiện đúng:
```
Nodes in ways missing: 0
```
Nếu số khác 0, nghĩa là cắt thiếu — báo lại nhóm trước khi dùng tiếp.

---

## Bước 3 — Lấy ranh giới 126 xã/phường mới (địa giới 2025)

Mục đích: từ 01/07/2025 Hà Nội đổi sang 126 xã/phường mới, không còn cấp quận/huyện. Cần bộ ranh giới mới này để tách riêng từng xã/phường.

**Input:** file JSON công khai tại
<https://raw.githubusercontent.com/lamngockhuong/vietnam-3d-map/main/public/wards/01.json>

**Làm:**
1. Tải về, lưu đúng tên `D:\NCKH\maps\01.json`.
2. File này **không phải GeoJSON chuẩn** (cấu trúc riêng: `provinceId`, `wards[]`, mỗi ward có `id`, `name`, `polygons[]`...), nên **không mở bằng QGIS**. Phải chạy script chuyển đổi:

```cmd
conda activate base
cd /d D:\NCKH
python convert_hanoi_wards_2025.py
```

**Output:** file `maps\hanoi_wards_2025.geojson` — đúng 126 xã/phường, mỗi xã/phường có các thông tin: `ward_id`, `ward` (tên), `unit_type` (Xã hay Phường), diện tích, dân số.

**Kiểm tra:**
1. Script tự kiểm tra khi chạy — nếu không đủ 126 đơn vị hoặc thiếu tên `Từ Liêm`/`Xuân Phương`, script sẽ báo lỗi ngay, không tạo ra file sai.
2. Mở file trong QGIS, đếm trong Attribute Table phải đúng 126 dòng.

**Lưu ý quan trọng:** đây là dữ liệu từ nguồn công khai trên GitHub, **chưa phải bản chính thức**. Trước khi dùng để báo cáo kết quả cuối cùng, phải đối chiếu bằng mắt với bản đồ chính thức trên ứng dụng iHanoi. Cho đến khi đối chiếu xong, gọi đây là "candidate boundary" (ranh giới tạm), chưa phải "chính thức".

---

## Bước 4 — Tách ra polygon của một xã (ví dụ Chương Dương)

**Input:** file `maps\hanoi_wards_2025.geojson` vừa tạo ở Bước 3.

**Làm (cách dễ nhất — dùng QGIS, không cần biết tiếng Việt có dấu trong dòng lệnh):**
1. Mở `maps\hanoi_wards_2025.geojson` trong QGIS.
2. Chuột phải layer → `Open Attribute Table`.
3. Bấm **Select by Expression**, gõ:
   ```sql
   "ward" = 'Chương Dương'
   ```
4. Kiểm tra chỉ có **đúng 1 dòng** được chọn (bôi vàng), và `ward_id` phải là `10237`.
5. Chuột phải layer → `Export` → `Save Selected Features As...`
6. Điền:
   - Format: `GeoJSON`
   - File name: `D:\NCKH\maps\chuong_duong_boundary.geojson`
   - CRS: `EPSG:4326 – WGS 84`
7. Bấm OK.

**Output:** file `maps\chuong_duong_boundary.geojson` — chỉ có đúng 1 polygon, là xã Chương Dương.

**Kiểm tra:** mở file này trong QGIS (cửa sổ mới hoặc thêm layer mới), chỉ thấy đúng 1 vùng nhỏ, đúng hình dạng xã Chương Dương.

> Làm xã khác thì lặp lại y hệt bước này, chỉ đổi `'Chương Dương'` thành tên xã của bạn và đổi tên file xuất ra.

---

## Bước 5 — Cắt OSM riêng cho xã Chương Dương

**Input:** file `maps\hanoi.osm.pbf` (Bước 2) + file `maps\chuong_duong_boundary.geojson` (Bước 4).

**Làm:** mở Anaconda Prompt:

```cmd
conda activate osmium
cd /d D:\NCKH
osmium extract --strategy=complete_ways -p maps\chuong_duong_boundary.geojson maps\hanoi.osm.pbf -o maps\chuong_duong.osm.pbf
osmium check-refs maps\chuong_duong.osm.pbf
```

**Output:** file `maps\chuong_duong.osm.pbf` — chỉ chứa đường/nhà/sông trong phạm vi xã Chương Dương (mẫu của nhóm ~152 KB, rất nhỏ so với file Hà Nội).

**Kiểm tra:** dòng cuối `check-refs` phải là `Nodes in ways missing: 0`.

**⚠️ Luôn cắt từ `hanoi.osm.pbf`** (Bước 2), không cắt từ file PBF của một xã khác.

---

## Bước 6 — Sinh lưới H3 (chia xã thành các ô lục giác)

Mục đích: mô hình không dự đoán theo xã/phường, mà theo từng **ô lục giác H3** nhỏ hơn. Bước này chia polygon xã thành các ô đó.

**Input:** file `maps\chuong_duong_boundary.geojson` (Bước 4) — **không cần** file PBF.

**Làm:**

```cmd
conda activate base
cd /d D:\NCKH
python build_h3_grid.py --boundary maps\chuong_duong_boundary.geojson --ward "Chương Dương" --output data\processed\pilots\chuong_duong\cells.parquet --geometry-output data\processed\pilots\chuong_duong\cells_geometry.geojson
```

**Output:** 2 file:
- `cells.parquet` — bảng danh sách ô, mỗi dòng 1 ô, có cột `h3_index` (mã ô), `resolution` (7 hoặc 8), `centroid_lat`/`centroid_lon` (tọa độ tâm ô), `district` (để trống vì địa giới mới không còn cấp quận/huyện), `ward` (tên xã). Mẫu Chương Dương ra 41 dòng: 6 ô resolution 7 + 35 ô resolution 8.
- `cells_geometry.geojson` — vẽ hình các ô lục giác, chỉ để mở trong QGIS kiểm tra bằng mắt, không dùng để huấn luyện mô hình.

**Kiểm tra:**
1. Script tự kiểm tra: nếu `h3_index` bị trùng hoặc ra 0 ô, script sẽ báo lỗi ngay và không tạo file.
2. Mở `cells_geometry.geojson` trong QGIS cùng với `chuong_duong_boundary.geojson`: các ô lục giác phải phủ kín và nằm trong ranh giới xã.

**⚠️ Ghi nhớ:** ô resolution 7 và resolution 8 **chồng lên nhau về không gian** (7 là ô to, 8 là ô nhỏ nằm bên trong). Vì vậy **không được cộng dồn** số liệu của tất cả 41 ô lại để nói đó là tổng của cả xã — sẽ ra con số sai (đếm trùng).

---

## Bước 7 — Thời tiết (dữ liệu mẫu ERA5)

### 7.1. Tải dữ liệu thời tiết thủ công

**Input:** trang Copernicus Climate Data Store (CDS) — cần đăng ký tài khoản miễn phí.

**Làm:**
1. Vào CDS, chọn dataset **"ERA5 hourly data on single levels from 1940 to present"** (không chọn bản "time-series", không chọn "ERA5-Land").
2. Chọn các mục:
   - Product type: `Reanalysis`
   - Variable: `2m temperature`, `2m dewpoint temperature`, `10m u-component of wind`, `10m v-component of wind`, `Total precipitation`, `Total cloud cover`
   - Năm/tháng (bản mẫu): 2019, tháng 1 đến tháng 4; chọn tất cả ngày, tất cả giờ
   - Area: North `21.00`, South `20.75`, West `105.75`, East `106.00` (CDS chỉ nhận số tròn theo bội số 0.25)
   - Data format: `NetCDF4 (Experimental)`; Download format: `Unarchived`
3. Bấm tải. CDS giới hạn dung lượng mỗi lần tải — nếu muốn tải cả 2019-2025 phải chia nhỏ thành nhiều lần như trên.
4. Giải nén file ZIP tải về vào đúng thư mục:
   ```text
   D:\NCKH\data\raw\weather\era5\chuong_duong\2019_01_04\
   ```

**Output của bước tải:** 2 file `.nc` trong thư mục trên — 1 file chứa nhiệt độ/gió/mây (tên có chữ `instant`), 1 file chứa lượng mưa (tên có chữ `accum`).

### 7.2. Chuyển sang bảng dữ liệu dùng được

**Input:** 2 file `.nc` vừa tải + `cells.parquet` (Bước 6).

**Làm:**

```cmd
conda activate base
cd /d D:\NCKH
python ingest_era5_weather.py --cells data\processed\pilots\chuong_duong\cells.parquet --source-dir data\raw\weather\era5\chuong_duong\2019_01_04 --output data\processed\pilots\chuong_duong\weather_2019_01_04.parquet
```

**Output:** `weather_2019_01_04.parquet` — mỗi dòng là 1 ô H3 tại 1 khung 6 giờ, có các cột: `temp_mean` (nhiệt độ trung bình), `precipitation_sum` (tổng mưa), `wind_speed_max` (gió mạnh nhất), `humidity_mean` (độ ẩm trung bình), `visibility_min` (tầm nhìn — hiện để trống, xem lưu ý dưới). Mẫu Chương Dương ra 19.721 dòng cho 41 ô.

**Kiểm tra:** mở kèm file `weather_2019_01_04_qa.json` — ghi rõ khoảng thời gian, số dòng, và tình trạng biến `visibility`.

**⚠️ Lưu ý bắt buộc phải biết:** dữ liệu CDS đã chọn **không có biến tầm nhìn (visibility)**. Cột `visibility_min` vẫn giữ trong bảng nhưng toàn bộ để trống — **không được tự bịa số**. Đây chỉ là bản thử nghiệm pipeline, chưa đủ để huấn luyện mô hình thật. Cần tìm nguồn dữ liệu tầm nhìn khác trước khi làm chính thức.

---

## Bước 8 — Đặc trưng mạng lưới đường

**Input:** `maps\chuong_duong.osm.pbf` (Bước 5) + `cells.parquet` + `cells_geometry.geojson` (Bước 6).

**Làm:**

```cmd
conda activate base
cd /d D:\NCKH
python build_road_features.py --pbf maps\chuong_duong.osm.pbf --cells data\processed\pilots\chuong_duong\cells.parquet --cell-geometry data\processed\pilots\chuong_duong\cells_geometry.geojson --output data\processed\pilots\chuong_duong\cells_b4.parquet
```

**Output:** `cells_b4.parquet` — là `cells.parquet` cũ cộng thêm các cột:
- `n_intersections`: số điểm giao nhau giữa các đường
- `road_length_primary`, `road_length_secondary`, `road_length_residential`: tổng chiều dài đường theo từng cấp (đơn vị mét)
- `n_traffic_signals`, `n_crossings`: số đèn tín hiệu, số vạch qua đường
- `has_major_road`: ô này có đường lớn đi qua hay không

Kèm file `cells_b4_qa.json` ghi lại số liệu tổng để kiểm tra nhanh (mẫu Chương Dương: 209 điểm giao, 0 đèn tín hiệu, 0 vạch qua đường có gắn tag trong OSM).

**Kiểm tra:** giá trị `0` ở đèn tín hiệu/vạch qua đường **không có nghĩa là thực địa không có** — chỉ có nghĩa là dữ liệu OSM chưa được ai gắn tag đầy đủ. Không tự suy luận thêm.

---

## Bước 9 — Dân số và điểm quan tâm (trường học, bệnh viện...)

**Input:**
- `cells_b4.parquet` + `cells_geometry.geojson` (Bước 6, 8)
- `maps\chuong_duong.osm.pbf` (Bước 5) — để đếm POI
- Raster dân số WorldPop, tải file `vnm_ppp_2020_UNadj_constrained.tif` (tìm trên trang WorldPop), đặt vào `D:\NCKH\data\raw\population\`

**Làm:**

```cmd
conda activate base
cd /d D:\NCKH
python build_population_poi_features.py --cells data\processed\pilots\chuong_duong\cells_b4.parquet --cell-geometry data\processed\pilots\chuong_duong\cells_geometry.geojson --population-raster data\raw\population\vnm_ppp_2020_UNadj_constrained.tif --pbf maps\chuong_duong.osm.pbf --output data\processed\pilots\chuong_duong\cells_b5.parquet
```

**Output:** `cells_b5.parquet` — cộng thêm cột `population`, `population_density`, `n_schools`, `n_hospitals`, `n_commercial_poi`. Kèm `cells_b5_qa.json`.

**Kiểm tra:** script tự dừng và báo lỗi ngay nếu raster dân số không đúng hệ tọa độ WGS84 (EPSG:4326) — đây là lỗi hay gặp nhất và nguy hiểm nhất vì nếu không kiểm tra sẽ ra số liệu sai mà nhìn qua tưởng đúng. Nếu script chạy xong không báo lỗi này, nghĩa là CRS đã khớp.

---

## Bước 10 — Ảnh bản đồ cho mô hình (Image Encoder)

**Input:** `maps\chuong_duong.osm.pbf` (Bước 5) + `cells_b5.parquet` + `cells_geometry.geojson`.

**Làm:**

```cmd
conda activate base
cd /d D:\NCKH
python render_cell_images.py --pbf maps\chuong_duong.osm.pbf --cells data\processed\pilots\chuong_duong\cells_b5.parquet --cell-geometry data\processed\pilots\chuong_duong\cells_geometry.geojson --image-dir data\processed\pilots\chuong_duong\cell_images --output data\processed\pilots\chuong_duong\cells_b3.parquet --contact-sheet data\processed\pilots\chuong_duong\cell_images_contact_sheet.png
```

**Output:**
- Một ảnh PNG 224×224 cho mỗi ô, lưu trong thư mục `cell_images\`, tên file là mã `h3_index`.
- `cells_b3.parquet` — bảng cuối cùng của Track B (đủ H3 + đường + dân số/POI + đường dẫn ảnh `image_path`).
- `cell_images_contact_sheet.png` — ghép 12 ảnh đầu tiên lại thành 1 ảnh lớn, để xem nhanh không cần mở từng file.

**Kiểm tra bắt buộc — mở `cell_images_contact_sheet.png` bằng mắt, xác nhận:**
- ✅ Có đường, sông, khối nhà hiện rõ.
- ✅ **Không có bất kỳ chữ nào** trên ảnh (tên đường, tên địa danh, watermark...).
- ✅ Không thấy dòng chữ báo lỗi kiểu "API KEY REQUIRED" — nếu thấy, nghĩa là script đang gọi bản đồ từ máy chủ ngoài bị lỗi, không phải vẽ từ dữ liệu OSM cục bộ như thiết kế đúng.
- ✅ Các ô cùng resolution (7 hoặc 8) trông có độ phóng to gần giống nhau, không có ô nào bị zoom quá gần hoặc quá xa so với ô khác cùng resolution.

Ảnh này vẽ trực tiếp từ file PBF đã cắt ở Bước 5, **không gọi bất kỳ dịch vụ bản đồ nào trên mạng** — nên không cần API key, không lo bị chặn hay giới hạn khi làm hàng loạt.

---

## Tổng kết: bảng cuối cùng và việc còn lại

File kết quả cuối của Track B (phần dữ liệu không gian) là:

```text
data\processed\pilots\chuong_duong\cells_b3.parquet
```

File này gộp đủ: H3 index, đặc trưng đường, dân số/POI, đường dẫn ảnh. Thời tiết nằm ở file riêng `weather_2019_01_04.parquet` vì còn thiếu dữ liệu các năm khác.

**Việc còn lại trước khi train mô hình được (không thuộc phạm vi bài mẫu này):**
1. Tải nốt thời tiết cho cả giai đoạn 2019–2025, và quyết định cách xử lý biến `visibility` bị thiếu.
2. Ghép dữ liệu tai nạn (Track A) vào từng ô H3 và khung giờ 6 tiếng.
3. Ghép Track A + Track B + thời tiết thành 1 bảng `panel.parquet` duy nhất.
4. Sau đó mới bắt đầu code mô hình.

---

## Quy tắc khi bạn làm một xã/phường khác

- Đặt tên thư mục riêng theo xã của bạn, ví dụ `data\processed\pilots\tu_liem\` — không ghi đè thư mục `chuong_duong`.
- Luôn dùng chung file `maps\hanoi_wards_2025.geojson` và `maps\hanoi.osm.pbf` đã có sẵn — không tự vẽ ranh giới tay, không tự tải lại OSM riêng.
- Giữ lại toàn bộ: file gốc đã tải (PBF, NetCDF, TIFF), các file `*_qa.json`, và ghi lại đúng lệnh bạn đã gõ — để người khác kiểm tra lại được.
- Gặp giá trị `0` hoặc ô trống: luôn coi là "chưa chắc, cần kiểm tra dữ liệu nguồn", không tự kết luận "thực địa không có".
- Không cộng số liệu giữa các ô resolution 7 và resolution 8 để suy ra "tổng của cả xã".
- Các file PBF, ảnh render hàng loạt, raster lớn: **không commit lên Git** (đã có trong `.gitignore`). Chỉ file boundary GeoJSON nhỏ và script `.py` mới commit.
