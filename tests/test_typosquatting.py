"""Kiểm Override #3 (src/override/typosquatting.py) — thuần tính toán, không mạng.

Bám ngưỡng PhishMatch (arXiv:2112.02226): ngưỡng-theo-độ-dài, **không loại nhãn
ngắn**. Brand VN thật trong dataset/brands/vn_brand_domains.csv.
"""

from src.override.typosquatting import kiem_tra_typosquatting as f


def _flag(url):
    return f(url)["flag"]


# --- domain chính thức -> False ------------------------------------------
def test_domain_chinh_thuc_khong_bao():
    assert _flag("https://vietcombank.com.vn/login") is False
    assert _flag("http://www.shopee.vn") is False
    assert _flag("https://tpb.vn") is False        # domain phụ của TPBank
    assert _flag("https://tpbank.com.vn") is False


# --- typosquat chính tả -> True ----------------------------------------
def test_typo_1_ky_tu_bi_bao():
    r = f("http://vietccombank.com")               # thêm 1 'c'
    assert r["flag"] is True
    assert "Levenshtein = 1" in r["reason"]
    assert "vietcombank" in r["reason"]
    assert _flag("http://vietcombankk.com") is True
    assert _flag("http://techcombannk.com") is True


def test_typo_brand_ngan_van_duoc_bat():
    # THAY ĐỔI vs bản Tuần 4: nhãn ngắn KHÔNG còn bị loại (theo PhishMatch)
    assert _flag("http://acbb.com") is True         # d=1 so 'acb'
    assert _flag("http://moomo.vn") is True         # d=1 so 'momo'


def test_mao_danh_truc_tiep_dung_ten_khac_domain():
    # nhãn trùng khít tên brand nhưng domain không chính thức -> mọi độ dài
    assert _flag("http://payoo.com") is True        # 'payoo' vs payoo.vn
    assert _flag("http://acb.com") is True          # 'acb' vs acb.com.vn (ngắn vẫn bắt)
    r = f("http://scb.xyz")
    assert r["flag"] is True and "scb" in r["reason"]


def test_brand_nhung_trong_nhan():
    assert _flag("http://techcombank-security.com") is True
    assert _flag("http://shopee-khuyen-mai.net") is True


def test_brand_trong_subdomain():
    r = f("http://vietcombank.dang-nhap-lai.com")
    assert r["flag"] is True
    assert "ubdomain" in r["reason"]


# --- KHÔNG bắt nhầm ----------------------------------------------------
def test_chuoi_khong_phai_brand_va_khong_gan_brand():
    # 'abc' cách 'acb' 2 phép sửa > ngưỡng 1 -> sạch
    assert _flag("http://abc.com") is False
    assert _flag("http://cba.io") is False


def test_domain_khong_lien_quan():
    assert _flag("https://www.google.com") is False
    assert _flag("https://github.com/a/b") is False
    assert _flag("https://en.wikipedia.org") is False


def test_candidate_trung_khit_brand_thi_khong_bao_typo_brand_khac():
    # 'acb' trùng khít brand 'acb' -> chỉ ra mao_danh_truc_tiep của 'acb',
    # KHÔNG kèm "typosquat của scb/ocb/ncb" (d=1) — nó chính là acb.
    r = f("http://acb.net")
    assert r["flag"] is True
    assert "acb" in r["reason"]
    assert "scb" not in r["reason"] and "ocb" not in r["reason"]


def test_dia_chi_ip_bo_qua():
    r = f("http://192.168.1.10/login")
    assert r["flag"] is False
    assert "IP" in r["reason"]


# --- hình dạng kết quả -----------------------------------------------
def test_ket_qua_dung_contract():
    r = f("http://vietccombank.com")
    assert set(r) == {"name", "flag", "reason", "latency_ms"}
    assert r["name"] == "typosquatting"
    assert isinstance(r["latency_ms"], float)


def test_khong_bao_gio_unknown():
    for u in ("http://vietcombank.com.vn", "http://acb.com", "http://x.io",
              "http://vietccombank.com", "http://1.2.3.4", "http://"):
        assert f(u)["flag"] in (True, False), u
