"""Kiểm Override #2 (src/override/ssl_tls.py) — KHÔNG chạm mạng.

Monkeypatch ``_lay_thong_tin_cert`` để test map trạng thái chứng chỉ → flag:
  hop_le + cũ            → False
  hop_le + cấp < 2 ngày  → True
  khong_hop_le           → True (kể cả khi không đọc được ngày)
  khong_doc_duoc         → "unknown" (KHÔNG mặc định an toàn)
"""

from datetime import datetime, timedelta, timezone

from src.override import ssl_tls as st


def _cert(trang_thai, not_before=None, not_after=None, chi_tiet="x") -> st.CertInfo:
    return {"trang_thai": trang_thai, "not_before": not_before,
            "not_after": not_after, "chi_tiet": chi_tiet}


def _truoc(**kw) -> datetime:
    return datetime.now(timezone.utc) - timedelta(**kw)


# --- tach_host_port ---------------------------------------------------------
def test_tach_host_port():
    assert st.tach_host_port("https://sub.vietcombank.com.vn/login?x=1") == ("sub.vietcombank.com.vn", 443)
    assert st.tach_host_port("http://example.com") == ("example.com", 443)
    assert st.tach_host_port("https://example.com:8443/a") == ("example.com", 8443)
    assert st.tach_host_port("user@host.tld:993/x") == ("host.tld", 993)
    assert st.tach_host_port("example.com") == ("example.com", 443)
    assert st.tach_host_port("[2001:db8::1]:8443") == ("2001:db8::1", 8443)


def test_host_rong_thi_unknown(monkeypatch):
    # không có host trong URL
    r = st.kiem_tra_ssl_tls("http:///chi-co-path")
    assert r["flag"] == "unknown"
    assert r["name"] == "ssl_tls"


# --- map trạng thái -> flag -----------------------------------------------
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
    # đúng 2 ngày (>= ngưỡng) -> ổn; strict '<'
    monkeypatch.setattr(st, "_lay_thong_tin_cert",
                        lambda h, p=443: _cert("hop_le", _truoc(days=2, minutes=1)))
    assert st.kiem_tra_ssl_tls("https://x.com")["flag"] is False


def test_nguong_tuy_chinh(monkeypatch):
    monkeypatch.setattr(st, "_lay_thong_tin_cert",
                        lambda h, p=443: _cert("hop_le", _truoc(days=5)))
    assert st.kiem_tra_ssl_tls("https://x.com", nguong_ngay=2)["flag"] is False
    assert st.kiem_tra_ssl_tls("https://x.com", nguong_ngay=30)["flag"] is True


def test_cert_khong_hop_le_thi_true_du_khong_co_ngay(monkeypatch):
    monkeypatch.setattr(st, "_lay_thong_tin_cert",
                        lambda h, p=443: _cert("khong_hop_le", None, None,
                                               "self signed certificate"))
    r = st.kiem_tra_ssl_tls("https://tu-ky.com")
    assert r["flag"] is True
    assert "self signed" in r["reason"]


def test_cert_khong_hop_le_co_ngay_ghi_ngay(monkeypatch):
    nb = _truoc(days=10)
    monkeypatch.setattr(st, "_lay_thong_tin_cert",
                        lambda h, p=443: _cert("khong_hop_le", nb, None, "hostname mismatch"))
    r = st.kiem_tra_ssl_tls("https://sai-ten.com")
    assert r["flag"] is True
    assert nb.date().isoformat() in r["reason"]


def test_khong_doc_duoc_thi_unknown_khong_an_toan(monkeypatch):
    monkeypatch.setattr(st, "_lay_thong_tin_cert",
                        lambda h, p=443: _cert("khong_doc_duoc", chi_tiet="timeout"))
    r = st.kiem_tra_ssl_tls("https://khong-ket-noi.example")
    assert r["flag"] == "unknown"
    assert r["flag"] is not False  # KHÔNG coi là an toàn
    assert set(r) == {"name", "flag", "reason", "latency_ms"}
