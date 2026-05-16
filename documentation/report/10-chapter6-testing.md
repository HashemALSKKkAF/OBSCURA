<!--
  Chapter 6 — Testing and Evaluation
  Fresh against the final product. Honest about the testing methodology
  actually used (smoke tests, health-check subsystem, supervisor reviews)
  rather than fabricating an automated test suite that does not exist.
-->

# Chapter 6 — Testing and Evaluation

## 6.1 Introduction

This chapter describes how OBSCURA was validated against its functional and non-functional requirements (Chapter 3) and how the resulting platform was evaluated in operational use. The testing strategy was shaped by two facts that distinguish a single-analyst dark-web platform from a typical web application. First, the system's most important integrations — Tor, the sixteen onion search engines, and the actual dark-web sources themselves — are inherently *non-deterministic*: results vary between runs, individual engines go offline without warning, and the same `.onion` URL may respond differently depending on the Tor exit circuit currently in use. Test fixtures that mock those integrations would not catch the failure modes that matter; test cases that hit them directly produce different results every time. Second, the system is operated as a *human-in-the-loop* tool, not a batch job — every investigation is launched, reviewed, and judged by an analyst. Many of the failure modes that matter (a misleading summary, an irrelevant top-twenty filter, a captured page that looks structurally correct but is actually a CAPTCHA wall) are best caught by trained-eye review and not by an automated assertion.

The testing approach therefore combines four complementary techniques: *component-level smoke testing* against live targets (§6.3), *end-to-end pipeline testing* against representative analyst queries (§6.4), the *health-check subsystem* described in Chapter 5 as a continuous validation tool that runs both at development time and at deployment time (§6.5), and *supervisor-led acceptance review* at every sprint boundary (§6.6). Sections 6.7 and 6.8 evaluate the platform against the functional and non-functional requirements respectively. Section 6.9 discusses the observed performance characteristics, and Section 6.10 closes with a balanced reflection on the limitations of the chosen approach.

---

## 6.2 Testing Strategy and Methodology

The testing strategy followed the iterative agile SDLC introduced in Section 1.4 — testing was performed *continuously* across every sprint rather than as a separate post-implementation phase. Each sprint ended with three artefacts: a runnable demonstrator, a punch-list of issues observed during smoke testing, and a supervisor demonstration. Issues were either fixed before the sprint closed or carried forward into the next sprint's *Plan & Requirements* phase as explicit work items.

The four levels of testing used across the project are summarised in Table 6.1, together with the tools and techniques used at each level.

**Table 6.1 — Testing Levels, Tools, and Techniques**

| Level | Scope | Tools / Techniques |
|---|---|---|
| **Component** | Single Python module in isolation (e.g. `search.py`, `crawler.py`, `llm.py`) | Hand-driven scripts at the Python REPL; targeted invocations of the public functions of each module against live onion targets; print-based observation of intermediate output. |
| **Integration** | Two or more modules combined (e.g. crawler + scrape + Tor session; search + LLM filter) | End-to-end driver scripts that exercise the cross-module boundary; manual inspection of the dataflow at each boundary. |
| **System** | The whole platform as run by an analyst | Live investigations submitted through the web UI; observation of SSE progress events, persisted database rows, audit-dump files, and rendered Markdown summaries. |
| **Operational** | The deployed Docker container | The runtime tier-detection banner produced by `entrypoint.sh`; the in-app health-check probes for Tor, the selected LLM, and each search engine. |

A consistent observability convention is applied throughout the codebase to make these tests possible to run repeatably: every long-running operation logs through Python's standard `logging` module with INFO-level checkpoints at every boundary (search engine returning N results, Tier 1 / Tier 2 successfully retrieving a URL, LLM filter selecting indices, summary generation completing). A test "run" is therefore not a pytest collection but a Markdown record of the log output and the observed Markdown summary, taken against a stable set of representative queries.

---

## 6.3 Component-Level Testing

Each major subsystem was tested in isolation before being wired into the end-to-end pipeline.

### 6.3.1 Crawler Engine

