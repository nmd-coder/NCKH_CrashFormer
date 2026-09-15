# Bối cảnh đề tài — file bàn giao

> **Cách dùng:** mở Claude Code (hoặc một cuộc trò chuyện mới) tại thư mục gốc
> của repo, rồi bắt đầu bằng câu: *"Đọc `docs/context.md` để nắm bối cảnh đề tài,
> sau đó [việc cần làm]."*
>
> **File này là tài liệu sống.** Mỗi khi nhóm chốt một quyết định mới hoặc phát
> hiện một vấn đề về dữ liệu, cập nhật vào đây ngay. Cả 4 thành viên dùng chung.
>
> Cập nhật lần cuối: tuần 2, sau khi chạy thử pilot lần một.

---

## 1. Thông tin đề tài

Nghiên cứu Khoa học Sinh viên, Khoa Công nghệ thông tin, Đại học Công nghiệp Hà Nội.
Giảng viên hướng dẫn: TS. Trần Hùng Cường. Nhóm 4 thành viên, thời lượng 16 tuần.
Chủ nhiệm: Trần Đức Huy (MSV 2023602954, lớp 2023KHMT01).

**Tên đề tài:** Nghiên cứu và xây dựng mô hình dự đoán nguy cơ tai nạn giao thông
đa phương thức cho địa bàn thành phố Hà Nội.

**Kiến trúc tham khảo:** CrashFormer (Karimi Monsefi et al., UrbanAI/SIGSPATIAL
2023, arXiv:2402.05151). Mô hình đa phương thức dự đoán nguy cơ tai nạn theo ô
lục giác và khung 6 giờ, gồm 5 thành phần: Historical Event Encoder (FEDFormer),
Image Encoder (VAN, ảnh bản đồ OSM), Data Encoder (nhân khẩu học), Feature Fusion,
Classifier nhị phân.

**Điểm khác biệt — đây mới là đóng góp chính, không phải mô hình:**
Việt Nam không có dataset tai nạn công khai có cấu trúc như Mỹ. Nhóm tự xây bộ dữ
liệu tai nạn Hà Nội bằng cách trích xuất từ tin tức trực tuyến tiếng Việt
(NLP/Information Extraction), và điều chỉnh mô hình cho giao thông hỗn hợp mật độ
cao, xe máy chiếm ưu thế — khác hẳn giao thông ô tô hóa ở Mỹ.

Hệ quả thực tế: **Giai đoạn 1 (xây dựng dữ liệu) quan trọng hơn giai đoạn huấn
luyện mô hình.** Dữ liệu tốt thì giai đoạn 3 chỉ là chạy code. Dữ liệu tệ thì
không kiến trúc nào cứu được.

---

## 2. Bốn quyết định thiết kế đã chốt

**1. Không gian — lưới H3.**
Resolution 7 (~5,16 km², khớp bài gốc) để so sánh công bằng. Chạy song song
resolution 8 (~0,74 km²) cho nội thành để sản phẩm dùng được. Báo cáo cả hai như
một phân tích độ nhạy theo độ phân giải trong đô thị châu Á mật độ cao.

*Lý do:* Hà Nội ~3.359 km², ở res 7 chỉ ra ~650 ô, nội thành chỉ ~60 ô — quá thô
để làm bản đồ nhiệt có ý nghĩa.

**2. Thời gian — 4 khung 6 giờ/ngày** (0–6, 6–12, 12–18, 18–24).
Có bảng ánh xạ cụm từ mơ hồ tiếng Việt ("rạng sáng", "chiều tối") sang khung giờ,
lưu ở `configs/time_mapping.yaml`. Mỗi bản ghi kèm cờ `time_confidence` nhận một
trong ba giá trị: `exact` / `approximate` / `date_only`.

**3. Nhãn và mẫu âm — điểm yếu học thuật lớn nhất, phải xử lý trung thực.**
Tin tức chỉ cho mẫu dương. Ô không có tin ≠ không có tai nạn.

- Bài toán phải phát biểu là: *dự đoán nguy cơ tai nạn **nghiêm trọng, được
  truyền thông ghi nhận***. Câu này bắt buộc xuất hiện trong phần giới hạn của
  báo cáo.
- Mất cân bằng lớp cực nặng (~0,1% dương). Xử lý: chỉ giữ ô có đường cấp
  `primary` trở lên; focal loss hoặc trọng số lớp; **chỉ báo cáo PR-AUC và F1,
  tuyệt đối không báo cáo accuracy** (mô hình luôn trả "không" cũng đạt 99,9%).

