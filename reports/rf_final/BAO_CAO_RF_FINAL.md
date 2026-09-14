# Báo cáo Feature selection + RF bản cuối — Tuần 3 (Bạn B)

Nối tiếp `reports/rf_v1/BAO_CAO_RF_V1.md`. Tái tạo:

```
python -m src.feature_selection     # chọn tập đặc trưng  -> reports/rf_final/feature_selection.csv
python -m src.train_rf_final        # train 3 mô hình     -> reports/rf_final/ + models/*.joblib
```

Trình bày: `notebooks/03_feature_selection_rf_final.ipynb`. `random_state=42` cố định.

---

## 1. Feature selection: 81 → 30 đặc trưng

Phương pháp: dùng thứ hạng `feature_importances_` của RF v1 làm bộ lọc, thử nhiều
mốc cắt, chấm **ROC-AUC 5-fold trên tập TRAIN** với đúng cấu hình RF tốt nhất của
v1 (chỉ danh sách đặc trưng thay đổi — không lẫn ảnh hưởng hyper-param). Không
đụng tập test.

Quy tắc chọn: tập **nhỏ nhất** trong khoảng 30–42 đặc trưng (Plan.md) mà ROC-AUC
còn trong **dung sai 0,002** so với mốc dùng cả 81 đặc trưng.

| Bộ cắt | n đặc trưng | ROC-AUC (mean) | ROC-AUC (std) | F1 (mean) |
|---|---|---|---|---|
| top_20 | 20 | 0,99167 | 0,00080 | 0,95999 |
| top_25 | 25 | 0,99234 | 0,00080 | 0,96248 |
| **top_30** | **30** | **0,99235** | **0,00075** | **0,96280** |
| top_33 | 33 | 0,99277 | 0,00085 | 0,96490 |
| top_36 / imp≥0,005 | 36 | 0,99301 | 0,00088 | 0,96412 |
| top_39 | 39 | 0,99321 | 0,00066 | 0,96535 |
| top_42 / imp≥0,003 | 42 | 0,99298 | 0,00073 | 0,96522 |
| top_50 | 50 | 0,99330 | 0,00074 | 0,96599 |
| top_81 (mốc) | 81 | 0,99353 | 0,00068 | 0,96770 |

→ **Chọn `top_30`**: ROC-AUC 0,99235 so với mốc-81 0,99353 → chênh **0,00118 < 0,002**.
Giữ ~99,9% ROC-AUC với 37% số đặc trưng.

Kết quả chốt vào `src/contracts.py`:
- `MODEL_FEATURES_FINAL` — 30 đặc trưng.
- `FAST_FEATURES_FINAL` — 25 đặc trưng (bỏ 5 đặc trưng tra cứu ngoài:
  `domain_registration_length`, `domain_age`, `web_traffic`, `google_index`, `page_rank`).

File máy đọc: `reports/rf_final/selected_features.json`.

---

## 2. Ba mô hình trên cùng split + cùng GridSearchCV k-fold (k=5)

**Đã chạy `--full` cho CẢ RF lẫn XGBoost (2026-09-13), rồi mở rộng thêm riêng
grid XGBoost (2026-09-14 — `XGB_GRID_FULL` 192 → 432 cấu hình, `n_estimators`
tới 1200, `learning_rate` tới 0,01, qua `python -m src.train_rf_final --xgb-only`).
Bảng dưới là số liệu CHỐT.**

| Mô hình | n đặc trưng | k-fold ROC-AUC | k-fold F1 | test ROC-AUC | test F1 (phishing) | test accuracy | thời gian |
|---|---|---|---|---|---|---|---|
| `rf_v1` (tham chiếu) | 81 | 0,9935 | 0,9666 | 0,9924 | 0,9612 | 0,9611 | ~105s |
| `rf_final` | 30 | 0,9924 | 0,9633 | 0,9914 | 0,9547 | 0,9545 | ~500-1000s |
| `rf_fast` | 25 | 0,9772 | 0,9255 | 0,9763 | 0,9292 | 0,9296 | ~400-800s |
| **`xgb_final` — CHỐT SẢN XUẤT** | **30** | **0,9944** | **0,9694** | **0,9922** | **0,9651** | **0,9650** | 516,6s |