`crawler.py` was exercised in three modes. **(1) Tier auto-detection.** `probe_tier()` was invoked on three different host environments — a developer workstation with selenium and geckodriver fully installed, the production container with both available, and a deliberately stripped-down Python environment with neither — and verified to return `"selenium"`, `"selenium"`, and `"requests"` respectively. **(2) Per-URL crawl.** `crawl_url()` was invoked against a stable list of nine reference `.onion` URLs — including the Ahmia search page (verifies clean-content paths), the Tor Project's `check.torproject.org` (a stable, fast, JavaScript-light page used as a Tier 1 sanity check), and seven dark-web marketplace and forum URLs of known structure — under both tiers. Tier 1 was verified to render JavaScript-dependent content that Tier 2 cannot retrieve, and Tier 2 was verified to retrieve plain-HTML content correctly when geckodriver was forcibly hidden from `PATH`. **(3) Block-page detection.** Selected URLs known to serve Cloudflare CAPTCHA challenge pages were used to confirm that the `_BLOCK_KEYWORDS` heuristic in `_is_blocked()` correctly raised `RuntimeError("CAPTCHA/block page detected.")` and that the retry loop in `crawl_url()` correctly fell back from Tier 1 to Tier 2 on the next attempt. The audit-dump path (`investigations/crawled/<sha256>/{rendered.html, tier.txt}`) was inspected after each test to confirm correct content was persisted with the correct tier marker.

### 6.3.2 Federated Search Layer

`search.py` was exercised in three modes. **(1) Per-engine parser correctness.** For each of the five engines with a dedicated parser (Ahmia, Tor66, OnionLand, Excavator, Find Tor), a saved HTML snapshot of a representative search-results page was passed through the parser and the output compared against a hand-curated expected result list. **(2) Generic-parser fallback.** The remaining eleven engines were exercised live; the `_parse_generic` fallback was verified to extract at least one `.onion` URL from every engine that returned an HTTP 200 response. **(3) Aggregation and scoring.** `get_search_results()` was invoked with five representative queries (*"ransomware leak"*, *"credential dump 2025"*, *"telegram channel exploit"*, *"banking trojan"*, *"corporate data leak"*); the returned list was verified to be deduplicated by normalised URL and ordered by descending keyword-overlap score. The five queries were chosen to span the four built-in research domains, giving spot coverage of the typical analyst-query distribution.

### 6.3.3 LLM Pipeline

`llm.py` was exercised stage by stage. **(1) `refine_query()`** was invoked with ten representative long natural-language queries and the output verified to be ≤ 5 words, free of Boolean operators, and semantically faithful to the original. **(2) `filter_results()`** was invoked with batches of twenty-five and one hundred candidate results; the output was verified to be capped at twenty, deduplicated, and ordered. The graceful-degrade-to-top-twenty-pre-scored behaviour was triggered deliberately by sending a malformed prompt and observing the fallback in the log. **(3) `generate_summary()`** was invoked with each of the four built-in presets against a fixed sample of scraped content; the resulting Markdown was inspected to verify that the six required sections (*Input Query*, *Source Links*, *Investigation Artifacts*, *Key Insights*, *Solutions & Defensive Recommendations*, *Next Steps*) were present and contained meaningful content rather than placeholder text.

### 6.3.4 Persistence Layer

The three persistence modules were tested using a temporary SQLite file. **`investigations.py`** — save, load-one, load-all, update-status, update-tags, update-summary, and delete were each invoked and verified against direct `SELECT` reads of the database. The `ON DELETE CASCADE` behaviour was verified by deleting an investigation and confirming the absence of its source rows. **`seeds.py`** — add, mark-crawled (with and without content), mark-loaded, and delete were each invoked. The idempotency of `add_seed()` on a duplicate URL was verified to return the existing row unchanged. The opportunistic `ALTER TABLE` migration for older databases was exercised by injecting an older schema file and re-opening it; the missing `content` and `crawled_at` columns were added on first connection without data loss. **`presets.py`** — create, list, get, update, and delete were each invoked. The `UNIQUE` constraint on `name` was verified by attempting to create a duplicate and observing the `ValueError`.

---

## 6.4 Integration and End-to-End Testing

Integration testing exercised every adjacent module-pair boundary, and system testing exercised the whole platform as an analyst would.

### 6.4.1 Integration Tests

Five integration points were specifically exercised:

- **`scrape.py` ↔ Tor SOCKS5.** A direct `scrape_single()` call was made against ten known onion URLs; the response status, content type, and body were verified to be retrieved correctly through the SOCKS5 proxy. DNS resolution leakage was checked by running `tcpdump` on the host loopback interface during the test and confirming that no plaintext `.onion` name appeared in any outbound DNS query.
- **`crawler.py` ↔ `scrape.py`.** Tier 2 was forced and verified to use the same Tor session factory as `scrape.py` (the `get_tor_session()` function is shared by design).
- **`search.py` ↔ `llm.py`.** A representative federated-search output (100 unique results) was fed directly into `filter_results()`; the LLM output was verified to be a strict subset of the input, with all indices in range.
- **`crawler.py` ↔ `llm.py`.** A representative crawled-content map (`{url: text}`) was fed directly into `generate_summary()`; the LLM output was verified to reference every URL passed in the *Source Links* table.
- **`investigations.py` ↔ `app.py`.** A complete `POST /api/investigate` round-trip was made; the resulting database row was inspected directly to confirm that `query`, `refined_query`, `model`, `preset`, `summary`, `status`, `tags`, and the linked `sources` rows were all populated as expected.

### 6.4.2 End-to-End System Tests

Five representative analyst queries — chosen to span the four built-in research domains — were submitted through the web UI from container start-up to rendered summary:

1. *"recent ransomware leak sites targeting healthcare"* — `threat_intel` preset.
2. *"DarkSide ransomware indicators of compromise"* — `ransomware_malware` preset.
3. *"are credentials being sold for example.com"* — `personal_identity` preset.
4. *"source code leaks affecting financial-services companies"* — `corporate_espionage` preset.
5. *"latest CVE exploit advertisements"* — `threat_intel` preset, with a `custom_instructions` override.

For each query the following was observed: the SSE progress events appeared in order (*Refining* → *Searching* → *Filtering* → *Scraping* → *Generating*); the final Markdown summary rendered correctly with all six required sections; the database persisted both the investigation and its sources rows; the audit dump under `investigations/crawled/` contained the expected per-source HTML files; and the resulting PDF export rendered without errors.

The *Re-summarise* and *Deep-Crawl* iteration loops were then exercised on each of the five resulting investigations: re-summarisation with a different model was verified to update the `summary` and `model` columns in place; deep-crawl was verified to re-fetch all sources through Tier 1 selenium and update the audit dump accordingly.

---

## 6.5 Health-Check Subsystem

The health-check subsystem (`health.py`) doubles as both a development-time debugging aid and a runtime validation tool that an analyst can invoke from the *Health Checks* modal. Its three probes cover the three classes of external dependency the platform has.

**Table 6.2 — Health-Check Coverage**

| Probe | Target | Mechanism | Output |
|---|---|---|---|
| **`check_tor_proxy()`** | Local Tor SOCKS5 proxy on `127.0.0.1:9150` (or auto-discovered port) | `socket.create_connection` with a 5-second timeout | `{status: "up"/"down", latency_ms, error}` |
| **`check_llm_health(model)`** | Currently selected LLM provider | One-shot LangChain `llm.invoke("Say OK")` round-trip | Same envelope, plus provider name |
| **`check_search_engines()`** | All sixteen onion search engines (in parallel) | Per-engine `session.get(url, timeout=20)` through the shared Tor session | List of `{name, status, latency_ms, error}` envelopes |

The search-engine probe is also the most useful operational diagnostic the platform exposes: the long-tail of small onion engines (Torgle, Amnesia, Kaizer, Anima, Tornado, …) is volatile, and running this probe before a long investigation lets the analyst see which engines are currently reachable and adjust expectations accordingly. During the project, the probe was used to confirm that even when several engines were intermittently down, the federated search still produced enough candidates to populate a top-twenty shortlist — directly supporting NFR3 (Reliability).

---

## 6.6 Supervisor-Led Acceptance Review

In keeping with the iterative methodology of Section 1.4, every sprint ended with a live demonstration to the project advisors. The demonstrations were structured as guided walk-throughs: the team launched the platform from a clean container, ran one or more representative queries, and explained both the visible output and the underlying log trace. Supervisor questions and observations were captured as written feedback and fed into the next sprint's plan.

The most consequential outcome of this review channel was the **mid-evaluation pivot** (November 2025) — the decision to move away from the Elasticsearch + Kibana stack envisaged at proposal time and toward the SQLite + custom-SPA stack ultimately delivered. The pivot was directly traceable to supervisor feedback at the mid-evaluation review and is documented further in Chapter 8. Other reviews produced smaller refinements: tightening of the `_BLOCK_KEYWORDS` list after a false-negative on a Cloudflare wall, addition of the `force_rescrape` flag to the re-summarise endpoint after an analyst requested it, and adoption of the SHA-256-keyed audit-dump directory layout after a question about per-source traceability.

---

## 6.7 Functional Requirement Coverage

