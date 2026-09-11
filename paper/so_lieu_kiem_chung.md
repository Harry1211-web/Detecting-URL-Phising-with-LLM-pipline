# Bảng kiểm chứng số liệu — draft IEEE

Mọi con số định lượng xuất hiện trong `phishing_tiered_ai_draft.md` / `.tex`, kèm nguồn và trạng thái
kiểm chứng (tra cứu web ngày 2026-09-06). Ba loại:

- **[TÀI LIỆU]** — số liệu trích từ công trình đã công bố, có DOI/arXiv/doc chính thức → đã xác minh.
- **[ĐO ĐƯỢC]** — kết quả nhóm tự đo bằng script đã commit trong repo (EDA + train RF); tái tạo bằng
  `python -m src.eda` / `src.train_rf` / `src.train_rf_final`. Số nằm trong `reports/*/summary.json`.
- **[MỤC TIÊU]** — ngưỡng/ngân sách thiết kế, KHÔNG phải kết quả đo. Sẽ đo trong Section VI (phần chưa chạy).

| # | Số liệu trong bài | Giá trị | Loại | Nguồn (ref trong bài) | Trạng thái |
|---|---|---|---|---|---|
| 1 | Dataset train: số URL | 11.430 | [TÀI LIỆU] | Hannousse & Yahiouche, EAAI vol.104 art.104347, 2021 — [2]; Mendeley V3 — [3] | ✅ Khớp chính xác |
| 2 | Dataset train: số đặc trưng | 87 | [TÀI LIỆU] | [2] | ✅ |
| 3 | Phân nhóm đặc trưng | 56 URL / 24 nội dung / 7 dịch vụ ngoài | [TÀI LIỆU] | [2] (abstract nêu rõ) | ✅ |
| 4 | Cân bằng nhãn | 50% / 50% | [TÀI LIỆU] | [2] | ✅ |
| 5 | **6** đặc trưng hằng số = 0 (`sfh`, `ratio_intErrors`, `ratio_intRedirection`, `nb_or`, `ratio_nullHyperlinks`, `submit_email`) | toàn bộ = 0 trong `dataset_B` | [ĐO ĐƯỢC] | `reports/eda/BAO_CAO_EDA.md` mục 1 + `constant_check.csv`; `src/contracts.py::CONSTANT_FEATURES_DATASET_B` | ✅ EDA Tuần 1 xác nhận. Bài (cũ ghi 3) đã sửa thành 6; `CLAUDE.md` cũng đã sửa |
| 6 | `google_index` tương quan với nhãn | Pearson r = **0,731** | [ĐO ĐƯỢC] | `reports/eda/summary.json::corr_google_index` + `target_correlation.csv` | ✅ Đã **khôi phục con số 0,73** vào bài (r=0,73). Kế: `page_rank` −0,51; `nb_www` −0,44 |
| 7 | Dataset Tamal et al. (OFVA) | 247.950 URL (128.541 phishing / 119.409 hợp lệ) | [TÀI LIỆU] | Tamal, Islam, Bhuiyan, Sattar, Frontiers in Computer Science vol.6 art.1308634, 2024 — [5], DOI 10.3389/fcomp.2024.1308634 | ✅ (lưu ý: doc thiết kế ghi "~275.000" — số đúng là 247.950) |
| 8 | OFVA rút gọn còn | 42 đặc trưng intra-URL | [TÀI LIỆU] | [5] | ✅ |
| 9 | GPT-4V (ChatPhishDetector): precision / recall | 98,7% / 99,6% | [TÀI LIỆU] | Koide, Nakano, Chiba, *IEEE Access* vol.12 pp.154381–154400, 2024 — [6], DOI 10.1109/ACCESS.2024.3483905 | ✅ |
| 10 | PhishLang: tiết kiệm bộ nhớ | tối đa 7× so với kiến trúc tương đương | [TÀI LIỆU] | Roy & Nilizadeh, arXiv:2408.05667, 2024 — [8] | ✅ |
| 11 | PhishLang: số site phishing bị gỡ | ~26.000 trong 3,5 tháng | [TÀI LIỆU] | [8] | ✅ |
| 12 | *Scientific Reports* 2026 [29]: mô tả phương pháp | định tính (đã **bỏ** con số 98,7% / 0,96 khỏi thân bài) | [TÀI LIỆU] | Dandotiya, Goyal, Khunteta, Tiwari, *Scientific Reports* vol.16 no.1 **art. 6612** (KHÔNG phải 35655), 29/01/2026 — [29], DOI 10.1038/s41598-026-35655-7 (đã resolve; Crossref + PubMed xác nhận) | ✅ DOI thật, tác giả + số bài đã sửa. Con số accuracy/MCC chưa tự đọc lại được từ toàn văn (Nature paywall) nên bài chỉ mô tả định tính "strong accuracy on PhishTank-based benchmarks" |
| 13 | `declarativeNetRequest`: luật động "safe" tối đa | 30.000 / extension | [TÀI LIỆU] | Chrome for Developers, API reference — [19] | ✅ (`MAX_NUMBER_OF_DYNAMIC_RULES` = 30000) |
| 14 | `declarativeNetRequest`: luật "unsafe" tối đa | 5.000 | [TÀI LIỆU] | [19] | ✅ |
| 15 | Static rulesets bật đồng thời | ≤ 50 (Chrome 120+) | [TÀI LIỆU] | [19] | ✅ |
| 16 | OWASP LLM Top 10 2025: hạng prompt injection | LLM01 (hạng 1) | [TÀI LIỆU] | OWASP GenAI Security Project, v2.0, 18/11/2024 — [9] | ✅ |
| 17 | OWASP LLM: data/model poisoning; embedding; excessive agency | LLM04 / LLM08 / LLM06 | [TÀI LIỆU] | [9] | ✅ |
| 18 | ICANN bỏ yêu cầu WHOIS cổng 43 cho gTLD | từ 28/01/2025 | [TÀI LIỆU] | ICANN — [18]; RFC 9224/9082/9083 — [15]–[17] | ✅ |
| 19 | Guardio: AI browser bị lừa vào luồng phishing | định tính (đã **bỏ** con số "under four minutes" khỏi thân bài) | [TÀI LIỆU – xám] | Guardio Labs "Scamlexity" + PromptFix, 8/2025 — [10]; URL blog chính xác đã thay vào `.bib` (labs.guard.io/scamlexity-...); nguồn thứ cấp The Hacker News 25/08/2025 | ✅ Nguồn công nghiệp (không bình duyệt) — đã ghi rõ nhãn "non-peer-reviewed vendor research" |
| 20 | `nomic-embed-text` | 137M tham số, context 8192, Apache-2 | [TÀI LIỆU] | Nussbaum, Morris, Duderstadt, Mulyar, arXiv:2402.01613, 2024 — [12] | ✅ (chi tiết 137M/8192 chưa đưa vào thân bài, chỉ trong ref) |
| 21 | PhiUSIIL: kích thước | 235.795 URL (134.850 hợp lệ / 100.945 phishing) | [TÀI LIỆU] | Prasad & Chandra, *Computers & Security* vol.136 art.103545, 2024 — [13]; UCI #967 | ✅ |
| 22 | Model LLM local + dung lượng | `qwen3.5:2b` ~2,7 GB (lượng tử hoá), vừa 4 GB VRAM GTX 1650; `qwen3.5:4b` ~3,4 GB là bản mạnh hơn (có thể tràn CPU) | [TÀI LIỆU + MỤC TIÊU] | Ollama library `ollama.com/library/qwen3.5` (tra 2026-09-06): Qwen3.5 small series 0.8b/2b/4b/9b, phát hành 2/2026, hỗ trợ thinking + tool calling + ảnh, context 256K. `qwen3.5:2b` = 2,7 GB đúng như bản gốc — [26], [27], [36] | ✅ Model + dung lượng khớp tài liệu. ⚠️ Việc "vừa VRAM có headroom" vẫn phải xác nhận bằng `ollama ps` (PROCESSOR = 100% GPU) khi cài |
| 23 | Timeout Override (RDAP/WHOIS/SSL) | ≈ 500 ms/bước | [MỤC TIÊU] | Lựa chọn thiết kế | ⚠️ Chưa đo |
| 24 | Cert TLS "quá mới" bị gắn cờ | cấp < 2 ngày | [MỤC TIÊU] | Lựa chọn thiết kế (heuristic) | ⚠️ Ngưỡng thiết kế, chưa hiệu chỉnh |
| 25 | Ngưỡng Levenshtein typosquatting | `max(1, floor(len(brand)/5))` | [MỤC TIÊU] | Lựa chọn thiết kế | ⚠️ Công thức thiết kế, chưa đánh giá false-match |
| 26 | Cache theo domain | 24 giờ | [MỤC TIÊU] | Lựa chọn thiết kế | ⚠️ |
| 27 | k trong k-fold CV | 5 | [MỤC TIÊU/PHƯƠNG PHÁP] | Chuẩn thực hành + [5] | Phương pháp, chưa chạy |
| 28 | Feature selection giữ lại | **30** đặc trưng (mốc top-30, ROC-AUC 0,99235 vs mốc-81 0,99353, chênh < dung sai 0,002) | [ĐO ĐƯỢC] | `reports/rf_final/selected_features.json` + `feature_selection.csv`; `src/feature_selection.py` | ✅ Đã chốt 30, thay "~30–42" trong bài |
| 29 | `.vn` chưa hỗ trợ RDAP | (định tính) | [TÀI LIỆU – gián tiếp] | IANA RDAP bootstrap registry (`dns.json`) không liệt kê `.vn`; RFC 9224 — [15] | ⚠️ Nên chụp lại `dns.json` làm bằng chứng khi viết phần thực nghiệm |
| 30 | Tỉ lệ traffic thật là hợp pháp | ">99%" (đã đổi thành "overwhelmingly"/"đại đa số" trong bài) | [GIẢ ĐỊNH] | Giả định thiết kế; hiệu chỉnh ngưỡng dùng danh sách Tranco — [11] | ⚠️ Đã **hạ giọng** thành định tính, không chốt con số |
| 31 | Alexa web-traffic rank ngừng hoạt động | 01/05/2022 (API 08/12/2022) | [TÀI LIỆU] | BleepingComputer / Engadget / Wikipedia "Alexa Internet" (tra 2026-09) | ✅ Dùng để lập luận đặc trưng `web_traffic` không tái tạo được lúc suy luận (Section II-A, III-C) |
| 32 | ICANN bỏ nghĩa vụ WHOIS cổng 43 (gTLD) | 28/01/2025; Registration Data Policy hiệu lực 21/08/2025 | [TÀI LIỆU] | ICANN announcement 27-01-2025 — [18] (URL cụ thể đã thay vào `.bib`) | ✅ |
| 33 | Ngưỡng số đăng ký trước Section VI | FPR ≤ 0,5%; routing ≤ 5%; ≥100 cặp injection; flip <5%; ≥200 URL gán nhãn; Layer A <10ms; low-zone p95 <1,5s | [MỤC TIÊU] | Nhóm tự đặt — Bảng 3 trong bài | ⚠️ Mục tiêu thiết kế, sẽ đo ở Section VI |
| 34 | Ref mới [32]–[35] (URLNet, Phishpedia, PhishIntention, Oest "Sunrise to Sunset") | — | [TÀI LIỆU] | arXiv:1802.03162; USENIX Security 2021 tr.3793–3810; USENIX Security 2022 tr.1633–1650; USENIX Security 2020 | ✅ Đã xác minh venue/năm (tra 2026-09) |
| 35 | Ref mới [36] Qwen3.5 model card | — | [TÀI LIỆU] | `ollama.com/library/qwen3.5` + arXiv:2604.15804 (Qwen3.5-Omni Technical Report, 4/2026) | ✅ Tra 2026-09-06 |
| 36 | Ref mới [37]–[38] (typosquatting: Szurdi USENIX Sec 2014, Agten NDSS 2015) | — | [TÀI LIỆU] | USENIX Security Symp. 2014; NDSS 2015 | ✅ Tra 2026-09-06 |
| 37 | Bảng 4 (`.tex`) — mô hình chi phí minh hoạ | N=10⁴/ngày, p=0,05, f_g/f_b=0,7/0,3 | [GIẢ ĐỊNH] | Nhóm tự đặt để minh hoạ cấu trúc trade-off; KHÔNG phải số đo | ⚠️ Ghi rõ "assumptions, not measurements" trong caption |
| 38 | EDA: cân bằng nhãn / NaN / URL trùng | 5.715/5.715 · 0 NaN · 1 URL trùng (bỏ trước split) · `domain_age = −1` ở 15,58% dòng | [ĐO ĐƯỢC] | `reports/eda/summary.json`, `missing_sentinel.csv` | ✅ Section VII (Preliminary Results) |
| 39 | RF v1 (81 đặc trưng, split 80/20, GridSearchCV k=5 refit ROC-AUC) | 5-fold ROC-AUC 0,9935±0,0007; test ROC-AUC 0,9924 / acc 0,9611 / F1 0,9612 | [ĐO ĐƯỢC] | `reports/rf_v1/summary.json` + `BAO_CAO_RF_V1.md`; `models/rf_v1.joblib` | ✅ `random_state=42`, tái tạo `python -m src.train_rf` |
| 40 | RF final (30 đặc trưng, grid rộng) | 5-fold ROC-AUC 0,9924±0,0008; test ROC-AUC 0,9914 / acc 0,9545 / F1 0,9547 | [ĐO ĐƯỢC] | `reports/rf_final/summary.json` + `so_sanh_mo_hinh.csv` | ✅ Cắt 81→30 mất ~0,7 điểm acc |
| 41 | RF fast (25 đặc trưng, không cần mạng) vs RF final | test acc 0,9296 vs 0,9545 (−2,5 đ); test ROC-AUC 0,9763 vs 0,9914; recall phishing −3,4 đ; 5 đặc trưng ngoài ≈46% importance | [ĐO ĐƯỢC] | `reports/rf_final/summary.json` (`rf_fast`) + `BAO_CAO_RF_FINAL.md` mục 2.3 | ✅ Định lượng rủi ro phụ thuộc tra cứu ngoài |
| 42 | XGBoost (30 đặc trưng) | 5-fold ROC-AUC 0,9942; test ROC-AUC 0,9924 / acc 0,9633 / F1 0,9634; train nhanh ~5× | [ĐO ĐƯỢC] | `reports/rf_final/summary.json` (`xgb_final`); `models/xgb_final.joblib` | ✅ Ghi là "phương án dự phòng mạnh", chốt sau Tuần 6 |
| 43 | Override #1/#2/#3 + 48 test | RDAP→WHOIS (`.vn` skiplist, 0,5s, 90 ngày mặc định) · TLS xác thực + chống SSRF · Levenshtein 62 brand VN | [ĐO ĐƯỢC – triển khai] | `src/override/*`, `tests/` (48 test offline, pytest xanh); commit 56ece0a / 7963dde / 5a2e2d2 | ✅ Chạy thử thật: github/google → không cờ; vietcombank.com.vn → unknown; badssl self-signed/expired/wrong-host → cờ; loopback / cổng 22 → chặn |
| 44 | Danh sách brand VN | 62 brand (ngân hàng / ví / TMĐT / viễn thông-CN / hàng không / dịch vụ công) | [ĐO ĐƯỢC – triển khai] | `src/override/brands_vn.json` (`_meta.so_luong = 62`) | ⚠️ `trang_thai = BAN_THAO_CAN_RA_SOAT` — phải đối chiếu NCSC / chongluadao.vn trước khi chốt số báo cáo |

