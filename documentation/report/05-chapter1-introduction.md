<!--
  Chapter 1 — Introduction  (Main Body, Arabic page numbering restarts at 1)
  Per user spec, with §1.4 Methodology inserted in the senior-report style:
    1.1 Introduction                  ← fresh
    1.2 Significance and Motivation   ← VERBATIM from mid-evaluation report
    1.3 Problem Statement             ← fresh
    1.4 Methodology                   ← fresh (added in senior-report style)
    1.5 Objectives                    ← fresh
    1.6 Scope                         ← fresh
-->

# Chapter 1 — Introduction

## 1.1 Introduction

Over the last decade, a substantial fraction of organised cybercrime has migrated from the open Internet to the *dark web* — the anonymised subset of the Internet reachable only through onion-routing networks such as Tor. Hidden services on Tor host the marketplaces where stolen credentials are sold, the leak sites where ransomware groups publish exfiltrated data, the forums where exploits and zero-days are advertised, and the chat channels where future operations are coordinated. The same technical properties that make Tor valuable for privacy and free expression — strong sender anonymity, end-to-end encryption between hops, address opacity through `.onion` self-authenticating names — make it extraordinarily difficult for defenders to observe these spaces at scale.

The cost of this observability gap is concrete. Threat-intelligence reports routinely document credentials, source code, and internal documents appearing on onion marketplaces months before the affected organisation detects an intrusion; ransomware leak sites have become a leading indicator of compromise for regulators and incident responders alike. Yet the conventional posture for most defenders is reactive: a breach is discovered, an incident-response team is engaged, and an analyst is then asked to manually canvas the dark web for related artefacts. This canvassing is slow, repetitive, legally sensitive, and — given the volume and churn of onion services — almost impossible to do exhaustively.

This project, **OBSCURA**, addresses that gap by building an end-to-end *Threat-Intelligence Automation* platform for dark-web sources. OBSCURA combines a Tor-routed two-tier crawler, a federation layer over sixteen onion search engines, a three-stage Large-Language-Model (LLM) pipeline for query refinement, result filtering, and structured summary generation, and a chat-style single-page application that gives a security analyst a single conversational surface for running, persisting, re-summarising, and exporting investigations. The system is built around the explicit constraint of *human oversight*: every artefact the LLM produces is grounded in URLs and source text that the analyst can inspect, and every investigation is recorded in a local SQLite database with on-disk audit dumps of the rendered HTML.

The remainder of this chapter sets out why automated dark-web threat intelligence is operationally important (Section 1.2), the specific problems that OBSCURA targets (Section 1.3), the methodology adopted to build the platform (Section 1.4), the concrete objectives the project was designed to meet (Section 1.5), and the scope and boundaries within which those objectives were pursued (Section 1.6).

---

## 1.2 Significance and Motivation

> **Note for the reader.** The text of Section 1.2 — including the two introductory paragraphs, the *Supporting Evidence & Market Context* subsection, and the five impact subsections under *Why Obscura Matters* — is carried over verbatim from the mid-evaluation report submitted in November 2025. Only formatting (heading levels, bullet rendering) has been preserved; no wording has been changed.

Dark web intelligence has become an indispensable part of modern cybersecurity operations. The dark web — particularly Tor-based onion sites, underground forums, and illicit marketplaces — serves as a fertile ground for cybercriminals to trade stolen credentials, malware, exploits, and even coordinate future attacks. This unregulated, anonymous space poses a major visibility gap for security teams and organizations. Manual monitoring of these sources is untenable: there is simply too much volume, too much churn, and too much risk, making automated intelligence collection not just beneficial but critical.

Obscura is motivated by this pressing need: to automate dark web threat intelligence gathering, significantly reduce human burden, speed up detection, and improve the quality and context of cybersecurity insights. By combining crawler technology, artificial intelligence (particularly NLP), and threat analytics, Obscura allows security teams to shift their focus from reconnaissance to action — from raw data to proactive defense.

### 1.2.1 Supporting Evidence & Market Context

