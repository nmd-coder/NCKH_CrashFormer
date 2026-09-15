#!/usr/bin/env python3
"""
Pilot report - do chat luong nguon truoc khi crawl quy mo lon.

Chay sau pilot_collect.py:
    python pilot_report.py

Ket qua:
    reports/tables/pilot_metrics.md   - bang 5 chi so + khuyen nghi
    reports/tables/pilot_survey.csv   - bang de NHOM DOC TAY 50 bai

QUAN TRONG: cac chi so tu dong chi la uoc luong bang bieu thuc chinh quy.
Con so that phai den tu viec doc tay 50 bai va dien vao pilot_survey.csv.
Bieu thuc chinh quy khong phan biet duoc "ngã tư Lê Văn Lương - Khuất Duy Tiến"
(geocode duoc) voi "một ngã tư ở quận Thanh Xuân" (khong geocode duoc).
"""

import csv
import json
import re
import unicodedata
from pathlib import Path
from filters import classify_article

import trafilatura

ROOT = Path(__file__).resolve().parent
MANIFEST = ROOT / "data" / "raw" / "news" / "manifest.jsonl"
OUT_DIR = ROOT / "reports" / "tables"
INTERIM = ROOT / "data" / "interim" / "news" / "01_parsed"

MIN_TEXT_CHARS = 200

# ------------------------------------------------------- bieu thuc nhan dang

RE_EXACT_TIME = re.compile(
    r"(?:khoảng\s+)?\b([01]?\d|2[0-3])\s*(?:h|giờ)\s*([0-5]?\d)?\b", re.I
)
RE_VAGUE_TIME = re.compile(
    r"\b(rạng sáng|sáng sớm|sáng|giữa trưa|trưa|chiều tối|chiều|tối|đêm|khuya|nửa đêm)\b",
    re.I,
)
RE_DATE = re.compile(r"\b(?:ngày\s+)?([0-3]?\d)[/\-.]([01]?\d)(?:[/\-.](20\d{2}))?\b")

# Dau hieu vi tri co the geocode duoc (nut giao, dia chi, moc km)
RE_LOC_PRECISE = re.compile(
    r"\b(ngã\s*(?:tư|ba|năm|sáu|bảy)|nút giao|vòng xuyến|cầu vượt|hầm chui|"
    r"km\s*\d+|số\s+\d+\s+(?:phố|đường)|trước\s+(?:số|cửa))\b",
    re.I,
)
# Dau hieu vi tri chi den cap hanh chinh (khong du de geocode chinh xac)
RE_LOC_COARSE = re.compile(
    r"\b(quận|huyện|thị xã|phường|xã)\s+[A-ZĐÀ-Ỹ]", re.I
)
RE_STREET = re.compile(r"\b(?:đường|phố|đại lộ|quốc lộ|cầu)\s+[A-ZĐÀ-Ỹ]")

VEHICLE_PATTERNS = {
    "motorcycle": r"xe máy|mô\s?tô|xe gắn máy|xe ôm",
    "car": r"ô\s?tô con|xe con|xe ô\s?tô(?! tải)|xe 4 chỗ|xe 7 chỗ",
    "truck": r"xe tải|xe ben|xe trộn bê\s?tông|xe bồn",
    "container": r"container|xe đầu kéo|xe siêu trường",
    "bus": r"xe buýt|xe bus",
    "coach": r"xe khách|xe giường nằm",
    "bicycle": r"xe đạp",
    "pedestrian": r"người đi bộ|người đi đường bị|sang đường",
}
RE_VEHICLES = {k: re.compile(v, re.I) for k, v in VEHICLE_PATTERNS.items()}

RE_CASUALTY = re.compile(
    r"\b(tử vong|thiệt mạng|chết tại chỗ|bị thương|nguy kịch|cấp cứu|thương vong)\b",
    re.I,
)
RE_CASUALTY_NUM = re.compile(
    r"\b(\d+)\s*(?:người\s+)?(tử vong|thiệt mạng|bị thương)\b", re.I
)
RE_WEATHER = re.compile(
    r"\b(trời mưa|mưa lớn|mưa to|đường trơn|sương mù|ngập nước|trời tối)\b", re.I
)

# Nhan dang tai nan + giai quyet dia ly (tang 2) lay tu filters.py - khong
# tu viet lai o day de tranh hai noi dung logic khac nhau ve cung mot cau hoi.


def norm(text: str) -> str:
    return unicodedata.normalize("NFC", text or "")


