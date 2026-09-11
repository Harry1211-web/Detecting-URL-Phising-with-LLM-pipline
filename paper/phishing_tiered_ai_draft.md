# A Confidence-Tiered AI Pipeline for Phishing Website Detection and Warning, with a Vietnamese Brand-Impersonation Focus

**Authors:** [Author 1] and [Author 2]
**Affiliation:** [Faculty of Information Technology, University Name], Vietnam
**Contact:** dongquan2110@gmail.com

> **Note.** `phishing_tiered_ai_draft.tex` is the canonical version (structure, citations, figures). This Markdown file mirrors its content for reading and review.

> **Manuscript status.** This is a **preliminary draft for supervisor review**. It is a system-design paper with **preliminary Layer B results** (Section VII: EDA + Random Forest / feature selection / override rules, reproducible from committed scripts, on the balanced 50/50 split). The suspicious-zone LLM stage is not yet built — threshold calibration on realistic traffic and the injection red-team come next. Quantitative values attributed to prior work are cited to a verifiable source; values described as "target" or "budget" are design goals, not measurements.

---

## Abstract

Phishing detection systems increasingly combine lightweight machine-learning (ML) classifiers with large language models (LLMs) for deep analysis, but most designs invoke the LLM for every request that needs scrutiny, and virtually all published systems are built and evaluated on English-language brands. We present the design of a confidence-tiered pipeline that spends heavy analysis only where it is warranted and that targets Vietnamese brand impersonation as a first-class concern. The pipeline has three stages. Layer A is a Manifest V3 `declarativeNetRequest` blocklist that blocks known-bad domains instantly and grows itself from confirmed verdicts produced downstream. Layer B extracts the 87 features of the Hannousse–Yahiouche benchmark dataset, scores them with a Random Forest, and runs three technical override rules in parallel: domain age via RDAP with a WHOIS fallback, TLS-certificate validity and recency, and Levenshtein typosquatting distance against a curated list of Vietnamese brand domains. A URL passes immediately only if the Random Forest score is low *and* no override rule fires; every other case enters a single "suspicious zone." In the suspicious zone a locally hosted small model of the Qwen3.5 family (~2 B parameters, e.g. `qwen3.5:2b`), grounded by a two-tier retrieval-augmented generation (RAG) store, produces the final verdict and a human-readable explanation, and any domain it confirms malicious is written back into Layer A. We motivate each design choice against the current literature, give a simple cost model that explains why self-hosted inference removes the incentive to split "grey" and "black" LLM tiers, and analyze the security exposure the LLM stage introduces — indirect prompt injection, knowledge-base poisoning, embedding weaknesses, and a shared-blocklist self-poisoning risk — using the OWASP Top 10 for LLM Applications (2025) as the reference taxonomy. We pre-register an evaluation protocol and report preliminary Layer B results against it: on the balanced benchmark the compact 30-feature Random Forest reaches test ROC-AUC 0.991 / accuracy 0.954, and a network-free variant loses 2.5 accuracy points, quantifying the pipeline's dependence on external lookups. The suspicious-zone LLM stage is not yet built; its evaluation, and threshold calibration on realistic traffic, are future work.

**Index Terms —** phishing detection, machine learning, large language models, retrieval-augmented generation, browser extension, Manifest V3, prompt injection, Vietnamese brand impersonation.

---

## Tóm tắt (Vietnamese abstract)

Các hệ thống phát hiện lừa đảo (phishing) hiện nay thường kết hợp bộ phân loại học máy nhẹ với mô hình ngôn ngữ lớn (LLM) để phân tích sâu, nhưng phần lớn thiết kế gọi LLM cho *mọi* yêu cầu cần xem xét, và gần như toàn bộ hệ thống đã công bố đều được xây dựng, đánh giá trên thương hiệu tiếng Anh. Bài báo trình bày thiết kế một pipeline phân tầng theo độ tin cậy: chỉ dồn tài nguyên phân tích sâu vào phần traffic thật sự đáng ngờ, và đặt bối cảnh giả mạo thương hiệu Việt Nam làm mục tiêu trọng tâm. Pipeline gồm ba lớp. Lớp A là blocklist `declarativeNetRequest` (Manifest V3) chặn tức thì domain đã biết xấu và tự học từ các phán quyết được xác nhận ở lớp sau. Lớp B trích 87 đặc trưng của bộ dữ liệu chuẩn Hannousse–Yahiouche, chấm điểm bằng Random Forest, đồng thời chạy song song ba luật kỹ thuật: tuổi domain qua RDAP (dự phòng WHOIS), tính hợp lệ và độ mới của chứng chỉ TLS, và khoảng cách Levenshtein so với danh sách domain thương hiệu Việt Nam. Một URL chỉ được cho qua ngay khi điểm Random Forest thấp *và* không luật nào kích hoạt; mọi trường hợp còn lại vào "vùng nghi ngờ" duy nhất. Ở vùng này, một mô hình nhỏ thuộc họ Qwen3.5 (~2 tỷ tham số, ví dụ `qwen3.5:2b`) chạy cục bộ, được tăng cường bằng kho RAG hai tầng, đưa ra phán quyết cuối cùng kèm giải thích; domain bị xác nhận nguy hiểm được nạp ngược vào Lớp A. Chúng tôi lập luận cho từng lựa chọn thiết kế dựa trên tài liệu hiện có, đưa ra một mô hình chi phí đơn giản giải thích vì sao suy luận tự host loại bỏ động lực tách hai mức LLM, và phân tích rủi ro bảo mật mà tầng LLM mang lại theo phân loại OWASP Top 10 for LLM Applications (2025). Bài báo kèm một giao thức đánh giá đăng ký trước. **Lớp B đã hiện thực:** trên bộ dữ liệu cân bằng, Random Forest rút gọn 30 đặc trưng đạt ROC-AUC 0,991 / độ chính xác 0,954 trên tập test, và bản chỉ dùng đặc trưng không cần mạng mất 2,5 điểm độ chính xác. Tầng LLM ở vùng nghi ngờ chưa được xây; việc đánh giá tầng này và hiệu chỉnh ngưỡng trên traffic thực tế là hướng phát triển tiếp.

**Từ khóa —** phát hiện phishing, học máy, mô hình ngôn ngữ lớn, RAG, tiện ích trình duyệt, Manifest V3, prompt injection, giả mạo thương hiệu Việt Nam.

---

## I. Introduction

Phishing remains one of the highest-volume forms of online fraud. Recent surveys report that machine-learning approaches now dominate phishing-website detection [1], [31], and a hybrid arrangement is common in practice: a fast statistical model filters the bulk of traffic, and a slower, more expressive model resolves the hard cases [6], [31]. Two limitations recur across recent designs.

**First, the expensive stage is invoked too often.** Systems that use an LLM as the deep analyzer typically call it for every input that the fast stage cannot dismiss [6], [7]. When the LLM is a paid cloud API, this couples detection coverage directly to operating cost, and it is the reason several designs introduce a second, cheaper "grey-zone" model before escalating to an expensive one.

**Second, the evaluation context is almost entirely English.** The datasets and brand lists used by the surveyed literature — including the multimodal LLM work of Lee *et al.* [7], the LLM crawler of Koide *et al.* [6], and the feature-based benchmarks [2], [5] — are built on internationally known, English-language brands. Vietnamese banking, e-commerce, and e-wallet brands, which are the actual impersonation targets for Vietnamese users, are absent.

