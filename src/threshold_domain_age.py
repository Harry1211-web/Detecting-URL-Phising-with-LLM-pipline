"""Hiệu chỉnh ngưỡng "domain non" của Override #1 bằng Precision/Recall + F-beta
(β>1) — thay cho việc chọn số ngày tuỳ ý (Plan.md mục 7 "ngưỡng tối ưu trên tập
cân bằng ≠ ngưỡng tối ưu trên traffic thật"; CLAUDE.md mục Rủi ro chung).

**CẢNH BÁO PHẠM VI — đọc trước khi dùng số ra**: hiệu chỉnh trên
`Dataset/train/dataset_phishing.csv` — tập TRAIN **cân bằng 50/50**, giống hệt
cách RF/XGBoost được train. Đây là **ngưỡng khởi động có căn cứ dữ liệu**, thay
số 90 ngày chọn tuỳ ý trước đó — KHÔNG PHẢI ngưỡng cuối. Phải hiệu chỉnh lại ở
Tuần 6 trên traffic mô phỏng thực tế (95% Tranco / 5% phishing), vì Precision đo
trên tập cân bằng luôn lạc quan hơn nhiều so với traffic thật (>99% hợp pháp).

Yêu cầu nghiệp vụ (đề bài Bạn B đặt ra 2026-09-13): luật domain_age không được bỏ
lọt quá nhiều phishing thật — bắt buộc **Recall >= 95%** trên tập hiệu chỉnh;
trong số các ngưỡng đạt điều kiện đó, chọn ngưỡng cho **Precision cao nhất**.

Phương pháp:
  1. Loại các dòng `domain_age` ÂM (không phải tuổi hợp lệ): `-1` là sentinel
     "không tra được" (EXTERNAL_LOOKUP_SENTINEL); `-2`/`-12` là lỗi tính ngày
     trong script gốc Hannousse & Yahiouche (WHOIS trả ngày đăng ký sau ngày
     crawl — dữ liệu bẩn, không phải "domain rất mới"). Tổng ~16,07% dòng bị
     loại — số này KHÔNG liên quan tới tỉ lệ "unknown" thực tế của Override #1
     lúc chạy sống (RDAP/WHOIS trực tuyến), chỉ là để cột dữ liệu tuổi domain
     "sạch" phục vụ hiệu chỉnh ngưỡng.
  2. Với MỌI ngưỡng nguyên T (ngày) trong khoảng xét, tính đúng vị từ luật thật
     `domain_age.py::kiem_tra_tuoi_domain` dùng: "non" <=> `tuoi_ngay < T`.
     Precision(T)/Recall(T) tính trên nhãn `status` thật.
  3. F_beta(T) với beta = F_BETA (mặc định 2 — coi Recall quan trọng gấp đôi
     Precision, đúng tinh thần "không được bỏ lọt phishing") — CHỈ dùng để BÁO
     CÁO/đối chiếu đường cong, KHÔNG dùng để chọn trực tiếp: tối ưu F_beta đơn
     thuần không đảm bảo sàn cứng Recall >= 95% mà đề bài yêu cầu.
  4. Chọn ngưỡng theo ràng buộc: trong các T có Recall(T) >= RECALL_TOI_THIEU,
     lấy T có Precision(T) lớn nhất (ngưỡng NHỎ nhất trong số hoà nhau, để tránh
     nới điều kiện "non" quá tay khi không cần thiết).

Output → reports/domain_age_threshold/ (bảng + biểu đồ P/R/F-beta theo T).
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

RECALL_TOI_THIEU = 0.95   # yêu cầu nghiệp vụ: bắt được >= 95% phishing thật
F_BETA = 2.0              # beta > 1: coi Recall quan trọng hơn Precision
T_MAX = 3650              # quét ngưỡng 1..3650 ngày (10 năm) — đủ phủ toàn miền hữu ích


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


def f_beta_score(precision: np.ndarray, recall: np.ndarray, beta: float = F_BETA) -> np.ndarray:
    tong = (beta ** 2) * precision + recall
    return np.divide((1 + beta ** 2) * precision * recall, tong,
                     out=np.zeros_like(tong, dtype=float), where=tong > 0)


def quet_nguong(df_hop_le: pd.DataFrame, t_max: int = T_MAX) -> pd.DataFrame:
    """Quét T=1..t_max, tính Precision/Recall/F-beta đúng vị từ `tuoi_ngay < T`."""
    tuoi = df_hop_le["domain_age"].to_numpy()
    y = (df_hop_le[TARGET_COLUMN] == "phishing").to_numpy()
    n_phishing = int(y.sum())
    n_legit = int((~y).sum())

    Ts = np.arange(1, t_max + 1)
    # (t_max, n) quá lớn nếu quét từng dòng x từng T riêng — dùng lũy kế theo
    # bincount(tuoi) đã sort thay vì ma trận (t_max x n) để nhẹ bộ nhớ hơn.
    max_tuoi = int(tuoi.max())
    dem_phishing_theo_ngay = np.bincount(tuoi[y], minlength=max_tuoi + 1)
    dem_legit_theo_ngay = np.bincount(tuoi[~y], minlength=max_tuoi + 1)
    tp_luy_ke = np.cumsum(dem_phishing_theo_ngay)  # TP(T) = phishing có tuổi < T => tuoi <= T-1
    fp_luy_ke = np.cumsum(dem_legit_theo_ngay)

    idx = np.minimum(Ts - 1, max_tuoi)  # TP(T) = phishing có tuổi <= T-1 (tức tuổi < T)
    TP = tp_luy_ke[idx].astype(float)
    FP = fp_luy_ke[idx].astype(float)
    FN = n_phishing - TP

    precision = np.divide(TP, TP + FP, out=np.zeros_like(TP), where=(TP + FP) > 0)
    recall = np.divide(TP, TP + FN, out=np.zeros_like(TP), where=(TP + FN) > 0)
    fbeta = f_beta_score(precision, recall)

    return pd.DataFrame({
        "nguong_ngay": Ts, "TP": TP.astype(int), "FP": FP.astype(int),
        "FN": FN.astype(int), "precision": precision, "recall": recall,
        f"f{F_BETA:g}": fbeta,
    })


PRECISION_SAN_DU_PHONG = 0.95  # sàn Precision dùng khi ràng buộc Recall chính bất khả thi


def _hang(bang: pd.DataFrame, i) -> dict:
    dong = bang.loc[i]
    return {
        "nguong_ngay": int(dong["nguong_ngay"]),
        "precision": round(float(dong["precision"]), 4),
        "recall": round(float(dong["recall"]), 4),
        f"f{F_BETA:g}": round(float(dong[f"f{F_BETA:g}"]), 4),
    }


def chon_nguong(bang: pd.DataFrame, recall_toi_thieu: float = RECALL_TOI_THIEU,
               precision_san_du_phong: float = PRECISION_SAN_DU_PHONG) -> dict:
    """Chọn ngưỡng theo 2 tầng ràng buộc.

    Tầng 1 (đúng yêu cầu gốc): trong các T có Recall >= `recall_toi_thieu`,
    chọn T cho Precision LỚN NHẤT (T nhỏ nhất nếu hoà).

    Tầng 2 (dự phòng — CHỈ kích hoạt khi Tầng 1 bất khả thi, tức domain_age
    KHÔNG THỂ đạt Recall yêu cầu ở mức Precision còn ý nghĩa — đúng giới hạn
    cấu trúc đã ghi trong domain_age.py: domain bị chiếm/dùng lâu năm khiến
    Recall trần thấp hơn hẳn 95% nếu không chấp nhận Precision rơi về ngang
    ngẫu nhiên): đảo ràng buộc — trong các T có Precision >= `precision_san_du_phong`,
    chọn T cho Recall LỚN NHẤT. Luôn trả về cả 2 tầng + điểm tối ưu F-beta thuần
    (đối chiếu, không dùng để chọn) để minh bạch quá trình quyết định.
    """
    dat_t1 = bang[bang["recall"] >= recall_toi_thieu]
    dong_fbeta = _hang(bang, bang[f"f{F_BETA:g}"].idxmax())

    tang1_kha_thi = not dat_t1.empty
    ket_qua_tang1 = None
    if tang1_kha_thi:
        precision_max = dat_t1["precision"].max()
        ung_vien = dat_t1[np.isclose(dat_t1["precision"], precision_max)]
        ket_qua_tang1 = _hang(bang, ung_vien["nguong_ngay"].idxmin())

    dat_t2 = bang[bang["precision"] >= precision_san_du_phong]
    if dat_t2.empty:
        raise ValueError(f"Bất khả thi cả 2 tầng: không có T nào đạt Precision >= "
                          f"{precision_san_du_phong} trong khoảng đã quét.")
    recall_max = dat_t2["recall"].max()
    ung_vien2 = dat_t2[np.isclose(dat_t2["recall"], recall_max)]
    ket_qua_tang2 = _hang(bang, ung_vien2["nguong_ngay"].idxmin())

    # Recall trần đạt được (T lớn nhất đã quét) — để định lượng "cách xa mục tiêu bao nhiêu"
    recall_tran = _hang(bang, bang["nguong_ngay"].idxmax())

    if tang1_kha_thi:
        ap_dung, ly_do = ket_qua_tang1, "Tầng 1 khả thi — dùng đúng yêu cầu Recall >= 95%."
    else:
        ap_dung = ket_qua_tang2
        ly_do = (f"Tầng 1 BẤT KHẢ THI trong khoảng đã quét (1..{int(bang['nguong_ngay'].max())} ngày): "
                 f"Precision tại T cho Recall cao nhất quét được ({recall_tran['nguong_ngay']} ngày, "
                 f"Recall={recall_tran['recall']:.2%}) chỉ còn {recall_tran['precision']:.2%} — gần "
                 f"ngẫu nhiên trên tập cân bằng 50/50. Khớp giới hạn cấu trúc đã ghi trong "
                 f"domain_age.py (CAIDA/WEIS: domain bị chiếm/lâu năm không thể bắt bằng tuổi domain "
                 f"dù đặt ngưỡng nào). Dùng Tầng 2 dự phòng: Precision >= "
                 f"{precision_san_du_phong:.0%}, tối đa Recall trong số đó.")

    return {
        "tang1_kha_thi": tang1_kha_thi,
        "tang1_recall_ge_95_max_precision": ket_qua_tang1,
        "tang2_precision_ge_95_max_recall": ket_qua_tang2,
        "recall_tran_trong_khoang_quet": recall_tran,
        "toi_uu_fbeta_thuan_doi_chieu": dong_fbeta,
        "ap_dung": ap_dung,
        "ly_do": ly_do,
    }


def _plot(bang: pd.DataFrame, chon: dict, out_dir: Path) -> None:
    fig, ax = plt.subplots(figsize=(7, 4.5))
    ax.plot(bang["nguong_ngay"], bang["precision"], label="Precision", color="#3B6C9E")
    ax.plot(bang["nguong_ngay"], bang["recall"], label="Recall", color="#8FB339")
    ax.plot(bang["nguong_ngay"], bang[f"f{F_BETA:g}"],
            label=f"F{F_BETA:g}", color="#B5651D", linestyle="--")
    ax.axhline(RECALL_TOI_THIEU, color="grey", linestyle=":", lw=1,
               label=f"Sàn Recall = {RECALL_TOI_THIEU}")
    ax.axvline(chon["ap_dung"]["nguong_ngay"], color="red", linestyle=":", lw=1.2,
               label=f"Ngưỡng áp dụng = {chon['ap_dung']['nguong_ngay']} ngày")
    ax.set_xlim(0, min(1500, bang["nguong_ngay"].max()))
    ax.set_xlabel("Ngưỡng T (ngày) — flag 'non' nếu tuổi domain < T")
    ax.set_ylabel("Điểm số")
    ax.set_title("Hiệu chỉnh ngưỡng domain_age — Precision/Recall/F-beta theo T")
    ax.legend()
    fig.tight_layout()
    fig.savefig(out_dir / "fig_nguong_domain_age.png", dpi=120)
    plt.close(fig)


def run(out_dir: Path = OUT_DIR) -> dict:
    out_dir.mkdir(parents=True, exist_ok=True)
    df = load_dataset()
    df_hop_le, thong_ke_loc = loc_tuoi_hop_le(df)
    bang = quet_nguong(df_hop_le)
    chon = chon_nguong(bang)

    bang.to_csv(out_dir / "quet_nguong.csv", index=False, encoding="utf-8-sig")
    _plot(bang, chon, out_dir)

    summary = {
        "recall_toi_thieu": RECALL_TOI_THIEU,
        "f_beta": F_BETA,
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
    print(f"Tầng 1 (Recall>={RECALL_TOI_THIEU:.0%}) khả thi: {chon['tang1_kha_thi']}")
    print(f"-> {chon['ly_do']}")
    ad = chon["ap_dung"]
    print(f"NGƯỠNG ÁP DỤNG: {ad['nguong_ngay']} ngày — Precision={ad['precision']} "
          f"Recall={ad['recall']} F{F_BETA:g}={ad[f'f{F_BETA:g}']}")
    print(f"(đối chiếu — tối ưu F{F_BETA:g} thuần, không ràng buộc: "
          f"{chon['toi_uu_fbeta_thuan_doi_chieu']})")
    return summary


if __name__ == "__main__":
    run()
