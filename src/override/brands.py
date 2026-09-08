"""Nạp danh sách thương hiệu VN (src/override/brands_vn.json).

Dùng bởi:
  - Override #3 (typosquatting Levenshtein) — Tuần 4.
  - RAG Tầng 1 (structured lookup) — Tuần 5, phía Bạn A.

Tuần 2 mới chỉ dựng file + loader + hàm ngưỡng. Logic so khớp Levenshtein viết ở
module override #3 sau.
"""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import TypedDict

BRANDS_PATH = Path(__file__).with_name("brands_vn.json")

NHOM_HOP_LE = {
    "ngan_hang", "vi_dien_tu", "tmdt", "vien_thong_cong_nghe",
    "hang_khong", "dich_vu_cong",
}


class Brand(TypedDict):
    ten: str
    nhan: str
    nhom: str
    domains: list[str]


@lru_cache(maxsize=1)
def load_brands(path: str | None = None) -> tuple[Brand, ...]:
    """Đọc + kiểm tính toàn vẹn file brand. Cache lại (file tĩnh)."""
    p = Path(path) if path else BRANDS_PATH
    data = json.loads(p.read_text(encoding="utf-8"))
    brands: list[Brand] = data["brands"]

    nhan_seen: set[str] = set()
    domain_seen: set[str] = set()
    for b in brands:
        assert set(b) >= {"ten", "nhan", "nhom", "domains"}, f"thiếu khoá: {b}"
        assert b["nhom"] in NHOM_HOP_LE, f"nhóm lạ: {b['nhom']} ({b['ten']})"
        assert b["nhan"] == b["nhan"].lower(), f"nhãn phải viết thường: {b['nhan']}"
        assert b["nhan"].isalnum(), f"nhãn chỉ gồm chữ/số: {b['nhan']}"
        assert b["nhan"] not in nhan_seen, f"nhãn trùng: {b['nhan']}"
        nhan_seen.add(b["nhan"])
        assert b["domains"], f"{b['ten']} không có domain"
        for d in b["domains"]:
            d = d.lower()
            assert "/" not in d and " " not in d, f"domain sai định dạng: {d}"
            assert "." in d, f"domain thiếu TLD: {d}"
            assert d not in domain_seen, f"domain trùng giữa 2 brand: {d}"
            domain_seen.add(d)

    meta_n = data.get("_meta", {}).get("so_luong")
    if meta_n is not None:
        assert meta_n == len(brands), f"_meta.so_luong={meta_n} ≠ {len(brands)}"
    return tuple(brands)


def brand_by_label() -> dict[str, Brand]:
    return {b["nhan"]: b for b in load_brands()}


def all_official_domains() -> set[str]:
    return {d.lower() for b in load_brands() for d in b["domains"]}


def typosquat_threshold(brand_label: str) -> int:
    """Ngưỡng khoảng cách Levenshtein cho 1 nhãn brand (CLAUDE.md, mục Kiến trúc).

    max(1, len(brand)//5) — brand tên ngắn ngưỡng 1 để giảm bắt nhầm.
    """
    return max(1, len(brand_label) // 5)


if __name__ == "__main__":
    bs = load_brands()
    from collections import Counter
    print(f"{len(bs)} thương hiệu, {len(all_official_domains())} domain chính thức")
    for nhom, n in sorted(Counter(b["nhom"] for b in bs).items()):
        print(f"  {nhom:22s} {n}")
