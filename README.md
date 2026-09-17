# NCKH — Dự đoán nguy cơ tai nạn giao thông đa phương thức Hà Nội

Nghiên cứu Khoa học Sinh viên, Khoa Công nghệ thông tin, Đại học Công nghiệp Hà Nội.
Giảng viên hướng dẫn: **TS. Trần Hùng Cường**. Nhóm 4 thành viên, thời lượng 16 tuần.

> Tài liệu này là điểm bắt đầu cho **bất kỳ ai trong nhóm** — đọc xong nên hiểu
> được: đề tài làm gì, tại sao khó, đang làm đến đâu, và cần đọc tiếp tài liệu
> nào để bắt tay vào việc cụ thể.

---

## 1. Đề tài này giải quyết vấn đề gì

Xây dựng mô hình dự đoán nguy cơ tai nạn giao thông theo **ô lục giác (H3)**
và **khung 6 giờ**, cho địa bàn Hà Nội. Kiến trúc tham khảo:
**CrashFormer** (Karimi Monsefi et al., UrbanAI/SIGSPATIAL 2023,
[arXiv:2402.05151](https://arxiv.org/abs/2402.05151)) — mô hình đa phương thức
gồm 5 thành phần: Historical Event Encoder (FEDFormer), Image Encoder (VAN),
Data Encoder (nhân khẩu học), Feature Fusion, Classifier nhị phân.

### Đóng góp chính KHÔNG PHẢI là mô hình

Việt Nam không có dataset tai nạn công khai có cấu trúc như Mỹ. Đóng góp thật
sự của đề tài là:

1. **Tự xây bộ dữ liệu tai nạn Hà Nội** bằng cách trích xuất từ tin tức trực
   tuyến tiếng Việt (crawl + NLP/Information Extraction) — chưa ai làm dataset
   này trước đó.
2. **Điều chỉnh mô hình cho giao thông hỗn hợp mật độ cao, xe máy chiếm ưu
   thế** — khác hẳn giao thông ô tô hóa ở Mỹ mà bài báo gốc CrashFormer dựa vào.
3. **Module geocoding nút giao tự xây** (tính giao điểm 2 tuyến đường từ OSM)
   — không có geocoder có sẵn nào xử lý tốt cách người Việt mô tả vị trí tai
   nạn ("ngã tư Lê Văn Lương - Khuất Duy Tiến").

> **Hệ quả quan trọng nhất cho cách làm việc:** Giai đoạn xây dựng dữ liệu
> quan trọng hơn giai đoạn huấn luyện mô hình. Dữ liệu tốt thì huấn luyện chỉ
> là chạy code có sẵn. Dữ liệu tệ thì không kiến trúc mô hình nào cứu được.
> Vì vậy phần lớn công sức và rủi ro của đề tài nằm ở Giai đoạn 1, không phải
> ở việc code mô hình.

---

## 2. Toàn cảnh 5 giai đoạn (16 tuần)

| Giai đoạn | Nội dung | Trạng thái |
|---|---|---|
| **1. Thu thập dữ liệu** | Crawl tin tức + dữ liệu không gian OSM/dân số/thời tiết | **Đang làm** — xem chi tiết mục 3 |
| 2. Tiền xử lý & hợp nhất | Ghép 2 nguồn dữ liệu thành `panel.parquet`, xử lý mất cân bằng lớp | Chưa bắt đầu |
| 3. Xây dựng & huấn luyện mô hình | Cài đặt CrashFormer, baseline so sánh, tinh chỉnh | Chưa bắt đầu |
| 4. Đánh giá & trực quan | PR-AUC/F1 (không dùng accuracy), ablation, bản đồ nhiệt | Chưa bắt đầu |
| 5. Báo cáo & nghiệm thu | Viết báo cáo, data card, slide, demo | Chưa bắt đầu |

Quản lý công việc theo tuần trên **Trello** (board "NCKH"): 5 trạng thái
*Tuần này → Đang làm → Chờ review → Hoàn thành → Blocked*, gắn nhãn màu theo
giai đoạn để lọc.

---

## 3. Giai đoạn 1 — chi tiết (đang làm)

Chia 2 nhánh **độc lập hoàn toàn**, hợp nhất ở bước cuối:

```
Track A (NLP tin tức)                Track B (dữ liệu không gian)
─────────────────────                ────────────────────────────
A1  Crawl tin tức                    B1  Tải + cắt OSM Hà Nội
A2  Lọc + khử trùng lặp              B2  Sinh lưới H3 (res 7 + 8)
A3  Trích xuất thông tin (LLM/NLP)   B3  Render ảnh bản đồ 224×224
A4  Geocoding tiếng Việt ◄───────────B4  Đặc trưng đường bộ dạng số
    (nút giao cần dữ liệu OSM        B5  Dân số + điểm quan tâm (POI)
     từ B1 — điểm phối hợp bắt buộc) B6  Thời tiết (Open-Meteo)
        │                                    │
        └──────────► panel.parquet ◄─────────┘
              (dữ liệu huấn luyện hoàn chỉnh)
```

Hướng dẫn **input/output từng bước, công cụ, độ khó**:
[`docs/track_a_guide.md`](docs/track_a_guide.md) và
[`docs/track_b_guide.md`](docs/track_b_guide.md).

### 4 quyết định thiết kế đã chốt (bắt buộc hiểu trước khi code)

| # | Quyết định | Vì sao |
|---|---|---|
| 1 | Lưới không gian: **H3 resolution 7 + 8** chạy song song | Res 7 khớp bài gốc để so sánh; res 8 (~0.74km²) mới đủ mịn cho nội thành Hà Nội — res 7 chỉ ra ~650 ô, quá thô để làm bản đồ nhiệt |
| 2 | Thời gian: **4 khung 6 giờ/ngày**, có cờ `time_confidence` (exact/approximate/date_only) | Tin tiếng Việt hay dùng cụm mơ hồ ("rạng sáng", "chiều tối") cần bảng ánh xạ riêng |
| 3 | **Chỉ báo cáo PR-AUC và F1, cấm accuracy** | Mất cân bằng lớp cực nặng (~0.1% dương) — mô hình luôn trả "không" vẫn đạt 99.9% accuracy |
| 4 | Phạm vi dữ liệu: **2019-2025**, có cờ `is_covid_period` | Lưu lượng giao thông 2020-2021 bất thường do giãn cách |

**Điểm yếu học thuật lớn nhất, phải xử lý trung thực:** tin tức chỉ cho mẫu
dương — ô không có tin ≠ không có tai nạn. Bài toán phải phát biểu rõ trong
báo cáo là *"dự đoán nguy cơ tai nạn **nghiêm trọng, được truyền thông ghi
nhận**"*, không phải toàn bộ tai nạn thực tế.

Toàn bộ quyết định + lý do đầy đủ: [`docs/context.md`](docs/context.md) mục 2.

---

## 4. Trạng thái hiện tại (cập nhật sau pilot lần 2)

| Bước | Trạng thái |
|---|---|
| A1 — Crawl | Đã chạy pilot thành công trên 4 nguồn (184 bài), cần mở rộng quy mô |
| A2 — Lọc 2 tầng | Đã hoàn thiện và kiểm chứng bằng dữ liệu thật; khử trùng lặp (SimHash/MinHash) **chưa làm** |
| A3 — Trích xuất thông tin | Chưa bắt đầu |
| A4 — Geocoding | Chưa bắt đầu — cần đo thử sớm vì là phần rủi ro cao nhất, chưa có số liệu thật nào đo |
| B1-B6 — Track B | Chưa bắt đầu, độc lập với Track A nên có thể bắt đầu song song ngay |

### Nguồn tin tức đã khảo sát (tỷ lệ giữ lại *r* sau lọc 2 tầng, đo trên dữ liệu thật)

| Nguồn | Trạng thái | r | Ghi chú |
|---|---|---|---|
| `anninhthudo.vn` | Dùng tốt | ~36% | Báo Công an Hà Nội, tốt nhất đã xác nhận |
| `vovgiaothong.vn` | Dùng tốt | ~29% | Tier-1 sạch 100% (không lọt rác), nhưng sitemap chỉ có 1000 URL gần nhất — không đủ cho dữ liệu lịch sử 2019-2025 |
| `baoxaydung.vn` | Dùng được, nguồn phụ | ~11% | Chính là `baogiaothong.vn` cũ — đã redirect 301 do sáp nhập Bộ GTVT vào Bộ Xây dựng (2025) |
| `congan.hanoi.gov.vn` | Cần crawler riêng | — | Không có sitemap.xml |
| `hanoimoi.vn`, `kinhtedothi.vn` | Bị chặn | — | WAF/Cloudflare trả 403/401 ngay từ trang chủ |
| `laodongthudo.vn` | Cần điều tra thêm | — | Sitemap đọc được nhưng tải từng bài bị timeout liên tục |

**Phát hiện quan trọng đã sửa:** bộ lọc slug ban đầu khớp chuỗi con thô, bị
mất dấu tiếng Việt gây trùng chữ ("tông"/"tổng"/"tống", "đâm"/"đám"/"dâm") nên
lọt hàng loạt bài không liên quan (án mạng, showbiz, tin quốc tế...). Đã viết
lại theo nhận diện cụm từ liên tiếp + bắt buộc đi kèm từ chỉ phương tiện —
xem `filters.py`.

---

## 5. Cấu trúc thư mục

```
.
├── filters.py             # Bộ lọc 2 tầng (slug URL + nội dung) cho crawl tin tức
├── pilot_collect.py       # Crawl thử nghiệm theo domain, dò sitemap, có checkpoint
├── pilot_report.py        # Đo chỉ số chất lượng nguồn từ dữ liệu pilot đã crawl
├── requirements.txt
├── docs/
│   ├── context.md           # Tài liệu gốc: bối cảnh, quyết định thiết kế, schema dữ liệu, phân công, lịch trình
│   ├── track_a_guide.md     # Hướng dẫn chi tiết Track A (input/output từng bước)
│   └── track_b_guide.md     # Hướng dẫn chi tiết Track B (input/output từng bước)
└── data/, reports/, logs/   # Sinh ra khi chạy script — nằm trong .gitignore, không commit
```

---

## 6. Bắt đầu nhanh

```bash
pip install -r requirements.txt
```

Kiểm tra bộ lọc (chạy self-test, phải thấy toàn bộ pass):

```bash
python filters.py
```

Crawl thử một nguồn (checkpoint tự bỏ qua URL đã tải, chạy lại an toàn):

```bash
python pilot_collect.py --domain anninhthudo.vn --limit 50
```

Sinh báo cáo chất lượng dữ liệu đã crawl:

```bash
python pilot_report.py
```

Kết quả nằm ở `reports/tables/pilot_metrics.md` (chỉ số tổng hợp, có bảng lý
do bị loại) và `reports/tables/pilot_survey.csv` (dữ liệu để cả nhóm gán nhãn
tay — điền 4 cột `MAN_*` để đo tỷ lệ loại nhầm thật).

---

## 7. Schema dữ liệu — hợp đồng, không tự ý sửa

4 file Parquet đầu ra cuối Giai đoạn 1: `incidents.parquet` (khóa
`incident_id`), `cells.parquet` (khóa `h3_index`), `weather.parquet` (khóa
`h3_index, time_bin`), `panel.parquet` (khóa `h3_index, time_bin`, gộp cả 3
bảng trên + `n_incidents` + `label` + `is_covid_period`).

Chi tiết từng cột: [`docs/context.md`](docs/context.md) mục 5. **Đổi tên
cột/kiểu dữ liệu phải báo nhóm và cập nhật tài liệu trước khi sửa code.**

---

## 8. Nguyên tắc kỹ thuật bất biến

1. **Không sửa/xóa `data/raw/`** — chỉ ghi thêm, mọi bước sau chạy lại được
   từ dữ liệu thô mà không cần crawl lại.
2. **Không thao tác tay trên dữ liệu** — mọi biến đổi nằm trong script chạy
   được từ đầu đến cuối. Không mở Excel sửa vài dòng.
3. **Schema là hợp đồng** (xem mục 7).
4. **Không commit dữ liệu lớn lên Git** (`data/` nằm trong `.gitignore`),
   nhưng `annotations/gold/` (tập vàng) **phải commit** — mất là mất luôn.
5. Thời gian: múi giờ `Asia/Ho_Chi_Minh`, ISO 8601. Tọa độ: WGS84 (EPSG:4326),
   lưu 2 cột riêng `lat`/`lon`.
6. **Trường không có thông tin để `null`, cấm suy đoán.**
7. Crawler phải có checkpoint và rate limit ngay từ đầu, đừng đợi bị chặn IP.

Đầy đủ: [`docs/context.md`](docs/context.md) mục 8.

---

## 9. Checkpoint quan trọng nhất — tuần 4

Đếm số vụ đã khử trùng lặp + geocode thành công:

- **> 2.000 vụ:** tiếp tục theo kế hoạch.
- **1.000-2.000:** nới ngưỡng geocoding, mở rộng thời gian, thêm nguồn.
- **< 1.000: đổi thiết kế bài toán ngay** — chuyển sang dự đoán mức ngày thay
  vì khung 6 giờ, hoặc xếp hạng rủi ro tĩnh theo ô.

Quyết định ở tuần 4 còn cứu được. Để đến tuần 10 mới phát hiện thì không kịp.

---

## 10. Tài liệu tham khảo

| Tài liệu | Nội dung | Khi nào đọc |
|---|---|---|
| [`docs/context.md`](docs/context.md) | Bối cảnh đầy đủ, schema, lịch trình, phân công, kết quả pilot chi tiết | Đọc trước khi bắt đầu bất kỳ việc gì |
| [`docs/track_a_guide.md`](docs/track_a_guide.md) | Track A theo input/output từng bước | Khi làm crawl/lọc/trích xuất/geocoding |
| [`docs/track_b_guide.md`](docs/track_b_guide.md) | Track B theo input/output từng bước | Khi làm dữ liệu không gian |

**File này là tài liệu sống** — mỗi khi nhóm chốt quyết định mới hoặc phát
hiện vấn đề dữ liệu, cập nhật `docs/context.md` trước, rồi phản ánh lại phần
liên quan ở README này nếu cần.

---

## 11. Nhóm thực hiện

| Vai trò | Phụ trách |
|---|---|
| Chủ nhiệm đề tài | Trần Đức Huy (MSV 2023602954, lớp 2023KHMT01) — kiến trúc pipeline, trích xuất A3, ghép `panel.parquet`, giữ schema |
| Vai trò 2 | Crawl (A1) + khử trùng lặp (A2) |
| Vai trò 3 | Toàn bộ Track B |
| Vai trò 4 | Geocoding (A4) + tổ chức gán nhãn tập vàng |
