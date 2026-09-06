"""Hợp đồng interface nội bộ — nguồn chân lý DUY NHẤT cho tên/thứ tự đặc trưng và
các kiểu dữ liệu trao đổi giữa các module.

Chốt tuần 1 (mục 1 & 4 của Plan.md). Cả service trích đặc trưng (Bạn A) lẫn code
train Random Forest (Bạn B) PHẢI import ``FEATURE_NAMES`` từ đây — không tự gõ lại
danh sách cột ở nơi khác.

Tài liệu người đọc: ``docs/interface_contract.md``.
"""

from __future__ import annotations

from typing import Literal, TypedDict

# ---------------------------------------------------------------------------
# 1. Danh sách 87 đặc trưng — đúng tên và thứ tự cột trong
#    Dataset/train/dataset_phishing.csv (bỏ 'url' đầu và 'status' cuối).
#    Hannousse & Yahiouche (2020), Mendeley dataset_B.
# ---------------------------------------------------------------------------

# 56 đặc trưng lexical/cú pháp URL (tính từ chuỗi, nhanh, không cần mạng).
LEXICAL_FEATURES: tuple[str, ...] = (
    "length_url", "length_hostname", "ip", "nb_dots", "nb_hyphens", "nb_at",
    "nb_qm", "nb_and", "nb_or", "nb_eq", "nb_underscore", "nb_tilde",
    "nb_percent", "nb_slash", "nb_star", "nb_colon", "nb_comma", "nb_semicolumn",
    "nb_dollar", "nb_space", "nb_www", "nb_com", "nb_dslash", "http_in_path",
    "https_token", "ratio_digits_url", "ratio_digits_host", "punycode", "port",
    "tld_in_path", "tld_in_subdomain", "abnormal_subdomain", "nb_subdomains",
    "prefix_suffix", "random_domain", "shortening_service", "path_extension",
    "nb_redirection", "nb_external_redirection", "length_words_raw",
    "char_repeat", "shortest_words_raw", "shortest_word_host",
    "shortest_word_path", "longest_words_raw", "longest_word_host",
    "longest_word_path", "avg_words_raw", "avg_word_host", "avg_word_path",
    "phish_hints", "domain_in_brand", "brand_in_subdomain", "brand_in_path",
    "suspecious_tld", "statistical_report",
)

# 24 đặc trưng nội dung HTML/DOM (cần tải trang — service phải fetch HTML).
CONTENT_FEATURES: tuple[str, ...] = (
    "nb_hyperlinks", "ratio_intHyperlinks", "ratio_extHyperlinks",
    "ratio_nullHyperlinks", "nb_extCSS", "ratio_intRedirection",
    "ratio_extRedirection", "ratio_intErrors", "ratio_extErrors", "login_form",
    "external_favicon", "links_in_tags", "submit_email", "ratio_intMedia",
    "ratio_extMedia", "sfh", "iframe", "popup_window", "safe_anchor",
    "onmouseover", "right_clic", "empty_title", "domain_in_title",
    "domain_with_copyright",
)

# 7 đặc trưng tra cứu dịch vụ ngoài (WHOIS/DNS/traffic/PageRank/Google index).
# Trùng vai trò với 3 Luật Override — xem docs/interface_contract.md.
EXTERNAL_FEATURES: tuple[str, ...] = (
    "whois_registered_domain", "domain_registration_length", "domain_age",
    "web_traffic", "dns_record", "google_index", "page_rank",
)

FEATURE_NAMES: tuple[str, ...] = (
    LEXICAL_FEATURES + CONTENT_FEATURES + EXTERNAL_FEATURES
)
assert len(FEATURE_NAMES) == 87, len(FEATURE_NAMES)
assert len(set(FEATURE_NAMES)) == 87, "tên đặc trưng bị trùng"

TARGET_COLUMN = "status"
URL_COLUMN = "url"

# Nhãn trong cột 'status'. Quy ước số: phishing = 1, legitimate = 0.
LABEL_PHISHING = "phishing"
LABEL_LEGITIMATE = "legitimate"
LABEL_MAP: dict[str, int] = {LABEL_LEGITIMATE: 0, LABEL_PHISHING: 1}

