#!/usr/bin/env python3
"""
Bo loc hai tang cho nhanh A - de tai du doan nguy co tai nan giao thong Ha Noi.

Sua hai loi phat hien o ban chay thu:
  (1) Bai khong lien quan den tai nan lot qua vi loc slug qua rong
  (2) Da so bai la tai nan o tinh khac, khong phai Ha Noi

Cach dung:
    from filters import slug_passes, classify_article

    # Tang 1: loc URL truoc khi tai (re, khong ton request)
    if slug_passes(url):
        html = fetch(url)

    # Tang 2: loc noi dung sau khi tai (chinh xac)
    verdict = classify_article(title, body)
    if verdict["keep"]:
        ...

Chay truc tiep de kiem tra lai ket qua pilot:
    python filters.py
"""

import re
import unicodedata

# ============================================================ TANG 1: SLUG
#
# Bo dau tieng Viet lam nhieu tu khac nghia sup thanh cung mot chuoi:
#   "tong"  <- tong (dam xe), tong (tong quat), tong (ho tong)
#   "dam"   <- dam (dam xe), dam (dam dong), dam (dam thoai), dam (hiep dam)
# Loc theo CHUOI CON tren toan bo URL (thiet ke cu) khop nham hang loat bai
# khong lien quan: "dinh-dam" (showbiz), "hiep-dam" (phap luat), "tong-kiem-tra"
# (thoi su), "ho-tong" (thoi su) deu chua "tong"/"dam" nhu mot tu doc lap.
#
# Thiet ke moi: tach slug thanh token theo dau "-", chi nhan dien theo
# CUM TU LIEN TIEP (n-gram) dung thu tu, va bat buoc cac dong tu mo ho
# (tong/dam/can/...) phai di kem mot token PHUONG TIEN trong cung slug thi
# moi duoc tinh la tai nan giao thong.

# Token phuong tien - dung de "go khoa" cac dong tu mo ho ben duoi.
# "tau" (tau hoa/tau thuy) duoc them sau khi phat hien vu "va cham voi
# tau hoa" bi loai oan vi khong co token "xe" trong slug.
VEHICLE_TOKENS = {"xe", "oto", "moto", "motor", "container", "tau"}


def _tokenize_slug(url: str) -> list:
    """Slug -> danh sach token, bo phan mo rong file va cac id so."""
    path = url.lower().split("?")[0].rstrip("/")
    slug = path.rsplit("/", 1)[-1]
    slug = re.sub(r"\.(html?|antd|aspx?)$", "", slug)
    return [t for t in slug.split("-") if t and not t.isdigit()]


def _has_vehicle_token(tokens: list) -> bool:
    if any(t in VEHICLE_TOKENS for t in tokens):
        return True
    # "o-to" (o to) bi tach thanh hai token rieng boi dau gach ngang.
    return any(tokens[i] == "o" and tokens[i + 1] == "to"
               for i in range(len(tokens) - 1))


def _has_phrase(tokens: list, phrase: tuple) -> bool:
    n = len(phrase)
    return any(tuple(tokens[i:i + n]) == phrase for i in range(len(tokens) - n + 1))


# Cum tu TU NO DA RO RANG la tai nan giao thong, khong can kiem tra them
# token phuong tien (vi ban than cum da chua "xe", hoac khong the mo ho
# thanh nghia khac trong tieng Viet bao chi).
SAFE_PHRASES = [
    ("tai", "nan", "giao", "thong"),
    ("va", "cham", "giao", "thong"),
    ("lat", "xe"), ("xe", "lat"),
    ("mat", "lai"),
    ("dam", "lien", "hoan"), ("tong", "lien", "hoan"),
    ("dam", "xe"), ("xe", "dam"),
    ("tong", "xe"), ("xe", "tong"),
]

# Cum tu CO THE la tai nan giao thong nhung cung co the la nghia khac
# ("dam chet" = tong chet HOAC dam (dao) chet; "can" = can (xe) HOAC can
# (bo), "than) - chi tinh la hop le neu slug co it nhat mot token phuong
# tien o dau do (xem VEHICLE_TOKENS).
GATED_PHRASES = [
    ("tai", "nan"),
    ("va", "cham"),
    ("dam", "vao"), ("tong", "vao"),
    ("dam", "trung"), ("tong", "trung"),
    ("dam", "truc", "dien"), ("tong", "truc", "dien"),
    ("dam", "chet"), ("tong", "chet"),
    ("can", "chet"), ("can", "tu", "vong"), ("can", "qua"),
    ("lao", "xuong"), ("roi", "xuong"),
    ("hat", "vang"),
    ("chet", "tai", "cho"),
]

