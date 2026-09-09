"""Override #3 — Typosquatting (Plan.md mục 2 & 3 Tuần 4; CLAUDE.md mục Kiến trúc,
điểm 2: *"Levenshtein Distance so với danh sách domain thương hiệu VN, ngưỡng tỉ
lệ theo độ dài tên ``max(1, len(brand)//5)`` để giảm bắt nhầm brand tên ngắn"*).

So **nhãn domain** của URL đang xét với từng ``nhan`` trong
``src/override/brands_vn.json`` (loader ở ``brands.py``). Không chạm mạng — thuần
tính toán, nên **không bao giờ trả "unknown"** (khớp docs/interface_contract.md §2).

Cờ (flag) trả về — khớp ``contracts.OverrideResult`` (name='typosquatting'):
  True   — nhãn domain khớp/gần khớp 1 thương hiệu VN nhưng KHÔNG phải domain
           chính thức của thương hiệu đó. 4 kiểu, xếp theo độ nghiêm trọng:
             1. mao_danh_truc_tiep  — trùng khít tên brand (dài >= 5 ký tự)
             2. mao_danh_subdomain  — tên brand nằm nguyên trong subdomain
             3. typosquat           — Levenshtein 1..ngưỡng so với tên brand
             4. brand_nhung         — tên brand (>= 6 ký tự) là chuỗi con của nhãn
  False  — là domain chính thức, hoặc không thương hiệu nào đủ gần trong ngưỡng.

Phạm vi & giới hạn có chủ đích:
  - Chỉ bắt biến thể *chính tả* của tên. Kiểu "brand + từ khoá" tách bằng dấu
    (``techcombank-xac-thuc.com``) mà Levenshtein không với tới thì để đặc trưng
    RF ``brand_in_path`` / ``domain_in_brand`` lo — xem GhiChú mục Kiến trúc.
  - **Brand tên < 5 ký tự** (mã ngân hàng 3 chữ: acb/scb/vib…, ví ngắn:
    momo/zalo/tiki…) bị **loại khỏi so khớp Levenshtein**: chuỗi 3-4 ký tự sai
    lệch 1 phép sửa trùng với vô số domain vô hại → theo đúng yêu cầu "không bắt
    nhầm brand tên ngắn" (Plan.md mục 7). Sự hiện diện của các tên này vẫn được
    RF ``domain_in_brand`` / ``brand_in_subdomain`` xử lý.

Chạy thử:  python -m src.override.typosquatting --smoke http://vietccombank.com
"""

from __future__ import annotations

import argparse
import ipaddress
import re
import time

from src.contracts import OverrideResult
from src.override.brands import all_official_domains, load_brands, typosquat_threshold
from src.override.domain_age import chuan_hoa_domain

try:  # python-Levenshtein (requirements) — fallback thuần Python nếu thiếu
    from Levenshtein import distance as _lev
except Exception:  # pragma: no cover - môi trường thiếu gói
    def _lev(a: str, b: str) -> int:
        if a == b:
            return 0
        if not a:
            return len(b)
        if not b:
            return len(a)
        truoc = list(range(len(b) + 1))
        for i, ca in enumerate(a, 1):
            hien = [i]
            for j, cb in enumerate(b, 1):
                hien.append(min(truoc[j] + 1, hien[j - 1] + 1,
                                truoc[j - 1] + (ca != cb)))
            truoc = hien
        return truoc[-1]

# Nhãn brand ngắn hơn mức này bị LOẠI hoàn toàn khỏi so khớp Levenshtein
# (cả "trùng khít" lẫn "typo 1..ngưỡng"): chuỗi 3-4 ký tự sai 1 phép sửa trùng
# với quá nhiều domain vô hại → "không bắt nhầm brand tên ngắn" (Plan.md mục 7).
NGUONG_NHAN_NGAN = 5
# Nhãn brand phải dài tối thiểu mức này mới xét "chuỗi con" (tránh 'momo', 'fpt'…
# khớp bừa vào tên dài).
NGUONG_BRAND_NHUNG_DAI = 6

_KIEU_UU_TIEN = {
    "mao_danh_truc_tiep": 0,
    "mao_danh_subdomain": 1,
    "typosquat": 2,
    "brand_nhung": 3,
}
_KIEU_MO_TA = {
    "mao_danh_truc_tiep": "dùng đúng tên thương hiệu nhưng không phải domain chính thức",
    "mao_danh_subdomain": "đặt tên thương hiệu trong subdomain",
    "typosquat": "sai khác chính tả nhỏ so với tên thương hiệu",
    "brand_nhung": "nhét nguyên tên thương hiệu vào nhãn domain",
}