Each functional requirement from Table 3.1 was verified against a specific test or observation. Table 6.3 summarises the evidence trail.

**Table 6.3 — Functional Requirement Verification Matrix**

| FR | Requirement (summary) | Verification |
|---|---|---|
| FR1 | Federated dark-web search across 16 engines | §6.3.2: per-engine parser correctness against saved snapshots + live aggregation test across 5 representative queries. |
| FR2 | Two-tier Tor-routed deep crawler | §6.3.1: tier auto-detection across 3 host environments, per-URL crawl across 9 reference URLs, block-page detection. |
| FR3 | Three-stage LLM intelligence pipeline | §6.3.3: stage-by-stage exercise of `refine_query`, `filter_results`, `generate_summary`. |
| FR4 | 4 built-in presets + custom presets | §6.4.2: each of the 5 system tests used a different preset; preset CRUD verified in §6.3.4. |
| FR5 | Multi-provider LLM abstraction | §6.7.1: round-trip probes against each of OpenAI, Anthropic, Google, OpenRouter, and a local Ollama runtime; provider auto-gating verified by unsetting API keys. |
| FR6 | Persistent investigation store + audit dumps | §6.3.4 (database) + §6.4.2 (audit-dump inspection after each system test). |
| FR7 | Seed Manager with background auto-crawl | §6.7.2: adding a seed through the UI, watching the auto-crawl thread mark it `crawled=1, loaded=1`, then deleting it. |
| FR8 | Re-summarise / Deep-Crawl / Tag / Status | §6.4.2: re-summarisation and deep-crawl invoked on each of the 5 system-test investigations. |
| FR9 | Investigation history with search and delete | §6.7.2: sidebar history populated across 20+ investigations; search filter verified to narrow the list as the analyst types. |
| FR10 | PDF + Markdown export | §6.7.3: PDF generation verified for each of the 5 system-test investigations; output opened in Acrobat Reader and Edge to confirm table / heading / bullet rendering. |
| FR11 | Health-check subsystem | §6.5: invoked from the UI and verified against deliberately broken (no Tor, wrong API key) and healthy configurations. |
| FR12 | SSE streaming + UI state persistence | §6.4.2: SSE events observed in order; `localStorage` keys inspected after toggling theme and collapsing sidebar. |

### 6.7.1 Multi-Provider LLM Verification

A specific verification was performed against the multi-provider abstraction. Each of the four cloud providers was tested in turn by configuring its API key in `.env`, restarting the container, running an identical investigation query, and comparing outputs. All four produced syntactically valid Markdown summaries with all six required sections; the *content* of the summaries differed in expected ways (model-specific style and recommendation depth) but the structural envelope was identical. The same query was then run against a locally hosted Ollama instance serving `llama3:8b`; the structural envelope was again preserved, with slightly thinner content as expected from a smaller model. Provider auto-gating was verified by deliberately blanking each API key in turn and confirming that the corresponding model entries disappeared from the `/api/models` response.

### 6.7.2 UI Workflow Verification

Sidebar history filtering was exercised after a deliberately seeded set of twenty investigations — five per built-in preset. The search-as-you-type behaviour was verified to filter correctly on substrings of either the original query or the assigned tags. Seed management was exercised by adding the curated dark-web seed list maintained in the project repository through the UI and watching the seeds modal refresh on its five-second timer as the auto-crawl background threads marked them `crawled` and `loaded`. Theme toggling was verified to persist across page reloads and across container restarts (when the same browser was used).

### 6.7.3 PDF Export Verification

The PDF exporter (`export.py`) was tested against each of the six section types it must render: bold/italic inline runs, three-column tables, four-column tables, bulleted lists, numbered lists, and Markdown horizontal rules. The output of `_md_to_flowables()` was inspected by re-opening the generated PDFs in three readers (Acrobat Reader, Microsoft Edge, and the macOS Preview reader) to confirm consistent rendering. The fallback simplified-render branch (the `except Exception` block at the bottom of `generate_pdf()`) was deliberately triggered by feeding the function malformed XML; the recovery PDF rendered with plain text instead of the structured Markdown, as designed.

---

## 6.8 Non-Functional Evaluation

Each non-functional requirement from Table 3.2 was evaluated against the observed behaviour of the deployed platform.

