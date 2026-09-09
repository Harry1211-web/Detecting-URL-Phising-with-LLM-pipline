"""Override #2 — SSL/TLS (Plan.md mục 2 & 3 Tuần 4; CLAUDE.md mục Kiến trúc,
điểm 2 "Luật Override": *"chứng chỉ hợp lệ / cấp quá gần đây (< 2 ngày) là cờ
đáng ngờ"*).

Quy trình:
  1. Phân giải hostname và **chặn đích nội bộ** (loopback / private / link-local /
     reserved / multicast) + chỉ cho cổng HTTPS chuẩn — luật này nhận URL kẻ tấn
     công kiểm soát, không được biến thành công cụ dò mạng nội bộ (SSRF).
  2. Bắt tay TLS **CÓ xác thực** (``ssl.create_default_context``: kiểm chuỗi tin
     cậy + khớp hostname + còn hạn), **ghim vào đúng IP đã kiểm** để tránh
     DNS-rebinding, vẫn gửi SNI = hostname gốc.
  3. Bắt tay OK → đọc ``notBefore`` chứng chỉ leaf:
       * cấp < ``NGUONG_CERT_MOI_NGAY`` ngày  → flag = True  (cert quá mới → đáng ngờ)
       * cấp >= ngưỡng                          → flag = False (hợp lệ, đủ "tuổi")
  4. Bắt tay trượt XÁC THỰC (self-signed, hết hạn, sai hostname, CA lạ)
     → flag = True. Lý do phân loại từ ``verify_code`` của OpenSSL (KHÔNG chép
     nguyên văn thông điệp lỗi vào ``reason`` — tránh lộ đường dẫn/chi tiết nội bộ).
  5. Không kết nối được / timeout / cổng không nói TLS / bị chặn ở bước 1
     → flag = "unknown". **KHÔNG mặc định an toàn** (giống Override #1).

Cờ (flag) trả về — khớp ``contracts.OverrideResult``:
  True      — chứng chỉ không hợp lệ HOẶC hợp lệ nhưng cấp < 2 ngày
  False     — chứng chỉ hợp lệ và cấp >= 2 ngày
  "unknown" — không đọc được chứng chỉ (mạng lỗi / timeout / không HTTPS / bị chặn)

``NGUONG_CERT_MOI_NGAY`` là MẶC ĐỊNH KHỞI ĐỘNG — hiệu chỉnh lại cùng ngưỡng phân
vùng ở Tuần 6 trên traffic mô phỏng (Plan.md mục 3 Tuần 6).

Chạy thử (có mạng):  python -m src.override.ssl_tls --smoke https://vietcombank.com.vn
"""

from __future__ import annotations

import argparse
import ipaddress
import socket
import ssl
import time
from datetime import datetime, timezone
from typing import Literal, TypedDict

from src.contracts import OverrideResult

# Bắt tay TLS = TCP + ClientHello + trao chứng chỉ, hiếm khi xong trong ~500ms
# như 1 GET RDAP đơn lẻ (Override #1). Cho rộng hơn nhưng vẫn chặn trên.
SSL_TIMEOUT_S = 2.0
NGUONG_CERT_MOI_NGAY = 2  # CLAUDE.md: "< 2 ngày" (hiệu chỉnh lại Tuần 6)

# Chỉ đi TLS trên cổng HTTPS chuẩn — không dùng luật này để chạm cổng dịch vụ
# khác (22/25/3306/6379...) trên đích bất kỳ.
CONG_HTTPS_CHO_PHEP = frozenset({443, 8443, 4443, 9443})

TrangThaiCert = Literal["hop_le", "khong_hop_le", "khong_doc_duoc"]

# Ánh xạ X509_V_ERR_* (OpenSSL) → câu tiếng Việt CỐ ĐỊNH, an toàn để đưa vào log
# / prompt Ollama / giải thích cho người dùng.
_LOI_XAC_THUC: dict[int, str] = {
    10: "chứng chỉ đã hết hạn",
    9: "chứng chỉ chưa tới ngày hiệu lực",
    18: "chứng chỉ tự ký (self-signed)",
    19: "chuỗi tin cậy tự ký, CA gốc không rõ",
    20: "không tìm được chứng chỉ CA phát hành",
    21: "không dựng được chuỗi tin cậy tới CA",
    62: "tên miền không khớp với chứng chỉ",
}


