"""Kiểm Override #2 (src/override/ssl_tls.py) — KHÔNG chạm mạng ngoài.

- Map trạng thái chứng chỉ → flag: monkeypatch ``_lay_thong_tin_cert``.
- Chống SSRF: gọi thẳng ``_giai_va_kiem_dich`` / ``kiem_tra_ssl_tls`` với IP
  literal nội bộ (getaddrinfo cục bộ, không ra Internet).
"""

from datetime import datetime, timedelta, timezone

from src.override import ssl_tls as st


def _cert(trang_thai, not_before=None, not_after=None, chi_tiet="x") -> st.CertInfo:
    return {"trang_thai": trang_thai, "not_before": not_before,
            "not_after": not_after, "chi_tiet": chi_tiet}


def _truoc(**kw) -> datetime:
    return datetime.now(timezone.utc) - timedelta(**kw)


# --- tach_host_port ------------------------------------------------------
def test_tach_host_port():
    assert st.tach_host_port("https://sub.vietcombank.com.vn/login?x=1") == ("sub.vietcombank.com.vn", 443)
    assert st.tach_host_port("http://example.com") == ("example.com", 443)
    assert st.tach_host_port("https://example.com:8443/a") == ("example.com", 8443)
    assert st.tach_host_port("user@host.tld:993/x") == ("host.tld", 993)
    assert st.tach_host_port("example.com") == ("example.com", 443)
    assert st.tach_host_port("[2001:db8::1]:8443") == ("2001:db8::1", 8443)


def test_host_rong_thi_unknown():
    r = st.kiem_tra_ssl_tls("http:///chi-co-path")
    assert r["flag"] == "unknown"
    assert r["name"] == "ssl_tls"


# --- chống SSRF --------------------------------------------------------
def test_ip_cong_cong():
    assert st._ip_cong_cong("8.8.8.8") is True
    assert st._ip_cong_cong("1.1.1.1") is True
    for noi_bo in ("127.0.0.1", "10.0.0.1", "192.168.1.1", "169.254.169.254",
                   "::1", "0.0.0.0", "224.0.0.1"):
        assert st._ip_cong_cong(noi_bo) is False, noi_bo


def test_giai_va_kiem_dich_chan_cong_la():
    ok, ip, ly_do = st._giai_va_kiem_dich("127.0.0.1", 22)
    assert ok is False and ip == "" and "cổng" in ly_do


def test_giai_va_kiem_dich_chan_dich_noi_bo():
    ok, ip, ly_do = st._giai_va_kiem_dich("127.0.0.1", 443)
    assert ok is False and "nội bộ" in ly_do
    ok, _, _ = st._giai_va_kiem_dich("169.254.169.254", 443)
    assert ok is False


def test_kiem_tra_ssl_tls_chan_loopback_tra_unknown():
    for u in ("https://127.0.0.1/", "https://[::1]/", "https://10.1.2.3:443/"):
        r = st.kiem_tra_ssl_tls(u)
        assert r["flag"] == "unknown", u
        assert r["flag"] is not False


# --- map trạng thái -> flag (monkeypatch, không mạng) ----------------
def test_cert_hop_le_va_cu_thi_false(monkeypatch):
    monkeypatch.setattr(st, "_lay_thong_tin_cert",
                        lambda h, p=443: _cert("hop_le", _truoc(days=400), _truoc(days=-300)))
    r = st.kiem_tra_ssl_tls("https://cong-ty-lau.com")
    assert r["flag"] is False
    assert set(r) == {"name", "flag", "reason", "latency_ms"}
    assert r["name"] == "ssl_tls"


def test_cert_hop_le_nhung_qua_moi_thi_true(monkeypatch):
    monkeypatch.setattr(st, "_lay_thong_tin_cert",
                        lambda h, p=443: _cert("hop_le", _truoc(hours=6)))
    r = st.kiem_tra_ssl_tls("https://vua-tao.com")
    assert r["flag"] is True
    assert "DƯỚI ngưỡng" in r["reason"]


def test_nguong_cert_moi_dung_bien_2_ngay(monkeypatch):
    monkeypatch.setattr(st, "_lay_thong_tin_cert",
                        lambda h, p=443: _cert("hop_le", _truoc(days=2, minutes=1)))
    assert st.kiem_tra_ssl_tls("https://x.com")["flag"] is False


def test_nguong_tuy_chinh(monkeypatch):
    monkeypatch.setattr(st, "_lay_thong_tin_cert",
                        lambda h, p=443: _cert("hop_le", _truoc(days=5)))
    assert st.kiem_tra_ssl_tls("https://x.com", nguong_ngay=2)["flag"] is False
    assert st.kiem_tra_ssl_tls("https://x.com", nguong_ngay=30)["flag"] is True


def test_cert_khong_hop_le_thi_true(monkeypatch):
    monkeypatch.setattr(st, "_lay_thong_tin_cert",
                        lambda h, p=443: _cert("khong_hop_le", chi_tiet="chứng chỉ tự ký (self-signed)"))
    r = st.kiem_tra_ssl_tls("https://tu-ky.com")
    assert r["flag"] is True
    assert "tự ký" in r["reason"]
    assert set(r) == {"name", "flag", "reason", "latency_ms"}


def test_khong_doc_duoc_thi_unknown_khong_an_toan(monkeypatch):
    monkeypatch.setattr(st, "_lay_thong_tin_cert",
                        lambda h, p=443: _cert("khong_doc_duoc", chi_tiet="không thiết lập được kết nối TLS"))
    r = st.kiem_tra_ssl_tls("https://khong-ket-noi.example")
    assert r["flag"] == "unknown"
    assert r["flag"] is not False
    assert set(r) == {"name", "flag", "reason", "latency_ms"}


def test_lay_thong_tin_cert_chi_tra_chi_tiet_co_dinh():
    # Đích nội bộ / cổng lạ: chi_tiet phải là 1 trong các chuỗi phân loại cố định,
    # tuyệt đối không có str(exception) / traceback / đường dẫn hệ thống.
    hop_le = {"cổng 22 không phải cổng HTTPS chuẩn",
              "không phân giải được tên miền",
              "đích trỏ tới địa chỉ nội bộ/không định tuyến công cộng"}
    assert st._lay_thong_tin_cert("127.0.0.1", 22)["chi_tiet"] in hop_le
    assert st._lay_thong_tin_cert("127.0.0.1", 443)["chi_tiet"] in hop_le


def test_phan_loai_loi_xac_thuc_map():
    class _E(Exception):
        verify_code = 10
    assert "hết hạn" in st._phan_loai_loi_xac_thuc(_E())

    class _E2(Exception):
        verify_code = 999
    assert st._phan_loai_loi_xac_thuc(_E2()) == "chứng chỉ không qua kiểm định tin cậy"
