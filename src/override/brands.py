"""Nạp danh sách thương hiệu VN từ ``dataset/brands/vn_brand_domains.csv``.

Dùng bởi:
  - Override #3 (typosquatting Levenshtein) — ``src/override/typosquatting.py``.
  - RAG Tầng 1 (structured lookup) — Tuần 5, phía Bạn A.

File CSV phẳng (1 dòng / domain), cột: ``brand, domain, category, verified, ghi_chu``
— xem ``Dataset/brands/README.md``. Thay cho ``brands_vn.json`` (đã bỏ) vì cần cột
``verified`` để theo dõi tiến độ rà tay từng dòng với nguồn SBV.
"""

from __future__ import annotations

import csv
from functools import lru_cache
from pathlib import Path
from typing import TypedDict

# Repo dùng 'Dataset/' viết hoa (xem Dataset/train/, tests/test_contracts.py).
BRANDS_PATH = Path(__file__).resolve().parents[2] / "Dataset" / "brands" / "vn_brand_domains.csv"

NHOM_HOP_LE = {
    "ngan_hang", "vi_dien_tu", "thuong_mai_dien_tu", "vien_thong",
    "hang_khong", "dich_vu_cong",
}
VERIFIED_HOP_LE = {"da_xac_minh", "chua_xac_minh"}


class Brand(TypedDict):
    nhan: str            # = cột 'brand' — nhãn so Levenshtein, duy nhất
    nhom: str            # = cột 'category'
    domains: list[str]   # mọi domain chính thức của brand này (phần tử [0] = dòng đầu trong CSV)
    verified: str        # 'da_xac_minh' nếu MỌI dòng của brand đã xác minh, ngược lại 'chua_xac_minh'
    ghi_chu: str         # ghi chú gộp (đổi tên / cảnh báo), rỗng nếu không có


@lru_cache(maxsize=1)
def load_brands(path: str | None = None) -> tuple[Brand, ...]:
    """Đọc CSV, gộp theo ``brand``, kiểm tính toàn vẹn. Cache lại (file tĩnh)."""
    p = Path(path) if path else BRANDS_PATH
    rows: list[dict[str, str]] = []
    with p.open(encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        assert reader.fieldnames == ["brand", "domain", "category", "verified", "ghi_chu"], \
            f"header CSV sai: {reader.fieldnames}"
        for r in reader:
            rows.append({k: (v or "").strip() for k, v in r.items()})

    gop: dict[str, Brand] = {}
    domain_seen: dict[str, str] = {}
    for r in rows:
        nhan, domain = r["brand"].lower(), r["domain"].lower()
        assert nhan.isalnum(), f"nhãn chỉ gồm chữ/số: {nhan!r}"
        assert r["category"] in NHOM_HOP_LE, f"nhóm lạ: {r['category']!r} ({nhan})"
        assert r["verified"] in VERIFIED_HOP_LE, f"verified lạ: {r['verified']!r} ({nhan})"
        assert "." in domain and "/" not in domain and " " not in domain, \
            f"domain sai định dạng: {domain!r}"
        assert domain not in domain_seen or domain_seen[domain] == nhan, \
            f"domain '{domain}' gán cho 2 brand: {domain_seen.get(domain)} + {nhan}"
        domain_seen[domain] = nhan

        b = gop.get(nhan)
        if b is None:
            gop[nhan] = Brand(nhan=nhan, nhom=r["category"], domains=[domain],
                              verified=r["verified"],
                              ghi_chu=r["ghi_chu"])
        else:
            assert b["nhom"] == r["category"], f"{nhan}: nhóm không nhất quán giữa các dòng"
            b["domains"].append(domain)
            # brand chỉ 'da_xac_minh' khi MỌI dòng của nó đã xác minh
            if r["verified"] != "da_xac_minh":
                b["verified"] = "chua_xac_minh"
            if r["ghi_chu"] and r["ghi_chu"] not in b["ghi_chu"]:
                b["ghi_chu"] = f"{b['ghi_chu']}; {r['ghi_chu']}".strip("; ")

    return tuple(gop.values())


def brand_by_label() -> dict[str, Brand]:
    return {b["nhan"]: b for b in load_brands()}


def all_official_domains() -> set[str]:
    return {d.lower() for b in load_brands() for d in b["domains"]}


def verified_official_domains() -> set[str]:
    """Chỉ domain của brand đã ``da_xac_minh`` — dùng khi cần độ chắc cao (RAG Tầng 1)."""
    return {d.lower() for b in load_brands() if b["verified"] == "da_xac_minh" for d in b["domains"]}


def typosquat_threshold(brand_label: str) -> int:
    """Ngưỡng khoảng cách Levenshtein cho 1 nhãn brand.

    Quy tắc theo độ dài của PhishMatch (arXiv:2112.02226, "A Layered Approach for
    Effective Detection of Phishing URLs"): nhãn **ngắn (<= 10 ký tự) → ngưỡng 1**,
    nhãn **dài (> 10) → ngưỡng 2**. Không loại
    bỏ nhãn ngắn — tài liệu đo typosquatting dùng ngưỡng-theo-độ-dài chứ không cắt
    nhãn ngắn; việc cắt sẽ bỏ sót typo của brand tên ngắn (acb/scb/vib/momo/zalo…).
    Tỉ lệ báo nhầm của luật này được đo riêng ở Section VI-A của bài.

    Xấp xỉ công thức ``max(1, len//5)`` ban đầu nhưng chặn trần ở 2 (PhishMatch
    không dùng ngưỡng >= 3 vì quá lỏng).
    """
    return 1 if len(brand_label) <= 10 else 2


if __name__ == "__main__":
    bs = load_brands()
    from collections import Counter
    nv = sum(1 for b in bs if b["verified"] == "da_xac_minh")
    print(f"{len(bs)} thương hiệu, {len(all_official_domains())} domain chính thức, "
          f"{nv} brand đã xác minh")
    for nhom, n in sorted(Counter(b["nhom"] for b in bs).items()):
        print(f"  {nhom:20s} {n}")
