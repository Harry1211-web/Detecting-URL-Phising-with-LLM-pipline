"""Feature selection — Tuần 3, Bạn B (Plan.md mục 3 Tuần 3, mục 2).

Ý tưởng: lấy thứ hạng ``feature_importances_`` của RF v1 (81 đặc trưng, Tuần 2)
làm bộ lọc, thử nhiều mốc cắt, so ROC-AUC 5-fold trên tập TRAIN (đúng split
``random_state=42`` với RF v1) rồi chọn tập NHỎ NHẤT trong khoảng ~30–42 đặc
trưng mà ROC-AUC còn nằm trong dung sai so với mốc dùng cả 81 đặc trưng.

Không đụng tập test — tập test để dành cho ``src.train_rf_final`` đánh giá bản cuối.

Kết quả:
  reports/rf_final/feature_selection.csv   — bảng so sánh mọi mốc cắt
  reports/rf_final/selected_features.json  — tập được chọn (máy đọc)
  + in ra đoạn dán sẵn cho src/contracts.py::MODEL_FEATURES_FINAL

Chạy:  python -m src.feature_selection
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import StratifiedKFold, cross_validate, train_test_split

from src.contracts import EXTERNAL_FEATURES, FEATURE_NAMES, MODEL_FEATURES_V1
from src.eda import load_dataset
from src.train_rf import CV_FOLDS, RANDOM_STATE, TEST_SIZE, build_xy

ROOT = Path(__file__).resolve().parents[1]
V1_IMPORTANCES = ROOT / "reports" / "rf_v1" / "feature_importances.csv"
OUT_DIR = ROOT / "reports" / "rf_final"

# Cấu hình RF tốt nhất của RF v1 (reports/rf_v1/summary.json) — cố định khi so mốc cắt
# để chỉ có DANH SÁCH đặc trưng thay đổi, không lẫn ảnh hưởng của hyper-param.
RF_BEST_V1 = dict(
    n_estimators=400, max_depth=None, min_samples_leaf=1,
    max_features="sqrt", random_state=RANDOM_STATE, n_jobs=-1,
)

SCORING = ("roc_auc", "f1", "precision", "recall")
TOL_ROC_AUC = 0.002           # tập rút gọn "không kém" nếu ROC-AUC >= mốc-81 - dung sai
MIN_FEATURES, MAX_FEATURES = 30, 42   # Plan.md: "~30–42 đặc trưng"


def _load_ranking() -> pd.Series:
    """Series importance giảm dần, index = tên đặc trưng (81 dòng của RF v1)."""
    s = pd.read_csv(V1_IMPORTANCES).set_index("dac_trung")["importance"]
    if set(s.index) != set(MODEL_FEATURES_V1):
        raise ValueError(
            "feature_importances.csv lệch MODEL_FEATURES_V1 — chạy lại "
            "`python -m src.train_rf` trước."
        )
    return s.sort_values(ascending=False)


def _candidate_sets(ranking: pd.Series) -> dict[str, list[str]]:
    """Các mốc cắt ứng viên: theo top-k, theo ngưỡng importance, theo tổng tích luỹ."""
    order = list(ranking.index)
    cands: dict[str, list[str]] = {}
    for k in (20, 25, 30, 33, 36, 39, 42, 50, 81):
        cands[f"top_{k}"] = order[:k]
    cands["imp>=0.005"] = ranking[ranking >= 0.005].index.tolist()
    cands["imp>=0.003"] = ranking[ranking >= 0.003].index.tolist()
    cum = ranking.cumsum()
    for tgt in (0.98, 0.99):
        n = int((cum < tgt).sum()) + 1
        cands[f"cum>={tgt}"] = order[:n]
    return cands


def _score(X: pd.DataFrame, y: pd.Series, feats: list[str],
           cv: StratifiedKFold) -> dict[str, tuple[float, float]]:
    rf = RandomForestClassifier(**RF_BEST_V1)
    res = cross_validate(rf, X[feats], y, cv=cv, scoring=list(SCORING), n_jobs=-1)
    return {m: (float(res[f"test_{m}"].mean()), float(res[f"test_{m}"].std()))
            for m in SCORING}


def _ordered(feats: set[str]) -> tuple[str, ...]:
    """Giữ đúng thứ tự FEATURE_NAMES cho danh sách đặc trưng (ổn định, dễ so)."""
    return tuple(f for f in FEATURE_NAMES if f in feats)


def run(out_dir: Path = OUT_DIR) -> dict:
    out_dir.mkdir(parents=True, exist_ok=True)
    ranking = _load_ranking()

    df = load_dataset()
    X, y = build_xy(df)
    X_tr, _X_te, y_tr, _y_te = train_test_split(
        X, y, test_size=TEST_SIZE, stratify=y, random_state=RANDOM_STATE
    )
    cv = StratifiedKFold(n_splits=CV_FOLDS, shuffle=True, random_state=RANDOM_STATE)

    cands = _candidate_sets(ranking)
    scores, rows = {}, []
    for name, feats in cands.items():
        sc = _score(X_tr, y_tr, feats, cv)
        scores[name] = sc
        rows.append({
            "bo_cat": name,
            "n_dac_trung": len(feats),
            "roc_auc_mean": round(sc["roc_auc"][0], 5),
            "roc_auc_std": round(sc["roc_auc"][1], 5),
            "f1_mean": round(sc["f1"][0], 5),
            "precision_mean": round(sc["precision"][0], 5),
            "recall_mean": round(sc["recall"][0], 5),
        })
    table = (pd.DataFrame(rows)
             .sort_values(["n_dac_trung", "bo_cat"]).reset_index(drop=True))
    table.to_csv(out_dir / "feature_selection.csv", index=False, encoding="utf-8-sig")

    base_auc = scores["top_81"]["roc_auc"][0]
    trong_khoang = [
        (name, cands[name]) for name in cands
        if MIN_FEATURES <= len(cands[name]) <= MAX_FEATURES
        and scores[name]["roc_auc"][0] >= base_auc - TOL_ROC_AUC
    ]
    trong_khoang.sort(key=lambda t: (len(t[1]), t[0]))
    if trong_khoang:
        chosen_name, chosen_list = trong_khoang[0]
    else:  # không mốc nào đạt dung sai trong [30,42] → lấy top-42 cho an toàn
        chosen_name, chosen_list = "top_42", cands["top_42"]

    chosen = _ordered(set(chosen_list))
    fast = _ordered(set(chosen) - set(EXTERNAL_FEATURES))
    bo_ngoai = _ordered(set(chosen) & set(EXTERNAL_FEATURES))

    result = {
        "bo_cat_duoc_chon": chosen_name,
        "dung_sai_roc_auc": TOL_ROC_AUC,
        "roc_auc_moc_81": round(base_auc, 5),
        "roc_auc_duoc_chon": round(scores[chosen_name]["roc_auc"][0], 5)
        if chosen_name in scores else None,
        "n_dac_trung": len(chosen),
        "MODEL_FEATURES_FINAL": list(chosen),
        "n_fast": len(fast),
        "FAST_FEATURES_FINAL": list(fast),
        "dac_trung_ngoai_bi_loai_o_ban_fast": list(bo_ngoai),
    }
    (out_dir / "selected_features.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")

    print(table.to_string(index=False))
    print(f"\n→ Chọn: {chosen_name}  ({len(chosen)} đặc trưng, "
          f"ROC-AUC {result['roc_auc_duoc_chon']} vs mốc-81 {result['roc_auc_moc_81']})")
    print("\n# --- dán vào src/contracts.py ---")
    print("MODEL_FEATURES_FINAL: tuple[str, ...] = (")
    for f in chosen:
        print(f'    "{f}",')
    print(f")\n# {len(chosen)} đặc trưng; bản 'chỉ đặc trưng nhanh' = bỏ "
          f"{len(bo_ngoai)} đặc trưng ngoài: {', '.join(bo_ngoai)}")
    return result


if __name__ == "__main__":
    run()
