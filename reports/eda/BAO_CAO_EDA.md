# Báo cáo EDA — `dataset_phishing.csv` (Tuần 1, Bạn B)

Nguồn: Hannousse & Yahiouche (2020), Mendeley `dataset_B`.
Tái tạo: `python -m src.eda` → ghi `reports/eda/` (bảng `.csv`, biểu đồ `.png`, `summary.json`).
Trình bày: `notebooks/01_eda_dataset_phishing.ipynb`.

---

## Kết quả chính

| Hạng mục | Kết quả | Khớp `CLAUDE.md`? |
|---|---|---|
| Kích thước | 11.430 dòng × 89 cột (`url` + 87 đặc trưng + `status`) | ✅ |
| Cân bằng nhãn | `legitimate` 5.715 / `phishing` 5.715 — **chính xác 50/50** | ✅ |
| Ô thiếu (NaN) | **0** trên toàn bộ 87 đặc trưng | — |
| Dòng trùng hoàn toàn | 0 | — |
| URL trùng | **1** URL xuất hiện 2 lần (`http://e710z0ear.du.r.appspot.com/...`, cả 2 đều `phishing`, vector đặc trưng khác nhau) | — |
| `corr(google_index, status)` | **0.7312** (Pearson) | ✅ (~0.73) |

## Phát hiện cần lưu ý

### 1. Có **6** cột hằng số = 0, không phải 3

`CLAUDE.md` ghi 3 cột: `sfh`, `ratio_intErrors`, `ratio_intRedirection`.
EDA cho thấy thêm 3 cột nữa cũng **toàn bộ = 0** trong `dataset_B`:

```
sfh  ratio_intErrors  ratio_intRedirection  nb_or  ratio_nullHyperlinks  submit_email
```

→ **Hành động:** bỏ cả 6 cột này ngay từ bước feature selection (tuần 2). Không có
thông tin ⇒ không đóng góp cho mô hình, chỉ làm chậm real-time. Đã phản ánh trong
`src/contracts.py::CONSTANT_FEATURES_DATASET_B` (mở rộng lên 6) và cần sửa lại
`CLAUDE.md` mục Dataset.

### 2. `domain_age` có ~15,6% giá trị `-1` ("không tra được")

`domain_age == -1` ở **1.781/11.430** dòng (15,58%). `domain_registration_length`
có 0,4% giá trị `-1`. Các cột tra cứu ngoài còn lại (`whois_registered_domain`,
`web_traffic`, `dns_record`, `google_index`, `page_rank`) không có `-1`.

→ **Hành động:**
- Khi train: xử lý `-1` như một hạng mục riêng (thêm cờ nhị phân `domain_age_unknown`
  hoặc dùng mô hình cây chịu được giá trị đặc biệt), **không** để `-1` trộn vào thang số năm.
- Override #1 (tuổi domain, tuần 3): khi RDAP + WHOIS đều rỗng phải trả `flag="unknown"`,
  **không** mặc định an toàn — đúng nguyên tắc *Domain ẩn WHOIS/RDAP* trong `CLAUDE.md`.

### 3. Top đặc trưng theo |tương quan| với nhãn

| # | Đặc trưng | Pearson r | Nhóm | Diễn giải |
|---|---|---|---|---|
| 1 | `google_index` | **+0,731** | ngoài | `=1` (không được Google index) ⇒ gần như luôn là phishing |
| 2 | `page_rank` | −0,511 | ngoài | PageRank cao ⇒ hợp pháp |
| 3 | `nb_www` | −0,443 | lexical | có `www` ⇒ thiên hợp pháp |
| 4 | `ratio_digits_url` | +0,356 | lexical | nhiều chữ số trong URL ⇒ phishing |
| 5 | `domain_in_title` | +0,343 | nội dung | |
| 6 | `nb_hyperlinks` | −0,343 | nội dung | trang phishing thường ít link |
| 7 | `phish_hints` | +0,335 | lexical | từ khoá đáng ngờ trong URL |
| 8 | `domain_age` | −0,332 | ngoài | domain non ⇒ phishing (lưu ý mục 2) |
| 9 | `ip` | +0,322 | lexical | dùng IP thay tên miền ⇒ phishing |
| 10 | `nb_qm` | +0,294 | lexical | nhiều dấu `?` |

**Rủi ro tập trung tín hiệu:** 3/4 đặc trưng mạnh nhất (`google_index`, `page_rank`,
`domain_age`) đều thuộc nhóm 7 đặc trưng **tra cứu dịch vụ ngoài** — chậm, rate-limit,
dễ concept drift, và đúng phần mà Luật Override xử lý song song. Cần theo dõi ở tuần 2–3:
nếu Random Forest dồn quá nhiều trọng số vào `google_index`, mô hình sẽ giòn khi tra cứu
lỗi/timeout. Cân nhắc train thêm 1 bản "chỉ đặc trưng nhanh" (lexical + nội dung) để so.

### 4. Nhiều cột gần hằng số (không loại, nhưng ghi nhận)

`path_extension`, `punycode`, `nb_star`, `onmouseover`, `nb_space`, `nb_dollar`... có
`std < 0,05` (gần như luôn bằng 1 giá trị). Giữ lại cho feature selection quyết định,
nhưng nhiều khả năng sẽ rơi khỏi top 30–42.

---

## Ảnh hưởng tới các bước sau

- **Tuần 2 (train RF v1):** loại 6 cột hằng số ⇒ còn **81** đặc trưng đưa vào GridSearchCV.
  Không cần `class_weight`/resampling vì cân bằng 50/50. Bỏ 1 dòng URL trùng trước khi split
  để tránh rò rỉ train/test.
- **Tuần 3 (feature selection):** kỳ vọng `google_index`, `page_rank`, `nb_www`,
  `ratio_digits_url`, `domain_age`, `phish_hints` nằm trong nhóm giữ lại.
- **Tuần 6 (hiệu chỉnh ngưỡng):** phân phối 50/50 ở đây KHÔNG dùng để chốt ngưỡng —
  hiệu chỉnh lại trên traffic mô phỏng 95% Tranco / 5% phishing.
- **Override #1:** phải test nhánh "cả RDAP lẫn WHOIS rỗng → unknown" vì 15,6% domain
  trong chính tập train đã không tra được tuổi.

## File sinh ra

```
reports/eda/
├── summary.json                    # số liệu máy đọc
├── label_balance.csv
├── constant_check.csv              # 87 đặc trưng, sắp theo std tăng dần
├── target_correlation.csv          # 87 đặc trưng, sắp theo |r| giảm dần
├── missing_sentinel.csv            # NaN + tỉ lệ giá trị -1
├── fig_label_balance.png
├── fig_top_correlations.png
└── fig_feature_distributions.png
```