The dark web intelligence market is growing very fast. According to market research, it was worth USD 520 million in 2023, with forecasts estimating it will reach USD 2,921 million by 2032 (CAGR ≈ 21.8%) ("Dark Web Intelligence Market News", 2025).

On the dark web, leaked information comprises a large chunk: as per SQ Magazine, 28% of dark web listings are data leaks, while stolen financials account for 12%, and hacked accounts 3% ("Dark Web Statistics", 2025).

The scale of data exposure is massive: Collection #1, one of the largest aggregation leaks, held over 773 million unique email addresses and 21 million unique passwords, totaling more than 2.7 billion email/password pairs ("Collection No. 1", 2025).

In terms of research methodology, a systematic literature review found that automated crawling is used in about two-thirds of dark web forum studies, and more than 90% of these used Python-based tools, highlighting both the prevalence and scalability of automation (Patra, 2025).

### 1.2.2 Why Obscura Matters — High-Level Impact

**Reducing Human Burden & Risk**

Security analysts often lack the bandwidth to manually scan hundreds or thousands of dark web sources. Automated crawling and NLP reduces this manual burden, freeing up human analysts to focus on investigation and mitigation.

Automation also mitigates risk: instead of having humans browse dangerous onion sites (which can be risky and legally ambiguous), crawlers can do the heavy lifting in a controlled, secure environment.

**Speed & Timeliness**

Real-time or near real-time data collection ensures faster detection of emerging threats (zero-day leaks, new malware, newly registered marketplaces).

Integration with SIEM/SOC means threat intelligence can be actioned rapidly, enabling proactive defense — blocking or monitoring indicators before they escalate into attacks.

**Quality & Context**

Using NLP to filter irrelevant chatter (only 20% is CTI-relevant) ensures that analysts see high signal, not noise (Schröer et al., 2025).

Profiling threat actors over time adds strategic context: which aliases come up repeatedly, what tools they use, which marketplaces they frequent — enabling attribution, prioritization, and long-term threat modeling.

**Scalability & Sustainability**

As the dark web grows (both in volume and volatility), automated architectures (e.g., big data pipelines, deduplication, clustering) make continuous, resilient monitoring feasible.

This kind of intelligence system scales better than manual methods and can adapt more flexibly as new forums or marketplaces appear or disappear.

**Contribution to Broader Cyber Resilience**

By feeding structured threat intelligence into existing security workflows, Obscura helps organizations move from reactive to proactive security.

It aligns well with capacity building and infrastructure goals: as cyber defense becomes more data-driven, organizations can better anticipate and mitigate digital risks — contributing to SDG 9 (Industry, Innovation, and Infrastructure) by strengthening digital infrastructure and innovation in threat prevention.

---

## 1.3 Problem Statement

A working security-operations analyst tasked with answering a dark-web question — *"are credentials for our domain being sold?"*, *"is this ransomware crew claiming us as a victim?"*, *"is anyone advertising an exploit against the software we ship?"* — currently faces six structural barriers, each of which OBSCURA is designed to dissolve.

1. **Volume and dispersion.** Threat-relevant material is not concentrated on a small number of well-known forums. It is fragmented across dozens of marketplaces and hundreds of mirror sites, indexed unevenly by a handful of competing onion search engines. No single search engine returns a comprehensive view of any non-trivial query.
2. **Churn and ephemerality.** Onion services come and go on the order of days or weeks. A search index built last month is partially stale by the time an analyst consults it. Static seed-lists curated by hand decay rapidly.
3. **Operational risk of manual browsing.** Manually visiting onion marketplaces and forums to triage results exposes both the analyst's machine and the organisation to non-trivial legal, technical, and reputational risk. Many investigations stall at this step because the analyst is — correctly — reluctant to load arbitrary onion pages in their own browser.
4. **Tooling gap.** Surveyed dark-web tooling falls into two disjoint camps. Reconnaissance crawlers (e.g. Dizzy, ACHE, CRATOR) map the onion topology but do not extract analyst-grade intelligence. CTI-oriented research systems (e.g. Snowball-Miner) extract indicators but assume a curated, static seed list and ship no usable interface. No widely available tool integrates federated discovery, deep crawling, intelligent triage, and an analyst-facing UI in a single workflow.
5. **Skill-stack burden.** Operating a competent dark-web pipeline in-house traditionally requires expertise in Tor configuration, headless browser automation, anti-fingerprinting, custom NLP pipelines, and dashboarding stacks such as Elasticsearch and Kibana. Few security teams can sustain that breadth of expertise on a CTI side project.
6. **Cost and brittleness of bespoke ML.** Building a domain-specific entity-recognition or classification model for dark-web text requires labelled data, training infrastructure, and ongoing re-training as language drifts. Most teams cannot justify that investment for a single in-house use case.

