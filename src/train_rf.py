"""Train Random Forest v1 — Tuần 2, Bạn B (Plan.md mục 3 Tuần 2, mục 7).

Quy trình:
  1. Nạp dataset (schema kiểm bằng src.eda.load_dataset), bỏ 6 cột hằng số → 81 đặc trưng.
  2. Bỏ 1 dòng URL trùng (BAO_CAO_EDA.md) trước khi split để tránh rò rỉ train/test.
  3. Split stratified 80/20, random_state cố định.
  4. GridSearchCV + StratifiedKFold(k=5) trên tập train, đa metric
     (precision / recall / f1 / roc_auc), refit theo roc_auc.
  5. Số liệu k-fold: mean ± std của 4 metric ở cấu hình tốt nhất.
  6. Đánh giá mô hình tốt nhất trên tập test giữ lại (chưa đụng tới).
  7. Xuất feature_importances_ (đầu vào cho feature selection Tuần 3).
  8. Lưu model → models/rf_v1.joblib; bảng + biểu đồ → reports/rf_v1/.

Chạy:  python -m src.train_rf            (grid rút gọn, ~vài phút CPU)
       python -m src.train_rf --full    (grid rộng hơn, lâu hơn)
Notebook trình bày: notebooks/02_train_rf_v1.ipynb
"""

from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from joblib import dump
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import (
    ConfusionMatrixDisplay,
    RocCurveDisplay,
    classification_report,
    roc_auc_score,
)
from sklearn.model_selection import GridSearchCV, StratifiedKFold, train_test_split

from src.contracts import LABEL_MAP, MODEL_FEATURES_V1, TARGET_COLUMN
from src.eda import load_dataset

ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "reports" / "rf_v1"
MODEL_PATH = ROOT / "models" / "rf_v1.joblib"

RANDOM_STATE = 42
TEST_SIZE = 0.20
CV_FOLDS = 5
SCORING = ("precision", "recall", "f1", "roc_auc")
REFIT = "roc_auc"

PARAM_GRID_QUICK = {
    "n_estimators": [200, 400],
    "max_depth": [None, 30],
    "min_samples_leaf": [1, 2],
    "max_features": ["sqrt", 0.5],
}
PARAM_GRID_FULL = {
    "n_estimators": [200, 400, 600],
    "max_depth": [None, 20, 30, 50],
    "min_samples_leaf": [1, 2, 4],
    "max_features": ["sqrt", 0.3, 0.5],
}


def build_xy(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.Series]:
    """81 đặc trưng (đã bỏ 6 cột hằng số) + nhãn nhị phân, bỏ URL trùng."""
    n_before = len(df)
    df = df.drop_duplicates(subset="url", keep="first").reset_index(drop=True)
    n_dropped = n_before - len(df)
    if n_dropped:
        print(f"Đã bỏ {n_dropped} dòng URL trùng ({n_before} → {len(df)}).")
    X = df[list(MODEL_FEATURES_V1)].copy()
    y = df[TARGET_COLUMN].map(LABEL_MAP).astype(int)
    return X, y