This paper describes a pipeline organized by *confidence tiering*: classify each URL by how certain the system is, and let that certainty decide how much computation the URL receives. Three defensive layers run before any generative model is consulted:

1. **Layer A** blocks domains already known to be malicious, using the browser's native `declarativeNetRequest` mechanism, and extends its own blocklist from verdicts confirmed later in the pipeline.
2. **Layer B** combines a Random Forest over the 87-feature Hannousse–Yahiouche representation [2], [3] with three parallel "override" rules grounded in registration, transport-security, and lexical-similarity signals.
3. **The suspicious zone** is reached only when Layers A and B are jointly inconclusive. Here a locally hosted small LLM, grounded by a two-tier RAG store that includes a Vietnamese brand-domain table, issues the final verdict and an explanation.

Two of these are deliberate design choices rather than novel mechanisms: requiring the statistical score *and* the technical rules to agree before the cheap path is taken (a stricter gate than a plain fast/slow cascade), and merging the customary grey/black LLM split into one zone because self-hosted inference has no per-request price to control (Section IV).

The contributions are: (i) a concrete instantiation of a tiered detector for **Vietnamese brand impersonation** — the two-tier RAG design, the curated brand-domain table, and the three override rules; (ii) a security analysis of the LLM stage mapped to the OWASP Top 10 for LLM Applications (2025) [9], including a shared-blocklist self-poisoning risk we have not seen discussed elsewhere; (iii) a design-rationale analysis, with a simple cost model, tying each choice to the literature and to consumer-grade hardware constraints; and (iv) a pre-registered evaluation protocol with fixed numeric targets and pass/fail criteria, and preliminary Layer B results against it (Section VII). The suspicious-zone LLM stage is not yet built, so no end-to-end detection claim is made.

---

## II. Related Work

### A. Feature-based ML detection and the benchmark dataset

Surveys of phishing-website detection classify approaches into list-based, visual-similarity, heuristic, classical-ML, and deep-learning families, and note that ML approaches dominate recent work because they generalize better than static rules while remaining cheaper than deep models [1]. Reviews aimed specifically at ML and deep learning reach the same conclusion and additionally stress deployment concerns — latency, model size, and the gap between benchmark accuracy and field performance [31].

Our classifier is trained on the dataset of Hannousse and Yahiouche [2], distributed through Mendeley Data [3]. It contains 11,430 URLs with 87 extracted features and is exactly balanced (50% phishing, 50% legitimate). The features fall into three groups: 56 computed from the URL string, 24 from the fetched page content, and 7 obtained by querying external services [2]. This tripartite split maps cleanly onto our Layer B: the 7 external-service features correspond to the signals our override rules recompute directly (domain age, DNS/registration, popularity), and the URL-string features are the ones available with no network round-trip. Our exploratory analysis of the public file (Section VII) found **six** features that are constant (all-zero) in this release — `sfh`, `ratio_intErrors`, `ratio_intRedirection`, `nb_or`, `ratio_nullHyperlinks`, `submit_email` — and that `google_index` has by far the strongest univariate association with the label (Pearson r = 0.73), followed by `page_rank` (r = −0.51). It also found `domain_age` set to its "not resolved" sentinel in 15.6% of rows — direct evidence that missing registration data is common and must not be read as benign.

Beyond this benchmark, the community also uses the classic UCI feature set of Mohammad *et al.* [14] and, more recently, the 235,795-URL PhiUSIIL corpus [13]; we use the latter only for a generalization check (Section VI-C).

A separate line of work builds larger URL-only corpora and dedicated feature-engineering pipelines. Tamal *et al.* [5] release a dataset of 247,950 URLs (128,541 phishing, 119,409 legitimate) and an "Optimal Feature Vectorization Algorithm" that reduces the representation to 42 intra-URL features. We adopt the *methodology* — importance-driven reduction to a few dozen strong features, tuned with grid search and k-fold cross-validation — while keeping the Hannousse–Yahiouche schema because it also carries content and external-service features that our pipeline needs.

A parallel line of work skips hand-engineered features and learns a URL representation end to end; URLNet [32] is the canonical character/word-level convolutional example. We stay with an interpretable feature-based Random Forest because Layer B must expose *which* signals fired, both to the suspicious-zone LLM and to the user-facing explanation. Two dataset properties also shape our protocol. First, phishing sites are short-lived — Oest *et al.* [35] measure campaign lifetimes of a few days — so several of the 24 content features and the 7 external-service features cannot be recomputed on historical URLs, and the training snapshot ages quickly. Second, the benchmark predates the retirement of Alexa web-traffic ranks (May 2022), so the `web_traffic` feature is no longer reproducible at inference time (Section III-C).

### B. LLM-based detection and explanation

Reference-based visual detectors established the brand-identity framing our suspicious zone reuses. Phishpedia [33] localizes brand logos on a screenshot with object detection and matches them to protected brands with a Siamese network, deliberately training on no phishing samples; PhishIntention [34] adds a credential-taking-intention check to cut false positives on benign brand mentions. Koide *et al.* [6] (extending an earlier preprint [28]) pair a web crawler with an LLM prompt and report, for GPT-4V, a precision of 98.7% and a recall of 99.6% on their multilingual test set, without any task-specific training. Lee *et al.* [7] use a multimodal LLM in two phases — brand identification from screenshot and HTML, then verification that the identified brand matches the URL's domain — and outperform the reference brand-based detector VisualPhishNet. Both LLM results establish that an LLM can recognize impersonated brands and social-engineering cues directly, and both use models with hundreds of billions of parameters accessed as cloud services; none of these four targets Vietnamese brands.

PhishLang [8] moves in the opposite direction: it runs a MobileBERT-based ensemble fully client-side, consuming up to 7× less memory than comparable architectures, ships as a Chromium extension, and reports contributing to the takedown of roughly 26,000 phishing sites over 3.5 months. It shows that a small, local language model is viable for this task, but it does not attempt the open-ended brand-reasoning and natural-language explanation that a generative model provides. Our suspicious zone occupies the space between [6], [7] and [8]: a *generative* small model, run locally, used only for the residual hard cases.

### C. Browser-based, real-time detection

Real-time protection in the browser is now an established target. Dandotiya *et al.* [29] (*Scientific Reports*, 2026) implement an ML-enhanced Chrome extension that combines lexical, structural, and visual-layout features, selects them with a grey-wolf optimizer, and classifies with SVM / decision-tree / Random-Forest models, reporting strong accuracy on PhishTank-based benchmarks while trading feature-extraction overhead for responsiveness. PhishLang [8] is delivered the same way. These systems confirm that the extension form factor is appropriate; our Layer A/Layer B split additionally exploits `declarativeNetRequest`, whose current limits allow up to 30,000 dynamic "safe" blocking rules per extension [19], to make the known-bad path a zero-inference lookup. Table 1 places the present design against these systems.

### D. Prompt injection and LLM security

