# Hệ thống AI phát hiện & cảnh báo website lừa đảo (phishing)

Đồ án CNTT (~9 tuần, 2 thành viên). Phân loại URL theo **độ tin cậy**: chỉ gọi LLM
(Ollama local) cho phần traffic thật sự đáng ngờ, giữ tốc độ cho phần rõ ràng an toàn.

- Kiến trúc: `GhiChu_Pipeline_DeTai.docx` (nguồn chân lý).
- Kế hoạch & phân vai: `Plan.md`.
- Hướng dẫn cho Claude Code: `CLAUDE.md`.

## Cấu trúc thư mục

```
Dataset/train/dataset_phishing.csv   # Hannousse & Yahiouche 2020, 11.430 × 89
docs/interface_contract.md           # hợp đồng /check-url + contract nội bộ (chốt Tuần 1)
src/contracts.py                     # NGUỒN CHÂN LÝ: 87 đặc trưng, MODEL_FEATURES_V1/FINAL (30), FAST_FEATURES_FINAL (25), phan_vung()
src/eda.py                           # EDA dataset (Tuần 1)
src/train_rf.py                      # train Random Forest v1 — 81 đặc trưng (Tuần 2)
src/feature_selection.py             # cắt 81 -> 30 đặc trưng, xác nhận bằng ROC-AUC 5-fold (Tuần 3)
src/train_rf_final.py                # RF bản cuối (30) + bản "chỉ đặc trưng nhanh" (25) + so XGBoost (Tuần 3)
src/features/                        # trích 87 đặc trưng — README + trial_extract.py
src/override/                        # brands_vn.json (62 brand) + 3 luật Override + aggregator + phân vùng
                                     #   #1 domain_age.py (T3) · #2 ssl_tls.py (T4) · #3 typosquatting.py (T4)
notebooks/01_eda_dataset_phishing.ipynb
notebooks/02_train_rf_v1.ipynb
notebooks/03_feature_selection_rf_final.ipynb
reports/eda/  reports/rf_v1/  reports/rf_final/   # output + BAO_CAO_*.md (binary gitignore, .md giữ)
tests/                               # kiểm hợp đồng interface + brand + 3 Override + gói phân vùng
models/rf_v1.joblib rf_final.joblib rf_fast.joblib xgb_final.joblib   # mô hình đã train (gitignore)
```

## Thiết lập

```bash
python -m venv .venv
.venv\Scripts\activate            # Windows
pip install -r requirements.txt
setx PYTHONIOENCODING utf-8        # output tiếng Việt trên terminal Windows
```

Python 3.12. Toàn bộ tài liệu / comment / output bằng **tiếng Việt**.

## Chạy nhanh

```bash
python -m src.eda                                  # sinh lại reports/eda/
python -m src.train_rf                              # train RF v1 (81 đặc trưng) -> reports/rf_v1/
python -m src.feature_selection                     # cắt 81 -> 30 đặc trưng -> reports/rf_final/
python -m src.train_rf_final                        # RF cuối + fast + XGBoost -> reports/rf_final/ + models/
python -m src.override.brands                       # kiểm danh sách brand VN
python -m src.override.domain_age --smoke https://github.com     # Override #1 tuổi domain (cần mạng)
python -m src.override.ssl_tls --smoke https://expired.badssl.com # Override #2 SSL/TLS (cần mạng)
python -m src.override.typosquatting --smoke http://vietccombank.com  # Override #3 typosquatting (không mạng)
jupyter notebook notebooks/01_eda_dataset_phishing.ipynb
python -m src.features.trial_extract --smoke https://www.vietcombank.com.vn/
python -m pytest -q                                # 43 test (contracts + brands + 3 Override + pipeline)
```

## Tiến độ

