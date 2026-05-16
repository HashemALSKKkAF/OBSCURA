<!--
  Chapter 3 — System Requirements
  Fresh against the FINAL product. Every Chapter (except Introduction and
  Conclusions) opens with "Introduction" and closes with "Summary" per the
  FYDP guidelines.
-->

# Chapter 3 — System Requirements

## 3.1 Introduction

This chapter sets out the requirements that drove the design and implementation of OBSCURA. Requirements are organised in the conventional two-tier structure used throughout the report: **functional requirements (FRs)** that describe *what the system must do*, and **non-functional requirements (NFRs)** that constrain *how well it must do it*. Each requirement was elicited using the methodology of Section 1.4.1 — literature review of comparable dark-web CTI tooling, advisor consultations with Dr Muhammad Mubashir Khan and Miss Saadia Arshad, and direct exploration of the live dark-web search-engine ecosystem.

Functional requirements are tracked in Table 3.1. Each FR is presented with an identifier, the subsystem (or *module*) of OBSCURA that owns it, a one-line statement of the requirement itself, a priority that reflects whether the requirement is core to the analyst workflow or supporting, and a status column that records the implementation state of the requirement at the time of writing. Every requirement listed in Table 3.1 is fully implemented in the final platform; the *Status* column is retained so that the table also serves as a verification checklist during evaluation.

Non-functional requirements are tracked in Table 3.2 and are organised by quality attribute (performance, security, usability, and so on). Where a non-functional requirement implies a specific design technique — for example, *reliability* implying the retry-and-fallback strategy in the crawler — the technique is named in the *Description* column so the requirement and its realisation can be traced together. The complete realisation of every requirement, functional and non-functional, is presented in Chapter 4 (system design) and Chapter 5 (implementation), and is verified in Chapter 6 (testing).

---

## 3.2 Functional Requirements

The functional requirements of OBSCURA are presented in Table 3.1. They cover the four operational subsystems of the platform — the *Crawler* (search and deep-crawl), the *LLM pipeline* (refinement, filtering, summarisation), the *Persistence* layer (SQLite + audit dumps), and the *Interface* (Flask API and the chat-style SPA) — and the auxiliary subsystems that support them (health checks, export, SSE streaming).

**Table 3.1 — Functional Requirements of OBSCURA**

| ID | Module | Functional Requirement | Priority | Status |
|---|---|---|---|---|
| **FR1** | Crawler / Search | The system must perform federated dark-web search by concurrently querying sixteen independent onion search engines through a Tor SOCKS5 proxy, deduplicate results by normalised URL, and pre-score the combined output by query-term overlap before further processing. | High | Implemented |
| **FR2** | Crawler / Deep-Crawl | The system must retrieve the visible textual content of `.onion` (and clearweb) URLs through Tor using a two-tier strategy: *Tier 1* renders JavaScript using Selenium with Firefox routed through Tor SOCKS5, and *Tier 2* falls back to plain HTTP via `requests` over the same SOCKS5 proxy when Selenium is unavailable. The system must detect CAPTCHA / block pages and retry with the alternative tier. | High | Implemented |
| **FR3** | LLM Pipeline | The system must drive a three-stage LLM-based intelligence pipeline that (a) refines a free-text analyst query into a ≤ 5-word search-engine-friendly query, (b) filters the aggregated search results in batches and selects the top twenty most relevant entries, and (c) generates a structured Markdown intelligence summary from the scraped source text. | High | Implemented |
| **FR4** | LLM Pipeline / Presets | The system must ship with four built-in research-domain prompt presets — *Dark Web Threat Intel*, *Ransomware / Malware Focus*, *Personal / Identity Investigation*, and *Corporate Espionage / Data Leaks* — and must allow analysts to create, edit, and delete an unlimited number of custom presets persisted in the database. | High | Implemented |
| **FR5** | LLM Pipeline / Providers | The system must abstract over multiple LLM providers — OpenAI, Anthropic, Google Gemini, OpenRouter, Ollama, and llama.cpp — behind a single dispatching layer, with token streaming, exponential-backoff retry on transient errors, and automatic gating of providers by the presence of the corresponding API credential. | High | Implemented |
| **FR6** | Persistence | The system must persist every investigation — its query, refined query, model, preset, source list, status, tags, and full Markdown summary — in a local SQLite database, and must additionally persist the raw rendered HTML of each successful deep-crawl on the filesystem under a content-addressed path for forensic audit. | High | Implemented |
| **FR7** | Persistence / Seeds | The system must provide a *Seed Manager* through which analysts can register `.onion` URLs of interest; newly added seeds must be automatically crawled in the background, marked as *crawled* / *loaded* on success, and made re-crawlable on demand. | Medium | Implemented |
| **FR8** | Interface / Workflow | The system must support post-completion analyst actions on an existing investigation: *re-summarise* with a different model, prompt override, or custom-instruction set; *deep-crawl* the existing source list with the Tier 1 selenium path; *tag*; and *update status* (active / pending / closed / complete). | High | Implemented |
| **FR9** | Interface / Workflow | The system must surface investigation history with sidebar search filtering, must allow individual investigations to be opened in the chat surface for review, and must allow investigations to be deleted with confirmation. | Medium | Implemented |
| **FR10** | Export | The system must allow any saved investigation, or the live result of a just-completed investigation, to be exported as a typeset PDF (using ReportLab Platypus with full Markdown-to-flowables conversion of tables, headings, and bullets) or as the raw Markdown source. | Medium | Implemented |
| **FR11** | Diagnostics | The system must provide an analyst-triggered *Health Check* subsystem that probes (a) the local Tor SOCKS5 proxy, (b) the currently selected LLM provider with a minimal round-trip call, and (c) each of the sixteen registered onion search engines, returning per-target status and latency for display. | Medium | Implemented |
| **FR12** | Interface / UX | The system must stream live pipeline-stage progress events ("Refining query…", "Searching…", "Filtering N results…", "Scraping…", "Generating final report…") from the backend to the chat UI via Server-Sent Events, and must allow the analyst to *abort* an in-flight investigation from the UI. The UI must persist theme (light/dark) and sidebar-collapse preference across sessions. | Medium | Implemented |