Cấu hình tốt nhất (grid rộng — `PARAM_GRID_FULL` cho RF trong `src/train_rf.py`,
`XGB_GRID_FULL` cho XGBoost trong `src/train_rf_final.py`):
- `rf_final`: `n_estimators=400, max_depth=20, min_samples_leaf=1, max_features='sqrt'`.
- `rf_fast`: `n_estimators=600, max_depth=None, min_samples_leaf=1, max_features='sqrt'`.
- `xgb_final`: `n_estimators=1200, max_depth=6, learning_rate=0.03, subsample=0.85`.
  So với grid 192-cấu-hình trước: `learning_rate=0,03` nay là điểm **giữa**
  `{0.01,0.02,0.03,0.1,0.2,0.3}` (hết ở biên) — xác nhận là tối ưu thật, không do
  grid hẹp. `n_estimators` vẫn ở biên trên `{200,...,1200}`, nhưng điểm số hầu
  như không đổi so với `n_estimators=800` trước đó (k-fold ROC-AUC 0,9943→0,9944,
  test accuracy/F1 không đổi) → đường cong đã bão hoà (thêm cây gần như không
  còn tác dụng); không tiếp tục nới grid vì lợi ích biên gần như bằng 0.

Biểu đồ: `fig_so_sanh_mo_hinh.png`, `fig_final_vs_fast_roc.png`, `fig_final_importances.png`.
Model đã lưu: `models/rf_final.joblib`, `models/rf_fast.joblib`, `models/xgb_final.joblib`.

### 2.1 Cắt 81 → 30 đặc trưng: chi phí ~0,7 điểm accuracy (RF)

`rf_final` bằng `rf_v1` về ROC-AUC (0,9914 vs 0,9924) nhưng test accuracy giảm
0,9611 → 0,9545 và F1 phishing 0,9612 → 0,9547. Đổi lại: ít hơn 51 đặc trưng,
trong đó cắt được **cả 2 đặc trưng nội dung HTML nặng** (`nb_hyperlinks` vẫn giữ)
và nhiều đặc trưng lexical gần như vô dụng — service trích đặc trưng của Bạn A nhẹ hơn.
(Đây là chi phí đo trên RF; `xgb_final` — mô hình được chọn — không mất khoản này,
xem 2.2.)

### 2.2 Quyết định: XGBoost là mô hình sản xuất Lớp B (2026-09-13)

Cùng grid rộng, cùng 30 đặc trưng, cùng split — `xgb_final` thắng `rf_final` **ở
MỌI chỉ số test**: ROC-AUC +0,0008, accuracy **+1,05 điểm**, F1 phishing +1,04
điểm; train nhanh hơn RF final dù grid XGBoost rộng hơn nhiều về SỐ cấu hình
(432 vs 108) — XGBoost train từng cây nhanh hơn RF nhiều.
`xgb_final` cũng vượt cả `rf_v1` (81 đặc trưng, mốc tham chiếu) dù chỉ dùng 30 →
XGBoost không phải đánh đổi độ chính xác lấy tốc độ như RF.

**→ CHỐT: XGBoost thay Random Forest làm mô hình chạy trong pipeline sản xuất**
(quyết định của Bạn B, không cần chờ Bạn A vì orchestrator chưa được cắm model
thật — xem `docs/interface_contract.md` mục 0 và `Plan.md`/`CLAUDE.md` đã đồng bộ).
RF vẫn được train + báo cáo song song mỗi lần chạy `train_rf_final.py`:
`feature_importances_` của RF trực quan/dễ diễn giải hơn cho phần viết báo cáo,
và giữ làm phương án dự phòng nếu XGBoost gặp vấn đề triển khai (kích thước
model, tương thích môi trường suy luận…) ở Tuần 5+.

### 2.3 Bỏ tra cứu ngoài → mô hình yếu đi rõ rệt (định lượng rủi ro #1 của RF v1)

`rf_fast` (25 đặc trưng, tính hoàn toàn không cần mạng) so với `rf_final`:
- test accuracy **0,9296 vs 0,9545** → tụt **2,5 điểm**.
- test ROC-AUC 0,9763 vs 0,9914 → tụt **1,5 điểm**.
- test recall phishing 0,9248 vs 0,9589 → **bỏ lọt thêm ~3,4% URL lừa đảo**.

5 đặc trưng tra cứu ngoài trong `rf_final` chiếm **47,5% tổng importance**
(`google_index` 23,2%; `page_rank` 11,7%; `web_traffic` 8,0%; `domain_age` 3,4%;
`domain_registration_length` 1,3%) — tập trung hơn cả RF v1 (~40%) vì đã cắt bớt
đặc trưng lexical yếu.

