"""Override #1 — Tuổi domain (Plan.md mục 2 & 3 Tuần 3; CLAUDE.md mục Kiến trúc,
điểm 2 "Luật Override").

Quy trình đúng thứ tự:
  1. RDAP trước: tra IANA bootstrap (https://data.iana.org/rdap/dns.json) lấy
     máy chủ RDAP theo TLD, rồi GET {base}/domain/{domain}, đọc mốc "registration".
  2. WHOIS fallback: nếu RDAP không ra ngày (TLD không có RDAP, lỗi mạng,
     bản ghi thiếu trường) → thử WHOIS (python-whois).
  3. Cả hai đều không ra ngày → flag = "unknown". **KHÔNG mặc định an toàn.**

  `.vn` hiện chưa có RDAP (VNNIC chưa triển khai) → domain .vn luôn rơi xuống
  WHOIS trên thực tế — đúng thiết kế, không phải lỗi.

Cờ (flag) trả về:
  True     — lấy được tuổi và tuổi < NGUONG_TUOI_MOI_NGAY (domain quá non → đáng ngờ)
  False    — lấy được tuổi và tuổi >= ngưỡng
  "unknown"— không xác định được ngày đăng ký từ cả RDAP lẫn WHOIS

Ngưỡng NGUONG_TUOI_MOI_NGAY là MẶC ĐỊNH KHỞI ĐỘNG — hiệu chỉnh lại cùng ngưỡng
phân vùng ở Tuần 6 trên traffic mô phỏng (Plan.md mục 3 Tuần 6). Không có con số
"chuẩn" thống nhất trong tài liệu: 30 ngày (heuristic phổ biến), 45 ngày (bằng
sáng chế Google US11777987 lấy làm ví dụ ngưỡng "an toàn"), 90 ngày (đang dùng).

**Giới hạn cấu trúc của luật này** (ghi vào Section "Limitations" của bài):
  - Chỉ hiệu quả với phishing dùng **domain đăng ký mới** — CAIDA/WEIS 2025 ước
    tính chỉ ~66% domain phishing là đăng ký mới cho mục đích xấu; ~34% còn lại là
    **domain hợp pháp bị chiếm** (đã tồn tại lâu năm) → luật này luôn báo "an
    toàn" cho nhóm đó, mù hoàn toàn, không phải chuyện chỉnh ngưỡng.
  - Ngay trong nhóm domain mới, xu hướng **"ủ domain"** (đăng ký sớm, để nội dung
    vô hại nhiều tháng rồi mới dùng) đang làm giảm hiệu quả — Allure Security
    4/2026: chỉ 7% domain phishing hiện dưới 30 ngày tuổi.
  ⇒ Phải dựa thêm Random Forest + Typosquatting để bù, không chỉ 1 luật domain_age.

Timeout ~500ms mỗi bước (Plan.md). WHOIS cổng 43 thường chậm hơn mốc này → hay
rơi về "unknown"; đó là hành vi đã lường trước, không phải bug.

Chạy thử (có mạng):  python -m src.override.domain_age --smoke vietcombank.com.vn
"""

from __future__ import annotations

import argparse
import socket
import time
from datetime import datetime, timezone
from functools import lru_cache

import requests

from src.contracts import OverrideResult

try:  # python-whois — chỉ dùng ở nhánh fallback
    import whois as _whois
except Exception:  # pragma: no cover - môi trường thiếu gói
    _whois = None

IANA_BOOTSTRAP_URL = "https://data.iana.org/rdap/dns.json"
BOOTSTRAP_TIMEOUT_S = 3.0  # tải 1 lần rồi cache (lru_cache) — không tính vào "~500ms/bước"
RDAP_TIMEOUT_S = 0.5       # mỗi truy vấn RDAP theo domain
WHOIS_TIMEOUT_S = 0.5      # mỗi truy vấn WHOIS cổng 43
NGUONG_TUOI_MOI_NGAY = 90  # < 90 ngày = "domain non" → cờ đáng ngờ (hiệu chỉnh Tuần 6)

_HEADERS = {
    "User-Agent": "doan-cntt-phishing-detector/0.1 (Override#1 tuoi-domain)",
    "Accept": "application/rdap+json",
}

# TLD (kể cả SLD .*.vn, .co.uk...) mà IANA bootstrap không phủ → bỏ qua RDAP luôn.
TLD_KHONG_CO_RDAP = {"vn", "com.vn", "net.vn", "org.vn", "gov.vn", "edu.vn"}


# ---------------------------------------------------------------------------
# Chuẩn hoá domain
# ---------------------------------------------------------------------------
def chuan_hoa_domain(url_hoac_domain: str) -> str:
    """URL hoặc host → domain đăng ký (registrable domain), viết thường, bỏ 'www.'.

    Dùng tldextract để tách đúng cả SLD kiểu '*.com.vn'.
    """
    import tldextract

    raw = url_hoac_domain.strip()
    if "://" in raw:
        raw = raw.split("://", 1)[1]
    raw = raw.split("/", 1)[0].split("?", 1)[0].split("#", 1)[0]
    raw = raw.split("@")[-1].split(":", 1)[0]
    ext = tldextract.extract(raw)
    if ext.domain and ext.suffix:
        return f"{ext.domain}.{ext.suffix}".lower()
    return raw.lower().lstrip(".")