# Danh sach loai tru - bat duoc bai tu thien, hoi nghi, chinh sach, va cac
# cum "tong"/"dam" pho bien KHONG lien quan tai nan (phong thu hai lop,
# tang 1 o tren da chan phan lon nhung giu lai de chac chan).
SLUG_EXCLUDE = [
    "trao-qua", "chia-se", "tu-thien", "ung-ho", "quyen-gop",
    "hoi-nghi", "hoi-thao", "toa-dam", "ra-quan", "phat-dong",
    "khen-thuong", "tuyen-truyen", "dien-tap", "le-ky-niem",
    "nghi-dinh", "thong-tu", "du-thao", "de-xuat", "quy-hoach",
    "khoi-cong", "khanh-thanh", "thong-xe", "dau-thau",
    "bong-da", "the-thao", "showbiz", "giai-tri",
    "tong-ket", "tong-hop", "tong-kiem-tra", "tong-thong", "tong-bi-thu",
    "tong-cuc", "tong-giam-doc", "tong-thu-ky", "tong-lanh-su", "ho-tong",
    "dinh-dam", "hiep-dam", "dam-o", "dam-duc", "dam-phan", "dam-dao",
    "dam-me", "dam-duoi", "loan-luan",
]


def slug_passes(url: str) -> bool:
    """Tang 1: loc nhanh theo duong dan URL. Re, khong ton request.

    Nhan dien theo cum tu lien tiep (khong phai chuoi con tuy y) de tranh
    khop nham do mat dau tieng Viet. Xem chi tiet o cac hang so ben tren.
    """
    path = url.lower().split("?")[0]
    if any(bad in path for bad in SLUG_EXCLUDE):
        return False

    tokens = _tokenize_slug(url)
    if any(_has_phrase(tokens, p) for p in SAFE_PHRASES):
        return True
    if _has_vehicle_token(tokens) and any(_has_phrase(tokens, p) for p in GATED_PHRASES):
        return True
    return False


# ================================================= TU DIEN DIA DANH HA NOI

HANOI_DISTRICTS = [
    "Hoàn Kiếm", "Ba Đình", "Đống Đa", "Hai Bà Trưng", "Tây Hồ", "Cầu Giấy",
    "Thanh Xuân", "Hoàng Mai", "Long Biên", "Nam Từ Liêm", "Bắc Từ Liêm",
    "Hà Đông", "Sơn Tây", "Ba Vì", "Chương Mỹ", "Đan Phượng", "Đông Anh",
    "Gia Lâm", "Hoài Đức", "Mê Linh", "Mỹ Đức", "Phú Xuyên", "Phúc Thọ",
    "Quốc Oai", "Sóc Sơn", "Thạch Thất", "Thanh Oai", "Thanh Trì",
    "Thường Tín", "Ứng Hòa",
]

# Duong, cau, nut giao dac trung Ha Noi. Xuat hien mot cai la gan nhu
# chac chan vu viec o Ha Noi - manh hon nhieu so voi chuoi "Ha Noi".
HANOI_LANDMARKS = [
    "Nguyễn Trãi", "Giải Phóng", "Trường Chinh", "Láng Hạ", "đường Láng",
    "Xuân Thủy", "Phạm Văn Đồng", "Võ Chí Công", "Nguyễn Văn Cừ",
    "Ngô Gia Tự", "Đại lộ Thăng Long", "Khuất Duy Tiến", "Lê Văn Lương",
    "Tố Hữu", "Trần Duy Hưng", "Phạm Hùng", "Lê Đức Thọ", "Hoàng Quốc Việt",
    "Nguyễn Xiển", "Nguyễn Khoái", "Minh Khai", "Tam Trinh", "Lĩnh Nam",
    "Ngọc Hồi", "Phan Trọng Tuệ", "Giải Phóng", "Kim Mã", "Liễu Giai",
    "Âu Cơ", "Nghi Tàm", "Yên Phụ", "Thanh Niên", "Xã Đàn", "Ô Chợ Dừa",
    "Cầu Giấy", "Cầu Chương Dương", "cầu Vĩnh Tuy", "cầu Thanh Trì",
    "cầu Nhật Tân", "cầu Long Biên", "cầu Thăng Long", "cầu Vĩnh Thịnh",
    "hầm chui Kim Liên", "hầm chui Thanh Xuân", "Ngã Tư Sở", "Ngã Tư Vọng",
    "Vành đai 3", "Vành đai 2", "Vành đai 2,5", "Vành đai 4",
    "Bến xe Mỹ Đình", "Bến xe Giáp Bát", "Bến xe Nước Ngầm",
    "Bến xe Gia Lâm", "sân bay Nội Bài", "Times City", "Royal City",
    "Linh Đàm", "Định Công", "Đại Kim", "Mỹ Đình", "Mễ Trì", "Trung Hòa",
]

