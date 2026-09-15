#!/usr/bin/env python3
"""
Pilot collector - Giai doan 1, nhanh A (thu thap tin tuc)
De tai: Du doan nguy co tai nan giao thong da phuong thuc - Ha Noi

Muc dich: thu thap ~50 bai bao de do chat luong nguon truoc khi crawl quy mo lon.

Cach chay:
    python pilot_collect.py --limit 50
    python pilot_collect.py --limit 50 --domain baogiaothong.vn

Ket qua:
    data/raw/news/<domain>/<sha1>.html   - HTML goc, khong bao gio sua/xoa
    data/raw/news/manifest.jsonl         - so sach: url, thoi diem tai, hash, duong dan

Script co checkpoint: chay lai se bo qua cac URL da tai.
"""

import argparse
import gzip
import hashlib
import json
import random
import re
import sys
import time
import urllib.robotparser as robotparser
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urljoin, urlparse

import requests
from lxml import etree
from filters import slug_passes

# ---------------------------------------------------------------- cau hinh

# QUAN TRONG: thay email that cua nhom truoc khi chay.
# Crawler tu gioi thieu ro rang la cong cu nghien cuu hoc thuat, co dia chi
# lien he. Day vua la phep lich su vua la cach tranh bi chan nham.
CONTACT_EMAIL = "tranhuy10052005@gmail.com"
USER_AGENT = (
    "HAUI-TrafficResearchBot/0.1 (Student research project, "
    "Hanoi University of Industry; contact: {})".format(CONTACT_EMAIL)
)

# Toc do: toi da 1 request moi 1.5 giay cho moi ten mien.
# Dung ha thap con so nay. Bi chan IP o tuan 2 se lam cham ca nhom.
DELAY_SECONDS = 1.5
TIMEOUT = 20
MAX_RETRIES = 3

ROOT = Path(__file__).resolve().parent
RAW_DIR = ROOT / "data" / "raw" / "news"
MANIFEST = RAW_DIR / "manifest.jsonl"
LOG_DIR = ROOT / "logs"

SITEMAP_NS = {"sm": "http://www.sitemaps.org/schemas/sitemap/0.9"}


# ---------------------------------------------------------------- tien ich

def log(msg: str) -> None:
    stamp = datetime.now().strftime("%H:%M:%S")
    line = f"[{stamp}] {msg}"
    print(line, flush=True)
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    with open(LOG_DIR / "pilot_collect.log", "a", encoding="utf-8") as f:
        f.write(line + "\n")


def url_hash(url: str) -> str:
    return hashlib.sha1(url.encode("utf-8")).hexdigest()


def load_manifest() -> dict:
    """Doc so sach da co de bo qua URL da tai (checkpoint)."""
    seen = {}
    if MANIFEST.exists():
        with open(MANIFEST, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    rec = json.loads(line)
                    seen[rec["url"]] = rec
                except json.JSONDecodeError:
                    continue
    return seen


def append_manifest(record: dict) -> None:
    MANIFEST.parent.mkdir(parents=True, exist_ok=True)
    with open(MANIFEST, "a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")


class Fetcher:
    """Bo tai co gioi han toc do, thu lai, va kiem tra robots.txt."""

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": USER_AGENT,
            "Accept-Language": "vi-VN,vi;q=0.9",
        })
        self._last_call = {}
        self._robots = {}

    def _throttle(self, domain: str) -> None:
        last = self._last_call.get(domain, 0)
        wait = DELAY_SECONDS - (time.time() - last)
        if wait > 0:
            time.sleep(wait)
        self._last_call[domain] = time.time()

    def robots(self, domain: str) -> robotparser.RobotFileParser:
        if domain not in self._robots:
            rp = robotparser.RobotFileParser()
            rp.set_url(f"https://{domain}/robots.txt")
            try:
                self._throttle(domain)
                resp = self.session.get(
                    f"https://{domain}/robots.txt", timeout=TIMEOUT
                )
                rp.parse(resp.text.splitlines())
                log(f"robots.txt cua {domain}: doc thanh cong")
            except Exception as exc:
                log(f"CANH BAO: khong doc duoc robots.txt cua {domain}: {exc}")
                rp.parse([])
            self._robots[domain] = rp
        return self._robots[domain]

    def allowed(self, url: str) -> bool:
        domain = urlparse(url).netloc
        return self.robots(domain).can_fetch(USER_AGENT, url)

    def get(self, url: str, binary: bool = False):
        domain = urlparse(url).netloc
        for attempt in range(1, MAX_RETRIES + 1):
            try:
                self._throttle(domain)
                resp = self.session.get(url, timeout=TIMEOUT)
                if resp.status_code == 200:
                    return resp.content if binary else resp.text
                if resp.status_code in (429, 503):
                    backoff = DELAY_SECONDS * (2 ** attempt)
                    log(f"  bi gioi han ({resp.status_code}), cho {backoff:.0f}s")
                    time.sleep(backoff)
                    continue
                log(f"  HTTP {resp.status_code}: {url}")
                return None
            except requests.RequestException as exc:
                log(f"  loi lan {attempt}/{MAX_RETRIES}: {exc}")
                time.sleep(DELAY_SECONDS * attempt)
        return None


