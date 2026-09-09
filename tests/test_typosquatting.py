"""Kiểm Override #3 (src/override/typosquatting.py) — thuần tính toán, không mạng.

Bám sát tiêu chí nghiệm thu Plan.md mục 7: *"typosquatting bắt đúng `paypa1.com`
kiểu, không bắt nhầm brand tên ngắn"* (ở đây dùng brand VN thật trong
brands_vn.json).
"""

from src.override.typosquatting import kiem_tra_typosquatting as f


def _flag(url):
    return f(url)["flag"]


# --- domain chính thức -> False ------------------------------------------
def test_domain_chinh_thuc_khong_bao():
    assert _flag("https://vietcombank.com.vn/login") is False
    assert _flag("http://www.shopee.vn") is False
    assert _flag("https://tpb.vn") is False  # domain phụ của TPBank cũng trong list


# --- typosquat chính tả -> True ----------------------------------------
def test_typo_1_ky_tu_bi_bao():
    r = f("http://vietccombank.com")          # thêm 1 'c'
    assert r["flag"] is True
    assert "Levenshtein = 1" in r["reason"]
    assert "Vietcombank" in r["reason"]
    assert _flag("http://vietcombankk.com") is True
    assert _flag("http://techcombannk.com") is True


def test_mao_danh_truc_tiep_dung_ten_khac_tld():
    # 'payoo' (>=5 ký tự) đúng tên brand nhưng .com thay vì .vn chính thức
    r = f("http://payoo.com")
    assert r["flag"] is True
    assert "Payoo" in r["reason"]


def test_brand_nhung_trong_nhan():
    assert _flag("http://techcombank-security.com") is True
    assert _flag("http://shopee-khuyen-mai.net") is True


def test_brand_trong_subdomain():
    r = f("http://vietcombank.dang-nhap-lai.com")
    assert r["flag"] is True
    assert "ubdomain" in r["reason"]


# --- KHÔNG bắt nhầm ------------------------------------------------------
def test_brand_ten_ngan_khong_bi_bao_nham():
    # mã ngân hàng 3 ký tự: không được match Levenshtein với nhau
    assert _flag("http://acb.com") is False
    assert _flag("http://scb.xyz") is False
    assert _flag("http://abc.com") is False
    assert _flag("http://cba.com") is False


def test_domain_khong_lien_quan():
    assert _flag("https://www.google.com") is False
    assert _flag("https://github.com/a/b") is False
    assert _flag("https://en.wikipedia.org") is False


def test_dia_chi_ip_bo_qua():
    r = f("http://192.168.1.10/login")
    assert r["flag"] is False
    assert "IP" in r["reason"]


# --- hình dạng kết quả -------------------------------------------------
def test_ket_qua_dung_contract():
    r = f("http://vietccombank.com")
    assert set(r) == {"name", "flag", "reason", "latency_ms"}
    assert r["name"] == "typosquatting"
    assert isinstance(r["latency_ms"], float)


def test_khong_bao_gio_unknown():
    for u in ("http://vietcombank.com.vn", "http://acb.com", "http://x.io",
              "http://vietccombank.com", "http://1.2.3.4", "http://"):
        assert f(u)["flag"] in (True, False), u