# 62 tinh thanh con lai. Xuat hien trong phan dau bai = dau hieu manh
# rang vu viec KHONG o Ha Noi.
OTHER_PROVINCES = [
    "An Giang", "Bà Rịa", "Vũng Tàu", "Bắc Giang", "Bắc Kạn", "Bạc Liêu",
    "Bắc Ninh", "Bến Tre", "Bình Định", "Bình Dương", "Bình Phước",
    "Bình Thuận", "Cà Mau", "Cần Thơ", "Cao Bằng", "Đà Nẵng", "Đắk Lắk",
    "Đắk Nông", "Điện Biên", "Đồng Nai", "Đồng Tháp", "Gia Lai",
    "Hà Giang", "Hà Nam", "Hà Tĩnh", "Hải Dương", "Hải Phòng", "Hậu Giang",
    "Hòa Bình", "Hưng Yên", "Khánh Hòa", "Kiên Giang", "Kon Tum",
    "Lai Châu", "Lâm Đồng", "Lạng Sơn", "Lào Cai", "Long An", "Nam Định",
    "Nghệ An", "Ninh Bình", "Ninh Thuận", "Phú Thọ", "Phú Yên",
    "Quảng Bình", "Quảng Nam", "Quảng Ngãi", "Quảng Ninh", "Quảng Trị",
    "Sóc Trăng", "Sơn La", "Tây Ninh", "Thái Bình", "Thái Nguyên",
    "Thanh Hóa", "Thừa Thiên", "Tiền Giang", "TP.HCM", "TP HCM",
    "Hồ Chí Minh", "Trà Vinh", "Tuyên Quang", "Vĩnh Long", "Vĩnh Phúc",
    "Yên Bái", "Huế",
]

# Ngu canh khien "Ha Noi" xuat hien MA KHONG phai noi xay ra tai nan.
# Day la bay lon nhat: nan nhan tinh khac duoc chuyen len vien o Ha Noi.
HANOI_FALSE_CONTEXT = re.compile(
    r"(?:chuyển|đưa|cấp cứu|điều trị|chuyển tuyến)\s+(?:lên|ra|về|đến|tới)\s+"
    r"(?:[^.]{0,40})?(?:Hà Nội|Bệnh viện Việt Đức|Bạch Mai|Việt Đức|"
    r"Trung ương Quân đội|103|108)",
    re.I,
)

# ==================================================== NHAN DANG TAI NAN

RE_CRASH_VERB = re.compile(
    r"\b(tai nạn giao thông|va chạm|đâm (?:vào|trúng|trực diện|liên hoàn)|"
    r"tông (?:vào|trúng|trực diện|liên hoàn)|cán (?:qua|trúng|chết)|"
    r"húc (?:vào|đổ)|lật (?:xe|nghiêng)|xe (?:lật|lao|mất lái)|"
    r"mất lái|lao xuống|rơi xuống|kẹt dưới (?:gầm|bánh))\b",
    re.I,
)

RE_VEHICLE = re.compile(
    r"\b(xe máy|mô ?tô|xe gắn máy|ô ?tô|xe con|xe tải|xe ben|xe bồn|"
    r"container|xe đầu kéo|xe buýt|xe bus|xe khách|xe giường nằm|"
    r"xe đạp|xe ba gác|người đi bộ|xe cứu thương|xe cứu hỏa)\b",
    re.I,
)

RE_OUTCOME = re.compile(
    r"\b(tử vong|thiệt mạng|chết tại chỗ|bị thương|nguy kịch|"
    r"đa chấn thương|hư hỏng nặng|biến dạng)\b",
    re.I,
)

# Dau hieu tin TONG HOP / CHINH SACH chu khong phai mot vu cu the
RE_AGGREGATE = re.compile(
    r"\b(trong (?:tháng|quý|năm|kỳ nghỉ|dịp)|tổng cộng|thống kê cho thấy|"
    r"so với cùng kỳ|cả nước xảy ra|trung bình mỗi (?:ngày|tháng)|"
    r"số vụ tai nạn (?:giảm|tăng)|nghị định|thông tư|dự thảo|"
    r"hội nghị|hội thảo|tọa đàm|ra quân|phát động|trao quà|"
    r"chia sẻ với|ủng hộ|quyên góp|khen thưởng|diễn tập)\b",
    re.I,
)