→ **Hệ quả cho pipeline:** nhánh fallback khi RDAP/WHOIS/Google timeout **không được
tin `rf_fast` một mình** — phải dựa thêm vào Luật Override (#1 tuổi domain, #2 SSL,
#3 typosquatting) và đẩy sang Vùng nghi ngờ cho Ollama khi điểm không dứt khoát.

---

## 3. Override #1 — Tuổi domain (RDAP → WHOIS)

`src/override/domain_age.py`. Điểm vào: `kiem_tra_tuoi_domain(url) -> OverrideResult`.

| Bước | Nguồn | Timeout | Ghi chú |
|---|---|---|---|
| 1 | RDAP (IANA bootstrap `data.iana.org/rdap/dns.json` → server theo TLD) | 0,5s/truy vấn (bootstrap 3s, cache 1 lần) | đọc mốc `events[].eventAction == "registration"` |
| 2 | WHOIS fallback (`python-whois`, socket cổng 43) | 0,5s | chỉ chạy khi bước 1 không ra ngày |
| 3 | — | — | rỗng cả hai → `flag="unknown"`, **KHÔNG** mặc định an toàn |

Quy tắc cờ: tuổi < `NGUONG_TUOI_MOI_NGAY` (mặc định **90 ngày**) → `flag=True`
(domain quá non → đáng ngờ); ≥ ngưỡng → `False`. Ngưỡng là mặc định khởi động,
**hiệu chỉnh lại ở Tuần 6** cùng ngưỡng phân vùng.

`.vn` nằm trong `TLD_KHONG_CO_RDAP` → bỏ qua RDAP không gọi mạng, xuống thẳng WHOIS
(VNNIC chưa triển khai RDAP — đúng thiết kế).

Chạy thử thật (Tuần 3):

| URL | flag | nguồn | ghi chú |
|---|---|---|---|
| `github.com` | `False` | RDAP | đăng ký 2007-10-09 |
| `google.com` | `False` | RDAP | đăng ký 1997-09-15 |
| `vietcombank.com.vn` | `unknown` | — | RDAP bỏ qua (.vn), WHOIS quá 0,5s → không xác định |

Test offline (không chạm mạng, monkeypatch 2 hàm tra cứu): `tests/test_domain_age.py`
— 7 test, phủ thứ tự RDAP→WHOIS, ngưỡng tuổi, và quy tắc "rỗng cả hai → unknown ≠ an toàn".

---

## 4. Rủi ro / việc còn nợ (chuyển tiếp)

1. ~~Grid vẫn rút gọn, cấu hình RF tốt nhất chạm biên.~~ **Đã chạy `--full` (2026-09-11)**
   — xem mục 2: `rf_final`/`rf_fast` không còn ở biên grid, điểm số ổn định.
   ~~Còn nợ: `XGB_GRID_QUICK` chưa mở rộng.~~ **Đã vá + chạy `XGB_GRID_FULL` (2026-09-13,
   mở rộng thêm 2026-09-14 lên 432 cấu hình)** — `xgb_final` thắng mọi chỉ số →
   **chốt XGBoost làm mô hình sản xuất** (mục 2.2). `learning_rate` đã xác nhận
   là điểm giữa grid (không còn ở biên); `n_estimators` vẫn ở biên trên nhưng
   điểm số bão hoà (0,9943→0,9944, không đổi ở test) — không ưu tiên nới thêm.
2. **`domain_age == -1` (15,6% dòng, EDA Tuần 1) vẫn coi là số −1.** Khi Bạn A ghép
   feature vào service, thêm cờ nhị phân `domain_age_unknown` để tách "domain non"
   khỏi "không tra được" — hiện RF gộp chung.
3. **WHOIS 0,5s quá chặt trên thực tế** → `.vn` gần như luôn trả `unknown`. Đúng
   thiết kế ("không mặc định an toàn") nhưng nghĩa là với domain `.vn` Override #1
   hầu như chỉ đóng vai "đẩy sang Vùng nghi ngờ". Cân nhắc nới WHOIS timeout riêng
   cho `.vn` ở Tuần 6 sau khi đo phân phối độ trễ thật.
4. **Chọn RF hay XGBoost làm mô hình chạy thật** — chưa chốt. Quyết định sau Tuần 6
   (hiệu chỉnh ngưỡng trên traffic 95% Tranco / 5% phishing) vì số liệu 50/50 hiện
   tại không phản ánh tỉ lệ báo động giả thật.
5. **Số liệu vẫn trên tập 50/50** — không dùng để chốt ngưỡng phân vùng.

## 5. File sinh ra

```
reports/rf_final/
├── feature_selection.csv        # 13 mốc cắt + ROC-AUC/F1 5-fold
├── selected_features.json       # tập 30 (FINAL) + 25 (FAST) máy đọc
├── so_sanh_mo_hinh.csv          # bảng 4 mô hình
├── summary.json                 # đầy đủ best_params + k-fold + test cho cả 3 mô hình
├── importances_rf_final.csv     # 30 đặc trưng
├── importances_rf_fast.csv      # 25 đặc trưng
├── importances_xgb_final.csv    # 30 đặc trưng
├── fig_so_sanh_mo_hinh.png
├── fig_final_vs_fast_roc.png
└── fig_final_importances.png
models/rf_final.joblib  models/rf_fast.joblib  models/xgb_final.joblib
```