**4. Phạm vi dữ liệu — 2019 đến 2025.**
Có cờ `is_covid_period` cho 2020–2021 làm biến điều khiển, vì lưu lượng giao
thông giai đoạn giãn cách bất thường.

---

## 3. Kết quả chạy thử pilot lần một — ĐỌC KỸ PHẦN NÀY

Chạy thử 50 bài trên `baogiaothong.vn` phát hiện **hai vấn đề đã làm thay đổi
chiến lược thu thập**.

### Vấn đề 1 — Đa số bài là tai nạn ở tỉnh khác

`baogiaothong.vn` là báo toàn quốc. Tin tai nạn Hà Nội chỉ chiếm ước tính 5–8%.
Lọc bằng slug URL không cứu được, vì URL bài tai nạn Hà Nội thường không chứa
`ha-noi` mà chứa tên đường hoặc tên quận.

### Vấn đề 2 — Bài không liên quan lọt qua bộ lọc

Bộ lọc slug ban đầu để các từ khóa quá rộng (`giao-thong`, `xe-may`, `o-to`).
Với một báo chuyên ngành giao thông thì gần như mọi URL đều chứa những từ đó.
Ví dụ bài lọt qua: *"Báo Giao thông chia sẻ với những số phận không may mắn"* —
bài từ thiện, slug chứa `giao-thong`.

### Thay đổi 1 — Đổi nguồn chính sang báo Hà Nội

Nguyên tắc mới: **lấy báo Hà Nội rồi lọc ra tin tai nạn**, thay vì lấy báo toàn
quốc rồi lọc ra Hà Nội. Tỷ lệ trúng chênh nhau khoảng 10 lần.

| Nguồn chính (mặc định là Hà Nội) | Ghi chú |
|---|---|
| `anninhthudo.vn` | Báo Công an Hà Nội, tin tai nạn dày, vị trí chi tiết |
| `congan.hanoi.gov.vn` | Nguồn cơ quan chức năng, chính xác nhất |
| `hanoimoi.vn` | Báo Đảng bộ Hà Nội |
| `kinhtedothi.vn` | Báo của UBND TP Hà Nội |
| `laodongthudo.vn` | Có chuyên mục giao thông |
| `vovgiaothong.vn` | Chuyên giao thông đô thị |

`baogiaothong.vn`, VnExpress, Dân trí, Tuổi Trẻ, Thanh Niên, VietnamNet chuyển
xuống **nguồn phụ** — vẫn crawl nhưng bắt buộc qua bộ lọc địa lý. Chúng bổ sung
những vụ lớn mà báo địa phương bỏ sót.

### Thay đổi 2 — Lọc hai tầng

Lọc slug chỉ làm nhiệm vụ thu hẹp rẻ tiền, không phải nhiệm vụ quyết định.

- **Tầng 1 (slug, trước khi tải):** chỉ giữ từ khóa đặc trưng tai nạn
  (`tai-nan`, `va-cham`, `tong-`, `lat-xe`, `dam-xe`). Bỏ hết từ chung chung.
  Thêm danh sách loại trừ (`trao-qua`, `hoi-nghi`, `ra-quan`, `phat-dong`).
- **Tầng 2 (nội dung, sau khi tải):** kiểm tra có động từ va chạm không, có
  phương tiện không, và **giải quyết địa lý** bằng từ điển địa danh.

Cả hai tầng đã cài đặt trong `filters.py`, hàm `slug_passes()` và
`classify_article()`.

### Bẫy quan trọng của bộ lọc địa lý

Rất nhiều bài tai nạn ở tỉnh khác có nhắc "Hà Nội" vì **nạn nhân được chuyển lên
bệnh viện ở Hà Nội** (Việt Đức, Bạch Mai, 108...). Nếu chỉ tìm chuỗi "Hà Nội" sẽ
nhận nhầm hàng loạt.

Cách xử lý đã cài trong `resolve_location()`: chấm điểm dựa trên tên quận/huyện
và tên đường Hà Nội xuất hiện trong **400 ký tự đầu** bài (tin tiếng Việt gần như
luôn nêu địa điểm ngay câu đầu), đồng thời phạt nếu xuất hiện tên tỉnh khác ở vị
trí đó, và nhận diện riêng ngữ cảnh "chuyển lên Hà Nội cấp cứu".

### Việc chưa làm — ưu tiên cao

Chạy thử lần hai: 50 bài từ `anninhthudo.vn` và 50 bài từ `baogiaothong.vn`,
đo tỷ lệ giữ lại *r* cho từng nguồn, rồi mới quyết định phân bổ công sức crawl.