def norm(s: str) -> str:
    return unicodedata.normalize("NFC", s or "")


def resolve_location(title: str, body: str, head_chars: int = 400) -> dict:
    """
    Xac dinh vu viec co xay ra o Ha Noi khong.

    Chi xet PHAN DAU bai (tieu de + head_chars ky tu dau), vi tin tieng Viet
    gan nhu luon neu dia diem ngay cau dau. Phan cuoi bai hay nhac cac dia
    danh khac (benh vien, co quan, vu viec tuong tu) gay nhieu.
    """
    head = norm(title) + "\n" + norm(body)[:head_chars]
    full = norm(title) + "\n" + norm(body)

    districts = [d for d in HANOI_DISTRICTS if d.lower() in head.lower()]
    landmarks = [l for l in HANOI_LANDMARKS if l.lower() in head.lower()]
    others = [p for p in OTHER_PROVINCES if p.lower() in head.lower()]

    bare_hanoi = "hà nội" in head.lower()
    false_ctx = bool(HANOI_FALSE_CONTEXT.search(full))

    hanoi_score = len(districts) * 3 + len(landmarks) * 3
    if bare_hanoi and not false_ctx:
        hanoi_score += 1
    other_score = len(others) * 3

    if hanoi_score == 0 and other_score > 0:
        verdict, conf = "other_province", "high"
    elif hanoi_score > 0 and other_score == 0:
        verdict, conf = "hanoi", "high" if (districts or landmarks) else "low"
    elif hanoi_score > other_score:
        verdict, conf = "hanoi", "medium"
    elif other_score > hanoi_score:
        verdict, conf = "other_province", "medium"
    else:
        verdict, conf = "unknown", "low"

    # Nan nhan duoc chuyen len vien Ha Noi nhung tai nan o tinh khac
    if false_ctx and not districts and not landmarks:
        verdict, conf = "other_province", "medium"

    return {
        "location_verdict": verdict,
        "location_confidence": conf,
        "hanoi_districts": districts,
        "hanoi_landmarks": landmarks[:3],
        "other_provinces": others,
        "transfer_context": false_ctx,
    }


def is_accident_report(title: str, body: str) -> dict:
    """Bai nay co tuong thuat MOT VU tai nan cu the khong?"""
    text = norm(title) + "\n" + norm(body)

    has_verb = bool(RE_CRASH_VERB.search(text))
    has_vehicle = bool(RE_VEHICLE.search(text))
    has_outcome = bool(RE_OUTCOME.search(text))
    is_agg = bool(RE_AGGREGATE.search(norm(title) + "\n" + norm(body)[:600]))

    # Can toi thieu: dong tu va cham + phuong tien.
    # Hau qua la dau hieu bo tro, khong bat buoc (va cham nhe van tinh).
    ok = has_verb and has_vehicle and not is_agg

    reasons = []
    if not has_verb:
        reasons.append("khong co dong tu va cham")
    if not has_vehicle:
        reasons.append("khong nhac phuong tien")
    if is_agg:
        reasons.append("tin tong hop/chinh sach/su kien")

    return {
        "is_accident": ok,
        "has_crash_verb": has_verb,
        "has_vehicle": has_vehicle,
        "has_outcome": has_outcome,
        "looks_aggregate": is_agg,
        "reject_reasons": reasons,
    }


def classify_article(title: str, body: str) -> dict:
    """Tang 2 day du: ket hop nhan dang tai nan va giai quyet dia ly."""
    acc = is_accident_report(title, body)
    loc = resolve_location(title, body)

    keep = acc["is_accident"] and loc["location_verdict"] == "hanoi"

    # Truong hop can nguoi xem lai thay vi vut bo ngay
    review = (
        acc["is_accident"]
        and loc["location_verdict"] == "unknown"
    ) or (
        acc["is_accident"]
        and loc["location_verdict"] == "hanoi"
        and loc["location_confidence"] == "low"
    )

    # is_accident_report() chi biet ly do lien quan toi "co phai tai nan
    # khong". Bo sung ly do dia ly o day de thong ke ly do loai bo day du
    # (dung cho bang "ly do loai" trong pilot_report.py).
    reject_reasons = list(acc["reject_reasons"])
    if acc["is_accident"] and loc["location_verdict"] != "hanoi":
        reject_reasons.append(f"dia_ban:{loc['location_verdict']}")

    return {
        "keep": keep, "needs_review": review,
        **acc, **loc,
        "reject_reasons": reject_reasons,
    }


