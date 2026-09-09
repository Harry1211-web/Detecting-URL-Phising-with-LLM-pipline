"""Gói Luật Override (Bạn B) — 3 luật kỹ thuật chạy **song song với** Random Forest
(không phải gate riêng), nuôi trực tiếp bước phân vùng 2 vùng.

  - Override #1 ``domain_age``     — tuổi domain (RDAP → WHOIS)      [Tuần 3]
  - Override #2 ``ssl_tls``        — chứng chỉ TLS (lỗi / cấp < 2 ngày) [Tuần 4]
  - Override #3 ``typosquatting``  — Levenshtein vs brand VN          [Tuần 4]

Mỗi luật trả ``contracts.OverrideResult`` = ``{name, flag, reason, latency_ms}``
với ``flag ∈ {True, False, "unknown"}``. Quy tắc bất di: ``"unknown"`` KHÔNG đồng
nghĩa an toàn — chỉ ``flag is False`` mới cho qua khi phân vùng
(``contracts.phan_vung``).

``chay_tat_ca_override`` ở đây chạy **tuần tự** — tiện cho test/CLI. Orchestrator
của Bạn A (Tuần 5) gọi 3 luật song song cùng RF bằng thread pool / asyncio, tổng
thời gian = max chứ không cộng dồn (docs/interface_contract.md §6).
"""

from __future__ import annotations

from src.contracts import RF_LOW_RISK_THRESHOLD_DEFAULT, OverrideResult, Zone, phan_vung
from src.override.domain_age import kiem_tra_tuoi_domain
from src.override.ssl_tls import kiem_tra_ssl_tls
from src.override.typosquatting import kiem_tra_typosquatting

__all__ = [
    "kiem_tra_tuoi_domain",
    "kiem_tra_ssl_tls",
    "kiem_tra_typosquatting",
    "chay_tat_ca_override",
    "phan_vung_tu_url",
    "phan_vung",
]


def chay_tat_ca_override(url: str) -> list[OverrideResult]:
    """3 luật Override theo thứ tự cố định [domain_age, ssl_tls, typosquatting]."""
    return [
        kiem_tra_tuoi_domain(url),
        kiem_tra_ssl_tls(url),
        kiem_tra_typosquatting(url),
    ]


def phan_vung_tu_url(url: str, rf_score: float,
                     rf_threshold: float = RF_LOW_RISK_THRESHOLD_DEFAULT
                     ) -> tuple[Zone, list[OverrideResult]]:
    """Tiện ích tích hợp/test: chạy 3 Override rồi phân vùng luôn.

    KHÔNG phải orchestrator sản xuất (đó là việc Bạn A) — chỉ gói lại 2 bước để
    kiểm thử end-to-end phía B và để Bạn A đối chiếu hành vi mong đợi.
    """
    flags = chay_tat_ca_override(url)
    return phan_vung(rf_score, flags, rf_threshold), flags