class CertInfo(TypedDict):
    trang_thai: TrangThaiCert
    not_before: datetime | None  # UTC
    not_after: datetime | None   # UTC
    chi_tiet: str                # LUÔN là chuỗi phân loại cố định, không phải str(e)


# ---------------------------------------------------------------------------
# Tách host:port từ URL (KHÔNG rút về registrable domain — chứng chỉ cấp theo
# FQDN, cần giữ nguyên cả subdomain).
# ---------------------------------------------------------------------------
def tach_host_port(url_hoac_host: str) -> tuple[str, int]:
    raw = url_hoac_host.strip()
    if "://" in raw:
        raw = raw.split("://", 1)[1]
    raw = raw.split("/", 1)[0].split("?", 1)[0].split("#", 1)[0]
    raw = raw.split("@")[-1]
    port = 443
    if raw.startswith("["):  # IPv6 literal: [::1]:8443
        host, _, rest = raw[1:].partition("]")
        if rest.startswith(":") and rest[1:].isdigit():
            port = int(rest[1:])
    elif ":" in raw:
        host, p = raw.rsplit(":", 1)
        if p.isdigit():
            port = int(p)
        else:
            host = raw
    else:
        host = raw
    return host.lower().strip("."), port


# ---------------------------------------------------------------------------
# Chống SSRF: phân giải + loại đích không định tuyến công cộng
# ---------------------------------------------------------------------------
def _ip_cong_cong(ip_txt: str) -> bool:
    try:
        ip = ipaddress.ip_address(ip_txt)
    except ValueError:
        return False
    return not (ip.is_private or ip.is_loopback or ip.is_link_local
                or ip.is_reserved or ip.is_multicast or ip.is_unspecified)


def _giai_va_kiem_dich(host: str, port: int) -> tuple[bool, str, str]:
    """→ (an_toàn, ip_để_kết_nối, lý_do_cố_định_nếu_chặn).

    Trả IP đã kiểm để tầng trên kết nối THẲNG vào đó (không phân giải lại tên →
    khép cửa DNS-rebinding), trong khi vẫn xác thực chứng chỉ theo ``host``.
    """
    if port not in CONG_HTTPS_CHO_PHEP:
        return False, "", f"cổng {port} không phải cổng HTTPS chuẩn"
    try:
        infos = socket.getaddrinfo(host, port, proto=socket.IPPROTO_TCP)
    except (socket.gaierror, UnicodeError, OSError):
        return False, "", "không phân giải được tên miền"
    ips = [sa[0] for *_, sa in infos]
    if not ips:
        return False, "", "không phân giải được tên miền"
    if any(not _ip_cong_cong(ip) for ip in ips):
        return False, "", "đích trỏ tới địa chỉ nội bộ/không định tuyến công cộng"
    return True, ips[0], ""


# ---------------------------------------------------------------------------
# Đọc chứng chỉ
# ---------------------------------------------------------------------------
def _epoch_to_utc(epoch: float | None) -> datetime | None:
    if epoch is None:
        return None
    return datetime.fromtimestamp(epoch, tz=timezone.utc)


def _phan_loai_loi_xac_thuc(e: ssl.SSLCertVerificationError) -> str:
    ma = getattr(e, "verify_code", None)
    return _LOI_XAC_THUC.get(ma, "chứng chỉ không qua kiểm định tin cậy")


