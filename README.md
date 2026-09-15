# NCKH — Dự đoán nguy cơ tai nạn giao thông đa phương thức Hà Nội

Nghiên cứu Khoa học Sinh viên, Khoa Công nghệ thông tin, Đại học Công nghiệp Hà Nội.
Giảng viên hướng dẫn: TS. Trần Hùng Cường. Nhóm 4 thành viên, thời lượng 16 tuần.

## Giới thiệu

Đề tài xây dựng mô hình dự đoán nguy cơ tai nạn giao thông theo ô lục giác
(H3) và khung 6 giờ cho địa bàn thành phố Hà Nội, dựa trên kiến trúc tham
khảo **CrashFormer** (Karimi Monsefi et al., UrbanAI/SIGSPATIAL 2023,
[arXiv:2402.05151](https://arxiv.org/abs/2402.05151)) — mô hình đa phương
thức gồm 5 thành phần: Historical Event Encoder (FEDFormer), Image Encoder
(VAN), Data Encoder, Feature Fusion, và Classifier nhị phân.

**Đóng góp chính không phải mô hình.** Việt Nam không có dataset tai nạn công
khai có cấu trúc như Mỹ. Nhóm tự xây bộ dữ liệu tai nạn Hà Nội bằng cách
trích xuất từ tin tức trực tuyến tiếng Việt (NLP/Information Extraction), và
điều chỉnh mô hình cho giao thông hỗn hợp mật độ cao, xe máy chiếm ưu thế —
khác hẳn giao thông ô tô hóa ở Mỹ mà bài báo gốc dựa vào.

> **Vì vậy: Giai đoạn 1 (xây dựng dữ liệu) quan trọng hơn giai đoạn huấn
> luyện mô hình.** Dữ liệu tốt thì huấn luyện chỉ là chạy code. Dữ liệu tệ
> thì không kiến trúc nào cứu được.

## Kiến trúc pipeline

Giai đoạn 1 chia thành 2 nhánh **độc lập hoàn toàn**, hợp nhất ở bước cuối:

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

Chi tiết từng bước — input/output/công cụ/độ khó — xem
[`docs/track_a_guide.md`](docs/track_a_guide.md) và
[`docs/track_b_guide.md`](docs/track_b_guide.md).

## Cấu trúc thư mục

```
.
├── filters.py             # Bộ lọc 2 tầng (slug URL + nội dung) cho crawl tin tức
├── pilot_collect.py       # Crawl thử nghiệm theo domain, dò sitemap, có checkpoint
├── pilot_report.py        # Đo chỉ số chất lượng nguồn từ dữ liệu pilot đã crawl
├── requirements.txt
├── docs/
│   ├── context.md           # Tài liệu gốc: bối cảnh, quyết định thiết kế, schema dữ liệu
│   ├── track_a_guide.md     # Hướng dẫn chi tiết Track A (input/output từng bước)
│   └── track_b_guide.md     # Hướng dẫn chi tiết Track B (input/output từng bước)
└── data/, reports/, logs/   # Sinh ra khi chạy script — không commit lên Git
```

## Trạng thái hiện tại

| Bước | Trạng thái |
|---|---|
| A1 — Crawl | Đã chạy pilot thành công trên 4 nguồn (184 bài), cần mở rộng quy mô |
| A2 — Lọc 2 tầng | Đã hoàn thiện và kiểm chứng bằng dữ liệu thật; khử trùng lặp (SimHash/MinHash) **chưa làm** |
| A3 — Trích xuất thông tin | Chưa bắt đầu |
| A4 — Geocoding | Chưa bắt đầu — cần đo thử sớm vì là phần rủi ro cao nhất |
| B1-B6 — Nhánh không gian | Chưa bắt đầu |

**Nguồn tin tức đã khảo sát** (tỷ lệ giữ lại *r* sau lọc 2 tầng, đo trên mẫu thật):

| Nguồn | Trạng thái | r |
|---|---|---|
| `anninhthudo.vn` | Hoạt động tốt | ~36% |
| `vovgiaothong.vn` | Hoạt động tốt, tier-1 sạch 100% | ~29% |
| `baoxaydung.vn` (đã sáp nhập từ `baogiaothong.vn`) | Hoạt động, nguồn phụ | ~11% |
| `congan.hanoi.gov.vn` | Không có sitemap, cần crawler riêng | — |
| `hanoimoi.vn`, `kinhtedothi.vn` | Bị chặn WAF (403/401) | — |
| `laodongthudo.vn` | Sitemap OK nhưng tải bài bị timeout | — |

## Bắt đầu nhanh

```bash
pip install -r requirements.txt
```

Kiểm tra bộ lọc (chạy self-test):

```bash
python filters.py
```

Crawl thử một nguồn:

```bash
python pilot_collect.py --domain anninhthudo.vn --limit 50
```

Sinh báo cáo chất lượng dữ liệu đã crawl:

```bash
python pilot_report.py
```

Kết quả nằm ở `reports/tables/pilot_metrics.md` (chỉ số tổng hợp) và
`reports/tables/pilot_survey.csv` (dữ liệu để gán nhãn tay).

## Tài liệu

| Tài liệu | Nội dung |
|---|---|
| [`docs/context.md`](docs/context.md) | Bối cảnh đề tài, 4 quyết định thiết kế đã chốt, schema dữ liệu (hợp đồng), lịch trình 6 tuần, tiêu chí hoàn thành |
| [`docs/track_a_guide.md`](docs/track_a_guide.md) | Hướng dẫn Track A theo input/output từng bước |
| [`docs/track_b_guide.md`](docs/track_b_guide.md) | Hướng dẫn Track B theo input/output từng bước |

## Nguyên tắc kỹ thuật bất biến

Xem đầy đủ ở `docs/context.md` mục 8. Tóm tắt:

1. Không sửa/xóa `data/raw/` — chỉ ghi thêm, mọi bước sau chạy lại được từ đầu.
2. Không thao tác tay trên dữ liệu — mọi biến đổi nằm trong script.
3. Schema là hợp đồng — đổi tên cột/kiểu dữ liệu phải báo nhóm trước.
4. Không commit dữ liệu lớn lên Git (`data/` nằm trong `.gitignore`), nhưng
   `annotations/gold/` (tập vàng) **phải commit**.
5. Thời gian: múi giờ `Asia/Ho_Chi_Minh`, ISO 8601. Tọa độ: WGS84 (EPSG:4326).
6. Trường không có thông tin để `null`, cấm suy đoán.
7. Bài toán phải phát biểu là *dự đoán nguy cơ tai nạn nghiêm trọng, được
   truyền thông ghi nhận* — không phải toàn bộ tai nạn thực tế.
8. Chỉ báo cáo **PR-AUC và F1**, tuyệt đối không báo cáo accuracy (mất cân
   bằng lớp cực nặng khiến accuracy vô nghĩa).

## Nhóm thực hiện

| Vai trò | Phụ trách |
|---|---|
| Chủ nhiệm đề tài | Trần Đức Huy — kiến trúc pipeline, trích xuất A3, ghép `panel.parquet`, giữ schema |
| Vai trò 2 | Crawl (A1) + khử trùng lặp (A2) |
| Vai trò 3 | Toàn bộ Track B |
| Vai trò 4 | Geocoding (A4) + tổ chức gán nhãn tập vàng |
