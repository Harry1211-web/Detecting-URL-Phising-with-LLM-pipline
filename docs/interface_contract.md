# Hợp đồng interface — chốt Tuần 1, cập nhật Tuần 4 (2026-09-13)

> Trạng thái: **CHỐT bởi Bạn B** để Bạn A triển khai theo — Bạn A chưa động tới
> orchestrator/backend nên không ai bị chặn bởi các quyết định dưới đây; góp ý thì
> sửa tiếp sau, không cần chờ duyệt trước khi bắt đầu code Tuần 5.
> Nguồn: `Plan.md` mục 1 & 4, `GhiChu_Pipeline_DeTai.docx` mục 2–3.
> Code hoá tại: `src/contracts.py` (nguồn chân lý — tài liệu này chỉ diễn giải).

Mục đích: mỗi người code trên **mock/stub** của phần kia, không chặn nhau tới mốc
tích hợp Tuần 5.

---

## 0. Quyết định mô hình Lớp B (2026-09-13, Bạn B tự quyết)

**Mô hình sản xuất của Lớp B là XGBoost, không phải Random Forest.**

So `rf_final` vs `xgb_final` CÙNG grid rộng (`GridSearchCV`, k=5, `--full`), CÙNG
30 đặc trưng (`MODEL_FEATURES_FINAL`), CÙNG split — `xgb_final` thắng mọi chỉ số:

| Mô hình | k-fold ROC-AUC | test ROC-AUC | test accuracy | test F1 (phishing) |
|---|---|---|---|---|
| `rf_final` (grid rộng) | 0,9924 | 0,9914 | 0,9545 | 0,9547 |
| **`xgb_final` (grid rộng, 192 cấu hình)** | **0,9943** | **0,9922** | **0,9650** | **0,9651** |

Chi tiết + cấu hình tốt nhất: `reports/rf_final/BAO_CAO_RF_FINAL.md` mục 2.
RF vẫn được train + báo cáo song song (đối chiếu/phương án dự phòng, importance dễ
diễn giải hơn cho phần viết báo cáo) nhưng **không phải mô hình chạy trong pipeline**.

**Hệ quả cho contract:** trường điểm số mô hình được đặt tên trung lập
**`clf_score`** (không phải `rf_score`) để không phải đổi contract nếu đổi mô
hình lần nữa; tương tự `RF_LOW_RISK_THRESHOLD_DEFAULT` → `CLF_LOW_RISK_THRESHOLD_DEFAULT`,
`source: "rf_override"` → `"clf_override"`.

---

## 1. `POST /check-url`

### Request
```json
{ "url": "http://vd-phishing.example/login" }
```

### Response
```json
{
  "url": "http://vd-phishing.example/login",
  "verdict": "nguy_hiem",
  "zone": "vung_nghi_ngo",
  "risk_score": 0.87,
  "clf_score": 0.72,
  "override_flags": [
    {"name": "domain_age",    "flag": true,      "reason": "Domain đăng ký 1 ngày trước", "latency_ms": 340.0},
    {"name": "ssl_tls",       "flag": false,     "reason": "Chứng chỉ hợp lệ, cấp 90 ngày trước", "latency_ms": 120.0},
    {"name": "typosquatting", "flag": "unknown", "reason": "Không so khớp được brand", "latency_ms": 5.0}
  ],
  "explanation": "Domain mới đăng ký, không được Google index...",
  "source": "ollama",
  "cached": false,
  "latency_ms": 4200.0
}
```

| Trường | Kiểu | Ý nghĩa |
|---|---|---|
| `verdict` | `"an_toan" \| "nguy_hiem" \| "canh_bao_nhe" \| "khong_xac_dinh"` | Phán quyết cuối trả người dùng |
| `zone` | `"vung_thap" \| "vung_nghi_ngo"` | Kết quả phân vùng (2 vùng, mục 3) |
| `risk_score` | `float [0,1]` | Điểm rủi ro tổng hợp (mô hình Lớp B + Override), để hiển thị/log |
| `clf_score` | `float [0,1]` | Xác suất phishing thô từ mô hình Lớp B (hiện là **XGBoost**, mục 0) |
| `override_flags` | `OverrideResult[]` | Kết quả 3 luật (mục 2) |
| `source` | `"blocklist" \| "clf_override" \| "ollama" \| "cache" \| "fallback"` | Tầng nào ra phán quyết |
| `cached` | `bool` | Lấy từ cache domain 24h hay không |
| `latency_ms` | `float` | Tổng thời gian xử lý phía backend |

