"""Hiệu chỉnh ngưỡng "domain non" của Override #1 bằng đường cong ROC + chỉ số
Youden's J (Youden, 1950) — thay cho việc chọn số ngày tuỳ ý (Plan.md mục 7
"ngưỡng tối ưu trên tập cân bằng ≠ ngưỡng tối ưu trên traffic thật"; CLAUDE.md
mục Rủi ro chung).

**CẢNH BÁO PHẠM VI — đọc trước khi dùng số ra**: hiệu chỉnh trên
`Dataset/train/dataset_phishing.csv` — tập TRAIN **cân bằng 50/50**, giống hệt
cách RF/XGBoost được train. Đây là **ngưỡng khởi động có căn cứ dữ liệu**, thay
số 90 ngày chọn tuỳ ý trước đó — KHÔNG PHẢI ngưỡng cuối. Phải hiệu chỉnh lại ở
Tuần 6 trên traffic mô phỏng thực tế (95% Tranco / 5% phishing).

Phương pháp — đường cong ROC + Youden's J:
  1. Loại các dòng `domain_age` ÂM (không phải tuổi hợp lệ): `-1` là sentinel
     "không tra được" (EXTERNAL_LOOKUP_SENTINEL); `-2`/`-12` là lỗi tính ngày
     trong script gốc Hannousse & Yahiouche (WHOIS trả ngày đăng ký sau ngày
     crawl — dữ liệu bẩn, không phải "domain rất mới"). Tổng ~16,07% dòng bị
     loại — số này KHÔNG liên quan tới tỉ lệ "unknown" thực tế của Override #1
     lúc chạy sống (RDAP/WHOIS trực tuyến), chỉ là để cột dữ liệu tuổi domain
     "sạch" phục vụ hiệu chỉnh ngưỡng.
  2. Với MỌI ngưỡng nguyên T (ngày) trong khoảng xét, tính đúng vị từ luật thật
     `domain_age.py::kiem_tra_tuoi_domain` dùng: "non" <=> `tuoi_ngay < T`.
     Sensitivity(T) = TP/(TP+FN) (đúng bằng Recall); Specificity(T) = TN/(TN+FP).
  3. **Youden's J(T) = Sensitivity(T) + Specificity(T) − 1 = TPR(T) − FPR(T)** —
     khoảng cách (theo trục dọc) từ điểm (FPR(T), TPR(T)) trên đường cong ROC
     tới đường chéo ngẫu nhiên. Ngưỡng chọn là **T tối đa hoá J(T)** trên toàn
     bộ khoảng quét — điểm cân bằng tốt nhất giữa bắt đúng phishing
     (Sensitivity) và không báo nhầm domain hợp pháp (Specificity), không thiên
     về 1 phía như đặt sàn Recall hay sàn Precision tuỳ ý.

Output → reports/domain_age_threshold/ (đường cong ROC + Sensitivity/Specificity/J
theo T, bảng số liệu, AUC của riêng đặc trưng domain_age).
Chạy:  python -m src.threshold_domain_age
"""

from __future__ import annotations

import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from src.contracts import TARGET_COLUMN
from src.eda import load_dataset

ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "reports" / "domain_age_threshold"

T_MAX = 13000  # quét ngưỡng 1..13000 ngày (~35 năm) — phủ hết miền quan sát được


