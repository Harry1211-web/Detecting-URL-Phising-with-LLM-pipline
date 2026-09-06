"""EDA cho dataset_phishing.csv — Tuần 1, Bạn B (Plan.md, mục 3 Tuần 1).

Mục tiêu:
  1. Kiểm tra cân bằng nhãn (kỳ vọng 50/50).
  2. Phân phối đặc trưng + phát hiện cột hằng số / gần hằng số.
  3. Xác nhận 3 cột hằng số = 0: sfh, ratio_intErrors, ratio_intRedirection.
  4. Xác nhận google_index tương quan ~0.73 với nhãn.
  5. Kiểm tra thiếu dữ liệu + giá trị sentinel (-1) của nhóm đặc trưng ngoài.

Chạy trực tiếp:  python -m src.eda
Sinh output vào: reports/eda/  (bảng .csv + .json + biểu đồ .png)
Notebook trình bày: notebooks/01_eda_dataset_phishing.ipynb (gọi lại các hàm ở đây).
"""

from __future__ import annotations

import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")  # không cần màn hình khi chạy script
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from src.contracts import (
    CONSTANT_FEATURES_CLAUDE_MD,
    EXTERNAL_FEATURES,
    FEATURE_NAMES,
    LABEL_MAP,
    STRONGEST_SIGNAL_FEATURE,
    TARGET_COLUMN,
)

ROOT = Path(__file__).resolve().parents[1]
DATA_PATH = ROOT / "Dataset" / "train" / "dataset_phishing.csv"
OUT_DIR = ROOT / "reports" / "eda"


def load_dataset(path: Path = DATA_PATH) -> pd.DataFrame:
    """Nạp CSV, kiểm tra schema khớp hợp đồng contracts.FEATURE_NAMES."""
    df = pd.read_csv(path)
    expected = ["url", *FEATURE_NAMES, TARGET_COLUMN]
    if list(df.columns) != expected:
        thieu = set(expected) - set(df.columns)
        thua = set(df.columns) - set(expected)
        raise ValueError(
            f"Schema CSV không khớp contracts.FEATURE_NAMES. "
            f"Thiếu={sorted(thieu)} Thừa={sorted(thua)}"
        )
    return df


def label_balance(df: pd.DataFrame) -> pd.DataFrame:
    counts = df[TARGET_COLUMN].value_counts()
    out = pd.DataFrame({
        "so_luong": counts,
        "ty_le": (counts / len(df)).round(4),
    })
    out.index.name = "nhan"
    return out


def constant_check(df: pd.DataFrame) -> pd.DataFrame:
    """Thống kê phương sai + số giá trị duy nhất cho 87 đặc trưng."""
    X = df[list(FEATURE_NAMES)]
    rows = []
    for col in FEATURE_NAMES:
        s = X[col]
        rows.append({
            "dac_trung": col,
            "n_unique": int(s.nunique(dropna=False)),
            "min": float(s.min()),
            "max": float(s.max()),
            "std": float(s.std()),
            "gia_tri_duy_nhat": (
                repr(s.iloc[0]) if s.nunique(dropna=False) == 1 else ""
            ),
        })
    res = pd.DataFrame(rows).sort_values("std").reset_index(drop=True)
    return res


def target_correlation(df: pd.DataFrame) -> pd.Series:
    """Tương quan Pearson |r| của từng đặc trưng với nhãn nhị phân.

    Cột hằng số (std = 0) cho r không xác định -> gán 0.0 thay vì NaN.
    """
    y = df[TARGET_COLUMN].map(LABEL_MAP)
    X = df[list(FEATURE_NAMES)]
    with np.errstate(invalid="ignore", divide="ignore"):
        corr = X.corrwith(y)
    corr = corr.fillna(0.0).sort_values(key=np.abs, ascending=False)
    corr.index.name = "dac_trung"
    corr.name = "pearson_r"
    return corr


def missing_and_sentinel(df: pd.DataFrame) -> pd.DataFrame:
    """NaN + tỉ lệ giá trị -1 (sentinel "không tra được") ở nhóm đặc trưng ngoài."""
    rows = []
    for col in FEATURE_NAMES:
        s = df[col]
        rows.append({
            "dac_trung": col,
            "n_nan": int(s.isna().sum()),
            "ty_le_am_1": float((s == -1).mean()),
            "nhom_ngoai": col in EXTERNAL_FEATURES,
        })
    return pd.DataFrame(rows)


# --------------------------- biểu đồ ---------------------------------------

def plot_label_balance(df: pd.DataFrame, out: Path) -> None:
    bal = df[TARGET_COLUMN].value_counts()
    fig, ax = plt.subplots(figsize=(4, 3.2))
    ax.bar(bal.index.astype(str), bal.values, color=["#4C9F70", "#D1495B"])
    ax.set_title("Cân bằng nhãn — dataset_phishing.csv")
    ax.set_ylabel("Số dòng")
    for i, v in enumerate(bal.values):
        ax.text(i, v, f"{v}\n{v / len(df):.1%}", ha="center", va="bottom")
    ax.set_ylim(0, bal.max() * 1.18)
    fig.tight_layout()
    fig.savefig(out, dpi=120)
    plt.close(fig)


