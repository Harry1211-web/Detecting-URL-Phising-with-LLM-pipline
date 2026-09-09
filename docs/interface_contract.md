# Hợp đồng interface — chốt Tuần 1

> Trạng thái: **BẢN THẢO của Bạn B** để Bạn A rà và thống nhất.
> Nguồn: `Plan.md` mục 1 & 4, `GhiChu_Pipeline_DeTai.docx` mục 2–3.
> Code hoá tại: `src/contracts.py` (nguồn chân lý — tài liệu này chỉ diễn giải).

Mục đích: sau khi chốt, mỗi người code trên **mock/stub** của phần kia, không chặn
nhau tới mốc tích hợp Tuần 5.

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
  "rf_score": 0.72,
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
| `risk_score` | `float [0,1]` | Điểm rủi ro tổng hợp (RF + Override), để hiển thị/log |
| `rf_score` | `float [0,1]` | Xác suất phishing thô từ Random Forest |
| `override_flags` | `OverrideResult[]` | Kết quả 3 luật (mục 2) |
| `source` | `"blocklist" \| "rf_override" \| "ollama" \| "cache" \| "fallback"` | Tầng nào ra phán quyết |
| `cached` | `bool` | Lấy từ cache domain 24h hay không |
| `latency_ms` | `float` | Tổng thời gian xử lý phía backend |

**Ánh xạ `zone → verdict`:**
- `vung_thap` → `verdict = "an_toan"`, `source = "rf_override"`, **không** gọi Ollama.
- `vung_nghi_ngo` → gọi Ollama; `verdict` theo `OllamaResult.verdict`
  (`nguy_hiem` → `"nguy_hiem"`, `co_ve_on` → `"canh_bao_nhe"`).
- Ollama timeout/lỗi → `verdict` suy từ RF/Override, `source = "fallback"`.
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
| `latency_ms` | `float` | Thời gian chạy luật (mỗi bước mạng timeout ~500ms) |

**Quy tắc bắt buộc:** `"unknown"` **không** đồng nghĩa an toàn. Chỉ `flag === false`
mới coi là "không vi phạm" khi phân vùng. Áp dụng cho:
- `domain_age`: RDAP (IANA bootstrap) → WHOIS fallback; cả 2 rỗng/timeout → `"unknown"`.
  `.vn` không có RDAP → luôn xuống WHOIS (không phải bug).
- `ssl_tls`: không đọc được chứng chỉ → `"unknown"`; chứng chỉ cấp < 2 ngày hoặc
  không hợp lệ → `flag = true`.
- `typosquatting`: Levenshtein vs danh sách brand VN, ngưỡng `max(1, len(brand)//5)`.
  Không match brand nào ở khoảng cách xét → `flag = false` (đã kiểm tra, không phải unknown).
  Thuần tính toán → **không bao giờ trả `"unknown"`**. Brand tên < 5 ký tự bị loại khỏi
  so khớp Levenshtein (giảm bắt nhầm — xem `src/override/typosquatting.py`).

---

## 3. Phân vùng (2 vùng) — `src/contracts.py::phan_vung()`

```
rf_score < NGƯỠNG  VÀ  mọi override_flags[i].flag === false   →  "vung_thap"
còn lại (RF cao HOẶC có ≥1 cờ true/unknown)                    →  "vung_nghi_ngo"
```

- `NGƯỠNG` mặc định khởi động = `0.30` (`RF_LOW_RISK_THRESHOLD_DEFAULT`).
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
  như `CLAUDE.md`): `sfh`, `ratio_intErrors`, `ratio_intRedirection`, `nb_or`,
  `ratio_nullHyperlinks`, `submit_email` — xem `reports/eda/BAO_CAO_EDA.md`.
- Giá trị "không tra được" của nhóm ngoài là **`-1`**, không phải `NaN`
  (`EXTERNAL_LOOKUP_SENTINEL`). `domain_age == -1` chiếm 15,6% ngay trong tập train.
- Model RF nhận **thứ tự cột cố định** theo `FEATURE_NAMES` trừ 6 cột đã bỏ →
  Bạn B sẽ chốt danh sách `MODEL_FEATURES` cuối cùng sau feature selection (Tuần 3)
  và thêm vào `contracts.py`.

---

## 6. Việc còn treo để chốt cùng Bạn A

1. Cơ chế cache 24h: key theo `domain` hay `url`? (đề xuất: `domain` cho pipeline,
   `url` cho kết quả Ollama).
2. Orchestrator gọi Override **song song** với RF (mục 2 `Plan.md`) — xác nhận chạy
   bằng `asyncio.gather` / thread pool, tổng thời gian = max chứ không cộng dồn.
3. Định dạng `explanation` khi `source = "fallback"`: template thuần từ
   `override_flags[].reason` + `rf_score`.
4. Mã lỗi HTTP khi `url` không hợp lệ / không fetch được HTML (đề xuất: vẫn `200`
   với `verdict = "khong_xac_dinh"`, `source = "fallback"`).
