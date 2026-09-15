# Hướng dẫn Track A — Dữ liệu tai nạn (NLP)

> **Phạm vi:** tài liệu này chỉ nói về Track A (crawl tin tức, lọc, trích xuất
> thông tin, geocoding). Track B (dữ liệu không gian) xem ở
> `docs/track_b_guide.md`.
>
> **Cách đọc:** mỗi bước ghi rõ Input (cần gì trước khi bắt đầu) và Output (ra
> file gì, cột gì) để người làm biết chính xác điểm bắt đầu/kết thúc, và người
> review biết kiểm tra cái gì.
>
> Khác với Track B (nhiều bước làm song song được), **Track A gần như tuyến
> tính**: A1 → A2 → A3 → A4, mỗi bước cần output của bước trước.

---

## Sơ đồ phụ thuộc

```
A1 (Crawl) ──► A2 (Lọc + khử trùng lặp) ──► A3 (Trích xuất) ──► A4 (Geocoding)
                                                                     ▲
                                                    Track B / B1 ────┘
                                          (cần hanoi.osm.pbf cho geocoding nút giao)
```

Lưu ý duy nhất về song song: **A4 (geocoding kiểu nút giao) phụ thuộc chéo vào
B1 của Track B** (cần dữ liệu đường OSM để tính giao điểm 2 tuyến đường) — đây
là điểm phối hợp bắt buộc giữa 2 track, không thể làm A4 hoàn chỉnh nếu Track B
chưa cắt xong OSM Hà Nội.

---

## A1. Crawl

**Input:**
- Danh sách domain nguồn (khuyến nghị dùng `configs/sources.yaml` — xem
  `docs/context.md` mục 3 để biết nguồn nào đã xác nhận dùng được)
- `robots.txt` của từng domain (crawler tự đọc lúc chạy)

**Output:**
- HTML gốc: `data/raw/news/<domain>/<sha1>.html`
- Sổ sách: `data/raw/news/manifest.jsonl` (url, domain, thời điểm tải, hash, đường dẫn)

**Đã có sẵn:** `pilot_collect.py` — dò sitemap XML tự động qua `robots.txt`,
lọc slug bằng `filters.py`, có checkpoint (chạy lại bỏ qua URL đã tải), rate
limit 1.5s/domain, tự giới thiệu User-Agent nghiên cứu.

**Cần làm thêm cho quy mô chính thức:**
- Bỏ giới hạn "chỉ đọc 5 sitemap con gần nhất" (giới hạn này chỉ để pilot chạy nhanh).
- Viết crawler theo chuyên mục (phân trang, không dùng sitemap) cho domain
  không có sitemap, ví dụ `congan.hanoi.gov.vn`.
- Với domain bị chặn WAF (`hanoimoi.vn`, `kinhtedothi.vn`): cần quyết định có
  đầu tư crawler headless browser (Selenium/Playwright) hay bỏ qua.

**Công cụ:** `requests`, `lxml` (đọc sitemap XML), `urllib.robotparser`.

**Nguyên tắc bất biến (mục 8 `context.md`):** không sửa/xóa `data/raw/`, chỉ
ghi thêm. Giới hạn 1-2 request/giây, có checkpoint ngay từ đầu.

**Độ khó:** Thấp-trung bình cho domain có sitemap (đã làm được). Trung bình-cao
cho domain cần crawler chuyên mục hoặc headless browser.

---

## A2. Bóc tách, lọc, và khử trùng lặp

**Input:**
- HTML gốc + `manifest.jsonl` từ A1

**Output:**
- Bản đã bóc tách: `data/interim/news/01_parsed/<sha1>.json` (title, published_at, text)
- Cột quyết định lọc trên từng bài: `filter_keep`, `filter_needs_review`,
  `filter_location_verdict`, `filter_reject_reasons`
- Sau khử trùng lặp: `incident_id` duy nhất cho mỗi vụ (một vụ có thể gộp từ
  nhiều bài/nhiều báo)
- Bài bị loại **phải lưu lại kèm lý do loại** — dùng làm mẫu âm huấn luyện
  PhoBERT ở A3, và để kiểm tra bộ lọc có loại nhầm không

**Đã có sẵn:**
- Bóc tách bằng `trafilatura` (trong `pilot_report.py`)
- Lọc 2 tầng bằng `filters.py`: tầng 1 `slug_passes()` (theo URL, rẻ, chạy trước
  khi tải), tầng 2 `classify_article()` (theo nội dung, chính xác) — đã kiểm
  chứng bằng dữ liệu thật, có test tự động (`python filters.py`)

**Cần làm thêm:**
- **Khử trùng lặp SimHash/MinHash (`datasketch`) — chưa có trong code hiện tại,
  là việc bắt buộc trước khi crawl quy mô lớn.** Một vụ lớn có thể lên 8 báo
  khác nhau; nếu bỏ qua bước này, mô hình sẽ học theo mức độ báo chí quan tâm
  thay vì rủi ro thực tế.
- Kết hợp khớp (ngày, địa danh) để gộp các bài trùng thành 1 `incident_id`.

**Công cụ:** `trafilatura`, `filters.py` (đã có), `datasketch` (SimHash/MinHash — cần thêm).

**Độ khó:** Lọc — đã xong, kiểm chứng kỹ (xem lịch sử sửa lỗi bộ lọc slug
trong `context.md`). Khử trùng lặp — trung bình, chưa bắt đầu.

---

## A3. Trích xuất thông tin

**Input:**
- Bài đã lọc + dedup từ A2 (chỉ những bài `filter_keep=True`, đã có `incident_id` duy nhất)