def run(full_grid: bool = False, out_dir: Path = OUT_DIR) -> dict:
    out_dir.mkdir(parents=True, exist_ok=True)
    t0 = time.perf_counter()

    df = load_dataset()
    X, y = build_xy(df)
    X_tr, X_te, y_tr, y_te = train_test_split(
        X, y, test_size=TEST_SIZE, stratify=y, random_state=RANDOM_STATE
    )
    print(f"Train {len(X_tr)} / Test {len(X_te)} | {X.shape[1]} đặc trưng")

    grid = PARAM_GRID_FULL if full_grid else PARAM_GRID_QUICK
    n_comb = int(np.prod([len(v) for v in grid.values()]))
    print(f"GridSearchCV: {n_comb} cấu hình × {CV_FOLDS} fold = {n_comb * CV_FOLDS} lần fit")

    cv = StratifiedKFold(n_splits=CV_FOLDS, shuffle=True, random_state=RANDOM_STATE)
    gs = GridSearchCV(
        RandomForestClassifier(random_state=RANDOM_STATE, n_jobs=-1),
        param_grid=grid,
        scoring=list(SCORING),
        refit=REFIT,
        cv=cv,
        n_jobs=-1,
        return_train_score=False,
        verbose=1,
    )
    gs.fit(X_tr, y_tr)

    best_i = gs.best_index_
    cvr = gs.cv_results_
    kfold_stats = {
        m: {
            "mean": round(float(cvr[f"mean_test_{m}"][best_i]), 4),
            "std": round(float(cvr[f"std_test_{m}"][best_i]), 4),
        }
        for m in SCORING
    }

    # --- đánh giá trên test giữ lại ---
    best = gs.best_estimator_
    y_pred = best.predict(X_te)
    y_proba = best.predict_proba(X_te)[:, 1]
    report = classification_report(y_te, y_pred, output_dict=True,
                                   target_names=["legitimate", "phishing"])
    test_metrics = {
        "precision_phishing": round(report["phishing"]["precision"], 4),
        "recall_phishing": round(report["phishing"]["recall"], 4),
        "f1_phishing": round(report["phishing"]["f1-score"], 4),
        "accuracy": round(report["accuracy"], 4),
        "roc_auc": round(float(roc_auc_score(y_te, y_proba)), 4),
    }

    # --- feature importances (đầu vào feature selection Tuần 3) ---
    imp = (pd.Series(best.feature_importances_, index=list(MODEL_FEATURES_V1))
           .sort_values(ascending=False))
    imp.index.name = "dac_trung"
    imp.name = "importance"
    imp.to_csv(out_dir / "feature_importances.csv", encoding="utf-8-sig")
    pd.DataFrame(cvr).to_csv(out_dir / "cv_results.csv", index=False, encoding="utf-8-sig")

    elapsed = round(time.perf_counter() - t0, 1)
    summary = {
        "n_train": int(len(X_tr)), "n_test": int(len(X_te)),
        "n_features_in": X.shape[1],
        "grid": "full" if full_grid else "quick",
        "best_params": gs.best_params_,
        "kfold_mean_std": kfold_stats,
        "test_metrics": test_metrics,
        "top15_importances": imp.head(15).round(4).to_dict(),
        "cum_importance_top30": round(float(imp.head(30).sum()), 4),
        "cum_importance_top42": round(float(imp.head(42).sum()), 4),
        "elapsed_sec": elapsed,
    }
    (out_dir / "summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")

    MODEL_PATH.parent.mkdir(parents=True, exist_ok=True)
    dump({"model": best, "features": list(MODEL_FEATURES_V1),
          "label_map": LABEL_MAP, "trained_at": time.strftime("%Y-%m-%d %H:%M"),
          "cv_roc_auc": kfold_stats["roc_auc"]}, MODEL_PATH)

    _plots(best, X_te, y_te, imp, out_dir)
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return summary


def _plots(model, X_te, y_te, imp: pd.Series, out_dir: Path) -> None:
    fig, ax = plt.subplots(figsize=(4.2, 3.8))
    ConfusionMatrixDisplay.from_estimator(
        model, X_te, y_te, display_labels=["legit", "phish"],
        cmap="Blues", colorbar=False, ax=ax)
    ax.set_title("RF v1 — ma trận nhầm lẫn (test)")
    fig.tight_layout(); fig.savefig(out_dir / "fig_confusion.png", dpi=120); plt.close(fig)

    fig, ax = plt.subplots(figsize=(4.6, 4))
    RocCurveDisplay.from_estimator(model, X_te, y_te, ax=ax)
    ax.set_title("RF v1 — ROC (test)"); ax.plot([0, 1], [0, 1], "--", c="grey", lw=0.8)
    fig.tight_layout(); fig.savefig(out_dir / "fig_roc.png", dpi=120); plt.close(fig)

    top = imp.head(25).iloc[::-1]
    fig, ax = plt.subplots(figsize=(6, 7))
    ax.barh(top.index, top.values, color="#3B6C9E")
    ax.set_title("RF v1 — 25 đặc trưng quan trọng nhất")
    ax.set_xlabel("feature_importances_")
    fig.tight_layout(); fig.savefig(out_dir / "fig_importances.png", dpi=120); plt.close(fig)


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--full", action="store_true", help="grid rộng hơn (lâu hơn)")
    args = ap.parse_args()
    run(full_grid=args.full)