def _lay_thong_tin_cert(host: str, port: int = 443) -> CertInfo:
    """Kiểm đích (SSRF) → bắt tay TLS có xác thực → phân loại trạng thái chứng chỉ.

    Đây là hàm được monkeypatch trong test — giữ chữ ký ổn định.
    """
    an_toan, ip, ly_do = _giai_va_kiem_dich(host, port)
    if not an_toan:
        return CertInfo(trang_thai="khong_doc_duoc", not_before=None,
                        not_after=None, chi_tiet=ly_do)

    ctx = ssl.create_default_context()
    try:
        with socket.create_connection((ip, port), timeout=SSL_TIMEOUT_S) as sock:
            with ctx.wrap_socket(sock, server_hostname=host) as ssock:
                cert = ssock.getpeercert() or {}
        nb = _epoch_to_utc(ssl.cert_time_to_seconds(cert["notBefore"])) if cert.get("notBefore") else None
        na = _epoch_to_utc(ssl.cert_time_to_seconds(cert["notAfter"])) if cert.get("notAfter") else None
        return CertInfo(trang_thai="hop_le", not_before=nb, not_after=na,
                        chi_tiet="bắt tay TLS có xác thực thành công")
    except ssl.SSLCertVerificationError as e:
        return CertInfo(trang_thai="khong_hop_le", not_before=None, not_after=None,
                        chi_tiet=_phan_loai_loi_xac_thuc(e))
    except (ssl.SSLError, socket.timeout, OSError):
        return CertInfo(trang_thai="khong_doc_duoc", not_before=None, not_after=None,
                        chi_tiet="không thiết lập được kết nối TLS")


# ---------------------------------------------------------------------------
# Điểm vào Override #2
# ---------------------------------------------------------------------------
def kiem_tra_ssl_tls(url: str,
                     nguong_ngay: int = NGUONG_CERT_MOI_NGAY) -> OverrideResult:
    """Đọc chứng chỉ TLS → contracts.OverrideResult (name='ssl_tls')."""
    t0 = time.perf_counter()
    host, port = tach_host_port(url)

    if not host:
        return OverrideResult(
            name="ssl_tls", flag="unknown",
            latency_ms=round((time.perf_counter() - t0) * 1000, 1),
            reason="Không tách được hostname từ URL để kiểm tra TLS.",
        )

    info = _lay_thong_tin_cert(host, port)
    latency_ms = round((time.perf_counter() - t0) * 1000, 1)

    if info["trang_thai"] == "khong_doc_duoc":
        return OverrideResult(
            name="ssl_tls", flag="unknown", latency_ms=latency_ms,
            reason=f"{host}: {info['chi_tiet']} (không mặc định an toàn).",
        )

    if info["trang_thai"] == "khong_hop_le":
        return OverrideResult(
            name="ssl_tls", flag=True, latency_ms=latency_ms,
            reason=f"{host}: {info['chi_tiet']} → đáng ngờ.",
        )

    # trang_thai == "hop_le"
    nb = info["not_before"]
    tuoi_ngay = (datetime.now(timezone.utc) - nb).days if nb else None

    if tuoi_ngay is not None and tuoi_ngay < nguong_ngay:
        return OverrideResult(
            name="ssl_tls", flag=True, latency_ms=latency_ms,
            reason=f"{host}: chứng chỉ hợp lệ nhưng cấp {nb.date().isoformat()} "
                   f"(~{tuoi_ngay} ngày trước, DƯỚI ngưỡng {nguong_ngay} ngày) → đáng ngờ.",
        )

    ngay_txt = nb.date().isoformat() if nb else "không rõ ngày"
    han_txt = f", hết hạn {info['not_after'].date().isoformat()}" if info["not_after"] else ""
    tuoi_txt = f"~{tuoi_ngay} ngày trước" if tuoi_ngay is not None else "ngày cấp không đọc được"
    return OverrideResult(
        name="ssl_tls", flag=False, latency_ms=latency_ms,
        reason=f"{host}: chứng chỉ hợp lệ, cấp {ngay_txt} ({tuoi_txt}, "
               f"từ ngưỡng {nguong_ngay} ngày){han_txt} → ổn.",
    )


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--smoke", metavar="URL", help="chạy thử thật (cần mạng)")
    args = ap.parse_args()
    if args.smoke:
        import json
        print(json.dumps(kiem_tra_ssl_tls(args.smoke), ensure_ascii=False, indent=2))
    else:
        ap.print_help()