## Ghi chú quan trọng về liêm chính học thuật

1. **Bài nay CÓ kết quả Lớp B** (Section VII — EDA + RF v1/final/fast + XGBoost + 3 override, 48 test),
   tất cả tái tạo được từ script đã commit, trên tập cân bằng 50/50. **Vùng nghi ngờ (LLM + RAG) chưa
   xây** → không có số accuracy/latency/injection cho tầng đó; nói rõ ở abstract, "Manuscript status",
   Section VI intro, Section VIII (Limitations). Không có tuyên bố end-to-end.
2. **Con số r = 0,731** (`google_index`) nay **đã đưa vào bài** (r=0,73) vì EDA Tuần 1 đã sinh bảng
   tương quan (`reports/eda/target_correlation.csv`).
3. **Netcraft "90.000 luật", Bolster AI "99,999%"** trong doc thiết kế: là tuyên bố marketing của nhà
   cung cấp, **không đưa vào** bài để tránh trích dẫn số liệu không kiểm chứng được.
4. **Đã xử lý (2026-09):**
   - `[29]` Scientific Reports 2026 — điền tác giả (Dandotiya, Goyal, Khunteta, Tiwari), sửa số bài
     6612 (không phải 35655); bỏ con số 98,7%/0,96 khỏi thân bài vì chưa đọc lại được toàn văn.
   - `[10]` Guardio — thay `guard.io/labs` bằng link blog "Scamlexity" chính xác; bỏ "4 phút" khỏi bài.
   - `[18]` ICANN — trỏ tới announcement 27-01-2025 cụ thể thay cho URL chung.
   - `qwen3.5:2b`: **giữ nguyên** — model CÓ THẬT (Qwen3.5 small series phát hành 2/2026, sau
     knowledge cutoff nên tra sót lần đầu). `qwen3.5:2b` = 2,7 GB đúng như bản gốc ghi. Đã thêm
     ref [36] (Ollama model card) + note vào [27].
5. **RFC 9224** tác giả Marc Blanchet — nên đối chiếu lại tại rfc-editor.org/info/rfc9224 khi hoàn thiện.
6. **Còn phải làm tay trước khi nộp:** đọc toàn văn `[29]` để xác nhận (hoặc bỏ hẳn) các con số
   accuracy/MCC nếu muốn trích số; xác nhận `dns.json` của IANA không liệt kê `.vn` (chụp màn hình);
   rà 62 brand VN với NCSC / chongluadao.vn (file đang `BAN_THAO_CAN_RA_SOAT`).
7. **Còn nợ trong Section VI-A** (đã ghi trong bài): khoảng tin cậy 95%, reliability diagram/ECE,
   dedupe theo registrable domain trước khi split (hiện chỉ bỏ 1 URL trùng nguyên văn).
8. **Số Lớp B là trên tập 50/50** — KHÔNG phải operating point. FPR / routing-rate thật cần hiệu
   chỉnh trên traffic mô phỏng 95% Tranco / 5% phishing (Section VI-B, chưa chạy).
