"""Kiểm danh sách thương hiệu VN (dataset/brands/vn_brand_domains.csv) + loader.

Chỉ kiểm CẤU TRÚC + công thức ngưỡng — không xác minh domain có thật/đang sống
(việc rà tay theo cột `verified`, xem dataset/brands/README.md).
"""

from src.override.brands import (
    all_official_domains,
    brand_by_label,
    load_brands,
    typosquat_threshold,
    verified_official_domains,
)


def test_load_and_min_count():
    brands = load_brands()
    assert len(brands) >= 40, "Plan.md yêu cầu ~40-60 thương hiệu"


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
    assert {"ngan_hang", "vi_dien_tu", "thuong_mai_dien_tu"} <= nhoms


def test_key_brands_present():
    labels = brand_by_label()
    for must in ("vietcombank", "techcombank", "momo", "shopee", "vneid"):
        assert must in labels, f"thiếu brand quan trọng: {must}"


def test_lienvietpostbank_da_doi_thanh_lpbank():
    labels = brand_by_label()
    assert "lpbank" in labels
    assert "lienvietpostbank" not in labels  # tên cũ, đã thay


def test_official_domains_helper():
    doms = all_official_domains()
    assert "vietcombank.com.vn" in doms
    assert all(d == d.lower() for d in doms)


def test_verified_subset_of_all():
    assert verified_official_domains() <= all_official_domains()
    # sacombank + lpbank đã đối chiếu SBV trong phiên rà 2026-09-10
    assert "sacombank.com.vn" in verified_official_domains()
    assert "lpbank.com.vn" in verified_official_domains()


def test_verified_values_valid():
    assert all(b["verified"] in {"da_xac_minh", "chua_xac_minh"} for b in load_brands())


def test_typosquat_threshold_phishmatch_rule():
    # PhishMatch: <=10 ký tự -> 1, >10 -> 2 (không loại nhãn ngắn)
    assert typosquat_threshold("acb") == 1          # 3
    assert typosquat_threshold("momo") == 1         # 4
    assert typosquat_threshold("vietcombank") == 2  # 11
    assert typosquat_threshold("thegioididong") == 2  # 13
    assert typosquat_threshold("shopeepay") == 1    # 9
    assert typosquat_threshold("viettelmoney") == 2  # 12