def _chuan_hoa_nhan(s: str) -> str:
    """Bỏ hết ký tự không phải chữ/số, viết thường — về cùng dạng với ``nhan``."""
    return re.sub(r"[^a-z0-9]", "", s.lower())


def _tach_nhan(url: str) -> tuple[str, str, list[str]]:
    """→ (registrable_domain, nhãn_chính_đã_chuẩn_hoá, [nhãn_subdomain_đã_chuẩn_hoá])."""
    import tldextract

    domain = chuan_hoa_domain(url)
    ext = tldextract.extract(domain)
    nhan_chinh = _chuan_hoa_nhan(ext.domain)

    raw = url.strip()
    if "://" in raw:
        raw = raw.split("://", 1)[1]
    raw = raw.split("/", 1)[0].split("?", 1)[0].split("#", 1)[0].split("@")[-1]
    raw = raw.split(":", 1)[0]
    sub = tldextract.extract(raw).subdomain
    subs = [_chuan_hoa_nhan(p) for p in sub.split(".") if p and p != "www"]
    return domain, nhan_chinh, subs


def kiem_tra_typosquatting(url: str) -> OverrideResult:
    """Levenshtein nhãn domain vs brand VN → contracts.OverrideResult."""
    t0 = time.perf_counter()
    domain, cand, subs = _tach_nhan(url)

    def _ket_qua(flag, reason) -> OverrideResult:
        return OverrideResult(
            name="typosquatting", flag=flag, reason=reason,
            latency_ms=round((time.perf_counter() - t0) * 1000, 1),
        )

    host_raw = domain.split("/")[0]
    try:
        ipaddress.ip_address(host_raw)
        return _ket_qua(False, f"{host_raw} là địa chỉ IP — không xét typosquatting (đặc trưng RF 'ip' lo).")
    except ValueError:
        pass

    if not cand:
        return _ket_qua(False, "Không tách được nhãn domain — bỏ qua typosquatting.")

    if domain in all_official_domains():
        ten = next((b["ten"] for b in load_brands() if domain in b["domains"]), domain)
        return _ket_qua(False, f"{domain} là domain chính thức của {ten}.")

    # (kiểu, khoảng_cách, tên_brand, nhãn_brand) — chọn bản nghiêm trọng nhất
    ung_vien: list[tuple[str, int, str, str]] = []
    for b in load_brands():
        nhan = b["nhan"]
        thr = typosquat_threshold(nhan)
        d = _lev(cand, nhan)
        ngan = len(nhan) < NGUONG_NHAN_NGAN

        if not ngan:
            if d == 0:
                ung_vien.append(("mao_danh_truc_tiep", 0, b["ten"], nhan))
            elif 1 <= d <= thr:
                ung_vien.append(("typosquat", d, b["ten"], nhan))

        if (len(nhan) >= NGUONG_BRAND_NHUNG_DAI and nhan in cand and cand != nhan):
            ung_vien.append(("brand_nhung", 0, b["ten"], nhan))

        if not ngan and nhan in subs:
            ung_vien.append(("mao_danh_subdomain", 0, b["ten"], nhan))

    if not ung_vien:
        return _ket_qua(False, f"Nhãn '{cand}' không khớp thương hiệu VN nào trong ngưỡng Levenshtein.")

    kieu, d, ten, nhan = min(ung_vien, key=lambda x: (_KIEU_UU_TIEN[x[0]], x[1]))
    if kieu == "mao_danh_subdomain":
        vi_tri = f"Subdomain của '{domain}'"
    else:
        vi_tri = f"Nhãn '{cand}'"
    chi_tiet = f" (Levenshtein = {d} so với '{nhan}')" if kieu == "typosquat" else ""
    return _ket_qua(
        True,
        f"{vi_tri} — {_KIEU_MO_TA[kieu]}: nghi mạo danh {ten}{chi_tiet}; "
        f"domain '{domain}' không nằm trong danh sách chính thức.",
    )


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--smoke", metavar="URL", help="chạy thử 1 URL")
    args = ap.parse_args()
    if args.smoke:
        import json
        print(json.dumps(kiem_tra_typosquatting(args.smoke), ensure_ascii=False, indent=2))
    else:
        ap.print_help()
