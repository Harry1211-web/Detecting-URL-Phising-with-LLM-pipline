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
src/contracts.py                     # NGUỒN CHÂN LÝ: tên/thứ tự 87 đặc trưng, kiểu dữ liệu, phan_vung()
src/eda.py                           # EDA dataset (Tuần 1, Bạn B)
src/features/                        # trích 87 đặc trưng — README + trial_extract.py
notebooks/01_eda_dataset_phishing.ipynb
reports/eda/                         # output EDA (bảng, biểu đồ, BAO_CAO_EDA.md)
tests/                               # kiểm hợp đồng interface
models/                             # mô hình đã train (gitignore)
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
jupyter notebook notebooks/01_eda_dataset_phishing.ipynb
python -m src.features.trial_extract --smoke https://www.vietcombank.com.vn/
python -m pytest -q                                # (cần: pip install pytest)
```

## Tiến độ

| Tuần | Bạn A (CNPM) | Bạn B (ML + Cyber) |
|---|---|---|
| **1** | scaffold FastAPI, cài Ollama, scaffold Extension MV3 | ✅ EDA dataset · scaffold repo/contract · trial trích đặc trưng |
| 2 | orchestrator + wiring 87 đặc trưng + cache 24h | train RF v1 (GridSearchCV, k-fold) · bắt đầu list brand VN |
| 3 | client Ollama + hạ tầng RAG | feature selection + RF cuối · Override #1 (tuổi domain) |
| 4 | job blocklist DNR | Override #2 (SSL) + #3 (typosquatting) · hàm phân vùng |
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