def plot_top_correlations(corr: pd.Series, out: Path, k: int = 20) -> None:
    top = corr.head(k).iloc[::-1]
    fig, ax = plt.subplots(figsize=(6, 6))
    colors = ["#D1495B" if v > 0 else "#4C9F70" for v in top.values]
    ax.barh(top.index, top.values, color=colors)
    ax.axvline(0, color="black", lw=0.8)
    ax.set_title(f"Top {k} đặc trưng theo |tương quan| với nhãn phishing")
    ax.set_xlabel("Pearson r (đỏ: cao khi phishing, xanh: cao khi hợp pháp)")
    fig.tight_layout()
    fig.savefig(out, dpi=120)
    plt.close(fig)


def plot_feature_distributions(df: pd.DataFrame, features: list[str],
                               out: Path) -> None:
    y = df[TARGET_COLUMN]
    n = len(features)
    ncol = 3
    nrow = (n + ncol - 1) // ncol
    fig, axes = plt.subplots(nrow, ncol, figsize=(4 * ncol, 3 * nrow))
    for ax, col in zip(axes.flat, features):
        for lab, c in (("legitimate", "#4C9F70"), ("phishing", "#D1495B")):
            vals = df.loc[y == lab, col].to_numpy()
            vals = vals[np.isfinite(vals)]
            ax.hist(vals, bins=40, alpha=0.55, label=lab, color=c, density=True)
        ax.set_title(col, fontsize=9)
        ax.tick_params(labelsize=7)
    for ax in axes.flat[n:]:
        ax.axis("off")
    axes.flat[0].legend(fontsize=8)
    fig.suptitle("Phân phối đặc trưng theo nhãn (chuẩn hoá mật độ)", y=1.002)
    fig.tight_layout()
    fig.savefig(out, dpi=120)
    plt.close(fig)


# --------------------------- chạy toàn bộ --------------------------------

def run(out_dir: Path = OUT_DIR) -> dict:
    out_dir.mkdir(parents=True, exist_ok=True)
    df = load_dataset()

    bal = label_balance(df)
    const = constant_check(df)
    corr = target_correlation(df)
    miss = missing_and_sentinel(df)

    bal.to_csv(out_dir / "label_balance.csv", encoding="utf-8-sig")
    const.to_csv(out_dir / "constant_check.csv", index=False, encoding="utf-8-sig")
    corr.to_csv(out_dir / "target_correlation.csv", encoding="utf-8-sig")
    miss.to_csv(out_dir / "missing_sentinel.csv", index=False, encoding="utf-8-sig")

    zero_const = const[(const["std"] == 0) & (const["max"] == 0)
                       & (const["min"] == 0)]["dac_trung"].tolist()
    near_const = const[const["std"] < 1e-6]["dac_trung"].tolist()
    claude_md_set = set(CONSTANT_FEATURES_CLAUDE_MD)
    extra_zero = sorted(set(zero_const) - claude_md_set)

    summary = {
        "n_rows": int(len(df)),
        "n_features": len(FEATURE_NAMES),
        "label_counts": df[TARGET_COLUMN].value_counts().to_dict(),
        "label_ratio": (df[TARGET_COLUMN].value_counts() / len(df)).round(4).to_dict(),
        "duplicated_rows": int(df.duplicated().sum()),
        "duplicated_urls": int(df["url"].duplicated().sum()),
        "constant_zero_features": sorted(zero_const),
        "near_constant_features(std<1e-6)": sorted(near_const),
        "expected_constant(CLAUDE.md)": list(CONSTANT_FEATURES_CLAUDE_MD),
        "constant_check_matches_claude_md": sorted(zero_const)
            == sorted(CONSTANT_FEATURES_CLAUDE_MD),
        "extra_zero_features_not_in_claude_md": extra_zero,
        f"corr_{STRONGEST_SIGNAL_FEATURE}": round(float(corr[STRONGEST_SIGNAL_FEATURE]), 4),
        "top10_abs_corr": corr.head(10).round(4).to_dict(),
        "total_nan": int(df[list(FEATURE_NAMES)].isna().sum().sum()),
        "external_features_neg1_ratio": {
            c: round(float((df[c] == -1).mean()), 4) for c in EXTERNAL_FEATURES
        },
    }
    (out_dir / "summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    plot_label_balance(df, out_dir / "fig_label_balance.png")
    plot_top_correlations(corr, out_dir / "fig_top_correlations.png")
    plot_feature_distributions(
        df,
        ["length_url", "nb_dots", "nb_hyphens", "ratio_digits_url",
         "phish_hints", "nb_hyperlinks", "domain_age",
         STRONGEST_SIGNAL_FEATURE, "page_rank"],
        out_dir / "fig_feature_distributions.png",
    )
    return summary


if __name__ == "__main__":
    s = run()
    print(json.dumps(s, ensure_ascii=False, indent=2))
