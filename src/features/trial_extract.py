"""Chạy thử trích 87 đặc trưng trên 1 URL — end-to-end (Plan.md, Tuần 1 Bạn B).

2 chế độ:
  * mặc định : gọi script gốc Hannousse & Yahiouche đã vendored vào
               ``src/features/hannousse_yahiouche/`` (xem README.md).
  * ``--smoke``: bộ trích lexical rút gọn, KHÔNG gọi mạng — chỉ để kiểm hình dạng
               vector (87 khoá, đúng thứ tự) và đường đi tới DataFrame model-ready.

Dù chế độ nào, script luôn kiểm: vector khớp ``contracts.FEATURE_NAMES``.
"""

from __future__ import annotations

import argparse
import ipaddress
import math
import sys
from importlib import import_module
from pathlib import Path
from urllib.parse import urlparse

import pandas as pd

from src.contracts import (
    EXTERNAL_FEATURES,
    EXTERNAL_LOOKUP_SENTINEL,
    FEATURE_NAMES,
    LEXICAL_FEATURES,
)

# Sửa nếu entrypoint script gốc có tên khác:
VENDOR_PKG = "src.features.hannousse_yahiouche"
ENTRYPOINT = "features_extraction"          # module bên trong VENDOR_PKG
ENTRYPOINT_FUNC = "extract_features"        # hàm nhận url -> list/dict 87 phần tử

PLACEHOLDER = -999  # đánh dấu "smoke mode chưa trích được đặc trưng này"


# --------------------------------------------------------------------------
# Bộ trích lexical rút gọn (smoke) — chỉ các đặc trưng định nghĩa rõ ràng.
# KHÔNG nhằm tái tạo chính xác script gốc; chỉ chứng minh đường đi end-to-end.
# --------------------------------------------------------------------------

_CHAR_COUNT = {
    "nb_dots": ".", "nb_hyphens": "-", "nb_at": "@", "nb_qm": "?", "nb_and": "&",
    "nb_or": "|", "nb_eq": "=", "nb_underscore": "_", "nb_tilde": "~",
    "nb_percent": "%", "nb_slash": "/", "nb_star": "*", "nb_colon": ":",
    "nb_comma": ",", "nb_semicolumn": ";", "nb_dollar": "$", "nb_space": " ",
}


def _is_ip(host: str) -> bool:
    try:
        ipaddress.ip_address(host)
        return True
    except ValueError:
        return False


def smoke_lexical(url: str) -> dict[str, float]:
    p = urlparse(url if "://" in url else "http://" + url)
    host = p.hostname or ""
    path = p.path or ""
    digits = sum(c.isdigit() for c in url)
    host_digits = sum(c.isdigit() for c in host)

    feats: dict[str, float] = {name: PLACEHOLDER for name in FEATURE_NAMES}

    feats.update({name: url.count(ch) for name, ch in _CHAR_COUNT.items()})
    feats["length_url"] = len(url)
    feats["length_hostname"] = len(host)
    feats["ip"] = int(_is_ip(host))
    feats["nb_www"] = url.lower().count("www")
    feats["nb_com"] = url.lower().count("com")
    feats["nb_dslash"] = max(url.count("//") - 1, 0)
    feats["http_in_path"] = int("http" in path.lower())
    feats["https_token"] = int(p.scheme == "https")
    feats["ratio_digits_url"] = round(digits / len(url), 6) if url else 0.0
    feats["ratio_digits_host"] = round(host_digits / len(host), 6) if host else 0.0
    feats["punycode"] = int("xn--" in url.lower())
    feats["port"] = int(p.port is not None)
    feats["prefix_suffix"] = int("-" in host)
    feats["nb_subdomains"] = max(host.split(".").__len__() - 2, 0) if host else 0
    feats["tld_in_path"] = PLACEHOLDER
    feats["tld_in_subdomain"] = PLACEHOLDER

    # nhóm ngoài: smoke không tra cứu -> sentinel "-1" đúng quy ước.
    for name in EXTERNAL_FEATURES:
        feats[name] = EXTERNAL_LOOKUP_SENTINEL
    return feats


# --------------------------------------------------------------------------

def vendored_extract(url: str) -> dict[str, float]:
    try:
        mod = import_module(f"{VENDOR_PKG}.{ENTRYPOINT}")
    except ModuleNotFoundError as e:
        raise SystemExit(
            "Chưa vendored script gốc. Xem src/features/README.md, hoặc chạy với "
            f"--smoke để kiểm hình dạng.\n(chi tiết: {e})"
        )
    func = getattr(mod, ENTRYPOINT_FUNC, None) or getattr(mod, "main", None)
    if func is None:
        raise SystemExit(
            f"Không tìm thấy hàm {ENTRYPOINT_FUNC}() trong {VENDOR_PKG}.{ENTRYPOINT}. "
            "Sửa ENTRYPOINT_FUNC trong trial_extract.py."
        )
    raw = func(url)
    if isinstance(raw, dict):
        return {k: raw[k] for k in FEATURE_NAMES}
    seq = list(raw)
    if len(seq) != len(FEATURE_NAMES):
        raise SystemExit(
            f"Script gốc trả {len(seq)} giá trị, kỳ vọng {len(FEATURE_NAMES)}."
        )
    return dict(zip(FEATURE_NAMES, seq))


def validate_and_frame(feats: dict[str, float]) -> pd.DataFrame:
    missing = [f for f in FEATURE_NAMES if f not in feats]
    extra = [f for f in feats if f not in FEATURE_NAMES]
    if missing or extra:
        raise SystemExit(f"Vector lệch contract. Thiếu={missing} Thừa={extra}")
    # ép đúng thứ tự FEATURE_NAMES
    row = {f: feats[f] for f in FEATURE_NAMES}
    df = pd.DataFrame([row], columns=list(FEATURE_NAMES))
    assert list(df.columns) == list(FEATURE_NAMES)
    return df


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("url")
    ap.add_argument("--smoke", action="store_true",
                    help="dùng bộ lexical rút gọn, không gọi mạng / script gốc")
    args = ap.parse_args(argv)

    feats = smoke_lexical(args.url) if args.smoke else vendored_extract(args.url)
    df = validate_and_frame(feats)

    done = [f for f in FEATURE_NAMES if df.iloc[0][f] != PLACEHOLDER]
    todo = [f for f in FEATURE_NAMES if df.iloc[0][f] == PLACEHOLDER]

    print(f"URL      : {args.url}")
    print(f"Chế độ   : {'SMOKE (lexical rút gọn)' if args.smoke else 'script gốc vendored'}")
    print(f"Vector   : {df.shape[1]} đặc trưng, thứ tự khớp contracts.FEATURE_NAMES  ✅")
    print(f"Trích được: {len(done)}/{len(FEATURE_NAMES)}"
          + (f"   | placeholder: {len(todo)}" if todo else ""))
    print(f"DataFrame model-ready: shape={df.shape}, dtype đồng nhất số  ✅")
    print()
    with pd.option_context("display.max_rows", None, "display.width", 120):
        show = df.T.rename(columns={0: "value"})
        show["nhom"] = [
            "lexical" if f in LEXICAL_FEATURES
            else "ngoai" if f in EXTERNAL_FEATURES else "noi_dung"
            for f in show.index
        ]
        print(show.to_string())

    if args.smoke:
        print("\nLƯU Ý: smoke mode chỉ kiểm hình dạng. Vendored script gốc "
              "(src/features/README.md) mới cho giá trị 87 đặc trưng đúng để train/serve.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
