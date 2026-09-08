"""Kiểm file danh sách thương hiệu VN (src/override/brands_vn.json).

Chỉ kiểm CẤU TRÚC — không xác minh domain có thật/đang sống (việc rà tay, xem
_meta.canh_bao trong file). Chạy: pytest -q  hoặc chạy tay như tests/test_contracts.py
"""

from src.override.brands import (
    all_official_domains,
    brand_by_label,
    load_brands,
    typosquat_threshold,
)


def test_load_and_min_count():
    brands = load_brands()
    assert len(brands) >= 40, "Plan.md yêu cầu ~40-60 domain thương hiệu"


def test_labels_unique_and_normalised():
    labels = [b["nhan"] for b in load_brands()]
    assert len(labels) == len(set(labels))
    assert all(l == l.lower() and l.isalnum() for l in labels)


def test_domains_unique_across_brands():
    doms = [d for b in load_brands() for d in b["domains"]]
    assert len(doms) == len(set(doms))
    assert all("." in d and "/" not in d for d in doms)


def test_covers_core_categories():
    nhoms = {b["nhom"] for b in load_brands()}
    assert {"ngan_hang", "vi_dien_tu", "tmdt"} <= nhoms


def test_key_brands_present():
    labels = brand_by_label()
    for must in ("vietcombank", "techcombank", "momo", "shopee", "vneid"):
        assert must in labels, f"thiếu brand quan trọng: {must}"


def test_official_domains_helper():
    doms = all_official_domains()
    assert "vietcombank.com.vn" in doms
    assert all(d == d.lower() for d in doms)


def test_typosquat_threshold_formula():
    # max(1, len//5)
    assert typosquat_threshold("acb") == 1          # 3//5 = 0 -> 1
    assert typosquat_threshold("momo") == 1         # 4//5 = 0 -> 1
    assert typosquat_threshold("vietcombank") == 2  # 11//5 = 2
    assert typosquat_threshold("thegioididong") == 2  # 13//5 = 2
