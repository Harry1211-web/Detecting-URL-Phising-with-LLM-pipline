# Báo cáo hiệu chỉnh ngưỡng Override #1 (tuổi domain) — Bạn B

Thay thế lựa chọn tuỳ ý bằng ngưỡng có căn cứ dữ liệu, dùng đường cong ROC +
chỉ số Youden's J (Youden, 1950). Tái tạo:

```
python -m src.threshold_domain_age    # -> reports/domain_age_threshold/
```

`random_state` không áp dụng (không train model — chỉ quét ngưỡng trên nhãn thật).

---

## 1. Dữ liệu & phương pháp

**Dữ liệu**: `Dataset/train/dataset_phishing.csv` (cột `domain_age`, đơn vị ngày).
Loại **1.837/11.430 dòng (16,07%)** có `domain_age` âm trước khi quét:

| Giá trị | Số dòng | Diễn giải |
|---|---|---|
| `-1` | 1.781 | Sentinel "không tra được" (`EXTERNAL_LOOKUP_SENTINEL`) |
| `-2` | 55 | Lỗi tính ngày trong script gốc Hannousse & Yahiouche (WHOIS trả ngày sau ngày crawl) |
| `-12` | 1 | Như trên |

Còn lại **9.593 dòng** (4.721 phishing / 4.872 hợp pháp) dùng để quét ngưỡng.

**Phương pháp — đường cong ROC + Youden's J:**

Với mỗi ngưỡng nguyên T (1..13.000 ngày), tính đúng vị từ luật thật
(`domain_age.py`): **"non" ⇔ tuổi < T**, rồi tính:

- **Sensitivity(T)** = TP/(TP+FN) — đúng bằng Recall.
- **Specificity(T)** = TN/(TN+FP).
- **Youden's J(T) = Sensitivity(T) + Specificity(T) − 1 = TPR(T) − FPR(T)** —
  khoảng cách (theo trục dọc) từ điểm (FPR(T), TPR(T)) trên đường cong ROC tới
  đường chéo ngẫu nhiên.

**Ngưỡng chọn = T tối đa hoá J(T)** trên toàn bộ khoảng quét. Đây là điểm cân
bằng tốt nhất giữa bắt đúng phishing (Sensitivity) và không báo nhầm domain hợp
pháp (Specificity), không thiên về 1 phía như đặt sàn Recall hay sàn Precision
tuỳ ý.

Coi tuổi domain (đảo dấu) là 1 điểm số rủi ro duy nhất, đường cong (FPR, TPR)
quét theo T chính là đường cong ROC của riêng đặc trưng `domain_age`.

---

## 2. Kết quả

**AUC của riêng đặc trưng domain_age: 0,7351** — có tín hiệu phân biệt thật
(0,5 = ngẫu nhiên), nhưng không mạnh, đúng như importance của nó trong RF/XGBoost
(không phải đặc trưng mạnh nhất).

| T (ngày) | Sensitivity | Specificity | Youden's J | Precision |
|---|---|---|---|---|
| 30 | 0,028 | 1,000 | 0,028 | 1,000 |
| 90 | 0,047 | 0,998 | 0,045 | 0,957 |
| 365 | 0,120 | 0,994 | 0,113 | 0,948 |
| 900 | 0,197 | 0,990 | 0,187 | 0,951 |
| 2.000 | 0,345 | 0,937 | 0,282 | 0,842 |
| 3.000 | 0,453 | 0,853 | 0,306 | 0,750 |
| **4.005 (chọn)** | **0,599** | **0,767** | **0,366** | **0,714** |
| 5.000 | 0,666 | 0,676 | 0,342 | 0,666 |

→ **Ngưỡng áp dụng: T = 4.005 ngày (~11 năm)** — Youden's J đạt cực đại duy
nhất tại đây (không có ngưỡng nào khác đồng hạng). Tại điểm này: Sensitivity
(Recall) 0,5994, Specificity 0,7668, Precision 0,7136.

**`NGUONG_TUOI_MOI_NGAY` trong `src/override/domain_age.py` = 4005.**

---

## 3. Giới hạn — đọc trước khi dùng số này để báo cáo

1. **Hiệu chỉnh trên tập TRAIN cân bằng 50/50** (Hannousse & Yahiouche) — Specificity
   và Precision đo trên tập này **lạc quan hơn nhiều** so với traffic thật (>99%
   hợp pháp). **Đây là ngưỡng khởi động có căn cứ dữ liệu, KHÔNG PHẢI ngưỡng
   cuối** — phải hiệu chỉnh lại ở Tuần 6 trên traffic mô phỏng 95% Tranco / 5%
   phishing, đúng nguyên tắc đã áp dụng cho `CLF_LOW_RISK_THRESHOLD_DEFAULT`
   (ngưỡng phân vùng).
2. **Youden's J cân bằng Sensitivity/Specificity ngang nhau** — không đặt trọng
   số ưu tiên Recall hay Precision. Nếu nghiệp vụ muốn ưu tiên 1 phía (ví dụ bắt
   buộc Recall tối thiểu), cần đổi tiêu chí chọn khác trên cùng bảng
   `quet_nguong.csv` (đã có đủ Sensitivity/Specificity/Precision từng T).
3. **AUC 0,7351 không cao** — domain_age đơn lẻ chỉ là 1 trong 3 luật Override +
   mô hình Lớp B; không kỳ vọng luật này một mình phân loại tốt (đúng thiết kế
   "chạy song song", không phải gate riêng).
4. **-2/-12 (56 dòng) là lỗi tính ngày của script gốc**, không phải tín hiệu thật
   — loại đúng, không phải lựa chọn tuỳ tiện.