# ------------------------------------------------------- do tim sitemap

def discover_sitemaps(fetcher: Fetcher, domain: str) -> list:
    """
    Lay danh sach sitemap tu robots.txt.
    Neu robots.txt khong khai bao, thu cac duong dan pho bien.
    Khong hardcode duong dan cua tung bao - moi bao mot kieu.
    """
    found = []
    rp = fetcher.robots(domain)
    site_maps = rp.site_maps()
    if site_maps:
        found.extend(site_maps)
        log(f"{domain}: robots.txt khai bao {len(site_maps)} sitemap")

    if not found:
        for path in ("/sitemap.xml", "/sitemap_index.xml", "/sitemap-index.xml",
                     "/sitemaps.xml", "/news-sitemap.xml"):
            candidate = f"https://{domain}{path}"
            body = fetcher.get(candidate)
            if body and "<" in body[:200]:
                found.append(candidate)
                log(f"{domain}: tim thay sitemap tai {path}")
                break

    if not found:
        log(f"{domain}: KHONG tim thay sitemap. Se can crawl theo chuyen muc.")
    return found


def parse_sitemap(fetcher: Fetcher, url: str, depth: int = 0) -> list:
    """
    Doc mot sitemap. Neu la sitemap index thi de quy xuong.
    Tra ve danh sach (url, lastmod).
    """
    if depth > 2:
        return []

    if url.endswith(".gz"):
        raw = fetcher.get(url, binary=True)
        if raw is None:
            return []
        try:
            body = gzip.decompress(raw)
        except OSError:
            body = raw
    else:
        text = fetcher.get(url)
        if text is None:
            return []
        body = text.encode("utf-8")

    try:
        root = etree.fromstring(body)
    except etree.XMLSyntaxError as exc:
        log(f"  sitemap khong parse duoc: {url} ({exc})")
        return []

    tag = etree.QName(root).localname

    if tag == "sitemapindex":
        children = root.findall("sm:sitemap/sm:loc", SITEMAP_NS)
        log(f"  sitemap index: {len(children)} sitemap con")
        results = []
        # Chi lay 5 sitemap con gan nhat de pilot khong keo dai
        for loc in children[-5:]:
            results.extend(parse_sitemap(fetcher, loc.text.strip(), depth + 1))
        return results

    entries = []
    for u in root.findall("sm:url", SITEMAP_NS):
        loc_el = u.find("sm:loc", SITEMAP_NS)
        if loc_el is None or not loc_el.text:
            continue
        mod_el = u.find("sm:lastmod", SITEMAP_NS)
        entries.append((loc_el.text.strip(),
                        mod_el.text.strip() if mod_el is not None else None))
    return entries


def filter_urls(entries: list, require_hanoi: bool = False) -> list:
    """Tang 1: loc slug. Dieu kien 'ha-noi' trong URL da bo -
    loc dia ly chuyen sang tang 2 dua tren noi dung bai."""
    return [(u, m) for u, m in entries if slug_passes(u)]