# Cột hằng số = 0 trong dataset_B — bỏ khi feature selection.
# CLAUDE.md ghi 3 (sfh, ratio_intErrors, ratio_intRedirection) nhưng EDA tuần 1
# tìm ra 6 (thêm nb_or, ratio_nullHyperlinks, submit_email) — xem
# reports/eda/BAO_CAO_EDA.md mục 1. Danh sách dưới là kết quả EDA (nguồn chuẩn).
CONSTANT_FEATURES_DATASET_B: tuple[str, ...] = (
    "sfh", "ratio_intErrors", "ratio_intRedirection",
    "nb_or", "ratio_nullHyperlinks", "submit_email",
)
# 3 cột CLAUDE.md liệt kê ban đầu — giữ để notebook đối chiếu.
CONSTANT_FEATURES_CLAUDE_MD: tuple[str, ...] = (
    "sfh", "ratio_intErrors", "ratio_intRedirection",
)

# Đặc trưng tương quan mạnh nhất với nhãn theo CLAUDE.md (~0.73) — EDA xác nhận.
STRONGEST_SIGNAL_FEATURE = "google_index"

# Giá trị "không tra được" mà script gốc điền cho nhóm đặc trưng ngoài.
# Không phải NaN — là -1 (hoặc 0 tuỳ đặc trưng). Xử lý ở bước tiền xử lý, không
# coi -1 là giá trị số bình thường.
EXTERNAL_LOOKUP_SENTINEL = -1


# ---------------------------------------------------------------------------
# 2. Hợp đồng /check-url (mục 4 Plan.md) — request/response backend.
# ---------------------------------------------------------------------------

Zone = Literal["vung_thap", "vung_nghi_ngo"]
Verdict = Literal["an_toan", "nguy_hiem", "canh_bao_nhe", "khong_xac_dinh"]
OllamaVerdict = Literal["nguy_hiem", "co_ve_on"]
OverrideFlag = Literal[True, False, "unknown"]


class FeatureVector(TypedDict):
    """dict {feature_name: value} đúng tên + thứ tự FEATURE_NAMES."""


class OverrideResult(TypedDict):
    """Kết quả 1 luật Override (mục 4 Plan.md)."""

    name: str                 # "domain_age" | "ssl_tls" | "typosquatting"
    flag: OverrideFlag        # True = vi phạm, False = ổn, "unknown" = không tra được
    reason: str               # giải thích ngắn tiếng Việt
    latency_ms: float


class OllamaResult(TypedDict):
    """Verdict Ollama cho Vùng nghi ngờ (mục 4 Plan.md)."""

    verdict: OllamaVerdict
    explanation: str
    rag_hits: list[str]
    timed_out: bool


class CheckUrlRequest(TypedDict):
    url: str


class CheckUrlResponse(TypedDict):
    url: str
    verdict: Verdict
    zone: Zone
    risk_score: float             # điểm rủi ro tổng hợp [0, 1]
    rf_score: float               # xác suất phishing từ Random Forest [0, 1]
    override_flags: list[OverrideResult]
    explanation: str
    source: Literal["blocklist", "rf_override", "ollama", "cache", "fallback"]
    cached: bool
    latency_ms: float


# ---------------------------------------------------------------------------
# 3. Ngưỡng phân vùng (hàm phân vùng — Bạn B, cắm vào orchestrator của Bạn A).
#    Giá trị dưới là MẶC ĐỊNH KHỞI ĐỘNG, hiệu chỉnh lại trên traffic mô phỏng
#    95% Tranco / 5% phishing ở tuần 6 (mục 3 Plan.md, mục 6 GhiChú).
# ---------------------------------------------------------------------------

RF_LOW_RISK_THRESHOLD_DEFAULT = 0.30


def phan_vung(rf_score: float, override_flags: list[OverrideResult],
              rf_threshold: float = RF_LOW_RISK_THRESHOLD_DEFAULT) -> Zone:
    """RF điểm thấp VÀ 0 cờ Override vi phạm -> Vùng thấp; còn lại -> Vùng nghi ngờ.

    "unknown" của Override KHÔNG tính là an toàn: chỉ ``flag is False`` mới cho qua.
    """
    co_vi_pham = any(o["flag"] is not False for o in override_flags)
    if rf_score < rf_threshold and not co_vi_pham:
        return "vung_thap"
    return "vung_nghi_ngo"