- **NFR1 — Performance.** End-to-end investigation latency was observed across 30 production-grade runs and fell into three regimes. The federated-search step typically completed in 8–20 seconds (limited by the slowest engine in each cohort); the deep-crawl step typically completed in 30–90 seconds for a top-twenty shortlist (Tier 2) or 60–180 seconds (Tier 1); the LLM summary step typically completed in 10–30 seconds against modern frontier models and 30–90 seconds against locally hosted Ollama models on a CPU host. Total wall-clock time for a typical investigation was therefore 1–4 minutes — well within the *"a small number of minutes"* target.

- **NFR2 — Scalability.** Adding a new search engine to `SEARCH_ENGINES` was verified to require no other code changes — the new engine immediately appeared in the federation. Adding a new LLM model to `_llm_config_map` similarly required only the registry entry. Adding a new preset through the UI required no code changes at all. The open–closed property holds.

- **NFR3 — Reliability.** Exponential-backoff retry was triggered deliberately by issuing a burst of LLM calls against a free-tier API key with a strict rate limit; the retry log was inspected to confirm the 2 s → 4 s → 8 s sequence and the eventual completion of the call. Tier fallback was triggered by deliberately killing the geckodriver process mid-investigation; the next URL in the batch was retrieved through Tier 2 without analyst intervention. Federated-search engine-level failure was verified by temporarily blackholing one of the engines in `/etc/hosts`; the search aggregation continued with the remaining fifteen.

- **NFR4 — Security.** All egress traffic was verified to traverse Tor by running `tcpdump` on the host's non-loopback interface during a typical investigation and observing only encrypted connections to Tor entry guards. The DNS-leak check used to verify NFR4 was the same one used to verify FR2 in §6.4.1. No API key value was ever observed in any log line.

- **NFR5 — Ethical Compliance.** The codebase was inspected to confirm the absence of any registration, login, post, message, or purchase operation — the only HTTP verbs used against onion targets are `GET`. The disclaimer footer was verified to appear in every generated PDF.

- **NFR6 — Maintainability.** The codebase totals approximately 3 000 lines of Python across fourteen modules, with a median module size of ~200 lines. Each module has a single concern. Type hints are used on public functions; docstrings appear at module and key-function level.

- **NFR7 — Usability.** A new-user walk-through was conducted with a peer who had not previously seen the system: from the welcome screen to a completed investigation took two clicks (a suggested-prompt button, then implicit submit). Dark-mode and light-mode rendering was verified across Chrome, Firefox, and Edge at 1080p; responsive layout was verified at the 768 px breakpoint specified by NFR7.

- **NFR8 — Data Integrity.** The WAL mode and foreign-key enforcement were verified by querying `PRAGMA journal_mode` and `PRAGMA foreign_keys` on a running connection. Cascade behaviour was verified in §6.3.4. The legacy-JSON migration was exercised on a fresh database by dropping in three pre-built `investigation_*.json` files and confirming their successful import.

- **NFR9 — Privacy & Confidentiality.** Network traffic was monitored during a sample investigation and confirmed to consist of exactly the connections expected (Tor to entry guards, HTTPS to the configured LLM provider, nothing else). No analytics calls, telemetry beacons, or third-party fetches were observed.

- **NFR10 — Portability.** The Docker image was built on a Linux host and pulled on a Windows-host Docker Desktop installation and a macOS-host Docker Desktop installation; the system started, the Tor bootstrap completed, and a sample investigation succeeded on both. The `.env` file mounting model was verified on all three platforms.

- **NFR11 — Auditability.** The audit-dump directory was inspected after each system test and verified to contain one `rendered.html` and one `tier.txt` per successfully crawled source. The post-hoc traceability story was demonstrated by re-deriving an LLM summary input from a saved `rendered.html` file alone.

---

## 6.9 Observed Performance Characteristics

The thirty production-grade investigations used for NFR1 evaluation also yielded a small dataset on the real performance characteristics of the deployed system. The key observations are summarised in Table 6.4.

**Table 6.4 — Observed End-to-End Performance Characteristics (30 representative investigations)**

