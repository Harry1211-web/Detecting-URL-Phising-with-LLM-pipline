# Báo cáo Random Forest v1 — Tuần 2 (Bạn B)

Tái tạo: `python -m src.train_rf` (grid rút gọn, ~60s CPU) → `reports/rf_v1/` + `models/rf_v1.joblib`.
Trình bày: `notebooks/02_train_rf_v1.ipynb`. Cấu hình cố định `random_state=42`.

## Thiết lập

| | |
|---|---|
| Đặc trưng đầu vào | **81** (87 − 6 cột hằng số, `contracts.MODEL_FEATURES_V1`) |
| Tiền xử lý | bỏ 1 dòng URL trùng trước khi split; nhãn `legitimate→0`, `phishing→1` |
| Chia dữ liệu | stratified 80/20 → train 9.143 / test 2.286 |
| Tuning | `GridSearchCV`, 16 cấu hình × `StratifiedKFold(k=5)` = 80 lần fit |
| Đa metric | precision / recall / f1 / roc_auc — refit theo **roc_auc** |
| Cấu hình tốt nhất | `n_estimators=400, max_depth=None, min_samples_leaf=1, max_features='sqrt'` |

## Kết quả

### k-fold CV trên tập train (mean ± std, tại cấu hình tốt nhất)

| Metric | Mean | Std |
|---|---|---|
| Precision (phishing) | 0,9678 | 0,0052 |
| Recall (phishing) | 0,9654 | 0,0058 |
| F1 (phishing) | 0,9666 | 0,0017 |
| ROC-AUC | **0,9935** | 0,0007 |

Std rất nhỏ → mô hình ổn định giữa các fold, không có fold nào lệch bất thường.

### Trên tập test giữ lại (2.286 URL, chưa đụng tới khi tuning)

| Metric | Giá trị |
|---|---|
| Accuracy | 0,9611 |
| Precision (phishing) | 0,9591 |
| Recall (phishing) | 0,9633 |
| F1 (phishing) | 0,9612 |
| ROC-AUC | 0,9924 |

Test khớp CV (chênh < 0,01) → **không overfit** rõ rệt. Biểu đồ: `fig_confusion.png`, `fig_roc.png`.

## Feature importances → chuẩn bị feature selection (Tuần 3)

15 đặc trưng mạnh nhất (`feature_importances.csv` có đủ 81):

| # | Đặc trưng | Importance | Nhóm |
|---|---|---|---|
| 1 | `google_index` | 0,190 | ngoài |
| 2 | `page_rank` | 0,109 | ngoài |
| 3 | `nb_hyperlinks` | 0,082 | nội dung |
| 4 | `web_traffic` | 0,076 | ngoài |
| 5 | `nb_www` | 0,041 | lexical |
| 6 | `ratio_extHyperlinks` | 0,032 | nội dung |
| 7 | `domain_age` | 0,030 | ngoài |
| 8 | `longest_word_path` | 0,026 | lexical |
| 9 | `ratio_intHyperlinks` | 0,025 | nội dung |
| 10 | `safe_anchor` | 0,025 | nội dung |
| 11 | `phish_hints` | 0,024 | lexical |
| 12 | `ratio_digits_url` | 0,020 | lexical |
| 13 | `length_url` | 0,018 | lexical |
| 14 | `longest_words_raw` | 0,016 | lexical |
| 15 | `length_hostname` | 0,016 | lexical |

- **Top 30 đặc trưng gộp 90,6% tổng importance; top 42 → 96,8%.**
- **45/81 đặc trưng có importance < 0,005** → cắt xuống ~30–42 đặc trưng gần như không mất
  tín hiệu (đúng kế hoạch Tuần 3).
- Đuôi bảng gần như bằng 0: `nb_star`, `punycode`, `nb_dollar`, `nb_external_redirection`,
  `path_extension`, `onmouseover`, `iframe`, `brand_in_subdomain`, `right_clic`, `nb_tilde`...

## Rủi ro ghi nhận (chuyển sang Tuần 3)

1. **Phụ thuộc nặng nhóm tra cứu ngoài.** 4 đặc trưng đầu bảng có 3 thuộc nhóm 7 đặc trưng
   ngoài (`google_index` + `page_rank` + `web_traffic` = ~37% importance; thêm `domain_age`
   ≈ 40%). Đây đúng phần chậm / rate-limit / dễ concept drift / trùng vai Luật Override.
   → Tuần 3: train thêm **1 bản "chỉ đặc trưng nhanh"** (lexical + nội dung, bỏ 7 đặc trưng
   ngoài) để đo mô hình mất bao nhiêu điểm khi không có tra cứu ngoài — phục vụ nhánh
   fallback khi RDAP/WHOIS/Google timeout.
2. **`domain_age == -1` (15,6%, EDA Tuần 1) vẫn đang được coi là số −1.** RF cây chịu được,
   nhưng bản cuối nên thêm cờ `domain_age_unknown` để tách "domain non" khỏi "không tra được".
3. **Số liệu trên tập 50/50 — KHÔNG dùng chốt ngưỡng phân vùng.** Hiệu chỉnh lại trên
   traffic mô phỏng 95% Tranco / 5% phishing ở Tuần 6.
4. **Grid mới ở mức rút gọn.** Cấu hình tốt nhất chạm biên (`n_estimators=400` là max,
   `max_depth=None`). Trước khi chốt bản cuối Tuần 3 nên chạy `python -m src.train_rf --full`
   (grid rộng: n_estimators tới 600, max_features 0.3/0.5) và so.

## File sinh ra

```
reports/rf_v1/
├── summary.json               # số liệu máy đọc
├── cv_results.csv             # toàn bộ 16 cấu hình GridSearchCV
├── feature_importances.csv    # 81 đặc trưng, importance giảm dần
├── fig_confusion.png
├── fig_roc.png
└── fig_importances.png
models/rf_v1.joblib            # {model, features, label_map, cv_roc_auc}
```
