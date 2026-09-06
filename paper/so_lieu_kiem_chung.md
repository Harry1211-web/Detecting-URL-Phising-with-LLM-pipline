# Bảng kiểm chứng số liệu — draft IEEE

Mọi con số định lượng xuất hiện trong `phishing_tiered_ai_draft.md` / `.tex`, kèm nguồn và trạng thái
kiểm chứng (tra cứu web ngày 2026-09-06). Ba loại:

- **[TÀI LIỆU]** — số liệu trích từ công trình đã công bố, có DOI/arXiv/doc chính thức → đã xác minh.
- **[QUAN SÁT]** — quan sát của nhóm trên file dataset công khai; nêu rõ là quan sát sơ bộ, chưa phải kết luận.
- **[MỤC TIÊU]** — ngưỡng/ngân sách thiết kế, KHÔNG phải kết quả đo. Sẽ đo trong Section VI.

| # | Số liệu trong bài | Giá trị | Loại | Nguồn (ref trong bài) | Trạng thái |
|---|---|---|---|---|---|
| 1 | Dataset train: số URL | 11.430 | [TÀI LIỆU] | Hannousse & Yahiouche, EAAI vol.104 art.104347, 2021 — [2]; Mendeley V3 — [3] | ✅ Khớp chính xác |
| 2 | Dataset train: số đặc trưng | 87 | [TÀI LIỆU] | [2] | ✅ |
| 3 | Phân nhóm đặc trưng | 56 URL / 24 nội dung / 7 dịch vụ ngoài | [TÀI LIỆU] | [2] (abstract nêu rõ) | ✅ |
| 4 | Cân bằng nhãn | 50% / 50% | [TÀI LIỆU] | [2] | ✅ |
| 5 | 3 đặc trưng hằng số (`sfh`, `ratio_intErrors`, `ratio_intRedirection`) | = 0 toàn bộ trong bản này | [QUAN SÁT] | Nhóm tự kiểm trên file `dataset_phishing.csv` | ⚠️ Cần chạy lại script EDA để in ra bằng chứng (Section VI-A) |
| 6 | `google_index` tương quan mạnh với nhãn | "notably strong" (bài không nêu số 0.73) | [QUAN SÁT] | Nhóm tự kiểm | ⚠️ Đã **bỏ con số 0.73** khỏi bài vì chưa có bảng tương quan chính thức; chỉ nói định tính |
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
| 28 | Feature selection giữ lại | ~30–42 đặc trưng | [MỤC TIÊU] | Theo phương pháp [5]; con số cuối phụ thuộc `feature_importances_` thực tế | ⚠️ Sẽ chốt ở Section VI-A |
| 29 | `.vn` chưa hỗ trợ RDAP | (định tính) | [TÀI LIỆU – gián tiếp] | IANA RDAP bootstrap registry (`dns.json`) không liệt kê `.vn`; RFC 9224 — [15] | ⚠️ Nên chụp lại `dns.json` làm bằng chứng khi viết phần thực nghiệm |
| 30 | Tỉ lệ traffic thật là hợp pháp | ">99%" (đã đổi thành "overwhelmingly"/"đại đa số" trong bài) | [GIẢ ĐỊNH] | Giả định thiết kế; hiệu chỉnh ngưỡng dùng danh sách Tranco — [11] | ⚠️ Đã **hạ giọng** thành định tính, không chốt con số |
| 31 | Alexa web-traffic rank ngừng hoạt động | 01/05/2022 (API 08/12/2022) | [TÀI LIỆU] | BleepingComputer / Engadget / Wikipedia "Alexa Internet" (tra 2026-09) | ✅ Dùng để lập luận đặc trưng `web_traffic` không tái tạo được lúc suy luận (Section II-A, III-C) |
| 32 | ICANN bỏ nghĩa vụ WHOIS cổng 43 (gTLD) | 28/01/2025; Registration Data Policy hiệu lực 21/08/2025 | [TÀI LIỆU] | ICANN announcement 27-01-2025 — [18] (URL cụ thể đã thay vào `.bib`) | ✅ |
| 33 | Ngưỡng số đăng ký trước Section VI | FPR ≤ 0,5%; routing ≤ 5%; ≥100 cặp injection; flip <5%; ≥200 URL gán nhãn; Layer A <10ms; low-zone p95 <1,5s | [MỤC TIÊU] | Nhóm tự đặt — Bảng 3 trong bài | ⚠️ Mục tiêu thiết kế, sẽ đo ở Section VI |
| 34 | Ref mới [32]–[35] (URLNet, Phishpedia, PhishIntention, Oest "Sunrise to Sunset") | — | [TÀI LIỆU] | arXiv:1802.03162; USENIX Security 2021 tr.3793–3810; USENIX Security 2022 tr.1633–1650; USENIX Security 2020 | ✅ Đã xác minh venue/năm (tra 2026-09) |
| 35 | Ref mới [36] Qwen3.5 model card | — | [TÀI LIỆU] | `ollama.com/library/qwen3.5` + arXiv:2604.15804 (Qwen3.5-Omni Technical Report, 4/2026) | ✅ Tra 2026-09-06 |
| 36 | Ref mới [37]–[38] (typosquatting: Szurdi USENIX Sec 2014, Agten NDSS 2015) | — | [TÀI LIỆU] | USENIX Security Symp. 2014; NDSS 2015 | ✅ Tra 2026-09-06 |
| 37 | Bảng 4 — mô hình chi phí minh hoạ | N=10⁴/ngày, p=0,05, f_g/f_b=0,7/0,3 | [GIẢ ĐỊNH] | Nhóm tự đặt để minh hoạ cấu trúc trade-off; KHÔNG phải số đo | ⚠️ Ghi rõ "assumptions, not measurements" trong caption |

## Ghi chú quan trọng về liêm chính học thuật

1. **Bài KHÔNG báo cáo kết quả của hệ thống đề xuất.** Không có số accuracy/precision/recall/latency
   nào của pipeline này trong bài — đúng như hiện trạng (chưa train, chưa đo). Điều này được nói rõ ở
   abstract, mục "Manuscript status", và Section VI.
2. **Con số 0.73** (`google_index`) trong `CLAUDE.md` đã **không** được đưa vào bài vì chưa có bảng
   tương quan tự chạy; bài chỉ nói định tính "notably strong univariate association".
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
   chạy script EDA in ra 3 đặc trưng hằng số làm bằng chứng cho Section VI-A.