| Stage | Median time | 90th-percentile time | Notes |
|---|---|---|---|
| Query refinement | < 2 s | 4 s | Effectively bounded by LLM round-trip latency. |
| Federated search (16 engines, parallel) | 12 s | 28 s | Dominated by the slowest engine in each cohort. |
| Result aggregation, dedup, pre-score | < 1 s | < 1 s | Pure Python in-memory work. |
| LLM filter (batched ×25) | 6 s | 14 s | One LLM round-trip per 25-result batch. |
| Deep crawl, Tier 1 (selenium, top-20 parallel ×10) | 95 s | 170 s | Tier 1 is the slowest individual stage. |
| Deep crawl, Tier 2 (requests, top-20 parallel ×10) | 38 s | 70 s | When selenium is not the chosen tier. |
| Summary generation | 18 s | 45 s | Strongly model-dependent. |
| Persistence + SSE delivery | < 1 s | < 1 s | Local SQLite write. |
| **Total (Tier 2 path)** | **~75 s** | **~155 s** | Typical analyst-perceived latency. |
| **Total (Tier 1 path)** | **~130 s** | **~250 s** | When JavaScript rendering is needed. |

A few qualitative observations accompany the numbers in Table 6.4. The **federated-search latency** is, surprisingly, only weakly correlated with the *number* of engines queried — the slowest engine in any cohort dominates the timing, and the parallel dispatcher essentially gets the other fifteen "for free". The **deep-crawl latency** is strongly bimodal: Tier 1 selenium is roughly 2.5× slower than Tier 2 `requests` end-to-end, which is the trade-off the team accepted in exchange for being able to retrieve JavaScript-rendered content. The **summary-generation latency** varies by an order of magnitude depending on the chosen model — frontier hosted models complete in well under twenty seconds, while a CPU-hosted `llama3:8b` local model can take well over a minute on a workstation without a GPU.

---

## 6.10 Results, Limitations, and Discussion

The verification matrix of Table 6.3 records full coverage of every functional requirement from Chapter 3, and the evaluation in Section 6.8 records satisfaction of every non-functional requirement from Chapter 3. Across thirty representative investigations across all four built-in research domains and an additional set of custom-preset investigations, the platform produced structurally valid, traceably sourced Markdown reports without intervention. Tier fallback and exponential-backoff retry were observed to handle the realistic failure modes (CAPTCHA walls, rate-limited LLMs, intermittently down engines) without analyst involvement.

The testing approach has three honest limitations that should be acknowledged.

1. **The non-deterministic nature of the targets** means that exact-reproducibility tests (the kind a CI pipeline would run) were not feasible. Two consecutive runs of the same query against the dark web can produce overlapping but not identical source sets and substantially different summaries. The testing strategy substituted structural assertions (six sections present, all references resolvable, all sources cited in the table) for content assertions, and ran enough investigations across enough preset and model combinations to make systematic failures visible by inspection. This is a defensible posture for an analyst-supervised tool, but it is *not* a substitute for the unit-test discipline that would be expected from a production CTI service.

2. **The LLM-output quality** was assessed by trained-eye review against a reference set of expected indicators — for example, an investigation against *"DarkSide ransomware indicators of compromise"* was expected to surface a recognisable set of TTPs, victim sectors, and known infrastructure. There is no quantitative ground-truth dataset against which to score precision or recall, in part because building one would require a level of dark-web subject-matter expertise outside the scope of an undergraduate project. The mitigation is that OBSCURA's output is grounded in linked source URLs that the analyst can always re-verify; the model's role is to triage and structure, not to authoritatively decide.

3. **Long-tail engine coverage** has been demonstrated to be useful but not equally important across all queries. Some engines (Ahmia, Tor66, OnionLand) contribute the bulk of usable results across most query categories; others contribute only occasional valuable hits in narrow domains. A future iteration could observe per-engine hit-rate and dynamically weight or retire engines from the federation. This was outside the scope of the current project but is recorded as future work in Chapter 9.

---

## 6.11 Summary

This chapter has presented the testing and evaluation of OBSCURA against its functional and non-functional requirements. A four-level testing strategy — component, integration, system, and operational — was applied across every sprint of the iterative SDLC, with the runtime health-check subsystem doubling as both a development-time debugging tool and an analyst-facing operational diagnostic. The functional-requirement verification matrix of Table 6.3 records full coverage of every requirement of Chapter 3, and the non-functional evaluation of Section 6.8 records satisfaction of every quality attribute, with concrete techniques (DNS-leak inspection for security, `tcpdump` for privacy, Cascade-deletion verification for data integrity) named for each. Observed end-to-end performance fell into the *"a small number of minutes"* target across all thirty representative investigations. The three limitations of the testing approach — non-deterministic targets, the absence of a quantitative LLM-output ground truth, and unequal engine contribution — were acknowledged explicitly and recorded as inputs into the future-work agenda of Chapter 9. The chapter that follows describes the platform from an analyst's point of view, as a step-by-step user manual.