def analyse(title: str, body: str) -> dict:
    text = norm(f"{title}\n{body}")

    # Quyet dinh that: co giu bai nay khong, va tai sao. Dung chung mot ham
    # voi bo loc san xuat (filters.py) de con so bao cao khop voi con so
    # crawl thuc te, thay vi mot phien ban regex rieng bi lech dan theo thoi gian.
    clf = classify_article(title, body)

    vehicles = [k for k, rx in RE_VEHICLES.items() if rx.search(text)]

    has_precise = bool(RE_LOC_PRECISE.search(text))
    has_street = bool(RE_STREET.search(text))
    has_coarse = bool(RE_LOC_COARSE.search(text))
    if has_precise:
        loc_level = "precise"       # nut giao / so nha / moc km
    elif has_street:
        loc_level = "street"        # co ten duong, chua chac dinh vi duoc
    elif has_coarse:
        loc_level = "coarse"        # chi den cap quan/phuong
    else:
        loc_level = "none"

    return {
        "has_exact_time": bool(RE_EXACT_TIME.search(text)),
        "has_vague_time": bool(RE_VAGUE_TIME.search(text)),
        "has_date": bool(RE_DATE.search(text)),
        "location_level": loc_level,
        "vehicles": ";".join(vehicles),
        "n_vehicle_types": len(vehicles),
        "has_casualty": bool(RE_CASUALTY.search(text)),
        "casualty_numeric": bool(RE_CASUALTY_NUM.search(text)),
        "has_weather": bool(RE_WEATHER.search(text)),
        # ---- tu classify_article() trong filters.py (tang 2) ----
        "filter_keep": clf["keep"],
        "filter_needs_review": clf["needs_review"],
        "filter_is_accident": clf["is_accident"],
        "filter_location_verdict": clf["location_verdict"],
        "filter_location_confidence": clf["location_confidence"],
        "filter_reject_reasons": ";".join(clf["reject_reasons"]),
        "hanoi_districts": ";".join(clf["hanoi_districts"][:3]),
    }


def pct(n: int, total: int) -> str:
    return f"{100 * n / total:.0f}%" if total else "n/a"