# ==================================================== KIEM TRA NHANH

def _selftest() -> None:
    cases = [
        ("Bao Giao thong chia se voi nhung so phan khong may man",
         "Su chia se, giup do cua Bao Giao thong khuyen khich nhung so phan "
         "khong may man vuon len trong cuoc song.",
         False, "bai tu thien"),
        ("Xe máy va chạm ô tô trên đường Nguyễn Trãi, 1 người tử vong",
         "Khoảng 5h30 sáng 12/3, tại ngã tư Nguyễn Trãi - Khuất Duy Tiến "
         "(quận Thanh Xuân, Hà Nội), xe máy va chạm với ô tô con.",
         True, "tai nan Ha Noi"),
        ("Tai nạn nghiêm trọng trên quốc lộ 1A qua Thanh Hóa",
         "Sáng 3/4, tại km 320 quốc lộ 1A đoạn qua huyện Hậu Lộc, Thanh Hóa, "
         "xe tải đâm vào xe máy. Nạn nhân được chuyển ra Hà Nội cấp cứu.",
         False, "tinh khac, bay chuyen vien Ha Noi"),
        ("Tháng 5, cả nước xảy ra 1.200 vụ tai nạn giao thông",
         "Theo thống kê của Ủy ban ATGT Quốc gia, trong tháng 5 cả nước xảy "
         "ra 1.200 vụ tai nạn giao thông, giảm so với cùng kỳ.",
         False, "tin tong hop"),
    ]

    print("KIEM TRA BO LOC\n" + "=" * 60)
    passed = 0
    for title, body, expected, label in cases:
        r = classify_article(title, body)
        mark = "OK  " if r["keep"] == expected else "SAI "
        passed += r["keep"] == expected
        print(f"{mark} {label}")
        print(f"     keep={r['keep']}  tai_nan={r['is_accident']}  "
              f"dia_ly={r['location_verdict']}/{r['location_confidence']}")
        if r["reject_reasons"]:
            print(f"     ly do loai: {', '.join(r['reject_reasons'])}")
        print()

    print(f"Dat {passed}/{len(cases)}")
    print("\nKIEM TRA LOC SLUG\n" + "=" * 60)
    urls = [
        ("https://baogiaothong.vn/bao-giao-thong-chia-se-voi-nhung-so-phan-khong-may-man-192.html", False),
        ("https://baogiaothong.vn/xe-may-va-cham-o-to-tren-duong-nguyen-trai-1-nguoi-tu-vong-192.html", True),
        ("https://baogiaothong.vn/hoi-nghi-tong-ket-cong-tac-giao-thong-2024-192.html", False),
        # Cac slug nay lot qua bo loc cu o pilot lan 2 vi mat dau tieng Viet
        # lam "tong"/"dam" trung voi tu khac nghia. Phai bi loai.
        ("https://anninhthudo.vn/nguoi-dan-ong-dong-tinh-bi-dam-chet-trong-phong-tro-post72341.antd", False),
        ("https://anninhthudo.vn/cuoc-hoi-tu-cua-nhung-cap-song-ca-dinh-dam-post68167.antd", False),
        ("https://anninhthudo.vn/vi-sao-bo-hinh-phat-tu-hinh-doi-voi-toi-hiep-dam-post72430.antd", False),
        ("https://anninhthudo.vn/trung-quoc-tong-kiem-tra-boeing-737-post70064.antd", False),
        ("https://anninhthudo.vn/dam-hong-dang-bi-xe-thit-post68400.antd", False),
        ("https://anninhthudo.vn/mexico-doan-xe-ho-tong-bi-tan-cong-4-nguoi-chet-post72825.antd", False),
        # Truong hop dong tu mo ho nhung THUC SU la tai nan: phai giu, vi
        # co token phuong tien ("xe") o dau do trong slug.
        ("https://anninhthudo.vn/xe-tai-bat-ngo-tong-vao-dai-phan-cach-tren-cao-toc-post99999.antd", True),
        ("https://anninhthudo.vn/o-to-lao-xuong-song-hong-2-nguoi-mat-tich-post88888.antd", True),
    ]
    slug_passed = 0
    for u, expected in urls:
        got = slug_passes(u)
        mark = "OK  " if got == expected else "SAI "
        slug_passed += got == expected
        print(f"{mark} {'GIU ' if got else 'LOAI'} {u.split('/')[-1][:65]}")
    print(f"\nDat {slug_passed}/{len(urls)}")


if __name__ == "__main__":
    _selftest()
