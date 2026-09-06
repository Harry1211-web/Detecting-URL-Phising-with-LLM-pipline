"""Kiểm hợp đồng interface (src/contracts.py) — chạy: pytest -q"""

import csv
from pathlib import Path

from src.contracts import (
    CONTENT_FEATURES,
    EXTERNAL_FEATURES,
    FEATURE_NAMES,
    LEXICAL_FEATURES,
    OverrideResult,
    RF_LOW_RISK_THRESHOLD_DEFAULT,
    phan_vung,
)

ROOT = Path(__file__).resolve().parents[1]
CSV_PATH = ROOT / "Dataset" / "train" / "dataset_phishing.csv"


def _ov(flag) -> OverrideResult:
    return {"name": "x", "flag": flag, "reason": "", "latency_ms": 0.0}


def test_group_sizes():
    assert len(LEXICAL_FEATURES) == 56
    assert len(CONTENT_FEATURES) == 24
    assert len(EXTERNAL_FEATURES) == 7
    assert len(FEATURE_NAMES) == 87
    assert len(set(FEATURE_NAMES)) == 87


def test_feature_names_match_csv_header():
    with CSV_PATH.open(encoding="utf-8") as f:
        header = next(csv.reader(f))
    assert header[0] == "url" and header[-1] == "status"
    assert tuple(header[1:-1]) == FEATURE_NAMES


def test_groups_partition_feature_names():
    assert LEXICAL_FEATURES + CONTENT_FEATURES + EXTERNAL_FEATURES == FEATURE_NAMES
    assert set(LEXICAL_FEATURES).isdisjoint(CONTENT_FEATURES)
    assert set(LEXICAL_FEATURES).isdisjoint(EXTERNAL_FEATURES)
    assert set(CONTENT_FEATURES).isdisjoint(EXTERNAL_FEATURES)


def test_phan_vung_low_zone_needs_low_rf_and_all_false():
    lo = RF_LOW_RISK_THRESHOLD_DEFAULT - 0.05
    hi = RF_LOW_RISK_THRESHOLD_DEFAULT + 0.05
    assert phan_vung(lo, [_ov(False), _ov(False)]) == "vung_thap"
    assert phan_vung(lo, []) == "vung_thap"
    # RF cao -> nghi ngờ dù override sạch
    assert phan_vung(hi, [_ov(False)]) == "vung_nghi_ngo"
    # 1 cờ true -> nghi ngờ dù RF thấp
    assert phan_vung(lo, [_ov(True), _ov(False)]) == "vung_nghi_ngo"
    # "unknown" KHÔNG coi là an toàn
    assert phan_vung(lo, [_ov("unknown")]) == "vung_nghi_ngo"


def test_phan_vung_threshold_is_strict():
    assert phan_vung(RF_LOW_RISK_THRESHOLD_DEFAULT, []) == "vung_nghi_ngo"
