# Danh sách thương hiệu — `Dataset/brands/`

## `vn_brand_domains.csv` — thương hiệu Việt Nam hay bị giả mạo phishing

**Nguồn chân lý** cho Override #3 (Levenshtein typosquatting, `src/override/typosquatting.py`
qua loader `src/override/brands.py`) và RAG Tầng 1 (structured lookup — Tuần 5).

Thay cho `src/override/brands_vn.json` (đã bỏ). Lý do đổi sang CSV: có cột `verified` để
theo dõi tiến độ rà tay từng dòng — bắt đúng rủi ro "brand tưởng ổn định nhưng đổi tên/đổi
domain liên tục".

### Cột

| Cột | Ý nghĩa |
|---|---|
| `brand` | Nhãn để so Levenshtein (thường = phần đầu domain chính, không dấu, không TLD, chỉ chữ/số). **Duy nhất.** |
| `domain` | 1 domain chính thức. 1 brand có thể nhiều dòng (vd `viettel.vn` + `viettel.com.vn`). |
| `category` | `ngan_hang` \| `vi_dien_tu` \| `thuong_mai_dien_tu` \| `vien_thong` \| `hang_khong` \| `dich_vu_cong` |
| `verified` | `da_xac_minh` = đã đối chiếu tên **và** domain với nguồn chính chủ · `chua_xac_minh` = chưa |
| `ghi_chu` | Đổi tên / đổi domain / cảnh báo. Không chứa dấu phẩy (giữ CSV phẳng). |

### Quy trình xác minh (đổi `chua_xac_minh` → `da_xac_minh`)

1. **Nguồn xác minh chính = SBV** (cơ quan cấp phép, không phải bên thứ 3 diễn giải lại):
   - Ngân hàng: `sbv.gov.vn` — "Danh sách các NHTM Nhà nước" / "Danh sách các NHTMCP trong nước"
     (bản mới nhất tra được: **30/9/2024**, 31 NHTMCP trong nước).
   - Ví điện tử / trung gian thanh toán: `sbv.gov.vn` — "DANH SÁCH CÁC TỔ CHỨC KHÔNG PHẢI LÀ
     NGÂN HÀNG ĐƯỢC NHNN CẤP GIẤY PHÉP HOẠT ĐỘNG CUNG ỨNG DỊCH VỤ TRUNG GIAN THANH TOÁN"
     (bản mới nhất: **09/12/2024**, ~50 tổ chức).
2. **Domain**: xác nhận trên chính website thương hiệu (link chân trang / trang "liên hệ").
3. **Nguồn phụ, chỉ để tra nhanh / sao chép tên** — KHÔNG dùng làm xác minh cuối:
   Wikipedia tiếng Việt "Danh sách ngân hàng tại Việt Nam" (có link Wayback về từng trang SBV).

### Đã đối chiếu web ngày 2026-09-10 (phiên Claude Code)

- **Sacombank** — NHNN ra QĐ 36/QĐ-QLGS4 ngày 01/6/2026: đổi tên ĐKKD "Sài Gòn Thương Tín"
  → **"Sài Gòn Tài Lộc"** (EN: Saigon Treasure Commercial Joint Stock Bank). **Viết tắt vẫn là
  SACOMBANK, domain `sacombank.com.vn` giữ nguyên** (thông báo đăng trên chính sacombank.com.vn).
  ⇒ nhãn + domain trong file KHÔNG đổi; chỉ ghi chú lịch sử tên. `verified = da_xac_minh`.
- **LPBank** — tên cũ LienVietPostBank; NHNN chấp thuận đổi viết tắt thành **LPBank** (2023).
  ⇒ đã thay dòng `lienvietpostbank` (bản nháp cũ) bằng `lpbank` / `lpbank.com.vn`.
  `verified = da_xac_minh`.

### Đã rà toàn bộ ngày 2026-09-14 (phiên Claude Code) — 63/68 brand `da_xac_minh`

Đối chiếu trực tiếp 2 danh sách SBV (fetch trực tiếp, không qua bên thứ 3):
- **NHTMCP trong nước, tính đến 30/9/2024** — 31 ngân hàng.
- **Tổ chức được cấp phép trung gian thanh toán, tính đến 30/4/2026** — 53 tổ chức.