def main() -> None:
    if not MANIFEST.exists():
        print(f"Khong tim thay {MANIFEST}. Chay pilot_collect.py truoc.")
        return

    records = []
    with open(MANIFEST, encoding="utf-8") as f:
        for line in f:
            if line.strip():
                records.append(json.loads(line))

    print(f"Doc {len(records)} ban ghi tu so sach\n")
    INTERIM.mkdir(parents=True, exist_ok=True)
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    rows, parse_failures = [], 0

    for rec in records:
        path = ROOT / rec["path"]
        if not path.exists():
            parse_failures += 1
            continue

        html = path.read_text(encoding="utf-8", errors="ignore")
        body = trafilatura.extract(
            html, include_comments=False, include_tables=False,
            favor_precision=True,
        ) or ""

        meta = trafilatura.extract_metadata(html)
        title = (meta.title if meta else "") or ""
        pub_date = (meta.date if meta else "") or ""

        if len(body) < MIN_TEXT_CHARS:
            parse_failures += 1
            parsed_ok = False
        else:
            parsed_ok = True

        flags = analyse(title, body)

        # Luu ban da boc tach de buoc sau dung lai
        (INTERIM / f"{rec['sha1']}.json").write_text(
            json.dumps({
                "url": rec["url"], "title": title, "published_at": pub_date,
                "text": body, **flags,
            }, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

        rows.append({
            "sha1": rec["sha1"],
            "url": rec["url"],
            "title": title[:120],
            "published_at": pub_date,
            "n_chars": len(body),
            "parsed_ok": parsed_ok,
            **flags,
            # Bon cot duoi day de NGUOI dien tay - khong tu dong duoc
            "MAN_is_incident": "",
            "MAN_in_hanoi": "",
            "MAN_geocodable": "",
            "MAN_note": "",
        })

    total = len(rows)
    if total == 0:
        print("Khong co bai nao de phan tich.")
        return

    ok = [r for r in rows if r["parsed_ok"]]
    n_ok = len(ok)

    m_parsed = total - parse_failures
    m_time = sum(r["has_exact_time"] for r in ok)
    m_vague = sum(r["has_vague_time"] and not r["has_exact_time"] for r in ok)
    m_precise = sum(r["location_level"] == "precise" for r in ok)
    m_street = sum(r["location_level"] == "street" for r in ok)
    m_coarse = sum(r["location_level"] == "coarse" for r in ok)
    m_veh = sum(r["n_vehicle_types"] > 0 for r in ok)
    m_cas = sum(r["has_casualty"] for r in ok)
    m_casnum = sum(r["casualty_numeric"] for r in ok)
    m_weather = sum(r["has_weather"] for r in ok)

    # Tang 2 - quyet dinh that tu filters.classify_article(). m_keep/n_ok
    # chinh la ty le giu lai r noi trong muc 3/9 cua docs/context.md.
    m_keep = sum(r["filter_keep"] for r in ok)
    m_review = sum(r["filter_needs_review"] for r in ok)
    reject_reason_counts = {}
    for r in ok:
        if r["filter_keep"]:
            continue
        for reason in r["filter_reject_reasons"].split(";"):
            if reason:
                reject_reason_counts[reason] = reject_reason_counts.get(reason, 0) + 1

    lines = [
        "# Ket qua chay thu pilot",
        "",
        f"- Tong bai tai ve: **{total}**",
        f"- Boc tach duoc noi dung: **{m_parsed}** ({pct(m_parsed, total)})",
        "",
        "## Nam chi so quyet dinh",
        "",
        "| Chi so | Ket qua | Nguong tot | Dat? |",
        "|---|---|---|---|",
        f"| Boc tach duoc noi dung | {pct(m_parsed, total)} | >95% | "
        f"{'OK' if m_parsed/total > .95 else 'CAN XEM LAI'} |",
        f"| Giu lai sau loc tang 2 (ty le r) | {pct(m_keep, n_ok)} | >40% | "
        f"{'OK' if m_keep/n_ok > .4 else 'CAN XEM LAI'} |",
        f"| Co gio cu the | {pct(m_time, n_ok)} | >40% | "
        f"{'OK' if m_time/n_ok > .4 else 'CAN XEM LAI'} |",
        f"| Vi tri muc nut giao/so nha | {pct(m_precise, n_ok)} | >70% | "
        f"{'OK' if m_precise/n_ok > .7 else 'CAN XEM LAI'} |",
        f"| Co loai phuong tien | {pct(m_veh, n_ok)} | >80% | "
        f"{'OK' if m_veh/n_ok > .8 else 'CAN XEM LAI'} |",
        "",
        "## Chi tiet bo sung",
        "",
        f"- Chi co moc thoi gian mo ho (rang sang, chieu toi...): {pct(m_vague, n_ok)}",
        f"- Vi tri chi co ten duong: {pct(m_street, n_ok)}",
        f"- Vi tri chi den cap quan/phuong: {pct(m_coarse, n_ok)}",
        f"- Co nhac thuong vong: {pct(m_cas, n_ok)}",
        f"- Co so lieu thuong vong cu the: {pct(m_casnum, n_ok)}",
        f"- Co nhac dieu kien thoi tiet: {pct(m_weather, n_ok)}",
        f"- Can nguoi xem lai (needs_review, khong tu dong quyet dinh): "
        f"{pct(m_review, n_ok)}",
        "",
        "### Ly do bi loai (trong so bai khong 'keep')",
        "",
    ] + [
        f"- `{reason}`: {count} bai"
        for reason, count in sorted(reject_reason_counts.items(),
                                     key=lambda kv: -kv[1])
    ] + [
        "",
        "## Doc so lieu nay the nao",
        "",
        "Chi so **vi tri muc nut giao/so nha** la quan trong nhat.",
        "",
        "- Tren 70%: giu nguyen thiet ke, dung H3 resolution 8 cho noi thanh.",
        "- Tu 50 den 70%: giu resolution 8 nhung phai ghi ro ty le loai bo",
        "  trong data card, va uu tien viet module tinh giao diem nut giao.",
        "- Duoi 50%: **phai hop nhom**. Lua chon: lui ve resolution 7, hoac",
        "  chuyen sang du doan o cap phuong/xa thay vi o luc giac.",
        "",
        "Chi so **co gio cu the** duoi 40% thi khung 6 gio mat y nghia:",
        "phan lon ban ghi se la date_only. Can nhac chuyen sang du doan muc ngay.",
        "",
        "Chi so **ty le r** dung de tinh san luong can crawl: can khoang",
        "`2000 / r` bai (nhan them ~1.4 lan cho khu trung lap) de co 2.000 vu",
        "Ha Noi. Ky vong theo docs/context.md: anninhthudo.vn r ~ 40-60%,",
        "baogiaothong.vn r ~ 5-8%.",
        "",
        "## Viec bat buoc lam tiep",
        "",
        "Mo `pilot_survey.csv`, doc tay tung bai, dien 4 cot:",
        "",
        "- `MAN_is_incident`: 1 neu la tuong thuat mot vu tai nan cu the, 0 neu khong",
        "- `MAN_in_hanoi`: 1 neu vu viec xay ra tren dia ban Ha Noi",
        "- `MAN_geocodable`: 1 neu mo ta vi tri du de xac dinh toa do trong",
        "  ban kinh khoang 300m (co nut giao, so nha, hoac moc km)",
        "- `MAN_note`: ghi chu truong hop kho, dac biet la cac cach mo ta vi tri",
        "  la ma bieu thuc chinh quy bo sot",
        "",
        "Sau khi dien xong, so sanh `MAN_is_incident` + `MAN_in_hanoi` voi cot",
        "`filter_keep`: bai nao MAN=1 nhung filter_keep=False la **loai nham**",
        "(mat du lieu ma khong ai biet) - day la con so quan trong nhat can bao",
        "cao, quan trong hon ca ty le r.",
        "",
        "Chia 50 bai cho 4 nguoi, moi nguoi khoang 13 bai, mat chung 30 phut.",
        "Con so trong cot MAN_ moi la con so that; bang tren chi la uoc luong.",
        "Ghi chu trong `MAN_note` se tro thanh dau vao truc tiep cho huong dan",
        "gan nhan o tuan 3.",
    ]

    (OUT_DIR / "pilot_metrics.md").write_text("\n".join(lines), encoding="utf-8")

    with open(OUT_DIR / "pilot_survey.csv", "w", encoding="utf-8-sig",
              newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)

    print("\n".join(lines))
    print(f"\nDa ghi: {OUT_DIR / 'pilot_metrics.md'}")
    print(f"Da ghi: {OUT_DIR / 'pilot_survey.csv'}")
    print(f"Ban boc tach: {INTERIM}")


if __name__ == "__main__":
    main()