The *High* priority entries (FR1–FR6 and FR8) describe the core analyst-workflow path: discover → crawl → triage → summarise → persist → iterate. The *Medium* priority entries (FR7, FR9, FR10, FR11, FR12) describe supporting and quality-of-life capabilities that are part of the final platform but are not strictly required for a one-shot investigation to complete.

---

## 3.3 Non-Functional Requirements

The non-functional requirements of OBSCURA are presented in Table 3.2. They are organised by quality attribute and are written so that each requirement names the specific design technique used to satisfy it — making the requirement directly traceable to the implementation in Chapter 5 and to the test that verifies it in Chapter 6.

**Table 3.2 — Non-Functional Requirements of OBSCURA**

| ID | Quality Attribute | Non-Functional Requirement |
|---|---|---|
| **NFR1** | **Performance** | An end-to-end investigation against a non-trivial query must complete within a small number of minutes on a typical analyst workstation, with the federated search step parallelised across up to sixteen workers, the deep-crawl step parallelised up to ten workers, and pipeline-stage status events surfaced to the UI within one second of the underlying transition. |
| **NFR2** | **Scalability** | Adding a new onion search engine, a new LLM provider, a new prompt preset, or a new seed URL must not require changes to the rest of the codebase. Each of these is parameterised through a registry, a configuration table, or a database row, in line with the open–closed principle. |
| **NFR3** | **Reliability** | The system must tolerate transient failures of its external dependencies: LLM rate-limit / 5xx / timeout responses retry with exponential back-off (2 s → 4 s → 8 s); the deep-crawler retries with tier fallback when selenium fails; the federated-search step continues gracefully when one or more engines time out or return errors. |
| **NFR4** | **Security** | All egress traffic to onion services must traverse the local Tor SOCKS5 proxy; no `.onion` URL must be fetched directly. API credentials must be loaded from a local `.env` file or environment variables and must never appear in log output. Seed URLs must be stored with their SHA-256 hash alongside the URL for stable identification across re-crawls. |
| **NFR5** | **Ethical Compliance** | The platform must perform *passive read-only* collection only. It must not register, log in, post, message, purchase, or otherwise interact with onion services. It must restrict its target set to publicly accessible content and surface a disclaimer in every exported report stating that findings must be manually verified and that the tool is for lawful investigative purposes only. |
| **NFR6** | **Maintainability** | The codebase must follow clear module boundaries (crawler, search, LLM, persistence, API, frontend) with each module owning a single concern. Cross-module communication must occur only through documented function interfaces. Type hints, in-line docstrings, and structured logging must be used throughout. |
| **NFR7** | **Usability** | An analyst with no specific dark-web tooling experience must be able to complete an end-to-end investigation in three clicks or fewer from the welcome screen, with no command-line interaction required after the initial container start-up. The chat-style UI must support both light and dark themes and remain responsive on screens down to 768 px wide. |
| **NFR8** | **Data Integrity** | All writes to SQLite must occur in WAL journal mode, foreign-key enforcement must be enabled, and the parent-to-child cascade between `investigations` and `sources` must protect against orphaned records. The one-time migration from the legacy flat-file JSON store must be idempotent. |
| **NFR9** | **Privacy & Confidentiality** | All persistent state — investigations, sources, seeds, custom presets, audit dumps, exported PDFs — must remain on the analyst's local machine. The platform must emit no external telemetry, must not send anything beyond the LLM and search-engine requests it is explicitly instructed to make, and must not log analyst queries to any remote service. |
| **NFR10** | **Portability** | The platform must be deployable as a single Docker container that bundles the Tor daemon, Firefox ESR, geckodriver, and the Python runtime. The container's start-up must synchronise with Tor's *Bootstrapped 100%* signal and pre-warm a circuit before exposing the analyst UI, so the first investigation does not pay the cold-circuit latency cost. |
| **NFR11** | **Auditability** | Every successful deep-crawl must persist the raw rendered HTML and a marker recording the tier used (`investigations/crawled/<sha256>/{rendered.html, tier.txt}`) so that a post-hoc analyst can re-derive the LLM input from the original captured page. Investigation status and tags must be editable after the fact for case-management workflows. |

---

## 3.4 Summary

This chapter has presented the twelve functional and eleven non-functional requirements that define the OBSCURA platform. Functional requirements (Table 3.1) cover federated search, two-tier deep crawling, the three-stage LLM pipeline, preset and provider management, persistence with audit dumps, the analyst-iteration workflow (re-summarise, deep-crawl, tag, export, history), health-checks, and live SSE-based progress streaming. Non-functional requirements (Table 3.2) constrain performance, scalability, reliability, security, ethical compliance, maintainability, usability, data integrity, privacy, portability, and auditability. Each requirement was elicited from the literature review of Chapter 2 and the supervisor consultations described in Section 1.4.1, and each will be revisited in Chapter 4 (where the system design realises it), Chapter 5 (where the implementation embodies it), and Chapter 6 (where the testing strategy verifies it).