Any system that feeds untrusted page content to an LLM inherits the LLM threat model. The OWASP Top 10 for LLM Applications 2025 [9] ranks prompt injection first (LLM01) and distinguishes *direct* injection ("ignore all previous instructions…") from *indirect* injection, in which instructions are embedded in a document or web page the model later processes. It also lists data and model poisoning (LLM04), vector and embedding weaknesses (LLM08), and excessive agency (LLM06) — all four are relevant to a RAG-grounded detector that reads live HTML. Non-peer-reviewed industry red-teaming has demonstrated the concrete risk: Guardio Labs' "Scamlexity" work drove an agentic AI browser end-to-end through a phishing flow, and its "PromptFix" technique hid adversarial instructions inside a fake CAPTCHA so the agent would act on them [10]. Because a smaller model has a weaker prior separating "system instruction" from "text I was asked to read," self-hosting a ~2 B model for cost reasons plausibly *raises* this exposure relative to a frontier model; we treat active injection testing as mandatory rather than optional (Section V, Section VI-E).

### E. Gap addressed

No surveyed system combines (a) a bound on how often the generative stage runs that comes from confidence tiering rather than from a paid-API cost ceiling, (b) a self-learning native blocklist fed by the system's own confirmed verdicts, and (c) a retrieval layer purpose-built for Vietnamese brand domains. Each ingredient is individually supported by prior work [1], [2], [6], [7], [8], [9], [19]; the combination and the Vietnamese instantiation are this paper's subject.

**Table 1 — the proposed design against representative prior systems.** *Gen.* = uses a generative model; *Local* = runs without a cloud service; *Self-learn* = blocklist grown from the system's own verdicts; *NL expl.* = natural-language explanation to the user; *$/req* = detection coverage bounded by paid-API cost.

| System | Gen. | Local | Self-learn | NL expl. | Lang. focus | $/req |
|---|---|---|---|---|---|---|
| ChatPhishDetector [6] | ✓ | – | – | ✓ | multiling. (EN) | yes |
| Lee *et al.* [7] | ✓ | – | – | partial | EN brands | yes |
| Phishpedia / PhishIntention [33], [34] | – | ✓ | – | partial | EN brands | no |
| PhishLang [8] | – | ✓ | – | – | EN | no |
| Dandotiya *et al.* [29] | – | ✓ | – | – | EN | no |
| **This design** | ✓ | ✓ | ✓ | ✓ | **Vietnamese** | no |

---

## III. System Architecture

### A. Overview: confidence tiering

When a user navigates to a URL, the pipeline asks a sequence of increasingly expensive questions and stops as soon as one is decisive:

```
navigate(URL)
  → Layer A: domain on blocklist?                    → yes → BLOCK (0 inference, no fetch)
             domain in Tranco allow-list?            → yes → ALLOW (short-circuit)
  → Layer B: fetch page once; RF score + 3 override rules (parallel)
        RF below threshold  AND  0 override flags     → LOW ZONE → allow (no LLM)
        otherwise                                     → SUSPICIOUS ZONE
  → Suspicious zone: local LLM + 2-tier RAG (sync)    → final verdict + explanation
        confirmed malicious → BLOCK + write domain back to Layer A (with safeguards, §V)
        looks acceptable    → allow with a soft warning
```

Only two output zones exist. The common case — an allow-listed or well-known legitimate site — resolves at Layer A with no page fetch and no LLM call. The low zone is cheaper than the suspicious zone but **not free**: it still pays one page fetch, 87-feature extraction, the Random Forest, and the override lookups (including the RDAP/WHOIS round-trip). The suspicious zone adds LLM and RAG cost on top and is meant to be reached only by genuinely ambiguous URLs; Section VI-B fixes a target for how often that happens.

### B. Layer A: self-learning `declarativeNetRequest` blocklist

Layer A is a static rule set consumed by the browser's `declarativeNetRequest` engine under Manifest V3, so matching happens in the browser without a message round-trip to the backend. Chrome currently permits up to 30,000 dynamic "safe" rules (block/allow/allowAllRequests/upgradeScheme) per extension, with a separate 5,000-rule cap on "unsafe" rules and up to 50 enabled static rulesets [19]; the 30,000 figure sets the working budget for the blocklist.

Two properties distinguish it from a conventional feed-driven blacklist:

- **Self-learning.** A domain that reaches the suspicious zone and is then confirmed malicious by the LLM is written back as a Layer A rule, so the second visit — by that user or any user — is blocked with no analysis.
- **Time-and-priority eviction, not liveness.** Rules are retired by a time-to-live weighted by source priority (system-confirmed > multi-source external > single-source external), never by probing whether the domain still resolves. Cloaking makes a liveness test actively dangerous: a phishing site can serve an error to scanners while serving victims normally, which would let an attacker evict its own domain from the blocklist. External feeds that are straightforward to automate — OpenPhish [22], URLhaus [23], and comparable community feeds — are merged on a fixed backend schedule, normalized to registrable domains, and de-duplicated before being pushed to the extension. The union of these feeds routinely exceeds the 30,000-rule budget, so TTL-and-priority eviction is a hard requirement, not an optimization: the blocklist is scoped to domains that are Vietnam-relevant or from a currently active campaign, and the oldest low-priority rules are retired first when the budget is hit. Operationally, one project-run backend compiles the ruleset and the extension pulls a refresh on a fixed interval (e.g. hourly); if the backend is unreachable, the extension keeps its last ruleset and Layer B still functions. Write-back rules from the suspicious zone carry a short TTL (days, not months) and are logged, so a wrong rule expires on its own and can also be pulled manually. A user who believes a site was blocked in error can report it from the interstitial; the report re-opens the domain for review and, pending that, adds it to that user's local allow-list.

### C. Layer B: Random Forest plus parallel override rules

Layer B runs on the backend, which fetches the page once and computes all 87 features there, so the extension needs no page-parsing or network-lookup logic.

**Classifier.** We use a Random Forest [4]. Six features that are all-zero in this dataset release (`sfh`, `ratio_intErrors`, `ratio_intRedirection`, `nb_or`, `ratio_nullHyperlinks`, `submit_email`) are dropped up front, leaving 81. Hyper-parameters are chosen by grid search *inside* a k=5 cross-validation, with an *outer* locked 80/20 test split used only for the reported numbers, so model selection never sees the evaluation data. Feature reduction ranks by the Random Forest's importances and takes the smallest cut in the 30–42 range whose 5-fold ROC-AUC stays within 0.002 of the all-81 baseline; in our run (Section VII) that cut is **30** features. A second, network-free model over the 25 lexical/content features of that set (`rf_fast`) is trained as the fallback for when the external lookups time out. Two of the retained features are flagged non-stationary: `web_traffic` (Alexa-derived; Alexa ranks retired May 2022, so it cannot be reproduced live and is imputed as "unknown" at inference time), and `google_index`, which carries the strongest signal in training (r = 0.73) but is exactly the kind that drifts — search engines de-index known phishing quickly, so its training-time and deployment-time distributions differ.

**Override rules.** Three rules run *in parallel with* the Random Forest — they are not a separate gate, and their outputs are combined with the RF score at the zoning step:

1. **Domain age.** Query RDAP first, falling back to WHOIS. RDAP returns structured JSON, and its query format, JSON responses, and bootstrap procedure are standardized [16], [17], [15]; since 28 January 2025 ICANN no longer requires gTLD registries to run port-43 WHOIS [18]. The IANA RDAP bootstrap registry is consulted to find the authoritative server per TLD [15]. `.vn` is on a fixed no-RDAP list, so Vietnamese domains skip RDAP and go straight to WHOIS — expected, not an error. Each step has a short timeout (≈ 500 ms; 3 s for the one-time bootstrap fetch). A domain younger than a configurable threshold (default 90 days, calibrated with the zoning threshold in Section VI-B) is flagged. If both sources return nothing — including deliberate registration-privacy redaction — the rule reports "unknown," which is *not* treated as safe.
2. **TLS certificate.** An authenticated TLS handshake is opened; a certificate that fails validation (self-signed, expired, wrong host, unknown CA) or one issued within the last two days raises a flag, and an unreadable certificate reports "unknown." Because this rule dials an attacker-controlled host, the probe is hardened against server-side request forgery (Section V).
3. **Typosquatting.** Levenshtein edit distance [21] between the registrable-domain label and each entry in a **62-brand** curated Vietnamese list (banks, e-wallets, e-commerce, telecom/tech, airlines, public services); measurement studies of typosquatting abuse motivate edit-distance screening [37], [38]. The acceptance threshold scales with brand-name length as `max(1, floor(len(brand)/5))` and brands shorter than 5 characters are excluded, so short names do not generate false matches. This rule is pure computation and never reports "unknown." Edit distance alone misses homoglyph substitutions (e.g. Cyrillic look-alikes); a skeleton/confusable normalization before the comparison is a planned addition, and the false-match rate of the rule is reported in Section VI-A.

**Table 2 — override rules.** Each runs in parallel with the Random Forest; an empty registration result is reported as "unknown," never "safe."

| Rule | Signal / source | Timeout | Flag condition |
|---|---|---|---|
| Domain age | RDAP [15]–[17], WHOIS fallback | ≈500 ms/step | very recent registration, or unresolvable |
| TLS certificate | certificate chain at connect | connect budget | missing/invalid, or issued < 2 days ago |
| Typosquatting | Levenshtein [21] vs. VN brand list | local | distance ≤ max(1, floor(len(brand)/5)) |

**Zoning.** A URL enters the low zone — allowed with no LLM call — only if the Random Forest score is below the calibrated threshold *and* none of the three override rules fired. Any other combination routes to the suspicious zone. The threshold is not fixed from the balanced test set; Section VI-B describes calibration on imbalanced simulated traffic.

### D. Suspicious zone: local LLM with two-tier RAG

**Model.** The verdict for the suspicious zone is produced by a small model of the Qwen3.5 family (~2 B parameters, e.g. `qwen3.5:2b`) served locally through Ollama [26], [27], [36]. The reference deployment is a single consumer GPU (GTX 1650, 4 GB VRAM); `qwen3.5:2b` quantized to ~2.7 GB fits in VRAM with headroom for context, which is the operational reason for the size ceiling. `qwen3.5:4b` (~3.4 GB) is possible if partial CPU offload and the added latency are acceptable; after installation the choice is confirmed with `ollama ps` (the processor column must read 100% GPU). Qwen3.5 models emit an optional `<think>` reasoning span that must be stripped before the verdict is parsed and that adds latency on the critical path. The call is synchronous — the pipeline waits for it before responding — with streaming used only to improve perceived latency. The LLM is the decision step for this zone: it can move an RF/override "suspicious" signal in either direction. Promotion of a confirmed-malicious domain into Layer A is *not* automatic — it is conditional on the corroboration and allow-list safeguards of Section V.

**Two-tier RAG.** Retrieval grounds the model and is deliberately split:

- **Tier 1 — structured brand lookup.** A table of official domains for common Vietnamese brands. The model is asked which brand, if any, the page is imitating; a mismatch between that brand's real domain and the URL's domain is strong phishing evidence. This tier is a deterministic lookup, not a model call. The table is hand-built and covers the brand classes that dominate Vietnamese impersonation targets — retail banks (Vietcombank, VietinBank, BIDV, Techcombank, MB…), e-wallets and payment intermediaries (MoMo, ZaloPay, VNPAY, ViettelPay), large e-commerce and logistics platforms (Shopee, Lazada, Tiki, Giao Hàng Nhanh) — each with its verified registrable domain(s). Two things make the Vietnamese setting distinct from the English-brand literature: many legitimate targets sit on the `.vn` ccTLD, which does not expose RDAP (Section III-C), and lure pages are written in Vietnamese, so the Tier-2 advisory corpus is Vietnamese-language.
- **Tier 2 — semantic search.** A ChromaDB [25] store of manually curated Vietnamese-language phishing advisories and descriptions (e.g. from national anti-fraud and cyber-security bodies). Embeddings are produced locally with `nomic-embed-text` [12] through the same Ollama runtime, so no external embedding API is needed (this model requires the `search_document:` / `search_query:` task prefixes, which the indexing and query paths must apply consistently). Only hand-verified sources are ingested; automated crawl-and-index is excluded to avoid knowledge-base poisoning, and retrieved passages are treated as untrusted (Section V).

**Timeout and fallback.** The suspicious-zone timeout is measured on the target hardware rather than assumed; local inference on a consumer GPU can be markedly slower and more variable than a cloud API. On timeout, the pipeline falls back to a purely technical explanation assembled from the Random Forest and override outputs.

### E. Backend API and MV3 extension

A backend service exposes a single `POST /check-url` endpoint that runs Layers A–B and, when needed, the suspicious zone, and returns the verdict, zone, contributing signals, and explanation. Results are cached for 24 hours; the cache key is the registrable domain, except for known shared-hosting suffixes (site builders, blogging platforms, code-hosting pages), where the key falls back to the full host or path prefix so that sibling sites are not tarred by one another's verdict.

Under Manifest V3 the extension **cannot hold a navigation open** while it waits for the backend: `webNavigation` is observational and cannot cancel a request [20], and `declarativeNetRequest` can only act on rules already installed. The two paths therefore differ. *Known-bad* domains are blocked **before** any request leaves the browser, by the Layer A `declarativeNetRequest` ruleset [19] refreshed from the backend. For an *unknown* URL, the navigation is allowed to proceed while `onBeforeNavigate` fires the `/check-url` call; until a verdict returns, a content script masks the page with a neutral "checking…" overlay. A malicious verdict then replaces the page with a full-stop interstitial; a soft-warning verdict dismisses the overlay and shows a dismissible banner with the streamed explanation; a low-zone or timed-out verdict simply removes the overlay. This leaves a brief window in which a malicious page is loaded but not yet interactable to the user (Section VIII). The extension targets Chrome and Edge, which share the Chromium extension APIs but ship through separate stores and diverge slightly in enterprise-policy behaviour.

---

## IV. Design Analysis and Rationale

**Why confidence tiering rather than a fixed cascade.** A two-stage cascade (fast model → deep model) still sends every non-trivial URL to the deep model. Tiering adds the requirement that *both* the statistical score and the technical rules agree before the cheap path is taken, which is what allows the expensive path to be reserved for genuine disagreement. The cost of this is discrimination *within* the suspicious zone: a "mildly odd" URL and an "almost certainly malicious" URL are handled identically (both wait for the LLM). We accept this as a simplification and note it as a limitation (Section VIII).