Công thức tính sản lượng: để có 2.000 vụ Hà Nội cần tải khoảng `2000 / r` bài,
nhân thêm ~1,4 lần vì khử trùng lặp sẽ gộp bớt.
Kỳ vọng: `anninhthudo.vn` r ≈ 40–60%; `baogiaothong.vn` r ≈ 5–8%.

Danh sách `HANOI_LANDMARKS` trong `filters.py` hiện chỉ có ~60 mục, chắc chắn
thiếu. Khi vai trò 4 xây từ điển chuẩn hóa tên đường từ dữ liệu OSM của vai trò
3, thay danh sách cứng này bằng danh sách sinh tự động từ OSM.

---

## 4. Pipeline giai đoạn 1 — hai nhánh song song

### Nhánh A — NLP trích xuất tin tức

**A1. Crawl.** Lấy URL qua sitemap XML (dò tự động từ `robots.txt`), bổ sung bằng
phân trang chuyên mục và tìm kiếm nội bộ khi cần dữ liệu lịch sử. Lưu HTML gốc
vào `data/raw/news/`. Tôn trọng `robots.txt`, giới hạn 1–2 request/giây,
`User-Agent` tự giới thiệu là crawler nghiên cứu kèm email liên hệ.

**A2. Bóc tách và lọc.** Dùng `trafilatura` lấy thân bài → lọc hai tầng bằng
`filters.py` → khử trùng lặp bằng SimHash/MinHash (`datasketch`) kết hợp khớp
(ngày, địa danh), gộp thành `incident_id` duy nhất.

> Khử trùng lặp là bắt buộc. Một vụ lớn có thể lên 8 báo. Bỏ qua bước này thì mô
> hình học theo mức độ quan tâm của báo chí thay vì rủi ro thực tế.

Các bài bị loại **phải lưu lại kèm lý do loại** — chúng là mẫu âm để huấn luyện
bộ phân loại PhoBERT, và để kiểm tra bộ lọc có loại nhầm không.

**A3. Trích xuất thông tin.** Các trường: thời gian, địa điểm, loại đường,
`vehicles_involved`, `fatalities`, `injuries`, thời tiết, nguyên nhân.

`vehicles_involved` phân loại: `motorcycle` / `car` / `truck` / `container` /
`bus` / `coach` / `bicycle` / `pedestrian` / `other`. Đây chính là chỗ thể hiện
đặc trưng giao thông hỗn hợp Việt Nam.

Chiến lược: LLM gán nhãn sơ bộ toàn corpus (prompt trả JSON schema cố định,
thiếu thì `null`, **cấm suy đoán**) + fine-tune PhoBERT+CRF trên tập vàng.
Lưu ý: PhoBERT yêu cầu input đã tách từ bằng VnCoreNLP hoặc underthesea, nếu
không kết quả rất tệ mà không có lỗi báo ra. So sánh hai phương án theo từng
trường, bảng so sánh đi thẳng vào báo cáo.

**A4. Geocoding tiếng Việt** — phần khó nhất. Ba dạng mô tả vị trí:

- *Địa chỉ điểm* ("số 234 Nguyễn Trãi") → Nominatim hoặc Goong Maps API
  (Goong tốt hơn cho địa chỉ Việt Nam).
- *Nút giao* ("ngã tư Lê Văn Lương – Khuất Duy Tiến") → **không geocoder nào xử
  lý tốt, phải tự xây**: lấy 2 `LineString` tên đường từ OSM, tính giao điểm bằng
  Shapely. Đây là đóng góp kỹ thuật rõ ràng nhất, đáng một mục riêng trong báo cáo.
- *Đoạn/mốc* ("km 8 đại lộ Thăng Long", "chân cầu Vĩnh Tuy") → nội suy theo chiều
  dài LineString hoặc khớp POI.

Mỗi kết quả gắn `geo_confidence` (bán kính sai số, mét). Ngưỡng loại bỏ: > 300 m
khi làm ở res 8. Cần từ điển chuẩn hóa tên đường Hà Nội. Cache kết quả vào
`data/cache/geocode.sqlite`.

### Nhánh B — Dữ liệu không gian (độc lập hoàn toàn với nhánh A)

**B1.** Tải `vietnam-latest.osm.pbf` từ Geofabrik, cắt Hà Nội bằng `osmium extract`.
Đừng đọc toàn bộ PBF vào RAM.

**B2.** Sinh lưới H3 res 7 và res 8 bằng `h3-py` + `geopandas`.