| Tuần | Bạn A (CNPM) | Bạn B (ML + Cyber) |
|---|---|---|
| **1** | scaffold FastAPI, cài Ollama, scaffold Extension MV3 | ✅ EDA dataset · scaffold repo/contract · trial trích đặc trưng |
| **2** | orchestrator + wiring 87 đặc trưng + cache 24h | ✅ train RF v1 (GridSearchCV k-fold, ROC-AUC 0,993) · ✅ list brand VN (62 domain) |
| **3** | client Ollama + hạ tầng RAG | ✅ feature selection 81→30 · ✅ RF cuối + bản nhanh + XGBoost · ✅ Override #1 (tuổi domain) |
| **4** | job blocklist DNR | ✅ Override #2 (SSL/TLS, chống SSRF) + #3 (typosquatting) · gói `override` + phân vùng · 29 test offline |
| 5 | tích hợp #1 · Extension Lớp B | nạp kho RAG Tầng 2 · ghép RAG vào prompt |
| 6 | hoàn thiện Extension · parity Chrome/Edge | hiệu chỉnh ngưỡng · benchmark Ollama |
| 7 | gia cố backend · health-check Ollama | red-team prompt injection · concept drift PhiUSIIL |
| 8 | tổng duyệt demo · đóng gói | đối chiếu Google Safe Browsing / VirusTotal / URLhaus / urlscan.io |
| 9 | đệm · báo cáo · slide · video demo | đệm · báo cáo · slide |

Chi tiết: `Plan.md` mục 3.

## Ghi chú Tuần 1 (kết quả EDA — xem `reports/eda/BAO_CAO_EDA.md`)

- Nhãn cân bằng **chính xác 50/50** (5.715/5.715), 0 ô NaN.
- `corr(google_index, status) = 0,731` — tín hiệu đơn lẻ mạnh nhất (khớp `CLAUDE.md`).
- **6** cột hằng số = 0 (không phải 3): `sfh`, `ratio_intErrors`, `ratio_intRedirection`,
  `nb_or`, `ratio_nullHyperlinks`, `submit_email` → bỏ khi feature selection.
- `domain_age == -1` ("không tra được") ở **15,6%** dòng → xử lý như hạng mục riêng khi
  train; Override #1 phải trả `"unknown"`, không mặc định an toàn.
- 3/4 đặc trưng mạnh nhất thuộc nhóm tra cứu ngoài (`google_index`, `page_rank`,
  `domain_age`) — theo dõi độ giòn của mô hình khi tra cứu lỗi.

## Ghi chú Tuần 2 (xem `reports/rf_v1/BAO_CAO_RF_V1.md`)

- RF v1 trên 81 đặc trưng: **k-fold ROC-AUC 0,9935 ± 0,0007**; test (2.286 URL giữ lại)
  accuracy 0,961 / F1 0,961 / ROC-AUC 0,992 → không overfit rõ rệt.
- Top 30 đặc trưng gộp **90,6%** importance, top 42 → 96,8%; 45/81 đặc trưng importance < 0,005
  → Tuần 3 cắt còn ~30–42 đặc trưng.
- 4 đặc trưng đầu bảng (`google_index`, `page_rank`, `nb_hyperlinks`, `web_traffic`) ≈ 40%
  importance, phần lớn là nhóm tra cứu ngoài → Tuần 3 train thêm bản "chỉ đặc trưng nhanh".
- `src/override/brands_vn.json`: **62** thương hiệu VN (30 ngân hàng, 8 ví, 10 TMĐT, 6 viễn
  thông/công nghệ, 3 hàng không, 5 dịch vụ công) — **bản thảo cần rà lại nguồn chính thức**.

## Ghi chú Tuần 3 (xem `reports/rf_final/BAO_CAO_RF_FINAL.md`)

- **Feature selection 81 → 30**: mốc `top-30` (theo importance RF v1) giữ ~99,9% ROC-AUC
  5-fold (0,99235 vs 0,99353) — tập nhỏ nhất trong khoảng 30–42 còn trong dung sai 0,002.
  Chốt vào `contracts.MODEL_FEATURES_FINAL` (30) + `FAST_FEATURES_FINAL` (25, bỏ nhóm ngoài).
- **RF bản cuối (30 đặc trưng)**: k-fold ROC-AUC 0,9923 / test accuracy 0,954 — chi phí ~0,7
  điểm so với 81 đặc trưng.
- **XGBoost (30 đặc trưng)** nhỉnh hơn: k-fold ROC-AUC **0,9942**, test accuracy 0,963, train
  nhanh hơn RF ~5×. Ghi nhận là phương án dự phòng mạnh; RF vẫn là mô hình theo thiết kế.
- **Bản "chỉ đặc trưng nhanh" (25 đặc trưng, không mạng)** tụt **2,6 điểm accuracy** / 1,5 điểm
  ROC-AUC → nhánh fallback lúc RDAP/WHOIS/Google timeout không được tin `rf_fast` một mình.
