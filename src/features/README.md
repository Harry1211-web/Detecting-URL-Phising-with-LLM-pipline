# Trích 87 đặc trưng (Hannousse & Yahiouche)

Chủ sở hữu bước wiring vào service: **Bạn A** (Plan.md mục 2).
Bạn B chỉ chạy thử end-to-end ở Tuần 1 và bảo đảm output khớp `contracts.FEATURE_NAMES`.

## Lấy script gốc (bắt buộc — KHÔNG commit vào repo)

1. Mở Mendeley Data record: **`10.17632/c2gw7fy2j4.3`**
   (https://data.mendeley.com/datasets/c2gw7fy2j4/3) — cùng nguồn đã tải `dataset_phishing.csv`.
2. "Download All" → giải nén. Trong gói có:
   - `dataset_B` (chính là `dataset_phishing.csv` — 11.430 × 89).
   - Thư mục script Python trích đặc trưng: nhận 1 URL, trả vector 87×1.
3. Chép **thư mục script** vào `src/features/hannousse_yahiouche/`
   (đã có trong `.gitignore` — tôn trọng bản quyền tác giả, không redistribute).
4. Nếu entrypoint không tên `features_extraction.py`, sửa biến `ENTRYPOINT` trong
   `trial_extract.py` cho khớp.

## Chạy thử

```bash
# sau khi đã vendored script gốc:
python -m src.features.trial_extract https://www.vietcombank.com.vn/

# chưa vendored — chạy smoke test bằng bộ trích lexical rút gọn (chỉ để kiểm hình dạng):
python -m src.features.trial_extract --smoke https://www.vietcombank.com.vn/
```

Script sẽ:
- gọi extractor (gốc hoặc rút gọn) trên 1 URL,
- kiểm vector có đúng 87 khoá, đúng thứ tự `contracts.FEATURE_NAMES`,
- dựng `pandas.DataFrame` 1 dòng sẵn sàng đưa vào model,
- in bảng giá trị + đánh dấu đặc trưng chưa trích được.

## Phụ thuộc mạng khi trích thật

- 24 đặc trưng nội dung: cần `GET` HTML trang (timeout ~5s, `requests`).
- 7 đặc trưng ngoài: WHOIS/DNS/Google index/PageRank/traffic — chậm, rate-limit.
  Giá trị không tra được điền **`-1`** (`contracts.EXTERNAL_LOOKUP_SENTINEL`), không phải `NaN`.
- Bộ smoke test rút gọn KHÔNG gọi mạng: chỉ tính đặc trưng lexical, phần còn lại điền `-1`.