**Why one LLM zone instead of grey/black tiers.** Splitting the LLM stage into a cheap "grey" model and an expensive "black" model is a cost-control mechanism that only pays off under per-request pricing. For *N* daily checks that reach the LLM stage at rate *p*, a two-model cloud design costs about *N·p·(f_g·c_g + f_b·c_b)* per day, where *f_g, f_b* are the grey/black split and *c_g ≪ c_b* their per-call prices. A single self-hosted model costs *C_amort + N·p·c_e*, with *C_amort* the amortized GPU/host cost per day and *c_e* the marginal energy per call. As *c_g, c_b → 0* the first expression collapses and the only term left is the fixed *C_amort*, which a second model does not reduce — it only adds VRAM pressure and routing logic. Merging the tiers is thus a direct consequence of self-hosting, not an independent design preference. Table 4 works the comparison for one illustrative operating point; the inputs are assumptions and exist only to show which term survives.

**Table 4 — illustrative daily-cost comparison** at one assumed operating point (*N* = 10⁴ checks/day reaching the LLM stage at rate *p* = 0.05).

| Design | Cost expression | Assumed value |
|---|---|---|
| Cloud, grey+black | *N·p·(f_g·c_g + f_b·c_b)* | 500·(0.7·c_g + 0.3·c_b), c_b ≫ c_g |
| Self-host, one model | *C_amort + N·p·c_e* | C_amort + 500·c_e, c_e → 0 |

**Why TTL-and-priority eviction, and this priority order.** Rules are retired by age weighted by source trust — system-confirmed > multi-source external > single-source external — because the failure modes differ by source: system-confirmed rules come from a full suspicious-zone analysis and should persist longest, whereas a single uncorroborated feed entry is the most likely to be stale or wrong and is evicted first. Liveness is deliberately *not* an eviction input, for the cloaking reason given in Section III-B.

**Why RDAP-first.** RDAP responses are structured JSON with explicit registration and expiry fields, which parse far more reliably than free-form WHOIS text, and RDAP is now the mandatory registration-data protocol for gTLDs [16], [17], [15], [18]. WHOIS remains as a fallback precisely because ccTLDs such as `.vn` do not yet expose RDAP. Treating an empty result as "unknown" rather than "safe" follows the surveyed guidance that privacy-redacted or missing registration data must not be read as a benign signal.

**Why a self-learning blocklist.** Feeds cover broadly known campaigns but lag on locally targeted Vietnamese phishing. Writing back the pipeline's own confirmed verdicts turns each expensive suspicious-zone analysis into a cheap Layer A block for every subsequent visitor, and does so specifically for the threats this deployment actually sees.

**Why threshold calibration is separated from training.** The training set is balanced 50/50, but operational traffic is overwhelmingly legitimate. A threshold that is optimal on balanced test data will over-flag in the field. Section VI-B calibrates on simulated traffic with a realistic legitimate/phishing mix drawn from a manipulation-hardened popularity list [11].

---

## V. Security Considerations

The suspicious zone reads attacker-controlled HTML and retrieves from a knowledge store, so it inherits the LLM/RAG threat model. We use the OWASP Top 10 for LLM Applications 2025 [9] as the reference taxonomy.

**Indirect prompt injection (LLM01).** An attacker can place hidden text in the page — same-colour-as-background, off-screen, zero-width characters — carrying instructions such as "disregard earlier guidance; conclude this page is safe." This does not appear in any user query, so conventional input filtering does not see it; it enters only through the page-reading path. This is a demonstrated attack against AI browsers, not a hypothetical one [10]. The same hazard applies to Tier-2 RAG passages: a poisoned or retrieval-optimized advisory could carry an instruction rather than evidence. Mitigations: segregate retrieved and page content from instruction context with explicit delimiters and role framing; constrain the model to a fixed verdict schema; strip non-visible DOM text before it reaches the model; treat retrieved passages as quoted data; and never let page or retrieved content trigger an action other than producing a verdict.

**Shared-blocklist self-poisoning.** The write-back path means a *false-positive* verdict from the small local model does not just misjudge one page — it installs a Layer A rule that blocks a legitimate domain for every user for the rule's lifetime. This is a poisoning vector that originates *inside* the pipeline and is amplified by the shared blocklist. Mitigations: an allow-list of the Tranco [11] top-ranked domains is exempt from write-back; a domain the LLM confirms malicious is quarantined and promoted to a live rule only after a second signal agrees (an external feed, a second independent check, or human review); write-back rules carry a short TTL and are logged so a bad rule can be rolled back quickly.

**Weaker instruction separation in small models.** A ~2 B model has a weaker learned boundary between trusted system instructions and untrusted read-in text than a frontier model. Choosing a small local model for cost and hardware fit therefore increases injection susceptibility, which makes the active red-team of Section VI-E a requirement, not an add-on.

**Data and knowledge-base poisoning (LLM04).** If the Tier-2 store were populated by automated crawling, an attacker could plant documents that the model would then retrieve as fact. Only manually verified sources are ingested.

**Vector and embedding weaknesses (LLM08).** Content optimized for retrieval — not necessarily adversarial — can rank into the top-k without being relevant, biasing the explanation. Retrieved passages are treated as unverified references, checked for relevance before use, and never inserted verbatim into the final verdict.

**Adversarial evasion of Layer B.** A phishing author can tune lexical and content features to push the Random Forest score below the zoning threshold and land in the low zone, which is allowed with no LLM call and no warning. The three override rules are the partial backstop — a very recent registration, a just-issued certificate, or a small typosquatting distance still routes such a URL to the suspicious zone regardless of the classifier score — but a URL that evades both the classifier and all three rules is a genuine blind spot. Section VI-B measures the low-zone false-negative rate for this reason.

**Server-side request forgery via the override probes.** The domain-age and TLS override rules open outbound connections to the host under analysis, which an attacker controls. The implemented probe restricts connections to standard HTTPS ports, resolves the hostname and refuses loopback / private / link-local / other non-public addresses, and pins the socket to the vetted IP while keeping the original SNI, closing a DNS-rebinding window. Error reasons are fixed classifier strings, never raw exception text, so the probe cannot be used to exfiltrate internal responses.

**Excessive agency (LLM06).** The model emits a verdict and an explanation only. It has no tool-calling or API-invocation capability driven by page content. The single automated downstream effect — a Layer A write-back — is gated on a confirmed-malicious verdict *and* the corroboration and allow-list safeguards above, and is itself only a blocklist addition.

**Sensitive-information disclosure (LLM02).** The knowledge store is reviewed and cleaned before ingestion so that a generated explanation cannot leak internal or sensitive text.

**Operational dependency.** Unlike a cloud API, `ollama serve` must be running on a GPU-equipped host; if it stops, the suspicious zone loses its analyzer. The pipeline degrades to the technical-only fallback, and the deployment plan includes service health-checking and a pre-recorded/cached demonstration path.

---

## VI. Evaluation Methodology (pre-registered)

This plan — metrics, numeric targets, and pass/fail criteria — was fixed in advance so that later results cannot be selectively framed. Section VII reports what has been executed so far (Layer B); the suspicious zone is not yet implemented and none of its rows below are answered. Table 3 collects the targets; they are design goals, not measurements.

**Table 3 — pre-registered numeric targets.**