**Phát hiện quan trọng — brand đổi tên/thiếu sót so với danh sách bản thảo cũ:**
- **DongA Bank → Ngân hàng Số Vikki (Vikki Bank)** từ 14/02/2025 (QĐ 42/QĐ-TTGSNH2 +
  237/QĐ-NHNN của NHNN), sau khi chuyển giao bắt buộc về HDBank (sở hữu 100%). Domain mới:
  `vikkibank.vn`. Đây là brand **thiếu hoàn toàn** trong bản thảo trước — thêm mới.
- **Ngân hàng Bản Việt → BVBank** (đổi thương hiệu hiển thị 2022), domain `bvbank.net.vn` —
  cũng thiếu trong bản thảo trước (dù đã nhắc tới trong ghi_chu của `timo`), thêm mới.
- **Kienlongbank** (`kienlongbank.com`) và **PGBank** (`pgbank.com.vn`, tên cũ Ngân hàng Xăng
  dầu Petrolimex) — 2 trong 31 NHTMCP của SBV nhưng thiếu hoàn toàn trong bản thảo cũ, thêm mới.
- **NAPAS** (`napas.com.vn`) — hạ tầng chuyển mạch/bù trừ liên ngân hàng quốc gia, có trong
  danh sách trung gian thanh toán SBV nhưng thiếu trong bản thảo cũ dù là mục tiêu mạo danh
  giá trị rất cao (hầu hết app ngân hàng đều dẫn chiếu NAPAS) — thêm mới.
- **Moca** — SBV (30/4/2026) vẫn liệt kê pháp nhân "MoCa" còn giấy phép hợp lệ, NHƯNG ví điện
  tử tiêu dùng trên Grab đã ngừng nhận người dùng mới + hoàn tiền toàn bộ từ 1/7/2024. Cả 2 vế
  đều đúng cùng lúc (pháp nhân còn hoạt động dịch vụ khác cho Grab, sản phẩm ví bán lẻ thì
  ngừng) — giữ trong danh sách, `da_xac_minh`, ghi chú làm rõ mức độ liên quan giảm.
- **SCB** — vẫn bị kiểm soát đặc biệt (từ 10/2022) nhưng hoạt động bình thường tính đến
  10/2026; đã dời trụ sở chính 09/2026 — domain `scb.com.vn` không đổi.
- **GDT (Tổng cục Thuế)** — tên cơ quan đổi thành "Cục Thuế" (trực thuộc Bộ Tài Chính, sau
  sáp nhập bộ ngành) nhưng domain `gdt.gov.vn` không đổi; dịch vụ thuế điện tử đang chuyển từ
  `thuedientu.gdt.gov.vn` sang `dichvucong.gdt.gov.vn` (từ 01/7/2025), vẫn cùng domain gốc.
- **VNPT / Viettel** — bổ sung thêm domain xác nhận được: `vnpt.vn` (song song `vnpt.com.vn`
  đã có) và `vietteltelecom.vn` (cổng bán lẻ Viettel Telecom, song song `viettel.vn`/
  `viettel.com.vn` đã có — 2 domain này CHƯA fetch xác nhận lại được do trang JS nặng, vẫn giữ
  `chua_xac_minh`, cần rà tay).

**Còn `chua_xac_minh` (5 dòng)**: `cake`, `timo` (thương hiệu con của ngân hàng khác, không
tách riêng trong danh sách NHTMCP của SBV nên không đối chiếu trực tiếp được), `viettel.vn`,
`viettel.com.vn` (chưa fetch lại được), `vng.com.vn`, `zalo.me` (chưa có nguồn xác minh độc lập
ngoài hiểu biết chung — cần rà tay).

**Còn cần rà tiếp dù đã `da_xac_minh`:** `moca` (theo dõi nếu SBV thu hồi giấy phép), `scb`
(theo dõi tình trạng kiểm soát đặc biệt), `gdt` (theo dõi tiến độ chuyển hẳn sang
`dichvucong.gdt.gov.vn`).

## `brands.csv` — thương hiệu quốc tế (Zenodo, 86 brand)

Danh sách brand quốc tế (category / description / identifier / name / website) tải từ Zenodo,
dùng cho **feature extractor gốc** Hannousse & Yahiouche (`domain_in_brand`, `brand_in_subdomain`,
`brand_in_path`) thay cho `allbrands.txt` rút gọn. Không dùng cho Override #3 (Override #3 chỉ so
brand Việt Nam).