**Output:**
- Các trường trong `incidents.parquet` (xem schema đầy đủ ở `docs/context.md` mục 5):
  `occurred_at`, `time_confidence`, `location_text`, `road_type`,
  `vehicles_involved`, `fatalities`, `injuries`, `weather_mentioned`,
  `cause_mentioned`, `extraction_method`

**Chiến lược (đã chốt trong `context.md`, chưa triển khai):**
1. **LLM gán nhãn sơ bộ toàn corpus** — prompt trả về đúng JSON schema cố định,
   trường nào không chắc thì để `null`, **cấm suy đoán**.
2. **Fine-tune PhoBERT+CRF** trên tập vàng (300 bài gán tay ở tuần 3).
3. **So sánh 2 phương án theo từng trường** (độ chính xác thời gian, địa điểm,
   phương tiện...) — bảng so sánh đưa thẳng vào báo cáo.

**⚠️ Lưu ý bắt buộc khi dùng PhoBERT:** input phải được **tách từ trước** bằng
VnCoreNLP hoặc `underthesea`. Thiếu bước này, mô hình vẫn chạy, **không báo
lỗi**, nhưng kết quả rất tệ — lỗi âm thầm dễ khiến nhóm tưởng nhầm là mô hình
kém.

**Công cụ:** LLM API (Claude/GPT/Gemini), `underthesea` hoặc VnCoreNLP (tách từ),
PhoBERT + CRF (fine-tune).

**Độ khó:** Cao — cần chuẩn bị tập vàng trước (phụ thuộc việc gán nhãn tuần 3),
và cần thiết kế prompt JSON schema cẩn thận.

---

## A4. Geocoding tiếng Việt

**Input:**
- `location_text` từ A3 (mô tả vị trí dạng chữ, ví dụ: "ngã tư Lê Văn Lương -
  Khuất Duy Tiến, Thanh Xuân")
- **`hanoi.osm.pbf` từ Track B / B1** — bắt buộc cho kiểu "nút giao" (xem sơ đồ
  phụ thuộc ở trên)

**Output:**
- Các trường trong `incidents.parquet`: `lat`, `lon`, `geo_confidence`,
  `geo_method`, `h3_r7`, `h3_r8`

**Ba kiểu mô tả vị trí, ba cách xử lý khác nhau:**

| Kiểu mô tả | Ví dụ | Cách xử lý |
|---|---|---|
| Địa chỉ điểm | "số 234 Nguyễn Trãi" | Nominatim hoặc Goong Maps API (Goong tốt hơn cho địa chỉ VN) |
| Nút giao | "ngã tư Lê Văn Lương – Khuất Duy Tiến" | **Không geocoder nào xử lý tốt — tự xây**: lấy 2 `LineString` tên đường từ OSM (Track B), tính giao điểm bằng Shapely |
| Đoạn/mốc | "km 8 đại lộ Thăng Long", "chân cầu Vĩnh Tuy" | Nội suy theo chiều dài `LineString` hoặc khớp POI |

**Kiểu "nút giao" là đóng góp kỹ thuật rõ ràng nhất của đề tài** — đáng một
mục riêng trong báo cáo, và là phần nên bắt đầu code sớm nhất trong A4 vì độ
khó cao nhất và không có thư viện có sẵn.

**Sau khi có tọa độ:**
- Gắn `geo_confidence` (bán kính sai số, mét). Ngưỡng loại bỏ: **> 300m khi
  làm ở resolution 8**.
- Tính `h3_r7`, `h3_r8` từ `lat`/`lon` bằng `h3-py`.
- **Cache kết quả vào `data/cache/geocode.sqlite`** — tránh gọi API geocode
  trùng lặp cho cùng một địa danh xuất hiện ở nhiều bài.

**Công cụ:** Goong Maps API, Nominatim, `shapely`, `geopy`, `sqlite3` (cache).

**Độ khó:** Cao nhất trong toàn bộ Track A — tài liệu gốc gọi đây là "phần khó
nhất". **Nên đo thử trên mẫu nhỏ (50 bài) sớm nhất có thể**, không đợi đến khi
A3 hoàn chỉnh mới bắt đầu, vì đây là rủi ro chưa có số liệu thật nào đo được.

---

## Bảng tổng hợp nhanh

| Bước | Input chính | Output chính | Phụ thuộc | Trạng thái | Độ khó |
|---|---|---|---|---|---|
| A1 | `sources.yaml` | HTML gốc + manifest | Không | Đã có (pilot), cần mở rộng | Thấp-TB |
| A2 | HTML từ A1 | Text đã lọc + `incident_id` dedup | A1 | Lọc: xong. Dedup: chưa làm | TB |
| A3 | Bài đã lọc+dedup từ A2 | Các trường có cấu trúc trong `incidents.parquet` | A2 | Chưa bắt đầu | Cao |
| A4 | `location_text` từ A3 + OSM (Track B/B1) | `lat`, `lon`, `h3_r7`, `h3_r8` | A3 + Track B | Chưa bắt đầu, cần đo thử sớm | Cao nhất |

## Định nghĩa hoàn thành Track A

Theo tiêu chí ở `docs/context.md` mục 7:
- Số vụ đã khử trùng lặp: **≥ 2.000**
- Tỷ lệ geocode thành công: **≥ 70%**
- Precision mỗi trường trích xuất: **≥ 0.85** trên tập vàng
- Cohen's kappa (gán nhãn tập vàng): **> 0.7**

Checkpoint bắt buộc ở tuần 4 (mục 6 `context.md`): đếm số vụ đã dedup + geocode
thành công — dưới 1.000 vụ thì phải đổi thiết kế bài toán ngay, không đợi đến
tuần 10.
