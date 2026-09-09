"""Kiểm gói Override (src/override/__init__.py): aggregator 3 luật + ghép phân vùng.

Monkeypatch phần chạm mạng của Override #1/#2; Override #3 thuần tính toán.
"""

from datetime import datetime, timedelta, timezone

import src.override as ov
from src.override import domain_age as da
from src.override import ssl_tls as st


def _truoc(days: int) -> datetime:
    return datetime.now(timezone.utc) - timedelta(days=days)


def _mock_mang_sach(monkeypatch):
    """Domain 'cũ' + cert hợp lệ lâu năm → cả 3 Override đều 'ổn' cho domain lạ."""
    monkeypatch.setattr(da, "_rdap_ngay_dang_ky", lambda d: _truoc(2000))
    monkeypatch.setattr(da, "_whois_ngay_dang_ky", lambda d: None)
    monkeypatch.setattr(st, "_lay_thong_tin_cert",
                        lambda h, p=443: {"trang_thai": "hop_le", "not_before": _truoc(500),
                                          "not_after": _truoc(-300), "chi_tiet": "ok"})


def test_chay_tat_ca_override_dung_thu_tu_va_ten(monkeypatch):
    _mock_mang_sach(monkeypatch)
    kq = ov.chay_tat_ca_override("https://trang-la-nhung-lanh.com")
    assert [r["name"] for r in kq] == ["domain_age", "ssl_tls", "typosquatting"]
    assert all(set(r) == {"name", "flag", "reason", "latency_ms"} for r in kq)
    assert all(r["flag"] is False for r in kq)


def test_phan_vung_tu_url_rf_thap_sach_thi_vung_thap(monkeypatch):
    _mock_mang_sach(monkeypatch)
    zone, flags = ov.phan_vung_tu_url("https://trang-la-nhung-lanh.com", rf_score=0.05)
    assert zone == "vung_thap"
    assert len(flags) == 3


def test_phan_vung_tu_url_rf_cao_thi_nghi_ngo(monkeypatch):
    _mock_mang_sach(monkeypatch)
    zone, _ = ov.phan_vung_tu_url("https://trang-la-nhung-lanh.com", rf_score=0.9)
    assert zone == "vung_nghi_ngo"


def test_phan_vung_tu_url_co_co_override_thi_nghi_ngo(monkeypatch):
    _mock_mang_sach(monkeypatch)
    # URL typosquat -> Override #3 = True -> nghi ngờ dù RF thấp
    zone, flags = ov.phan_vung_tu_url("http://vietccombank.com", rf_score=0.01)
    assert zone == "vung_nghi_ngo"
    assert any(r["name"] == "typosquatting" and r["flag"] is True for r in flags)


def test_domain_age_unknown_keo_ve_nghi_ngo(monkeypatch):
    # RDAP + WHOIS đều rỗng -> domain_age = "unknown" -> KHÔNG cho vào vùng thấp
    monkeypatch.setattr(da, "_rdap_ngay_dang_ky", lambda d: None)
    monkeypatch.setattr(da, "_whois_ngay_dang_ky", lambda d: None)
    monkeypatch.setattr(st, "_lay_thong_tin_cert",
                        lambda h, p=443: {"trang_thai": "hop_le", "not_before": _truoc(500),
                                          "not_after": None, "chi_tiet": "ok"})
    zone, flags = ov.phan_vung_tu_url("https://an-danh.example", rf_score=0.01)
    assert zone == "vung_nghi_ngo"
    assert flags[0]["flag"] == "unknown"