The composite effect of these six barriers is that the majority of organisations possess essentially no internal dark-web visibility, and rely instead on episodic, externally produced threat reports that surface incidents only after damage has already been done. OBSCURA addresses this composite by replacing the tooling, skill-stack, and bespoke-ML requirements with a single integrated platform driven by general-purpose LLMs.

---

## 1.4 Methodology

OBSCURA was delivered through an **iterative, agile-style Software Development Life Cycle (SDLC)** organised into six recurring phases — *Plan & Requirements*, *System Design*, *Implementation*, *Integration & Testing*, *Deployment & Hardening*, and *Review & Iteration*. Each pass through the cycle produced a working, demonstrable artefact, and supervisor feedback at the end of each pass was folded back into the next *Plan & Requirements* iteration. The same SDLC is rendered in detail as Figure 4.5 in Chapter 4; the subsections below break it down by the activities the team actually performed.

### 1.4.1 Requirement Analysis

The project opened with a structured requirements-gathering phase that combined three independent inputs. The first was a literature review of academic and industry CTI tooling — Dizzy, Snowball-Miner, CRATOR, Ahmia, and ACHE — surveyed in detail in Chapter 2, which set the *bar* the proposed platform had to clear. The second was a sequence of advisor and co-advisor consultations with **Dr Muhammad Mubashir Khan** and **Miss Saadia Arshad**, which scoped the project to a single-analyst tool with strict ethical boundaries (passive read-only collection, no engagement with threat actors). The third was direct exploration of the dark-web search-engine ecosystem to confirm operational feasibility — which onion search engines were reachable, which had stable HTML structures, and which were too volatile to depend on. The output of this phase was the explicit list of ten functional and ten non-functional requirements presented in Chapter 3.

### 1.4.2 System Design

The design phase produced four classes of artefact:

- **Architectural design.** A five-layer architecture — Presentation, API, Service, LLM Abstraction, and Data — was selected for its testability, its clean separation between business orchestration and external integrations, and its compatibility with a single-machine Docker deployment. The full layered model is presented in Figure 4.6.
- **Data design.** A four-table SQLite schema (`investigations`, `sources`, `seeds`, `custom_presets`) was modelled in the Entity-Relationship Diagram (Figure 4.4). Foreign-key cascade behaviour, WAL-mode journalling, and idempotent migrations from the project's earlier flat-file JSON store were all decided up front.
- **Behavioural design.** End-to-end behaviour was captured in three complementary UML diagrams: a Use-Case Diagram (Figure 4.1) identifying actors and capabilities, a Sequence Diagram (Figure 4.2) tracing the *Run a New Investigation* flow across seven participants, and an Activity Diagram (Figure 4.3) showing parallel forks and decision branches.
- **Technology-stack decisions.** Each technology choice was made with explicit alternatives evaluated and rejected; for example, **SQLite** was selected over Elasticsearch (the mid-evaluation plan) because the storage volume of a single-analyst tool does not justify a JVM-resident indexer, and **LangChain** was selected over hand-rolled HTTP clients per provider because the project required portability across six vendors.

### 1.4.3 Development Tools

The toolchain used to build OBSCURA spans seven distinct concerns. Where multiple alternatives existed, the rationale for each pick is noted.