**Ánh xạ `zone → verdict`:**
- `vung_thap` → `verdict = "an_toan"`, `source = "clf_override"`, **không** gọi Ollama.
- `vung_nghi_ngo` → gọi Ollama; `verdict` theo `OllamaResult.verdict`
  (`nguy_hiem` → `"nguy_hiem"`, `co_ve_on` → `"canh_bao_nhe"`).
- Ollama timeout/lỗi → `verdict` suy từ mô hình Lớp B/Override, `source = "fallback"`
  (định dạng `explanation` cụ thể — mục 6.3).
- Domain trong blocklist DNR → `verdict = "nguy_hiem"`, `source = "blocklist"`, bỏ qua phần còn lại.

---

## 2. `OverrideResult` — kết quả 1 luật Override

```json
{ "name": "domain_age", "flag": true, "reason": "...", "latency_ms": 340.0 }
```

| Trường | Kiểu | Ghi chú |
|---|---|---|
| `name` | `"domain_age" \| "ssl_tls" \| "typosquatting"` | 3 luật cố định |
| `flag` | `true \| false \| "unknown"` | `true` = vi phạm/đáng ngờ · `false` = ổn · `"unknown"` = không tra được |
| `reason` | `str` | Giải thích ngắn tiếng Việt (đưa vào prompt Ollama + log) |
| `latency_ms` | `float` | Thời gian chạy luật (mỗi bước mạng timeout ~500ms, riêng SSL/TLS 2s) |

**Quy tắc bắt buộc:** `"unknown"` **không** đồng nghĩa an toàn. Chỉ `flag === false`
mới coi là "không vi phạm" khi phân vùng. Áp dụng cho:
- `domain_age`: RDAP (IANA bootstrap) → WHOIS fallback; cả 2 rỗng/timeout → `"unknown"`.
  `.vn` không có RDAP → luôn xuống WHOIS (không phải bug). Ngưỡng "domain non"
  **900 ngày** (hiệu chỉnh bằng Precision/Recall + F-beta trên tập train, xem
  `src/threshold_domain_age.py` + `reports/domain_age_threshold/`; vẫn là ngưỡng
  khởi động, hiệu chỉnh lại Tuần 6 trên traffic mô phỏng thực tế).
- `ssl_tls`: không đọc được / bị chặn SSRF → `"unknown"`; chứng chỉ cấp < 2 ngày
  hoặc không hợp lệ → `flag = true`. Có guard chống SSRF (chỉ cổng HTTPS chuẩn,
  chặn IP nội bộ, ghim IP đã kiểm).
- `typosquatting`: Levenshtein vs `Dataset/brands/vn_brand_domains.csv` (63 brand),
  ngưỡng **theo độ dài kiểu PhishMatch** (nhãn ≤10 ký tự → 1, >10 → 2 — **không**
  loại nhãn ngắn, xem `src/override/typosquatting.py`). Không match brand nào
  trong ngưỡng → `flag = false` (đã kiểm tra, không phải unknown). Thuần tính
  toán → **không bao giờ trả `"unknown"`**.

---

## 3. Phân vùng (2 vùng) — `src/contracts.py::phan_vung()`

```
clf_score < NGƯỠNG  VÀ  mọi override_flags[i].flag === false   →  "vung_thap"
còn lại (clf_score cao HOẶC có ≥1 cờ true/unknown)               →  "vung_nghi_ngo"
```

- `NGƯỠNG` mặc định khởi động = `0.30` (`CLF_LOW_RISK_THRESHOLD_DEFAULT`).
- **Bắt buộc hiệu chỉnh lại** ở Tuần 6 trên traffic mô phỏng 95% Tranco / 5% phishing
  — không chốt theo test set cân bằng 50/50.
- Hàm này do Bạn B viết, cắm vào orchestrator của Bạn A.

---

## 4. `OllamaResult` — verdict Vùng nghi ngờ