**B3. Render ảnh bản đồ** 224×224 mỗi ô (đầu vào chuẩn của VAN). Ba nguyên tắc:
cùng zoom cho mọi ô cùng resolution; **tắt toàn bộ nhãn chữ** (nếu để tên đường,
mô hình học đọc chữ thay vì học cấu trúc hình học — lỗi kinh điển); giữ lớp đường
phân cấp, sông hồ, khối nhà. Dùng `contextily` tile không nhãn hoặc QGIS/Mapnik.

**B4. Đặc trưng đường bộ dạng số** (không có trong bài gốc, thêm vào để làm
baseline không dùng ảnh, chứng minh Image Encoder đóng góp gì): số nút giao,
chiều dài đường theo cấp `highway`, mật độ đèn tín hiệu, số `crossing`, số làn.

**B5. Dân số.** KHÔNG dùng OSM (quá thưa). Dùng WorldPop raster 100 m hoặc
GHS-POP, zonal statistics sang H3 bằng `rasterio`. Chú ý CRS của raster và vector
phải khớp, nếu không kết quả sai lặng lẽ không báo lỗi. Thêm số trường học, bệnh
viện, POI thương mại làm biến đại diện cho lưu lượng phát sinh.

**B6. Thời tiết.** Open-Meteo Historical API (miễn phí, nền ERA5, theo giờ). Gộp
sang khung 6 giờ: mưa lấy tổng, tầm nhìn lấy **min** (điều kiện xấu nhất mới gây
tai nạn), nhiệt độ lấy trung bình.

---

## 5. Schema — hợp đồng dữ liệu, không tự ý sửa

### `incidents.parquet` — khóa `incident_id`

```json
{
  "incident_id": "hn_2023_001842",
  "source_urls": ["https://...", "https://..."],
  "primary_url": "https://...",
  "published_at": "2023-03-12T08:15:00+07:00",
  "occurred_at": "2023-03-12T05:30:00+07:00",
  "time_confidence": "approximate",
  "location_text": "ngã tư Lê Văn Lương - Khuất Duy Tiến, Thanh Xuân",
  "lat": 20.9938, "lon": 105.8005,
  "geo_confidence": 120,
  "geo_method": "intersection",
  "h3_r7": "871f1d4c2ffffff",
  "h3_r8": "881f1d4c25fffff",
  "time_bin": "2023-03-12T00:00:00+07:00",
  "road_type": "urban_arterial",
  "vehicles_involved": ["motorcycle", "truck"],
  "fatalities": 1, "injuries": 2,
  "weather_mentioned": "rain",
  "cause_mentioned": "speeding",
  "extraction_method": "llm_v2",
  "raw_text": "..."
}
```

### `cells.parquet` — khóa `h3_index`

`resolution`, `centroid_lat`, `centroid_lon`, `district`, `ward`, `population`,
`population_density`, `image_path`, `n_intersections`, `road_length_primary`,
`road_length_secondary`, `road_length_residential`, `n_traffic_signals`,
`n_crossings`, `n_schools`, `n_hospitals`, `n_commercial_poi`, `has_major_road`

### `weather.parquet` — khóa `(h3_index, time_bin)`

`temp_mean`, `precipitation_sum`, `visibility_min`, `wind_speed_max`, `humidity_mean`

### `panel.parquet` — khóa `(h3_index, time_bin)`

Toàn bộ đặc trưng từ ba bảng trên + `n_incidents` + `label` + `is_covid_period`

---

## 6. Phân công và lịch

| Vai trò | Người | Nội dung |
|---|---|---|
| 1 | Trần Đức Huy | Kiến trúc pipeline, trích xuất A3, ghép `panel.parquet`, giữ repo và schema |
| 2 | *(điền tên)* | Crawl A1 + khử trùng lặp A2 |
| 3 | *(điền tên)* | Toàn bộ nhánh B |
| 4 | *(điền tên)* | Geocoding A4 + tổ chức gán nhãn tập vàng |

Cả 4 người cùng gán nhãn ở tuần 3; 200 bài gán đôi để tính Cohen's kappa (> 0,7).

| Tuần | Nội dung | Mốc |
|---|---|---|
| 1 | Khởi động, chốt 4 quyết định | Tài liệu thiết kế được duyệt |
| 2 | Pilot, crawl 3 nguồn đầu, nhánh B khởi động | 500 bài thô đầu tiên |
| 3 | Gán nhãn tập vàng | 300 bài, kappa > 0,7 |
| 4 | Crawl toàn bộ, trích xuất, geocoding | **CHECKPOINT — xem dưới** |
| 5 | Hoàn tất nhánh B, ghép dữ liệu | 4 file Parquet bản nháp |
| 6 | Kiểm định, data card | Bàn giao dataset v1.0 |

**Checkpoint tuần 4 — quan trọng nhất.** Đếm số vụ thật đã khử trùng lặp và
geocode thành công:

