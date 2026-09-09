"""Override #2 — SSL/TLS (Plan.md mục 2 & 3 Tuần 4; CLAUDE.md mục Kiến trúc,
điểm 2 "Luật Override": *"chứng chỉ hợp lệ / cấp quá gần đây (< 2 ngày) là cờ
đáng ngờ"*).

Quy trình:
  1. Bắt tay TLS CÓ xác thực (``ssl.create_default_context``: kiểm chuỗi tin cậy +
     khớp hostname + còn hạn) tới ``host:443``.
  2. Bắt tay OK → đọc ``notBefore`` của chứng chỉ leaf:
       * cấp < ``NGUONG_CERT_MOI_NGAY`` ngày  → flag = True  (cert quá mới → đáng ngờ)
       * cấp >= ngưỡng                          → flag = False (hợp lệ, đủ "tuổi")
  3. Bắt tay báo lỗi XÁC THỰC (self-signed, hết hạn, sai hostname, CA lạ)
     → flag = True (chứng chỉ không hợp lệ). Vẫn cố đọc ``notBefore`` qua kênh
     KHÔNG xác thực để ghi lý do rõ hơn.
  4. Không kết nối được / timeout / cổng không nói TLS → flag = "unknown".
     **KHÔNG mặc định an toàn** (giống Override #1).

Cờ (flag) trả về — khớp ``contracts.OverrideResult``:
  True      — chứng chỉ không hợp lệ HOẶC hợp lệ nhưng cấp < 2 ngày
  False     — chứng chỉ hợp lệ và cấp >= 2 ngày
  "unknown" — không đọc được chứng chỉ (mạng lỗi / timeout / không phải HTTPS)

``NGUONG_CERT_MOI_NGAY`` là MẶC ĐỊNH KHỞI ĐỘNG — hiệu chỉnh lại cùng ngưỡng phân
vùng ở Tuần 6 trên traffic mô phỏng (Plan.md mục 3 Tuần 6).

Chạy thử (có mạng):  python -m src.override.ssl_tls --smoke https://vietcombank.com.vn
"""

from __future__ import annotations

import argparse
import socket
import ssl
import time
from datetime import datetime, timezone
from typing import Literal, TypedDict

from src.contracts import OverrideResult

try:  # đọc notBefore ở nhánh KHÔNG xác thực (chứng chỉ lỗi) — tuỳ chọn
    from cryptography import x509 as _x509
except Exception:  # pragma: no cover - môi trường thiếu gói
    _x509 = None

# Bắt tay TLS = TCP + ClientHello + trao chứng chỉ, hiếm khi xong trong ~500ms
# như 1 GET RDAP đơn lẻ (Override #1). Cho rộng hơn nhưng vẫn chặn trên.
SSL_TIMEOUT_S = 2.0
NGUONG_CERT_MOI_NGAY = 2  # CLAUDE.md: "< 2 ngày" (hiệu chỉnh lại Tuần 6)

TrangThaiCert = Literal["hop_le", "khong_hop_le", "khong_doc_duoc"]


class CertInfo(TypedDict):
    trang_thai: TrangThaiCert
    not_before: datetime | None  # UTC
    not_after: datetime | None   # UTC
    chi_tiet: str


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
# Đọc chứng chỉ
# ---------------------------------------------------------------------------
def _epoch_to_utc(epoch: float | None) -> datetime | None:
    if epoch is None:
        return None
    return datetime.fromtimestamp(epoch, tz=timezone.utc)


def _doc_notbefore_khong_xac_thuc(host: str, port: int) -> tuple[datetime | None, datetime | None]:
    """Nhánh cứu vãn: chứng chỉ ĐÃ trượt xác thực ở ``_lay_thong_tin_cert`` — ở đây
    chỉ mở lại kết nối để ĐỌC ``notBefore``/``notAfter`` phục vụ câu lý do, KHÔNG
    gửi/nhận dữ liệu ứng dụng nào qua socket này. Kết quả vẫn là flag=True (đáng
    ngờ); tắt xác thực ở đây không nới lỏng phán quyết, chỉ làm rõ nguyên nhân.
    """
    if _x509 is None:
        return None, None
    ctx = ssl._create_unverified_context()  # noqa: SLF001 - chỉ để đọc ngày, xem docstring
    try:
        with socket.create_connection((host, port), timeout=SSL_TIMEOUT_S) as sock:
            with ctx.wrap_socket(sock, server_hostname=host) as ssock:
                der = ssock.getpeercert(binary_form=True)
        if not der:
            return None, None
        cert = _x509.load_der_x509_certificate(der)
        nb = cert.not_valid_before_utc
        na = cert.not_valid_after_utc
        return nb, na
    except Exception:
        return None, None


def _lay_thong_tin_cert(host: str, port: int = 443) -> CertInfo:
    """Bắt tay TLS có xác thực; phân loại hop_le / khong_hop_le / khong_doc_duoc.

    Đây là hàm được monkeypatch trong test — giữ chữ ký ổn định.
    """
    ctx = ssl.create_default_context()
    try:
        with socket.create_connection((host, port), timeout=SSL_TIMEOUT_S) as sock:
            with ctx.wrap_socket(sock, server_hostname=host) as ssock:
                cert = ssock.getpeercert() or {}
        nb = _epoch_to_utc(ssl.cert_time_to_seconds(cert["notBefore"])) if cert.get("notBefore") else None
        na = _epoch_to_utc(ssl.cert_time_to_seconds(cert["notAfter"])) if cert.get("notAfter") else None
        return CertInfo(trang_thai="hop_le", not_before=nb, not_after=na,
                        chi_tiet="bắt tay TLS có xác thực thành công")
    except ssl.SSLCertVerificationError as e:
        nb, na = _doc_notbefore_khong_xac_thuc(host, port)
        ly_do = (getattr(e, "verify_message", None) or str(e)).strip()
        return CertInfo(trang_thai="khong_hop_le", not_before=nb, not_after=na,
                        chi_tiet=f"lỗi xác thực chứng chỉ: {ly_do}")
    except (ssl.SSLError, socket.timeout, OSError) as e:
        return CertInfo(trang_thai="khong_doc_duoc", not_before=None, not_after=None,
                        chi_tiet=f"không đọc được chứng chỉ ({type(e).__name__}: {e})")


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

    nb = info["not_before"]
    tuoi_ngay = (datetime.now(timezone.utc) - nb).days if nb else None

    if info["trang_thai"] == "khong_hop_le":
        them = f", chứng chỉ cấp {nb.date().isoformat()}" if nb else ""
        return OverrideResult(
            name="ssl_tls", flag=True, latency_ms=latency_ms,
            reason=f"{host}: {info['chi_tiet']}{them} → đáng ngờ.",
        )

    # trang_thai == "hop_le"
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