```json
{ "verdict": "nguy_hiem", "explanation": "...", "rag_hits": ["chongluadao#123"], "timed_out": false }
```

| Trường | Kiểu | Ghi chú |
|---|---|---|
| `verdict` | `"nguy_hiem" \| "co_ve_on"` | Phán quyết cuối của Vùng nghi ngờ |
| `explanation` | `str` | Giải thích sinh ra (hiển thị streaming ở Extension) |
| `rag_hits` | `str[]` | ID/nguồn tài liệu RAG đã dùng (Tầng 1 brand + Tầng 2 ChromaDB) |
| `timed_out` | `bool` | `true` → backend chuyển sang fallback lý do kỹ thuật |

`verdict = "nguy_hiem"` → domain nạp ngược vào blocklist DNR (vòng tự học, Bạn A).

---

## 5. Vector 87 đặc trưng

- Kiểu: `dict {feature_name: number}`.
- Tên + thứ tự: **`src/contracts.py::FEATURE_NAMES`** (87 phần tử). Service trích đặc
  trưng (Bạn A) và code train (Bạn B) import chung hằng số này — không gõ lại danh sách.
- 3 nhóm: `LEXICAL_FEATURES` (56) · `CONTENT_FEATURES` (24) · `EXTERNAL_FEATURES` (7).
- **Bỏ khi train/serve:** 6 cột hằng số trong `dataset_B` (EDA Tuần 1, không phải 3
  như `CLAUDE.md` bản đầu — đã sửa): `sfh`, `ratio_intErrors`, `ratio_intRedirection`,
  `nb_or`, `ratio_nullHyperlinks`, `submit_email` — xem `reports/eda/BAO_CAO_EDA.md`.
- Giá trị "không tra được" của nhóm ngoài là **`-1`**, không phải `NaN`
  (`EXTERNAL_LOOKUP_SENTINEL`). `domain_age == -1` chiếm 15,6% ngay trong tập train
  (thêm `-2`/`-12` là lỗi tính ngày của script gốc, ~0,49% — cũng coi như không hợp lệ).
- Mô hình Lớp B (XGBoost — mục 0) nhận **thứ tự cột cố định** theo
  `contracts.MODEL_FEATURES_FINAL` (30 đặc trưng, đã chốt Tuần 3).

---

## 6. Quyết định (trước đây "còn treo", nay đã chốt — Bạn A triển khai theo)

1. **Cache 24h — key theo `domain`** cho toàn bộ pipeline (điểm mô hình + override +
   verdict), riêng key theo `url` đầy đủ cho **explanation** của Ollama (2 URL cùng
   domain có thể khác path/nội dung → giải thích khác nhau dù verdict domain giống nhau).
2. **Override chạy song song với mô hình Lớp B** — `asyncio.gather` (nếu orchestrator
   async) hoặc thread pool (nếu sync); tổng thời gian chờ = **max** các nhánh, không
   cộng dồn. 3 luật Override tự chúng cũng độc lập với nhau, có thể chạy song song luôn
   (không phụ thuộc kết quả lẫn nhau).
3. **Định dạng `explanation` khi `source = "fallback"`** — template cố định, không
   qua LLM:
   ```
   "Không phân tích sâu được (Ollama timeout/lỗi). Đánh giá kỹ thuật: điểm mô hình "
   f"{clf_score:.2f}"
   + ("; " + "; ".join(f"{o['name']}: {o['reason']}"
                        for o in override_flags if o["flag"] is not False)
      if any(o["flag"] is not False for o in override_flags) else
      "; không luật Override nào bị kích hoạt.")
   ```
   Ví dụ: *"Không phân tích sâu được (Ollama timeout/lỗi). Đánh giá kỹ thuật: điểm mô
   hình 0.72; domain_age: Domain đăng ký 1 ngày trước; typosquatting: Không so khớp
   được brand."*
4. **Mã lỗi HTTP khi `url` không hợp lệ / không fetch được HTML**: vẫn `200` với
   `verdict = "khong_xac_dinh"`, `source = "fallback"`, `explanation` giải thích lý do
   không xử lý được (không trả 4xx/5xx — Extension luôn nhận được 1 JSON hợp lệ để hiển thị).
