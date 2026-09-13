# Báo cáo hiệu chỉnh ngưỡng Override #1 (tuổi domain) — 2026-09-13 (Bạn B)

Thay thế "90 ngày" chọn tuỳ ý (Tuần 3) bằng ngưỡng có căn cứ dữ liệu, dùng
Precision/Recall + F-beta (β>1). Tái tạo:

```
python -m src.threshold_domain_age    # -> reports/domain_age_threshold/
```

`random_state` không áp dụng (không train model — chỉ quét ngưỡng trên nhãn thật).

---

## 1. Yêu cầu & phương pháp

**Yêu cầu nghiệp vụ** (đặt ra 2026-09-13): luật `domain_age` không được bỏ lọt quá
nhiều phishing — bắt buộc **Recall ≥ 95%**; trong số các ngưỡng đạt điều kiện đó,
chọn ngưỡng cho **Precision cao nhất**.

**Dữ liệu**: `Dataset/train/dataset_phishing.csv` (cột `domain_age`, đơn vị ngày).
Loại **1.837/11.430 dòng (16,07%)** có `domain_age` âm trước khi quét:

| Giá trị | Số dòng | Diễn giải |
|---|---|---|
| `-1` | 1.781 | Sentinel "không tra được" (`EXTERNAL_LOOKUP_SENTINEL`) |
| `-2` | 55 | Lỗi tính ngày trong script gốc Hannousse & Yahiouche (WHOIS trả ngày sau ngày crawl) |
| `-12` | 1 | Như trên |

Còn lại **9.593 dòng** dùng để quét ngưỡng. Với mỗi ngưỡng nguyên T (1..3.650
ngày = 10 năm), tính đúng vị từ luật thật (`domain_age.py`): **"non" ⇔ tuổi < T**.

**Tiêu chí F-beta**: β = 2 (Recall quan trọng gấp đôi Precision — đúng yêu cầu
"không bỏ lọt phishing"), chỉ dùng để **báo cáo/đối chiếu đường cong**, không dùng
để chọn trực tiếp (lý do — mục 3).

---

## 2. Kết quả — Tầng 1 (đúng yêu cầu gốc) BẤT KHẢ THI

Không có ngưỡng T nào trong 1..3.650 ngày đạt Recall ≥ 95%. Recall chỉ chạm mức
đó khi T vượt xa miền hữu ích:

| T (ngày) | TP | FP | Precision | Recall | F2 |
|---|---|---|---|---|---|
| 30 | 132 | 0 | 1,000 | 0,028 | 0,035 |
| 90 (mốc cũ) | 222 | 10 | **0,957** | 0,047 | 0,058 |
| 365 | 565 | 31 | 0,948 | 0,120 | 0,145 |
| 900 | 930 | 48 | 0,951 | 0,197 | 0,234 |
| 1.825 | 1.488 | 248 | 0,857 | 0,315 | 0,361 |
| 3.650 (biên quét) | 2.384 | 975 | 0,710 | 0,505 | 0,536 |
| 10.000 (ngoài biên quét, tham khảo) | 4.721 | 4.726 | 0,500 | 1,000 | 0,833 |

→ Recall chỉ đạt 100% khi T ≈ 10.000 ngày (~27 năm) — tại đó **Precision rơi về
~50%, đúng bằng tỉ lệ nền của tập cân bằng 50/50** (tương đương đoán ngẫu nhiên).
Tối ưu F2 thuần cũng suy biến về vùng ngưỡng cực lớn này (T≈3.641, Precision chỉ
0,710) vì β=2 đủ lớn để "bắt hết bằng cách coi mọi domain là non" luôn thắng về
điểm số — **cả tiêu chí gốc lẫn F-beta thuần đều không dùng được trực tiếp ở đây**.

**Đây là bằng chứng thực nghiệm trực tiếp cho giới hạn cấu trúc đã ghi trong
`domain_age.py`**: CAIDA/WEIS 2025 ước tính ~34% domain phishing là domain hợp
pháp bị chiếm (đã tồn tại lâu năm) — không thể phân biệt với domain hợp pháp thật
chỉ bằng tuổi đăng ký, dù đặt ngưỡng ở đâu.

---

## 3. Ngưỡng áp dụng — Tầng 2 dự phòng

Vì Tầng 1 bất khả thi, đảo ràng buộc: trong các ngưỡng đạt **Precision ≥ 95%**
(ngang mức tin cậy của mốc 90 ngày cũ), chọn ngưỡng cho **Recall lớn nhất**.

| | Mốc cũ (90 ngày, chọn tuỳ ý) | **Mốc mới (900 ngày, Tầng 2)** |
|---|---|---|
| Precision | 0,9569 | 0,9509 (**−0,6 điểm**, không đáng kể) |
| Recall | 0,0470 | **0,1970 (gấp ~4,2 lần)** |
| F2 | 0,0581 | 0,2341 |

→ **`NGUONG_TUOI_MOI_NGAY` trong `src/override/domain_age.py` đổi 90 → 900**:
cùng mức tin cậy khi luật này báo "non", bắt được phishing nhiều hơn hẳn.

---

## 4. Giới hạn — đọc trước khi dùng số này để báo cáo

1. **Hiệu chỉnh trên tập TRAIN cân bằng 50/50** (Hannousse & Yahiouche) — Precision
   đo trên tập này **lạc quan hơn nhiều** so với traffic thật (>99% hợp pháp).
   **Đây là ngưỡng khởi động có căn cứ dữ liệu, KHÔNG PHẢI ngưỡng cuối** — phải
   hiệu chỉnh lại ở Tuần 6 trên traffic mô phỏng 95% Tranco / 5% phishing, đúng
   nguyên tắc đã áp dụng cho `CLF_LOW_RISK_THRESHOLD_DEFAULT` (ngưỡng phân vùng).
2. **Recall 19,7% vẫn thấp về số tuyệt đối** — luật domain_age đơn lẻ chỉ là 1
   trong 3 luật Override + mô hình Lớp B; không kỳ vọng luật này một mình bắt hết
   phishing (đúng thiết kế "chạy song song", không phải gate riêng).
3. **-2/-12 (56 dòng) là lỗi tính ngày của script gốc**, không phải tín hiệu thật
   — loại đúng, không phải lựa chọn tuỳ tiện.