- **Anonymity transport.** The **Tor daemon** runs as an embedded service inside the Docker container; traffic is routed through SOCKS5 on `127.0.0.1:9150`; circuit rotation is triggered through the Tor ControlPort on `127.0.0.1:9151` using the standard `SIGNAL NEWNYM` command.
- **Deep-crawl engine.** *Tier 1* uses **Selenium WebDriver** with **Firefox ESR** and **geckodriver** for JavaScript-rendered onion pages, with anti-fingerprinting preferences set explicitly in code. *Tier 2* uses the **`requests`** library with a SOCKS5 adapter (**`pysocks`**) for plain HTTP retrieval when Selenium is unavailable. HTML is parsed with **BeautifulSoup 4**.
- **LLM orchestration.** **LangChain** is used as the provider abstraction, with the `langchain-openai`, `langchain-anthropic`, `langchain-google-genai`, `langchain-ollama`, and `langchain-community` adapters covering six providers in total. A custom `BufferedStreamingHandler` exposes the token stream upward to the API layer.
- **API and runtime.** The HTTP server is **Flask**, chosen for its small dependency surface, its native support for Server-Sent Events (`Response(generate(), mimetype='text/event-stream')`), and its strong fit with single-process container deployment.
- **Frontend.** The user interface is a hand-written single-page application built in **vanilla HTML, CSS, and JavaScript** with **Font Awesome** icons — no build step, no framework lock-in, and no transpilation overhead. Persistent UI state (theme, sidebar collapse) is stored in `localStorage`.
- **Persistence.** **SQLite** is accessed through Python's standard-library `sqlite3` module, in **WAL journal mode** for concurrent reads while the auto-crawl background thread is writing.
- **Report export.** PDF generation uses **ReportLab Platypus** for typesetting; the Markdown-to-flowables converter is implemented inside `export.py`. Markdown export is a direct file download from the browser.

### 1.4.4 Implementation Phases

Implementation was organised as a sequence of vertical slices, each ending in a runnable demonstrator. The phases below correspond to the seven sprints that delivered the platform between project kick-off and final submission.

- **Sprint 1 — Crawler MVP.** A single-tier `requests` + Tor SOCKS5 crawler that retrieved and persisted HTML from a hand-curated seed list. Output was raw HTML in dated folders. This sprint produced the foundation of `scrape.py` and the Tor session factory.
- **Sprint 2 — Linear LLM pipeline.** A first-pass `refine_query` → `filter_results` → `generate_summary` chain wired against the OpenAI API only. Output was Markdown printed to standard output. This sprint validated that the pipeline as a whole was useful before further investment was made in any one stage.
- **Sprint 3 — Multi-provider abstraction.** The LLM dispatcher was generalised: the OpenAI-only call site was replaced with a LangChain-mediated `get_llm()` factory; Anthropic, Google Gemini, OpenRouter, Ollama, and llama.cpp adapters were wired in; provider auto-gating by API-key presence was added; the exponential-backoff retry wrapper was implemented.
- **Sprint 4 — Web frontend & Flask API.** The command-line driver was replaced with `app.py` exposing a REST + SSE API; the single-page application (`index.html`, `script.js`, `styles.css`) was built; investigation history, configuration, and seed management were exposed through three modal dialogs.
- **Sprint 5 — Persistent storage.** Investigations were migrated from `investigation_*.json` files to a four-table SQLite schema with a one-time importer; the seed list was migrated from `seeds.json` to the `seeds` table; the four built-in research domains were complemented by user-creatable `custom_presets`.
- **Sprint 6 — Tier 1 deep crawl.** Selenium + Firefox + geckodriver was added as a Tier 1 crawler, with the tier-fallback logic, CAPTCHA / block-page detection, anti-fingerprinting Firefox preferences, and the on-disk audit dump (`investigations/crawled/<sha256>/`).
- **Sprint 7 — Polish, hardening, and packaging.** The health-check subsystem (`health.py`) for Tor, LLMs, and the sixteen search engines; the ReportLab PDF exporter; the NEWNYM circuit-rotation utility; the Docker container with embedded Tor daemon; and the `entrypoint.sh` bootstrap synchronisation logic were all built in this final sprint.

