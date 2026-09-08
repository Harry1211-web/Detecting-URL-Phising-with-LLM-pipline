"""Kiểm Override #1 (src/override/domain_age.py) — KHÔNG chạm mạng.

Monkeypatch 2 hàm tra cứu (_rdap_ngay_dang_ky, _whois_ngay_dang_ky) để test
logic: thứ tự RDAP→WHOIS, ngưỡng tuổi, và quy tắc "rỗng cả hai → unknown,
không mặc định an toàn".

Chạy: pytest -q  hoặc chạy tay như tests/test_contracts.py
"""

from datetime import datetime, timedelta, timezone

from src.override import domain_age as da


def _ngay_truoc(n: int) -> datetime:
    return datetime.now(timezone.utc) - timedelta(days=n)


def test_chuan_hoa_domain():
    assert da.chuan_hoa_domain("https://sub.vietcombank.com.vn/login?x=1") == "vietcombank.com.vn"
    assert da.chuan_hoa_domain("http://www.shopee.vn") == "shopee.vn"
    assert da.chuan_hoa_domain("tpb.vn") == "tpb.vn"
    assert da.chuan_hoa_domain("user@mail.google.com:443/path") == "google.com"


def test_vn_bo_qua_rdap():
    # .vn nằm trong TLD_KHONG_CO_RDAP → _rdap_ngay_dang_ky trả None mà không gọi mạng
    assert da._rdap_ngay_dang_ky("vietcombank.com.vn") is None
    assert da._rdap_ngay_dang_ky("vneid.gov.vn") is None


def test_flag_true_khi_domain_non(monkeypatch):
    monkeypatch.setattr(da, "_rdap_ngay_dang_ky", lambda d: _ngay_truoc(10))
    monkeypatch.setattr(da, "_whois_ngay_dang_ky", lambda d: None)
    r = da.kiem_tra_tuoi_domain("https://vi-du-moi-toanh.com")
    assert r["name"] == "domain_age"
    assert r["flag"] is True
    assert "RDAP" in r["reason"]


def test_flag_false_khi_domain_cu(monkeypatch):
    monkeypatch.setattr(da, "_rdap_ngay_dang_ky", lambda d: None)
    monkeypatch.setattr(da, "_whois_ngay_dang_ky", lambda d: _ngay_truoc(5 * 365))
    r = da.kiem_tra_tuoi_domain("https://cong-ty-lau-doi.vn")
    assert r["flag"] is False
    assert "WHOIS" in r["reason"]


def test_whois_chi_goi_khi_rdap_rong(monkeypatch):
    goi = {"rdap": 0, "whois": 0}

    def fake_rdap(d):
        goi["rdap"] += 1
        return _ngay_truoc(1000)

    def fake_whois(d):  # không được gọi
        goi["whois"] += 1
        return None

    monkeypatch.setattr(da, "_rdap_ngay_dang_ky", fake_rdap)
    monkeypatch.setattr(da, "_whois_ngay_dang_ky", fake_whois)
    da.kiem_tra_tuoi_domain("https://co-rdap.com")
    assert goi == {"rdap": 1, "whois": 0}


def test_rong_ca_hai_thi_unknown_khong_an_toan(monkeypatch):
    monkeypatch.setattr(da, "_rdap_ngay_dang_ky", lambda d: None)
    monkeypatch.setattr(da, "_whois_ngay_dang_ky", lambda d: None)
    r = da.kiem_tra_tuoi_domain("https://an-danh.example")
    assert r["flag"] == "unknown"
    assert r["flag"] is not False  # KHÔNG được coi là an toàn
    assert set(r) == {"name", "flag", "reason", "latency_ms"}


def test_nguong_tuy_chinh(monkeypatch):
    monkeypatch.setattr(da, "_rdap_ngay_dang_ky", lambda d: _ngay_truoc(120))
    monkeypatch.setattr(da, "_whois_ngay_dang_ky", lambda d: None)
    assert da.kiem_tra_tuoi_domain("https://x.com", nguong_ngay=90)["flag"] is False
    assert da.kiem_tra_tuoi_domain("https://x.com", nguong_ngay=180)["flag"] is True