| Quantity | Target | Where |
|---|---|---|
| Zoning false-positive rate (simulated legit. traffic) | ≤ 0.5% | VI-B |
| Legitimate traffic routed to the LLM | ≤ 5% | VI-B |
| Low-zone false-negative rate | report | VI-B |
| Cross-check stream size / duration | ≥ 1,000 / 4 wk | VI-D |
| Early-detection rule (≥ 2/3 services flip, 72 h) | fixed pre-run | VI-D |
| Injection red-team pairs | ≥ 100 | VI-E |
| Post-hardening verdict-flip rate | < 5% | VI-E |
| LLM verdict-quality labelled set (κ reported) | ≥ 200 | VI-F |
| Layer A decision latency | < 10 ms | VI-G |
| Low-zone decision latency (p95) | < 1.5 s | VI-G |

### A. Classifier training and internal validation

Train the Random Forest on [3]. Before any split, deduplicate by registrable domain to keep near-identical URLs from the same kit out of both sides; the dataset carries no reliable timestamps, so a temporal split is not possible and random splitting is used with this caveat stated. Hyper-parameters are tuned by grid search *inside* a k=5 cross-validation; the headline numbers come from an outer locked test partition (nested design) so selection never touches the reported set. Report precision, recall, F1, and ROC-AUC as outer-split values with 95% confidence intervals, and the per-fold mean ± SD from the inner CV separately. Drop the six constant features; repeat for the compact model. Also report a reliability diagram, since the score is thresholded downstream, and the false-match rate of the typosquatting rule against the curated brand list. Results so far are in Section VII; still outstanding here are the confidence intervals, the reliability diagram, and the by-registrable-domain deduplication.

### B. Decision-threshold calibration

Build simulated traffic with a realistic class mix (legitimate sampled from Tranco [11]; phishing from held-out feed data), recording the fraction of phishing URLs already dead at collection time (their content and external features are then imputed as "unknown," and this fraction is reported, because it bounds how representative the simulation is). Sweep the zoning threshold and report the false-positive rate and suspicious-zone routing rate as functions of it. **Targets:** choose the operating point at FPR ≤ 0.5% on the simulated legitimate stream, and report the routing rate there with a design goal of ≤ 5% of legitimate traffic reaching the LLM. Also report the low-zone false-negative rate — phishing that scores low *and* trips no override, hence passes with no warning — as the safety-critical number.

### C. Generalization / concept-drift check

Evaluate the frozen classifier on PhiUSIIL [13]. List explicitly which Hannousse–Yahiouche features have a PhiUSIIL counterpart and map only those; features without a faithful counterpart are imputed as "unknown" and the count is reported. Because PhiUSIIL is known to be very easily separated by trivial models (a possible label-leakage or source-separability artefact), it is used only to estimate *relative* degradation against the 2020–2021 training snapshot [2], never as an absolute accuracy claim.

### D. Independent cross-checking

For a stream of fresh, previously unseen URLs (target ≥ 1,000 over ≥ 4 weeks), compare the pipeline's verdict against reputable external services — Google Safe Browsing v5 [24], VirusTotal v3 [30], URLhaus [23], and a scanning/screenshot service — computing agreement and disagreement rates; disagreements are re-queried after 24–72 h. Most fresh suspicious URLs are never confirmed by any service, so the expected confirmation yield is stated up front and disagreement is not read as vindication by default. The criterion for counting a disagreement as an early detection is fixed *before* the run (≥ 2 of 3 independent services flip to a malicious label within 72 h) and is not relaxed afterwards. Any public display of Safe Browsing results follows its attribution terms.

### E. Prompt-injection red-team

Build a corpus of matched page pairs (target ≥ 100 pairs), identical except that one member carries a hidden adversarial instruction of a catalogued type — same-colour text, hidden element, zero-width characters, fake-CAPTCHA framing as in [10] — plus a smaller set that plants the instruction in a Tier-2 RAG passage rather than the page. Measure the rate at which the local model's verdict flips toward "safe" in the presence of the injected instruction, before and after prompt-hardening; report both. **Pass criterion:** post-hardening flip rate < 5%, with any residual flips inspected individually.

### F. LLM verdict quality

