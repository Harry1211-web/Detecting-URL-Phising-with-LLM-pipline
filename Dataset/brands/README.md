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
- Các dòng `da_xac_minh` khác (`vietinbank`, `vietbank`, `vnpt`) là do người dùng đánh dấu từ
  trước — giữ nguyên.
- Toàn bộ dòng còn lại: `chua_xac_minh` — cần rà tay theo quy trình trên.

### Cần rà tiếp (ghi chú trong cột `ghi_chu`)

- `moca` — Moca đã dừng dịch vụ ví (2024); cân nhắc bỏ.
- `scb` — SCB đang kiểm soát đặc biệt.
- `gdt` — Tổng cục Thuế có thể đổi tên/đổi domain sau sáp nhập bộ ngành 2025.

## `brands.csv` — thương hiệu quốc tế (Zenodo, 86 brand)

Danh sách brand quốc tế (category / description / identifier / name / website) tải từ Zenodo,
dùng cho **feature extractor gốc** Hannousse & Yahiouche (`domain_in_brand`, `brand_in_subdomain`,
`brand_in_path`) thay cho `allbrands.txt` rút gọn. Không dùng cho Override #3 (Override #3 chỉ so
brand Việt Nam).