# ---------------------------------------------------------------- chay

def collect(domain: str, limit: int, require_hanoi: bool, seed: int) -> None:
    fetcher = Fetcher()
    seen = load_manifest()
    log(f"So sach hien co: {len(seen)} URL da tai")

    sitemaps = discover_sitemaps(fetcher, domain)
    if not sitemaps:
        log("Dung lai. Can bo sung crawler theo chuyen muc cho ten mien nay.")
        return

    entries = []
    for sm in sitemaps:
        log(f"Doc sitemap: {sm}")
        entries.extend(parse_sitemap(fetcher, sm))
    log(f"Tong URL trong sitemap: {len(entries)}")

    candidates = filter_urls(entries, require_hanoi)
    log(f"Sau khi loc slug: {len(candidates)} URL ung vien")

    if require_hanoi and len(candidates) < limit:
        log("Khong du URL khi bat buoc co 'ha-noi' trong slug. "
            "Noi long dieu kien, se loc Ha Noi o buoc phan tich.")
        candidates = filter_urls(entries, require_hanoi=False)
        log(f"Sau khi noi long: {len(candidates)} URL ung vien")

    candidates = [c for c in candidates if c[0] not in seen]
    if not candidates:
        log("Tat ca URL ung vien deu da tai truoc do. Khong co gi de lam.")
        return

    # Lay mau ngau nhien co seed co dinh de tai lap duoc ket qua pilot.
    random.seed(seed)
    random.shuffle(candidates)
    batch = candidates[:limit]
    log(f"Se tai {len(batch)} bai (seed={seed})")

    out_dir = RAW_DIR / domain
    out_dir.mkdir(parents=True, exist_ok=True)

    ok = skipped = failed = 0
    for i, (url, lastmod) in enumerate(batch, 1):
        if not fetcher.allowed(url):
            log(f"[{i}/{len(batch)}] robots.txt khong cho phep, bo qua: {url}")
            skipped += 1
            continue

        log(f"[{i}/{len(batch)}] {url}")
        html = fetcher.get(url)
        if html is None:
            failed += 1
            continue

        h = url_hash(url)
        path = out_dir / f"{h}.html"
        path.write_text(html, encoding="utf-8")

        append_manifest({
            "url": url,
            "domain": domain,
            "lastmod": lastmod,
            "fetched_at": datetime.now(timezone.utc).isoformat(),
            "sha1": h,
            "path": str(path.relative_to(ROOT)),
            "bytes": len(html.encode("utf-8")),
            "batch": "pilot",
        })
        ok += 1

    log("")
    log("=" * 52)
    log(f"Tai thanh cong : {ok}")
    log(f"Bo qua (robots): {skipped}")
    log(f"That bai       : {failed}")
    log(f"HTML goc       : {out_dir}")
    log(f"So sach        : {MANIFEST}")
    log("=" * 52)
    log("Buoc tiep theo: python pilot_report.py")


def main():
    ap = argparse.ArgumentParser(description="Thu thap pilot tin tuc tai nan Ha Noi")
    ap.add_argument("--domain", default="baogiaothong.vn",
                    help="Ten mien nguon (mac dinh: baogiaothong.vn)")
    ap.add_argument("--limit", type=int, default=50,
                    help="So bai can tai (mac dinh: 50)")
    ap.add_argument("--any-location", action="store_true",
                    help="Khong bat buoc slug chua 'ha-noi'")
    ap.add_argument("--seed", type=int, default=2023,
                    help="Seed lay mau, giu co dinh de tai lap duoc")
    args = ap.parse_args()

    if "REPLACE_ME" in CONTACT_EMAIL:
        log("DUNG LAI: hay sua CONTACT_EMAIL trong file nay thanh email that "
            "cua nhom truoc khi chay.")
        sys.exit(1)

    collect(args.domain, args.limit, not args.any_location, args.seed)


if __name__ == "__main__":
    main()