def _suffix(domain: str) -> str:
    import tldextract

    return tldextract.extract(domain).suffix.lower()


# ---------------------------------------------------------------------------
# RDAP
# ---------------------------------------------------------------------------
@lru_cache(maxsize=1)
def _tai_bootstrap() -> dict[str, str]:
    """Tải IANA bootstrap 1 lần → map {tld: rdap_base_url (có '/' cuối)}."""
    r = requests.get(IANA_BOOTSTRAP_URL, headers=_HEADERS, timeout=BOOTSTRAP_TIMEOUT_S)
    r.raise_for_status()
    mapping: dict[str, str] = {}
    for services in r.json().get("services", []):
        tlds, urls = services[0], services[1]
        base = next((u for u in urls if u.startswith("https://")), urls[0])
        if not base.endswith("/"):
            base += "/"
        for tld in tlds:
            mapping[tld.lower()] = base
    return mapping


def _rdap_ngay_dang_ky(domain: str) -> datetime | None:
    """None nếu TLD không có RDAP / lỗi mạng / bản ghi thiếu mốc 'registration'."""
    suffix = _suffix(domain)
    tld = suffix.split(".")[-1] if suffix else ""
    if suffix in TLD_KHONG_CO_RDAP or tld in TLD_KHONG_CO_RDAP:
        return None
    try:
        base = _tai_bootstrap().get(tld)
        if not base:
            return None
        r = requests.get(f"{base}domain/{domain}", headers=_HEADERS,
                         timeout=RDAP_TIMEOUT_S)
        if r.status_code != 200:
            return None
        for ev in r.json().get("events", []):
            if ev.get("eventAction") == "registration" and ev.get("eventDate"):
                return _parse_iso(ev["eventDate"])
    except (requests.RequestException, ValueError, KeyError):
        return None
    return None


def _parse_iso(s: str) -> datetime | None:
    s = s.strip().replace("Z", "+00:00")
    try:
        dt = datetime.fromisoformat(s)
    except ValueError:
        for fmt in ("%Y-%m-%dT%H:%M:%S", "%Y-%m-%d"):
            try:
                dt = datetime.strptime(s[:19] if "T" in s else s[:10], fmt)
                break
            except ValueError:
                continue
        else:
            return None
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


# ---------------------------------------------------------------------------
# WHOIS fallback
# ---------------------------------------------------------------------------
def _whois_ngay_dang_ky(domain: str) -> datetime | None:
    if _whois is None:
        return None
    cu = socket.getdefaulttimeout()
    socket.setdefaulttimeout(WHOIS_TIMEOUT_S)
    try:
        w = _whois.whois(domain)
        cd = w.get("creation_date") if isinstance(w, dict) else getattr(w, "creation_date", None)
    except Exception:
        return None
    finally:
        socket.setdefaulttimeout(cu)
    if isinstance(cd, (list, tuple)):
        cd = next((x for x in cd if x), None)
    if isinstance(cd, datetime):
        return cd if cd.tzinfo else cd.replace(tzinfo=timezone.utc)
    if isinstance(cd, str):
        return _parse_iso(cd)
    return None


# ---------------------------------------------------------------------------
# Điểm vào Override #1
# ---------------------------------------------------------------------------
def kiem_tra_tuoi_domain(url: str,
                         nguong_ngay: int = NGUONG_TUOI_MOI_NGAY) -> OverrideResult:
    """RDAP → WHOIS → 'unknown'. Trả contracts.OverrideResult."""
    t0 = time.perf_counter()
    domain = chuan_hoa_domain(url)

    ngay = _rdap_ngay_dang_ky(domain)
    nguon = "RDAP"
    if ngay is None:
        ngay = _whois_ngay_dang_ky(domain)
        nguon = "WHOIS"

    latency_ms = round((time.perf_counter() - t0) * 1000, 1)

    if ngay is None:
        return OverrideResult(
            name="domain_age", flag="unknown", latency_ms=latency_ms,
            reason=f"Không tra được ngày đăng ký của '{domain}' qua RDAP lẫn WHOIS "
                   f"(không mặc định an toàn).",
        )

    tuoi_ngay = (datetime.now(timezone.utc) - ngay).days
    non = tuoi_ngay < nguong_ngay
    return OverrideResult(
        name="domain_age", flag=bool(non), latency_ms=latency_ms,
        reason=f"{domain}: đăng ký {ngay.date().isoformat()} ({nguon}), "
               f"tuổi ~{tuoi_ngay} ngày "
               f"({'DƯỚI' if non else 'từ'} ngưỡng {nguong_ngay} ngày → "
               f"{'đáng ngờ' if non else 'ổn'}).",
    )


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--smoke", metavar="URL", help="chạy thử thật (cần mạng)")
    args = ap.parse_args()
    if args.smoke:
        import json
        print(json.dumps(kiem_tra_tuoi_domain(args.smoke), ensure_ascii=False, indent=2))
    else:
        ap.print_help()