def loc_tuoi_hop_le(df: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    """Bỏ domain_age < 0 (sentinel -1 + lỗi tính ngày -2/-12). Trả (df sạch, thống kê loại)."""
    am = df["domain_age"] < 0
    thong_ke = {
        "tong_dong": int(len(df)),
        "bi_loai_am": int(am.sum()),
        "ti_le_loai_pct": round(100 * am.sum() / len(df), 2),
        "phan_bo_gia_tri_am": df.loc[am, "domain_age"].value_counts().to_dict(),
    }
    return df.loc[~am].copy(), thong_ke


def quet_nguong(df_hop_le: pd.DataFrame, t_max: int = T_MAX) -> pd.DataFrame:
    """Quét T=1..t_max, tính Sensitivity/Specificity/Youden's J/Precision đúng
    vị từ `tuoi_ngay < T` (khớp `domain_age.py::kiem_tra_tuoi_domain`)."""
    tuoi = df_hop_le["domain_age"].to_numpy()
    y = (df_hop_le[TARGET_COLUMN] == "phishing").to_numpy()
    n_phishing = int(y.sum())
    n_legit = int((~y).sum())

    Ts = np.arange(1, t_max + 1)
    max_tuoi = int(tuoi.max())
    dem_phishing_theo_ngay = np.bincount(tuoi[y], minlength=max_tuoi + 1)
    dem_legit_theo_ngay = np.bincount(tuoi[~y], minlength=max_tuoi + 1)
    tp_luy_ke = np.cumsum(dem_phishing_theo_ngay)  # TP(T) = phishing tuổi <= T-1 (tức tuổi < T)
    fp_luy_ke = np.cumsum(dem_legit_theo_ngay)

    idx = np.minimum(Ts - 1, max_tuoi)
    TP = tp_luy_ke[idx].astype(float)
    FP = fp_luy_ke[idx].astype(float)
    FN = n_phishing - TP
    TN = n_legit - FP

    sensitivity = TP / n_phishing          # = Recall
    specificity = TN / n_legit
    youden_j = sensitivity + specificity - 1.0
    precision = np.divide(TP, TP + FP, out=np.zeros_like(TP), where=(TP + FP) > 0)

    return pd.DataFrame({
        "nguong_ngay": Ts, "TP": TP.astype(int), "FP": FP.astype(int),
        "FN": FN.astype(int), "TN": TN.astype(int),
        "sensitivity": sensitivity, "specificity": specificity,
        "fpr": 1 - specificity, "youden_j": youden_j, "precision": precision,
    })


def tinh_auc(bang: pd.DataFrame) -> float:
    """AUC của riêng đặc trưng domain_age (coi tuổi càng nhỏ càng đáng ngờ),
    tính bằng hình thang trên đường cong ROC (fpr, sensitivity)."""
    thu_tu = np.argsort(bang["fpr"].to_numpy())
    fpr = bang["fpr"].to_numpy()[thu_tu]
    tpr = bang["sensitivity"].to_numpy()[thu_tu]
    return float(np.trapz(tpr, fpr))


def chon_nguong(bang: pd.DataFrame) -> dict:
    """Youden's J: T* = argmax(Sensitivity + Specificity - 1)."""
    i = int(bang["youden_j"].idxmax())
    dong = bang.loc[i]
    return {
        "nguong_chon_ngay": int(dong["nguong_ngay"]),
        "sensitivity": round(float(dong["sensitivity"]), 4),
        "specificity": round(float(dong["specificity"]), 4),
        "youden_j": round(float(dong["youden_j"]), 4),
        "precision": round(float(dong["precision"]), 4),
    }


def _plot(bang: pd.DataFrame, chon: dict, auc: float, out_dir: Path) -> None:
    fig, axes = plt.subplots(1, 2, figsize=(11, 4.5))

    ax = axes[0]
    ax.plot(bang["fpr"], bang["sensitivity"], color="#3B6C9E", label=f"ROC (AUC={auc:.3f})")
    ax.plot([0, 1], [0, 1], "--", color="grey", lw=0.8, label="Ngẫu nhiên")
    diem = bang[bang["nguong_ngay"] == chon["nguong_chon_ngay"]].iloc[0]
    ax.scatter([diem["fpr"]], [diem["sensitivity"]], color="red", zorder=5,
              label=f"T={chon['nguong_chon_ngay']} ngày (J max)")
    ax.set_xlabel("False Positive Rate (1 − Specificity)")
    ax.set_ylabel("True Positive Rate (Sensitivity)")
    ax.set_title("Đường cong ROC — đặc trưng domain_age")
    ax.legend(loc="lower right", fontsize=8)

    ax = axes[1]
    ax.plot(bang["nguong_ngay"], bang["sensitivity"], label="Sensitivity", color="#8FB339")
    ax.plot(bang["nguong_ngay"], bang["specificity"], label="Specificity", color="#3B6C9E")
    ax.plot(bang["nguong_ngay"], bang["youden_j"], label="Youden's J", color="#B5651D", linestyle="--")
    ax.axvline(chon["nguong_chon_ngay"], color="red", linestyle=":", lw=1.2,
              label=f"Ngưỡng chọn = {chon['nguong_chon_ngay']} ngày")
    ax.set_xlim(0, min(8000, bang["nguong_ngay"].max()))
    ax.set_xlabel("Ngưỡng T (ngày) — flag 'non' nếu tuổi domain < T")
    ax.set_ylabel("Điểm số")
    ax.set_title("Sensitivity / Specificity / Youden's J theo T")
    ax.legend(fontsize=8)

    fig.tight_layout()
    fig.savefig(out_dir / "fig_nguong_domain_age.png", dpi=120)
    plt.close(fig)


def run(out_dir: Path = OUT_DIR) -> dict:
    out_dir.mkdir(parents=True, exist_ok=True)
    df = load_dataset()
    df_hop_le, thong_ke_loc = loc_tuoi_hop_le(df)
    bang = quet_nguong(df_hop_le)
    auc = tinh_auc(bang)
    chon = chon_nguong(bang)

    bang.to_csv(out_dir / "quet_nguong.csv", index=False, encoding="utf-8-sig")
    _plot(bang, chon, auc, out_dir)

    summary = {
        "phuong_phap": "ROC + Youden's J (J = Sensitivity + Specificity - 1)",
        "auc_domain_age": round(auc, 4),
        "thong_ke_loc_tuoi": thong_ke_loc,
        "n_dong_hieu_chinh": int(len(df_hop_le)),
        "ket_qua_chon": chon,
        "canh_bao": ("Hiệu chỉnh trên tập TRAIN cân bằng 50/50 — KHÔNG phải ngưỡng "
                     "cuối, phải hiệu chỉnh lại Tuần 6 trên traffic mô phỏng 95% "
                     "Tranco / 5% phishing."),
    }
    (out_dir / "summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"Loại {thong_ke_loc['bi_loai_am']}/{thong_ke_loc['tong_dong']} dòng "
          f"domain_age âm ({thong_ke_loc['ti_le_loai_pct']}%).")
    print(f"AUC (riêng đặc trưng domain_age): {auc:.4f}")
    print(f"Ngưỡng chọn (Youden's J lớn nhất): {chon['nguong_chon_ngay']} ngày — "
          f"Sensitivity={chon['sensitivity']} Specificity={chon['specificity']} "
          f"J={chon['youden_j']} Precision={chon['precision']}")
    return summary


if __name__ == "__main__":
    run()