### 1.4.5 Testing and Iteration

Testing was performed *continuously* rather than as a final phase. Each sprint ended with a live demonstration against real onion sources, supervisor review, and a punch list of fixes folded into the next sprint's *Plan & Requirements* block. Three categories of test were maintained throughout:

- **Smoke tests** — short scripted runs of the full investigation pipeline against well-known onion targets, performed on every significant commit to verify that Tor, the crawler, the LLM, and persistence still co-operated end-to-end.
- **Tier-fallback tests** — deliberate runs with geckodriver absent or Selenium uninstalled, to confirm that the Tier 2 fallback path produced acceptable output without manual intervention.
- **Health-check probes** — the `check_tor_proxy`, `check_llm_health`, and `check_search_engines` routines were used both during development (to debug breakage) and at runtime (so an analyst can verify the platform's readiness before launching a long-running investigation).

The mid-evaluation review in November 2025 was the major formal feedback event during the project; the design changes it precipitated — most visibly the pivot away from Elasticsearch + Kibana and toward the SQLite + custom SPA architecture — are documented in Chapter 8.

### 1.4.6 Deployment

Final deployment is delivered as a single self-contained Docker image. The container bundles the Tor daemon, Firefox ESR, geckodriver, and the Python runtime, and is started by an entrypoint script (`entrypoint.sh`) that:

1. Launches `tor` in the background and captures its log;
2. Waits up to sixty seconds for the SOCKS port (`127.0.0.1:9150`) to open;
3. Waits up to four minutes for the Tor log to report `Bootstrapped 100%` (or, earlier, "consensus contains exit nodes");
4. Pre-warms the circuit with one outbound HTTPS request through SOCKS5, so the very first analyst investigation does not pay the cold-circuit latency cost;
5. Probes which crawl tier is available (Selenium-ready or `requests`-only) and prints a runtime check banner;
6. Finally execs `python app.py`, which serves the SPA on port 8501.

The same container image runs on any Docker-capable host without further configuration; LLM credentials are supplied through a `.env` file mounted at run time.

---

## 1.5 Objectives

OBSCURA was designed to achieve a focused set of measurable objectives. Each objective listed below is realised by a corresponding subsystem of the final platform; the chapter cross-reference in parentheses points to where each is described in technical detail.

1. **Tor-routed automated crawling with redundant transport.** Develop a deep-crawl engine that retrieves the full visible content of onion (and clearweb) URLs through Tor, with a robust two-tier strategy: Tier 1 uses Selenium with Firefox for JavaScript-rendered pages, Tier 2 falls back to plain HTTP via a SOCKS5 proxy when Selenium is unavailable. *(Chapter 4 §4.3, Chapter 5 §5.3.)*

2. **Federated dark-web search.** Aggregate results from sixteen independent onion search engines in parallel, with dedicated HTML parsers for the most reliable five and a generic fallback parser for the remainder, then deduplicate and pre-score the combined output by query-term overlap. *(Chapter 5 §5.4.)*

3. **LLM-driven investigation pipeline.** Build a three-stage LLM pipeline — query refinement, batched result filtering, and preset-driven summary generation — that turns a free-text analyst query into a structured Markdown intelligence report covering source links, extracted artefacts, key insights, defensive recommendations, and follow-up actions. *(Chapter 5 §5.5.)*

4. **Multi-domain prompt presets.** Provide four built-in research-domain presets — *Dark Web Threat Intel*, *Ransomware / Malware Focus*, *Personal / Identity Investigation*, and *Corporate Espionage / Data Leaks* — and allow analysts to author, save, and re-use their own custom domains. *(Chapter 5 §5.5.3.)*

5. **Multi-provider LLM abstraction.** Decouple the pipeline from any single language-model vendor by abstracting over six providers (OpenAI, Anthropic, Google Gemini, OpenRouter, Ollama, llama.cpp), with streaming, exponential-backoff retry on transient errors, and automatic gating of providers by configured API-key presence. *(Chapter 5 §5.6.)*

6. **Persistent, auditable investigation store.** Persist every investigation — its query, refined query, model, preset, sources, status, tags, and full Markdown summary — in a local SQLite database, and additionally persist the raw rendered HTML of each crawled source on the filesystem for forensic audit. *(Chapter 4 §4.4, Chapter 5 §5.7.)*

7. **Analyst-friendly user interface.** Deliver a chat-style single-page application served by Flask, with live progress streaming via Server-Sent Events, light/dark theming, modal-driven configuration and seed management, and one-click export of any investigation as a typeset PDF or raw Markdown file. *(Chapter 5 §5.8, Chapter 7.)*

8. **Reproducible, container-native deployment.** Package the system as a Docker container that embeds the Tor daemon, synchronises start-up with Tor's bootstrap completion, pre-warms a circuit, and reports its detected crawl-tier and runtime capabilities at start-up. *(Chapter 5 §5.9.)*

---

## 1.6 Scope

The boundaries of the project were set deliberately to make a single FYDP team deliver a usable, defensible, and ethically clean platform within a fixed timeline.

### 1.6.1 In Scope

- **Ethical, read-only collection** of publicly accessible dark-web content for research and defensive cybersecurity purposes.
- **Tor onion services** as the primary target, with incidental support for clearweb URLs that share the same scraping pipeline.
- **English-language CTI categories** — leaked credentials, exploit and zero-day discussion, malware advertising, ransomware leak-site listings, marketplace activity around stolen data.
- **Single-analyst, local deployment** on a workstation or single-host container, with no requirement on external infrastructure other than the analyst's own LLM API credentials (or a local Ollama / llama.cpp instance).
- **LLM-driven analysis** for query refinement, result filtering, indicator-of-compromise (IOC) surfacing, threat categorisation, and structured report generation — all anchored to the URLs and source text that the analyst can re-inspect.
- **PDF and Markdown export** of every investigation, for incorporation into wider incident-response or executive reporting.

### 1.6.2 Out of Scope

- **Active engagement** with threat actors — OBSCURA does not post, register, message, purchase, or otherwise interact with onion services. Crawling is strictly passive.
- **Multi-user, role-based access control** — OBSCURA is a single-user tool; no authentication, no admin/analyst split, no concurrent-session handling.
- **Real-time / always-on streaming pipelines** — investigations are *on-demand* operations triggered by an analyst; OBSCURA does not run as a continuously crawling daemon.
- **Automated response or SOAR integration** — OBSCURA *informs* analysts; it does not block IPs, revoke credentials, fire detection rules, or otherwise act on detected indicators.
- **Non-Tor anonymity networks** (I2P, Freenet, Zeronet) are not targeted in this iteration.
- **Languages other than English** are not formally supported; non-English content is fetched and stored unchanged, but the prompt presets and pre-scoring assume English-language terms.
- **Bespoke ML model training** — OBSCURA relies entirely on hosted or local *general-purpose* LLMs and does not include any project-specific model training, fine-tuning, or evaluation.

### 1.6.3 Report Outline

Chapter 2 surveys the existing landscape of dark-web crawling and CTI extraction systems, identifies the gaps that motivated OBSCURA, and positions the proposed system against five comparable tools. Chapter 3 sets out the functional and non-functional requirements that drove the design. Chapter 4 presents the full system design — actors and use cases, end-to-end interaction sequences, operational activity flows, the database ERD, the SDLC adopted, and the layered architectural model. Chapter 5 details the implementation: the crawler, the search-federation layer, the LLM pipeline, the multi-provider abstraction, the persistence layer, the frontend, and the deployment story. Chapter 6 describes the testing and evaluation strategy and the observed results. Chapter 7 provides an analyst-facing walk-through of the system as a user manual. Chapter 8 covers project management, the timeline, tooling, and the lessons learned along the way. Chapter 9 concludes with a reflection on the work and a structured agenda for future development. The back matter lists every reference cited.
