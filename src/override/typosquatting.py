"""Override #3 — Typosquatting (Plan.md mục 2 & 3 Tuần 4; CLAUDE.md mục Kiến trúc,
điểm 2: *"Levenshtein Distance so với danh sách domain thương hiệu VN"*).

So **nhãn domain** của URL đang xét với từng ``nhan`` trong
``dataset/brands/vn_brand_domains.csv`` (loader ở ``brands.py``). Không chạm mạng —
thuần tính toán, nên **không bao giờ trả "unknown"** (khớp docs/interface_contract.md §2).

Ngưỡng Levenshtein: quy tắc **theo độ dài** của PhishMatch (arXiv:2112.02226) —
``brands.typosquat_threshold``: nhãn <=10 ký tự → 1, nhãn >10 → 2. **KHÔNG loại bỏ
nhãn ngắn.** (Bản Tuần 4 từng cắt nhãn < 5 ký tự; tài liệu đo typosquatting —
PhishMatch, và ghi nhận vấn đề của Szurdi 2014 / Agten 2015 — dùng ngưỡng-theo-độ-dài
chứ không cắt nhãn ngắn. Cắt nhãn ngắn bỏ sót typo của acb/scb/vib/momo/zalo…; tỉ lệ
báo nhầm được đo riêng ở Section VI-A của bài thay vì chặn trước.)

Cờ (flag) trả về — khớp ``contracts.OverrideResult`` (name='typosquatting'):
  True   — nhãn domain khớp/gần khớp 1 thương hiệu VN nhưng KHÔNG phải domain
           chính thức. 4 kiểu, xếp theo độ nghiêm trọng:
             1. mao_danh_truc_tiep  — nhãn trùng khít tên brand (mọi độ dài)
             2. mao_danh_subdomain  — tên brand (>= 4 ký tự) là 1 nhãn subdomain
             3. typosquat           — Levenshtein 1..ngưỡng so với tên brand
             4. brand_nhung         — tên brand (>= 6 ký tự) là chuỗi con của nhãn
  False  — là domain chính thức, hoặc không thương hiệu nào đủ gần trong ngưỡng.

Giới hạn có chủ đích (ghi trong Section "Limitations" của bài):
  - Chỉ bắt biến thể *chính tả gần* của tên. Domain đặt tên **xa hẳn** brand
    (``secure-amazon-login.com`` cách ``amazon`` 20+ phép sửa — Spoofguard.io 3/2026)
    thì Levenshtein bó tay; đặc trưng RF nội dung + ``brand_in_path`` lo phần đó.
  - Khi nhãn candidate TRÙNG KHÍT 1 brand, các match "typo" tới brand khác gần đó
    bị bỏ qua (nó chính là brand kia, không phải typo).

Chạy thử:  python -m src.override.typosquatting --smoke http://vietccombank.com
"""

from __future__ import annotations

import argparse
import ipaddress
import re
import time

from src.contracts import OverrideResult
from src.override.brands import all_official_domains, brand_by_label, load_brands, typosquat_threshold
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

# Nhãn brand phải dài tối thiểu mức này mới xét "chuỗi con" (tránh 'momo','fpt'… khớp
# bừa vào tên dài) và "khớp trong subdomain" (nhãn subdomain hay là từ tuỳ ý).
NGUONG_BRAND_NHUNG_DAI = 6
NGUONG_SUBDOMAIN_DAI = 4

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
        nhan_thuoc = next((b["nhan"] for b in load_brands() if domain in b["domains"]), domain)
        return _ket_qua(False, f"{domain} là domain chính thức của '{nhan_thuoc}'.")

    nhan_hop_le = set(brand_by_label())
    cand_la_brand = cand in nhan_hop_le  # candidate CHÍNH LÀ 1 tên brand (chỉ khác domain)

    # (kiểu, khoảng_cách, nhãn_brand) — chọn bản nghiêm trọng nhất
    ung_vien: list[tuple[str, int, str]] = []
    for b in load_brands():
        nhan = b["nhan"]
        d = _lev(cand, nhan)

        if d == 0:
            ung_vien.append(("mao_danh_truc_tiep", 0, nhan))
        elif 1 <= d <= typosquat_threshold(nhan) and not cand_la_brand:
            ung_vien.append(("typosquat", d, nhan))

        if len(nhan) >= NGUONG_BRAND_NHUNG_DAI and nhan in cand and cand != nhan:
            ung_vien.append(("brand_nhung", 0, nhan))

        if len(nhan) >= NGUONG_SUBDOMAIN_DAI and nhan in subs:
            ung_vien.append(("mao_danh_subdomain", 0, nhan))

    if not ung_vien:
        return _ket_qua(False, f"Nhãn '{cand}' không khớp thương hiệu VN nào trong ngưỡng Levenshtein.")

    kieu, d, nhan = min(ung_vien, key=lambda x: (_KIEU_UU_TIEN[x[0]], x[1]))
    vi_tri = f"Subdomain của '{domain}'" if kieu == "mao_danh_subdomain" else f"Nhãn '{cand}'"
    chi_tiet = f" (Levenshtein = {d} so với '{nhan}', ngưỡng {typosquat_threshold(nhan)})" \
        if kieu == "typosquat" else ""
    return _ket_qua(
        True,
        f"{vi_tri} — {_KIEU_MO_TA[kieu]}: nghi mạo danh '{nhan}'{chi_tiet}; "
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