On a labelled set of suspicious-zone URLs (target ≥ 200; two annotators, with Cohen's κ reported and disagreements adjudicated), measure the local model's verdict accuracy and the factual correctness of its explanations, with confidence intervals. A frontier reference (GPT-4V's 98.7% / 99.6% precision/recall [6]) is quoted for context only; because that number is on a different test set it is not a comparison, and if a frontier model is run it is run on *this* set. The stated expectation is that a ≤ 4 B local model does not match a frontier model; the aim is to bound the gap.

### G. Latency and throughput

Report end-to-end latency (p50/p95) for each zone on the reference hardware, broken down into page fetch, 87-feature extraction, Random Forest, RDAP/WHOIS round-trip, and LLM inference (with and without the `<think>` span). **Targets:** Layer A decision < 10 ms; low-zone decision p95 < 1.5 s; suspicious-zone p95 within a timeout measured on the reference GPU, past which the technical-only fallback is returned.

### H. Ablations

Report suspicious-zone routing rate and end-to-end verdict quality with (i) override rules disabled, (ii) Tier-1 RAG disabled, (iii) Tier-2 RAG disabled, (iv) self-learning write-back disabled, and (v) the Tranco allow-list disabled, to isolate each component's contribution.

---

## VII. Preliminary Results (Layer B)

Layer B has been implemented and evaluated on the training benchmark. All figures below are reproducible from committed scripts and are on the **balanced** 50/50 split — they are not operating-point numbers (Section VIII). The suspicious zone is not yet built, so Sections VI-C through VI-H report nothing.

**Exploratory analysis.** The dataset is exactly balanced (5,715 / 5,715), has no missing cells, and contains one duplicated URL (removed before splitting). Six features are all-zero (listed in Section III-C). The strongest label correlations are `google_index` (r = +0.73), `page_rank` (r = −0.51), and `nb_www` (r = −0.44); `domain_age` sits at its "not resolved" sentinel in 15.6% of rows.

**Classifier.** After dropping the six constants (81 features), a stratified 80/20 split (train 9,143 / test 2,286) and grid search over a k=5 stratified CV (refit on ROC-AUC, `random_state=42`) give the reference model `rf_v1`: 5-fold ROC-AUC 0.9935 ± 0.0007; held-out test ROC-AUC 0.9924, accuracy 0.961, F1(phishing) 0.961. The CV–test gap is below 0.01. Importance-ranked reduction selects 30 features — the smallest cut whose 5-fold ROC-AUC (0.9924) stays within 0.002 of the all-81 value (0.9935). The compact `rf_final` scores test ROC-AUC 0.991 and accuracy 0.954: the 81→30 cut costs about 0.7 accuracy points for 51 fewer features.

**Table 4 — Layer B models** (same split and grid; `rf_fast` uses only the 25 network-free features; `xgb_final` uses the same 30 as `rf_final`). Balanced-set numbers, not operating points.

| Model | Feat. | CV ROC-AUC | Test ROC-AUC | Test F1 | Test acc. |
|---|---|---|---|---|---|
| `rf_v1` | 81 | 0.9935 | 0.9924 | 0.9612 | 0.9611 |
| `rf_final` | 30 | 0.9924 | 0.9914 | 0.9547 | 0.9545 |
| `rf_fast` | 25 | 0.9772 | 0.9763 | 0.9292 | 0.9296 |
| `xgb_final` | 30 | 0.9942 | 0.9924 | 0.9634 | 0.9633 |

**External-lookup dependency.** The network-free `rf_fast` trails `rf_final` by 2.5 accuracy points and 3.4 points of phishing recall; the five external-service features carry ≈ 46% of the compact model's importance. The technical-only fallback path therefore cannot rely on the fast model alone — it must lean on the override rules and route uncertain cases to the suspicious zone.

**Gradient boosting.** On the same 30 features, `xgb_final` matches the all-81 `rf_v1` on every test metric while training about 5× faster. It is recorded as a strong alternative; the final choice is deferred to threshold calibration, since balanced-set accuracy is not the operating criterion.

**Override rules.** All three are implemented with offline unit tests (network calls monkeypatched; 48 tests, all passing). Live checks: rule 1 flags no well-known domain (`github.com`, `google.com`) and returns "unknown" for `vietcombank.com.vn` (`.vn` WHOIS exceeds the 0.5 s budget); rule 2, against *badssl.com* endpoints, flags self-signed, expired, and wrong-host certificates, and the SSRF guard blocks a loopback address and a non-HTTPS port (both return "unknown"); rule 3 runs entirely offline against the 62-brand list.

---

## VIII. Limitations

- **No suspicious-zone results yet.** Layer B is evaluated (Section VII); the LLM/RAG stage is not implemented, so its accuracy, latency, and injection-resistance are still unmeasured, and no end-to-end detection claim is made.
- **Layer B numbers are balanced-set only.** Every value in Section VII is on the 50/50 split; the false-positive and routing rates that matter operationally await calibration on imbalanced traffic (Section VI-B), and by-registrable-domain deduplication is not yet applied.
- **Training data is a 2020–2021 snapshot** [2]; concept drift is only partially addressed by the PhiUSIIL check [13], and two features are already degraded — `web_traffic` (Alexa retired May 2022) and the drift-prone `google_index`.
- **Balanced-set thresholds do not transfer to field traffic**; calibration (Section VI-B) mitigates but does not eliminate this.
- **Resolution loss in the suspicious zone**: one zone means a mildly odd URL and an almost-certainly-malicious URL both wait for the LLM.
- **Shared-blocklist self-poisoning**: a local-model false positive can block a legitimate domain for all users until its rule expires; the allow-list and corroboration safeguards (Section V) reduce but do not eliminate this.
- **Low-zone false negatives**: phishing that scores low and trips no override passes with no warning; Section VI-B measures the rate but the design cannot drive it to zero.
- **MV3 cannot hold a navigation**: for unknown URLs a malicious page is briefly loaded behind the "checking" overlay before it can be blocked.
- **Small-model exposure to injection** is higher than for a frontier model (Section V); the mitigation is testing and hardening, not elimination.
- **Local-inference variability and infrastructure dependency**: latency on a consumer GPU is not guaranteed, and the suspicious zone requires a running local model service on compatible hardware.
- **`.vn` registration data** is WHOIS-only, so domain-age signals for Vietnamese domains are less structured and less reliable than for gTLDs.
- **Vietnamese brand list and advisory corpus are hand-built**, so coverage is bounded by manual effort and needs periodic refresh.
- **Self-assessment bias risk** when comparing against reputable APIs; Section VI-D fixes criteria in advance to counter it.

---

## IX. Conclusion and Future Work

We have described a confidence-tiered phishing-detection pipeline in which the amount of computation a URL receives is decided by how certain the system is about it. A self-learning native blocklist handles known-bad domains at zero inference cost; a Random Forest and three technical override rules clear the unambiguous remainder; and only the residual hard cases reach a locally hosted small LLM grounded by a two-tier RAG store built for Vietnamese brand impersonation. Self-hosting removes per-request pricing, which is why the usual grey/black LLM split is unnecessary here. We motivated each choice against current work [1]–[10], [19], analyzed the LLM stage's security exposure with the OWASP LLM Top 10 (2025) [9], and pre-registered an evaluation protocol. Layer B is built and evaluated (Section VII): the compact model holds ROC-AUC on the benchmark, and the network-free ablation quantifies the cost of losing external lookups. Future work is the suspicious zone — the local model, the two-tier RAG store, and its injection red-team — followed by threshold calibration on realistic traffic and the browser-extension field trial.

---

## Statements

**Data availability.** The training dataset is publicly available: Hannousse and Yahiouche, *Web page phishing detection*, Mendeley Data V3 [3]. The PhiUSIIL dataset is available from the UCI Machine Learning Repository [13]. The Layer B training scripts, EDA and model reports, and the 62-brand Vietnamese list (a working draft pending cross-check against NCSC and *chongluadao.vn*) are in the project repository. The advisory corpus and the suspicious-zone prompt templates (system prompt and untrusted-content delimiter scheme, needed to audit the injection-resistance claims of Section V) will be released with the LLM-stage implementation, subject to source licensing.

**Ethics.** The classifier and protocol work with URLs and publicly served web content and involve no human subjects. The browser extension, however, observes the URLs a user visits and sends them to the backend, which is processing of personal data under Vietnam's Personal Data Protection Decree (13/2023/ND-CP). The design intent — not yet independently audited — is to send only the registrable domain (or a hash) rather than full URLs, to require explicit consent at install time, to store verdicts under a 24-hour TTL with no identity-linked browsing history, and to keep live phishing URLs inside controlled, isolated backend processes. External detection APIs are used within their published terms, with attribution where required.

**Author contributions (CRediT).** [Author 1]: conceptualization, methodology, software (backend, extension, LLM/RAG infrastructure, blocklist), writing — review and editing. [Author 2]: methodology, software (classifier, override rules, evaluation harness), validation, formal analysis, writing — original draft. Both authors approved the final manuscript.

**Conflict of interest.** The authors declare no competing interests.

**Funding.** This work received no external funding; it was carried out as an undergraduate information-technology capstone project.

**Use of AI tools.** AI-based coding and writing assistants were used for drafting, literature triage, and code scaffolding. All cited facts and figures were verified by the authors against the primary sources listed in the References. The authors are responsible for the final content.

---

## References

[1] A. Safi and S. Singh, "A systematic literature review on phishing website detection techniques," *Journal of King Saud University – Computer and Information Sciences*, vol. 35, no. 2, pp. 590–611, 2023, doi: 10.1016/j.jksuci.2023.01.004.

[2] A. Hannousse and S. Yahiouche, "Towards benchmark datasets for machine learning based website phishing detection: An experimental study," *Engineering Applications of Artificial Intelligence*, vol. 104, art. 104347, 2021, doi: 10.1016/j.engappai.2021.104347.

[3] A. Hannousse and S. Yahiouche, "Web page phishing detection," Mendeley Data, V3, 2021, doi: 10.17632/c2gw7fy2j4.3.

[4] L. Breiman, "Random forests," *Machine Learning*, vol. 45, no. 1, pp. 5–32, 2001, doi: 10.1023/A:1010933404324.

[5] M. A. Tamal, M. K. Islam, T. Bhuiyan, and A. Sattar, "Dataset of suspicious phishing URL detection," *Frontiers in Computer Science*, vol. 6, art. 1308634, 2024, doi: 10.3389/fcomp.2024.1308634.

[6] T. Koide, H. Nakano, and D. Chiba, "ChatPhishDetector: Detecting phishing sites using large language models," *IEEE Access*, vol. 12, pp. 154381–154400, 2024, doi: 10.1109/ACCESS.2024.3483905.

[7] J. Lee, P. Lim, B. Hooi, and D. M. Divakaran, "Multimodal large language models for phishing webpage detection and identification," in *Proc. APWG Symp. Electronic Crime Research (eCrime)*, 2024, arXiv:2408.05941.

[8] S. S. Roy and S. Nilizadeh, "PhishLang: A real-time, fully client-side phishing detection framework using MobileBERT," arXiv:2408.05667, 2024.

[9] OWASP GenAI Security Project, "OWASP Top 10 for LLM Applications 2025 (v2.0)," 18 Nov. 2024. [Online]. Available: https://owasp.org/www-project-top-10-for-large-language-model-applications/

[10] Guardio Labs, "Scamlexity: The dangerous new world of agentic AI browsers" (including the "PromptFix" technique), Aug. 2025. [Online]. Available: https://guard.io/labs (industry red-team report; see also secondary coverage, The Hacker News, "Experts find AI browsers can be tricked by PromptFix exploit," Aug. 2025).

[11] V. Le Pochat, T. Van Goethem, S. Tajalizadehkhoob, M. Korczyński, and W. Joosen, "Tranco: A research-oriented top sites ranking hardened against manipulation," in *Proc. Network and Distributed System Security Symp. (NDSS)*, 2019, doi: 10.14722/ndss.2019.23386.

[12] Z. Nussbaum, J. X. Morris, B. Duderstadt, and A. Mulyar, "Nomic Embed: Training a reproducible long context text embedder," arXiv:2402.01613, 2024.

[13] A. Prasad and S. Chandra, "PhiUSIIL: A diverse security profile empowered phishing URL detection framework based on similarity index and incremental learning," *Computers & Security*, vol. 136, art. 103545, 2024, doi: 10.1016/j.cose.2023.103545. Dataset: UCI Machine Learning Repository, "PhiUSIIL Phishing URL Dataset," 2024, doi: 10.24432/C5D030.

[14] R. M. Mohammad, F. Thabtah, and L. McCluskey, "An assessment of features related to phishing websites using an automated technique," in *Proc. Int. Conf. Internet Technology and Secured Transactions (ICITST)*, 2012, pp. 492–497.

[15] IETF, M. Blanchet, "Finding the authoritative Registration Data Access Protocol (RDAP) service," RFC 9224, Mar. 2022, doi: 10.17487/RFC9224.

[16] IETF, S. Hollenbeck and A. Newton, "Registration Data Access Protocol (RDAP) query format," RFC 9082, Jun. 2021, doi: 10.17487/RFC9082.

[17] IETF, S. Hollenbeck and A. Newton, "JSON responses for the Registration Data Access Protocol (RDAP)," RFC 9083, Jun. 2021, doi: 10.17487/RFC9083.

[18] ICANN, "ICANN Update: Launching RDAP; Sunsetting WHOIS," announcement, 27 Jan. 2025. [Online]. Available: https://www.icann.org/en/announcements/details/icann-update-launching-rdap-sunsetting-whois-27-01-2025-en — as of 28 Jan. 2025, gTLD registries/registrars are no longer contractually required to operate WHOIS on port 43; the ICANN Registration Data Policy took effect 21 Aug. 2025.

[19] Google, "chrome.declarativeNetRequest — API reference (dynamic and static rule limits)," Chrome for Developers, 2024. [Online]. Available: https://developer.chrome.com/docs/extensions/reference/api/declarativeNetRequest

[20] Google, "chrome.webNavigation — API reference," Chrome for Developers, 2024. [Online]. Available: https://developer.chrome.com/docs/extensions/reference/api/webNavigation

[21] V. I. Levenshtein, "Binary codes capable of correcting deletions, insertions, and reversals," *Soviet Physics Doklady*, vol. 10, no. 8, pp. 707–710, 1966.

[22] OpenPhish, "OpenPhish community feed." [Online]. Available: https://openphish.com/

[23] abuse.ch, "URLhaus — malware URL exchange." [Online]. Available: https://urlhaus.abuse.ch/

[24] Google, "Safe Browsing API (v5)," Google for Developers. [Online]. Available: https://developers.google.com/safe-browsing

[25] Chroma, "Chroma — the open-source embedding database." [Online]. Available: https://www.trychroma.com/

[26] Ollama, "Ollama — get up and running with large language models locally." [Online]. Available: https://ollama.com/

[27] Qwen Team, "Qwen3 technical report," arXiv:2505.09388, 2025.

[28] T. Koide, H. Nakano, and D. Chiba, "Detecting phishing sites using ChatGPT," arXiv:2306.05816, 2023 (preprint predecessor of [6]).

[29] M. Dandotiya, N. K. Goyal, A. Khunteta, and B. Tiwari, "Real time identification of phishing attacks through machine learning enhanced browser extensions," *Scientific Reports*, vol. 16, no. 1, art. 6612, 2026, doi: 10.1038/s41598-026-35655-7.

[30] VirusTotal, "VirusTotal API v3 documentation." [Online]. Available: https://docs.virustotal.com/

[31] D. M. Divakaran and A. Oest, "Phishing detection leveraging machine learning and deep learning: A review," *IEEE Security & Privacy*, vol. 20, no. 5, pp. 86–95, 2022, doi: 10.1109/MSEC.2022.3175225.

[32] H. Le, Q. Pham, D. Sahoo, and S. C. H. Hoi, "URLNet: Learning a URL representation with deep learning for malicious URL detection," arXiv:1802.03162, 2018.

[33] Y. Lin *et al.*, "Phishpedia: A hybrid deep learning based approach to visually identify phishing webpages," in *Proc. 30th USENIX Security Symp.*, 2021, pp. 3793–3810.

[34] R. Liu, Y. Lin, X. Yang, S. H. Ng, D. M. Divakaran, and J. S. Dong, "Inferring phishing intention via webpage appearance and dynamics: A deep vision based approach," in *Proc. 31st USENIX Security Symp.*, 2022, pp. 1633–1650.

[35] A. Oest *et al.*, "Sunrise to sunset: Analyzing the end-to-end life cycle and effectiveness of phishing attacks at scale," in *Proc. 29th USENIX Security Symp.*, 2020.

[36] Qwen Team, "Qwen3.5 small model series," Ollama model library, 2026. [Online]. Available: https://ollama.com/library/qwen3.5 (released Feb. 2026; `qwen3.5:2b` ≈ 2.7 GB quantized). See also Qwen Team, "Qwen3.5-Omni Technical Report," arXiv:2604.15804, 2026.

[37] J. Szurdi, B. Kocso, G. Cseh, J. Spring, M. Félegyházi, and C. Kanich, "The long 'taile' of typosquatting domain names," in *Proc. 23rd USENIX Security Symp.*, 2014.

[38] P. Agten, W. Joosen, F. Piessens, and N. Nikiforakis, "Seven months' worth of mistakes: A longitudinal study of typosquatting abuse," in *Proc. Network and Distributed System Security Symp. (NDSS)*, 2015.
