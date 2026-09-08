"""Train RF bản cuối + biến thể "chỉ đặc trưng nhanh" + so XGBoost — Tuần 3, Bạn B
(Plan.md mục 2 & mục 3 Tuần 3).

3 mô hình, CÙNG split (`random_state=42`, 80/20) và CÙNG GridSearchCV
`StratifiedKFold(k=5)`, refit theo roc_auc:

  rf_final  — RandomForest trên contracts.MODEL_FEATURES_FINAL (30 đặc trưng
              sau feature selection).
  rf_fast   — RandomForest trên contracts.FAST_FEATURES_FINAL (25 đặc trưng,
              bỏ 5 đặc trưng tra cứu ngoài). Đo mô hình mất bao nhiêu điểm khi
              KHÔNG có tra cứu ngoài — nhánh fallback lúc RDAP/WHOIS/Google
              timeout (rủi ro #1 trong reports/rf_v1/BAO_CAO_RF_V1.md).
  xgb_final — XGBoost trên MODEL_FEATURES_FINAL — so với rf_final (Plan.md
              "so sánh XGBoost nếu kịp").

Output → reports/rf_final/ (bảng so sánh + biểu đồ) và
         models/rf_final.joblib, models/rf_fast.joblib, models/xgb_final.joblib.

Chạy:  python -m src.train_rf_final           (grid rút gọn)
       python -m src.train_rf_final --full    (grid rộng hơn — chỉ cho RF)
Notebook trình bày: notebooks/03_feature_selection_rf_final.ipynb
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
from sklearn.metrics import RocCurveDisplay, classification_report, roc_auc_score
from sklearn.model_selection import GridSearchCV, StratifiedKFold, train_test_split

from src.contracts import (
    EXTERNAL_FEATURES,
    FAST_FEATURES_FINAL,
    LABEL_MAP,
    MODEL_FEATURES_FINAL,
    TARGET_COLUMN,
)
from src.eda import load_dataset
from src.train_rf import (
    CV_FOLDS,
    PARAM_GRID_FULL,
    PARAM_GRID_QUICK,
    RANDOM_STATE,
    REFIT,
    SCORING,
    TEST_SIZE,
    build_xy,
)

ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "reports" / "rf_final"
MODELS_DIR = ROOT / "models"
RF_V1_SUMMARY = ROOT / "reports" / "rf_v1" / "summary.json"

# Grid XGBoost (rút gọn, 16 cấu hình) — tương đương độ rộng với PARAM_GRID_QUICK của RF.
XGB_GRID_QUICK = {
    "n_estimators": [300, 600],
    "max_depth": [4, 6],
    "learning_rate": [0.1, 0.3],
    "subsample": [0.8, 1.0],
}


def _kfold_stats(cv_results: dict, best_i: int) -> dict:
    return {
        m: {
            "mean": round(float(cv_results[f"mean_test_{m}"][best_i]), 4),
            "std": round(float(cv_results[f"std_test_{m}"][best_i]), 4),
        }
        for m in SCORING
    }


def _test_metrics(model, X_te, y_te) -> dict:
    y_pred = model.predict(X_te)
    y_proba = model.predict_proba(X_te)[:, 1]
    rep = classification_report(y_te, y_pred, output_dict=True,
                                target_names=["legitimate", "phishing"])
    return {
        "precision_phishing": round(rep["phishing"]["precision"], 4),
        "recall_phishing": round(rep["phishing"]["recall"], 4),
        "f1_phishing": round(rep["phishing"]["f1-score"], 4),
        "accuracy": round(rep["accuracy"], 4),
        "roc_auc": round(float(roc_auc_score(y_te, y_proba)), 4),
    }


def _fit_grid(estimator, grid, X_tr, y_tr) -> GridSearchCV:
    cv = StratifiedKFold(n_splits=CV_FOLDS, shuffle=True, random_state=RANDOM_STATE)
    gs = GridSearchCV(estimator, param_grid=grid, scoring=list(SCORING),
                      refit=REFIT, cv=cv, n_jobs=-1, verbose=1)
    gs.fit(X_tr, y_tr)
    return gs


def _train_one(name: str, estimator, grid: dict, feats: tuple[str, ...],
               X_tr, X_te, y_tr, y_te) -> tuple[dict, object, pd.Series]:
    t0 = time.perf_counter()
    gs = _fit_grid(estimator, grid, X_tr[list(feats)], y_tr)
    best = gs.best_estimator_
    imp = (pd.Series(best.feature_importances_, index=list(feats))
           .sort_values(ascending=False))
    info = {
        "n_dac_trung": len(feats),
        "best_params": gs.best_params_,
        "kfold_mean_std": _kfold_stats(gs.cv_results_, gs.best_index_),
        "test_metrics": _test_metrics(best, X_te[list(feats)], y_te),
        "elapsed_sec": round(time.perf_counter() - t0, 1),
    }
    print(f"[{name}] {len(feats)} đặc trưng | "
          f"k-fold ROC-AUC {info['kfold_mean_std']['roc_auc']['mean']} | "
          f"test ROC-AUC {info['test_metrics']['roc_auc']} | {info['elapsed_sec']}s")
    return info, best, imp


def run(full_grid: bool = False, out_dir: Path = OUT_DIR) -> dict:
    out_dir.mkdir(parents=True, exist_ok=True)
    MODELS_DIR.mkdir(parents=True, exist_ok=True)

    df = load_dataset()
    X, y = build_xy(df)
    X_tr, X_te, y_tr, y_te = train_test_split(
        X, y, test_size=TEST_SIZE, stratify=y, random_state=RANDOM_STATE
    )
    print(f"Train {len(X_tr)} / Test {len(X_te)}")

    rf_grid = PARAM_GRID_FULL if full_grid else PARAM_GRID_QUICK
    results: dict[str, dict] = {}
    importances: dict[str, pd.Series] = {}

    # 1) RF bản cuối — 30 đặc trưng
    info, rf_final, imp = _train_one(
        "rf_final",
        RandomForestClassifier(random_state=RANDOM_STATE, n_jobs=-1),
        rf_grid, MODEL_FEATURES_FINAL, X_tr, X_te, y_tr, y_te)
    results["rf_final"], importances["rf_final"] = info, imp
    dump({"model": rf_final, "features": list(MODEL_FEATURES_FINAL),
          "label_map": LABEL_MAP, "trained_at": time.strftime("%Y-%m-%d %H:%M"),
          "cv_roc_auc": info["kfold_mean_std"]["roc_auc"]},
         MODELS_DIR / "rf_final.joblib")

    # 2) RF "chỉ đặc trưng nhanh" — 25 đặc trưng (không tra cứu ngoài)
    info, rf_fast, imp = _train_one(
        "rf_fast",
        RandomForestClassifier(random_state=RANDOM_STATE, n_jobs=-1),
        rf_grid, FAST_FEATURES_FINAL, X_tr, X_te, y_tr, y_te)
    results["rf_fast"], importances["rf_fast"] = info, imp
    dump({"model": rf_fast, "features": list(FAST_FEATURES_FINAL),
          "label_map": LABEL_MAP, "trained_at": time.strftime("%Y-%m-%d %H:%M"),
          "cv_roc_auc": info["kfold_mean_std"]["roc_auc"]},
         MODELS_DIR / "rf_fast.joblib")

    # 3) XGBoost trên 30 đặc trưng — so với rf_final
    try:
        from xgboost import XGBClassifier
        xgb = XGBClassifier(tree_method="hist", eval_metric="logloss",
                            random_state=RANDOM_STATE, n_jobs=-1)
        info, xgb_final, imp = _train_one(
            "xgb_final", xgb, XGB_GRID_QUICK, MODEL_FEATURES_FINAL,
            X_tr, X_te, y_tr, y_te)
        results["xgb_final"], importances["xgb_final"] = info, imp
        dump({"model": xgb_final, "features": list(MODEL_FEATURES_FINAL),
              "label_map": LABEL_MAP, "trained_at": time.strftime("%Y-%m-%d %H:%M"),
              "cv_roc_auc": info["kfold_mean_std"]["roc_auc"]},
             MODELS_DIR / "xgb_final.joblib")
    except ImportError:
        results["xgb_final"] = {"skipped": "xgboost chưa cài (pip install xgboost)"}
        print("[xgb_final] BỎ QUA — xgboost chưa cài.")

    # --- mốc tham chiếu: RF v1 (81 đặc trưng, Tuần 2) ---
    rf_v1 = json.loads(RF_V1_SUMMARY.read_text(encoding="utf-8"))
    results["rf_v1_81_thamchieu"] = {
        "n_dac_trung": rf_v1["n_features_in"],
        "kfold_mean_std": rf_v1["kfold_mean_std"],
        "test_metrics": rf_v1["test_metrics"],
    }

    # --- bảng so sánh ---
    cmp_rows = []
    for name in ("rf_v1_81_thamchieu", "rf_final", "rf_fast", "xgb_final"):
        r = results.get(name, {})
        if "kfold_mean_std" not in r:
            continue
        cmp_rows.append({
            "mo_hinh": name,
            "n_dac_trung": r["n_dac_trung"],
            "kfold_roc_auc": r["kfold_mean_std"]["roc_auc"]["mean"],
            "kfold_f1": r["kfold_mean_std"]["f1"]["mean"],
            "test_roc_auc": r["test_metrics"]["roc_auc"],
            "test_f1_phishing": r["test_metrics"]["f1_phishing"],
            "test_accuracy": r["test_metrics"]["accuracy"],
        })
    cmp = pd.DataFrame(cmp_rows)
    cmp.to_csv(out_dir / "so_sanh_mo_hinh.csv", index=False, encoding="utf-8-sig")

    for name, imp in importances.items():
        imp.rename_axis("dac_trung").rename("importance").to_csv(
            out_dir / f"importances_{name}.csv", encoding="utf-8-sig")

    summary = {
        "features_final": list(MODEL_FEATURES_FINAL),
        "features_fast": list(FAST_FEATURES_FINAL),
        "dac_trung_ngoai_bo_o_fast": [f for f in MODEL_FEATURES_FINAL
                                      if f in set(EXTERNAL_FEATURES)],
        "grid_rf": "full" if full_grid else "quick",
        "ket_qua": results,
        "bang_so_sanh": cmp_rows,
    }
    (out_dir / "summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")

    _plots(rf_final, rf_fast, X_te, y_te, importances["rf_final"], cmp, out_dir)
    print("\n" + cmp.to_string(index=False))
    return summary


def _plots(rf_final, rf_fast, X_te, y_te, imp_final: pd.Series,
           cmp: pd.DataFrame, out_dir: Path) -> None:
    # ROC rf_final vs rf_fast trên cùng tập test
    fig, ax = plt.subplots(figsize=(4.8, 4.2))
    RocCurveDisplay.from_estimator(
        rf_final, X_te[list(MODEL_FEATURES_FINAL)], y_te, ax=ax, name="rf_final (30)")
    RocCurveDisplay.from_estimator(
        rf_fast, X_te[list(FAST_FEATURES_FINAL)], y_te, ax=ax, name="rf_fast (25)")
    ax.plot([0, 1], [0, 1], "--", c="grey", lw=0.8)
    ax.set_title("RF bản cuối vs bản 'chỉ đặc trưng nhanh' — ROC (test)")
    fig.tight_layout(); fig.savefig(out_dir / "fig_final_vs_fast_roc.png", dpi=120)
    plt.close(fig)

    # importance rf_final
    top = imp_final.iloc[::-1]
    fig, ax = plt.subplots(figsize=(6, 8))
    colors = ["#B5651D" if f in set(EXTERNAL_FEATURES) else "#3B6C9E"
              for f in top.index]
    ax.barh(top.index, top.values, color=colors)
    ax.set_title("rf_final — importance 30 đặc trưng (cam = tra cứu ngoài)")
    ax.set_xlabel("feature_importances_")
    fig.tight_layout(); fig.savefig(out_dir / "fig_final_importances.png", dpi=120)
    plt.close(fig)

    # so sánh mô hình
    fig, ax = plt.subplots(figsize=(6, 3.6))
    xlab = list(cmp["mo_hinh"])
    xi = np.arange(len(xlab))
    ax.bar(xi - 0.2, cmp["test_roc_auc"], width=0.4, label="test ROC-AUC", color="#3B6C9E")
    ax.bar(xi + 0.2, cmp["test_f1_phishing"], width=0.4, label="test F1 (phishing)", color="#8FB339")
    ax.set_xticks(xi); ax.set_xticklabels(xlab, rotation=20, ha="right")
    ax.set_ylim(0.9, 1.0); ax.legend(); ax.set_title("So sánh mô hình (tập test giữ lại)")
    fig.tight_layout(); fig.savefig(out_dir / "fig_so_sanh_mo_hinh.png", dpi=120)
    plt.close(fig)


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--full", action="store_true", help="grid RF rộng hơn (lâu hơn)")
    args = ap.parse_args()
    run(full_grid=args.full)