- **Override #1** (`src/override/domain_age.py`): RDAP (IANA bootstrap) → WHOIS fallback,
  timeout 0,5s/bước, `.vn` bỏ qua RDAP, rỗng cả hai → `flag="unknown"` (không mặc định an toàn).
  7 test offline. Ngưỡng "domain non" mặc định 90 ngày, hiệu chỉnh lại Tuần 6.

## Ghi chú Tuần 4 (Bạn B)

- **Override #2 — SSL/TLS** (`src/override/ssl_tls.py`): bắt tay TLS **có xác thực**
  (`ssl.create_default_context`: chuỗi tin cậy + khớp hostname + còn hạn), timeout 2s
  (bắt tay nặng hơn 1 GET RDAP nên nới so với 0,5s).
  - `flag=True`: chứng chỉ **không hợp lệ** (self-signed / hết hạn / sai hostname / CA lạ)
    **hoặc** hợp lệ nhưng **cấp < 2 ngày** (`NGUONG_CERT_MOI_NGAY`, CLAUDE.md).
  - `flag=False`: hợp lệ và cấp ≥ 2 ngày. `flag="unknown"`: không kết nối / timeout / cổng
    không nói TLS / bị chặn — **không mặc định an toàn**.
  - **Chống SSRF** (luật nhận URL kẻ tấn công kiểm soát): chỉ cổng HTTPS chuẩn
    (443/8443/4443/9443); phân giải hostname và **từ chối IP nội bộ** (loopback/private/
    link-local/reserved/multicast); kết nối **ghim vào đúng IP đã kiểm** (đóng cửa
    DNS-rebinding), SNI vẫn theo hostname gốc.
  - **Không rò thông tin**: `reason` KHÔNG chép nguyên văn `str(exception)`; lỗi xác thực
    ánh xạ từ `verify_code` OpenSSL sang câu tiếng Việt cố định.
  - Smoke thật đã kiểm: `vietcombank.com.vn`→False; `self-signed`/`expired`/`wrong.host.badssl.com`→True;
    `127.0.0.1`, `google.com:22`→"unknown" (bị chặn).
- **Override #3 — Typosquatting** (`src/override/typosquatting.py`): Levenshtein nhãn domain
  vs 62 brand VN, ngưỡng `max(1, len(brand)//5)`. Thuần tính toán → **không bao giờ `"unknown"`**.
  - 4 kiểu cờ (nghiêm trọng giảm dần): trùng khít tên brand khác TLD chính thức ·
    tên brand trong subdomain · Levenshtein 1..ngưỡng · tên brand (≥6 ký tự) là chuỗi con.
  - **Brand < 5 ký tự bị loại khỏi so khớp Levenshtein** (mã NH 3 chữ acb/scb/vib…, ví ngắn
    momo/zalo…): chuỗi 3-4 ký tự sai 1 phép sửa trùng vô số domain vô hại → theo tiêu chí
    "không bắt nhầm brand tên ngắn" (Plan.md mục 7). Sự hiện diện tên brand vẫn được RF
    `domain_in_brand`/`brand_in_subdomain` xử lý.
  - Không với tới kiểu "brand + từ khoá" tách bằng dấu (`techcombank-xac-thuc.com`) — để RF lo.
- **Gói `src/override/__init__.py`**: `chay_tat_ca_override(url)` → 3 `OverrideResult` theo
  thứ tự `[domain_age, ssl_tls, typosquatting]`; `phan_vung_tu_url(url, rf_score)` ghép luôn
  `contracts.phan_vung` (tiện test/tích hợp — orchestrator sản xuất là việc Bạn A, chạy 3 luật
  **song song** với RF).
- **Test**: +29 offline (`test_ssl_tls.py` 15 gồm chống SSRF/rò lộ · `test_typosquatting.py` 10 ·
  `test_override_pipeline.py` 6), monkeypatch mọi bước chạm mạng ngoài. Tổng repo **48 test**,
  `pytest -q` xanh.
- Ngưỡng `NGUONG_CERT_MOI_NGAY=2`, `RF_LOW_RISK_THRESHOLD_DEFAULT=0.30` là **mặc định khởi
  động** — hiệu chỉnh lại Tuần 6 trên traffic mô phỏng 95% Tranco / 5% phishing.