- \> 2.000: tiếp tục theo kế hoạch.
- 1.000–2.000: nới ngưỡng geocoding, mở rộng khoảng thời gian, thêm nguồn.
- < 1.000: **đổi thiết kế bài toán ngay** — chuyển sang dự đoán mức ngày thay vì
  khung 6 giờ, hoặc chuyển sang xếp hạng rủi ro tĩnh theo ô.

Quyết định ở tuần 4 còn cứu được. Để đến tuần 10 thì không kịp.

---

## 7. Tiêu chí hoàn thành giai đoạn 1

| Tiêu chí | Ngưỡng |
|---|---|
| Số vụ đã khử trùng lặp | ≥ 2.000 |
| Tỷ lệ geocode thành công | ≥ 70% |
| Precision mỗi trường trích xuất | ≥ 0,85 trên tập vàng |
| Cohen's kappa | > 0,7 |
| Ô H3 có ảnh bản đồ và dân số | 100% |
| Thời tiết không lỗ hổng | 100% |
| `panel.parquet` sinh được bằng một lệnh | Có |

---

## 8. Nguyên tắc kỹ thuật bất biến

1. **Không sửa hoặc xóa `data/raw/`.** Chỉ ghi thêm. Mọi bước sau phải chạy lại
   được từ dữ liệu thô mà không cần crawl lại.
2. **Không thao tác tay trên dữ liệu.** Mọi biến đổi nằm trong script chạy được
   từ đầu đến cuối. Không mở Excel sửa vài dòng.
3. **Schema là hợp đồng.** Đổi tên cột hay kiểu dữ liệu phải báo nhóm và cập nhật
   file này trước khi sửa code.
4. **Không commit dữ liệu lớn lên git.** `data/` nằm trong `.gitignore`. Nhưng
   `annotations/gold/` **phải commit** — tập vàng do người làm, mất là mất luôn.
5. Thời gian: múi giờ `Asia/Ho_Chi_Minh`, định dạng ISO 8601.
6. Tọa độ: WGS84 (EPSG:4326), lưu ra hai cột riêng `lat` và `lon`.
7. **Trường không có thông tin để `null`, cấm suy đoán.** Dữ liệu suy đoán làm
   hỏng cả tập vàng lẫn mô hình.
8. Crawler phải có checkpoint và rate limit ngay từ đầu, đừng đợi bị chặn IP.

---

## 9. Trạng thái hiện tại

**Đã có:**
- `filters.py` — lọc hai tầng, đã pass 4/4 ca kiểm tra bằng `python filters.py`
- `pilot_collect.py` — dò sitemap, lọc slug, tải HTML, có checkpoint và rate limit
- `pilot_report.py` — bóc tách, đo 5 chỉ số, xuất `pilot_survey.csv` để gán tay

**Cần làm tiếp:**
1. Ghép `filters.py` vào hai script pilot (thay `filter_urls` bằng `slug_passes`;
   gọi `classify_article` trong `pilot_report.py`)
2. Chạy pilot lần hai trên `anninhthudo.vn` và `baogiaothong.vn`, đo tỷ lệ *r*
3. Cả nhóm đọc tay 100 dòng `pilot_survey.csv`, điền 4 cột `MAN_*` — mục đích
   chính là đo tỷ lệ **loại nhầm** (bộ lọc vứt bỏ bài đúng), vì nhận nhầm còn lọc
   tiếp được, loại nhầm là mất dữ liệu mà không ai biết
4. Dựa vào *r* để tính số bài cần crawl, rồi lên lịch crawl chính thức

**Chưa bắt đầu:** toàn bộ nhánh B, geocoding, gán nhãn tập vàng.

---

## 10. Yêu cầu cho phiên làm việc này

*(Viết yêu cầu cụ thể ở đây trước khi gửi, ví dụ:)*

- Ghép `filters.py` vào `pilot_collect.py` và `pilot_report.py`
- Viết `src/htar/geocoding/intersection.py` tính giao điểm hai tuyến đường từ OSM
- Soạn `docs/annotation_guideline.md` kèm ví dụ trường hợp khó
- Viết crawler theo chuyên mục cho `anninhthudo.vn` (dự phòng khi không có sitemap)
- Thiết kế prompt trích xuất JSON cho bước A3
- Viết script sinh lưới H3 và render ảnh bản đồ 224×224 tắt nhãn

**Yêu cầu chung:** trả lời bằng tiếng Việt. Code phải chạy được ngay, có xử lý
lỗi và checkpoint, tuân thủ đúng schema ở mục 5 và nguyên tắc ở mục 8.
