<!--
  Chapter 2 — Literature Review
  Per user spec:
    2.1, 2.2, 2.3   ← VERBATIM from the mid-evaluation report
    2.4 onward      ← write fresh against the FINAL OBSCURA
-->

# Chapter 2 — Literature Review

## 2.1 Introduction

> **Note for the reader.** The text of Sections 2.1, 2.2, and 2.3 — including the five sub-system reviews of Dizzy, Snowball-Miner, CRATOR, Ahmia, and ACHE — is carried over verbatim from the mid-evaluation report submitted in November 2025. Only formatting (heading levels, bullet rendering) has been preserved; no wording has been changed.

In this chapter, we survey the key research and existing systems related to collecting cyber threat intelligence (CTI) from the dark web. We begin with a discussion of the dark-web threat landscape, then examine a variety of crawling and intelligence systems, especially those designed for Tor (.onion) services. We analyze their strengths and gaps, focusing on features relevant to our proposed crawler, and conclude with a comparative summary.

## 2.2 Dark-Web Threat Intelligence Landscape

The dark web, especially onion services accessible via Tor — remains a fertile ground for cybercriminal activity. Hidden forums, exploit markets, and ransomware leak sites provide cyber adversaries with infrastructure to trade malware, stolen credentials, and zero-day exploits. Manual monitoring of this ecosystem is notoriously difficult due to high domain churn, dynamic web structures, and the anonymized nature of Tor networks.

To address this, researchers stress the importance of automated pipelines that combine crawling, NLP, indicator-of-compromise (IOC) extraction, and structured storage for CTI. While many systems exist, few offer a fully integrated solution covering discovery, analysis, and visualization.

## 2.3 Additional Crawlers and CTI Systems

Here we discuss several relevant tools and platforms, comparing their objectives, architectures, and limitations.

### 2.3.1 Dizzy: Large-Scale Onion Service Crawler

Dizzy is an open-source system for large-scale crawling and analysis of onion services. Boshmaf et al. deployed Dizzy over years, crawling tens of millions of Tor pages to analyze domain churn, graph structure, and usage patterns (Boshmaf et al., 2022).

**Strengths:**

- Scales to a very large portion of the onion space without overwhelming the Tor network.
- Performs classification of service types, content churn analysis, and domain graph modeling.

**Limitations:**

- Primarily focused on reconnaissance and mapping, not CTI.
- Does not inherently extract IOCs, perform threat actor profiling, or integrate with threat-intelligence formats.

### 2.3.2 Snowball-Miner: Deep Learning for Dark-Web CTI

In "Snowball-Miner," Dutta, Bhushan, and Kant propose a system to extract CTI from dark-web forums and marketplaces (Dutta et al., 2023).

**Architecture:**

- Uses a Python-based Snowball crawler that connects via Tor to crawl .onion forums and marketplaces.
- For domain classification, they apply hybrid deep learning: CNN–LSTM and CNN–GRU models trained on doc2vec embeddings.
- They then apply Regex parsing and semantic dependency analysis (SOV semantics) to extract IOCs (e.g., IPs, hashes, wallet addresses) and threat-related entities.

**Results:**

- Their CNN-LSTM model achieved 96.37% classification accuracy on their dataset.
- The extracted IOCs are then associated with threat keywords and domain categories to build domain-specific CTI.

**Limitations:**

- The crawler provides limited coverage.
- Scaling to a much larger dynamic set of onion sites or maintaining up-to-date seeds can be difficult.

### 2.3.3 CRATOR: Dark-Web Intelligence and Crawler System

CRATOR (Crawling Onion Router) is a Tor-focused crawler designed for reconnaissance and partial CTI collection. It focuses on classifying and mapping dark-web services while collecting metadata that can support threat-intelligence tasks (Singh, Kumar, et al., 2021).

**How it works:**

- Uses a modular pipeline capable of crawling onion services while respecting Tor constraints.
- Performs HTML parsing, link extraction, snapshotting, and service classification.
- Provides structural and content-based analysis of onion domains, enabling threat analysts to identify marketplaces, forums, or suspicious infrastructure.

**Strengths:**

- More CTI-aware than generic crawlers like ACHE, as it focuses on identifying service categories.
- Supports metadata extraction useful for high-level profiling.
- Offers better domain classification than simple regex crawlers.

**Limitations:**

- Does not extract detailed IOCs (IPs, hashes, wallets) automatically.
- No NLP modules, entity recognition, or threat categorization.
- Lacks visualization and real-time streaming components.

### 2.3.4 Ahmia: Onion Search Engine for Tor Services

Ahmia is one of the longest-running onion search engines, focusing on indexing .onion websites in a privacy-preserving manner (Project, n.d.).

**How it works:**

- Crawls onion sites submitted through its platform and identified through open directories.
- Filters illegal content using transparency reports and community moderation.
- Maintains an index of active onion domains and provides a searchable public interface.

**Strengths:**

- Provides a curated, stable seed list of active and legitimate onion domains, which is very useful for initial seed discovery.
- Actively maintains availability and uptime checks, helping analysts understand domain lifecycle and churn patterns.
- Offers an open API that can be used to collect onion URLs programmatically.

**Limitations:**

- Not a CTI system; provides no IOC extraction, NLP, or threat classification.
- Filters potentially malicious or harmful content, meaning many threat sources may not appear in its index.
- Does not support deep crawling (mostly surface-level indexing).

### 2.3.5 ACHE Crawler for Tor

The ACHE ("Adaptive Crawler for Hidden Entities") crawler supports crawling Tor hidden services (Documentation, n.d.).

**How it works:**

- Configures a Tor proxy (e.g., via Privoxy) and routes HTTP requests through Tor.
- Uses Docker for easy deployment (Tor proxy + ACHE + Elasticsearch). Can store crawled content in Elasticsearch and local files, making it suitable for indexing and subsequent analysis.

**Limitations:**

- ACHE is a general-purpose crawler, not specifically built for CTI; lacks built-in threat classification, IOC parsing, or NLP modules.
- Depth and breadth of crawling may need careful configuration to avoid overwhelming Tor or missing deep content.

---

## 2.4 Gaps and Research Opportunities

The five systems reviewed above, taken together, span the design space currently available for dark-web threat intelligence. Reading the set as a whole — rather than each tool in isolation — surfaces a clearer picture of what the literature *does not* yet provide. Six gaps are particularly relevant for the design of OBSCURA.

1. **Integration gap.** The literature partitions cleanly into two camps. *Reconnaissance crawlers* (Dizzy, Ahmia, ACHE) map the onion topology but do not extract analyst-grade CTI. *CTI-extraction systems* (Snowball-Miner, CRATOR) extract IOCs but assume a curated, static seed list and ship no usable analyst interface. No widely available tool integrates federated discovery, deep crawling, intelligent triage, and an analyst-facing UI in a single workflow.

2. **Federation gap.** Every CTI system surveyed depends on a single search backend, a single seed file, or a single crawl scope. Given the well-documented coverage variance across onion search engines, a federated approach that queries many engines in parallel and merges their results would substantially improve recall — but none of the reviewed systems implement this.

3. **Operator-facing UX gap.** All five systems are research prototypes or infrastructure components, not analyst tools. Their output is typically a JSON dump, an Elasticsearch index, or a paper-grade dataset. None ships a conversational interface, none records investigations as first-class objects with status and tags, and none supports interactive re-summarisation, deep-crawl on demand, or analyst-driven export.

4. **Vendor lock-in to bespoke ML.** Systems such as Snowball-Miner achieve high accuracy by training proprietary CNN–LSTM / CNN–GRU classifiers and binding their output schema to a fixed ontology. This makes them powerful for the specific corpus they were trained on but brittle as language and threat vocabularies drift; re-training requires fresh labels and substantial compute. A general-purpose LLM, if effectively prompted, can substitute for several bespoke ML stages without the labelled-data overhead.

5. **Onboarding gap.** ACHE's Docker bundle (Tor + ACHE + Elasticsearch) is representative of the deployment burden the literature imposes: a working CTI pipeline routinely requires multiple JVM services, a managed index, a custom dashboarding stack, and a non-trivial DevOps capability. For a smaller security team, this is prohibitive, and the literature rarely treats *single-host single-analyst* operation as a target.

6. **Reproducibility and resilience gap.** Few of the reviewed systems are distributed as a self-contained reproducible artefact. Bootstrap synchronisation with Tor, circuit pre-warming, anti-fingerprinting browser preferences, and graceful tier fallback when a heavier crawler component is unavailable are mostly absent from the open-source literature and are typically rediscovered by each new implementer.

Each of these gaps maps directly to a deliberate design choice in OBSCURA, as set out in the next section.

---

## 2.5 Positioning OBSCURA

OBSCURA is positioned as an *integrated, analyst-first* dark-web threat-intelligence platform that closes the gaps identified above without re-inventing what the surveyed systems already do well.

- **Integrated end-to-end workflow.** OBSCURA fuses *federated discovery* (parallel search across sixteen onion engines), *deep crawling* (a Tor-routed two-tier crawler with selenium and `requests` fallback), *intelligent triage* (a three-stage LLM pipeline of refinement, filtering, and summarisation), and an *analyst interface* (a chat-style single-page application with investigation history, tags, status, and export) in a single deployable unit.

- **Federation by design.** The search layer queries sixteen independent onion search engines in parallel, with dedicated HTML parsers for the most reliable five (Ahmia, Tor66, OnionLand, Excavator, Find Tor) and a generic anchor-scraping fallback for the remainder. Combined results are deduplicated by normalised URL and pre-scored by query-term overlap before the LLM filter step ever sees them.

- **LLM as a general-purpose NLP substrate.** Rather than train a domain-specific classifier in the style of Snowball-Miner, OBSCURA delegates query refinement, relevance filtering, IOC surfacing, and structured summary generation to general-purpose large language models. This eliminates the labelled-data and re-training burden, accepts the trade-off in fixed-corpus accuracy for substantially higher portability across threat categories, and lets the system follow advances in commercial and open-source LLMs without code changes.

- **Provider-agnostic LLM abstraction.** Vendor lock-in is structurally avoided: the platform abstracts over six providers — OpenAI, Anthropic, Google Gemini, OpenRouter, Ollama, and llama.cpp — behind a single dispatching layer. Cloud providers are gated by API-key presence; local providers are discovered dynamically. An analyst can switch between a hosted frontier model and a locally hosted open-weight model from the same UI dropdown.

- **Single-file, single-host persistence.** OBSCURA replaces the Elasticsearch + Kibana stack typical of the surveyed systems with a single SQLite database in WAL mode, plus a content-addressed on-disk audit dump (`investigations/crawled/<sha256>/`) for each crawled source. This makes the data layer reproducible, transparent, and backup-friendly, and brings the deployment footprint to a single Docker container.

- **Analyst-first user experience.** Every investigation is a first-class persistent object with a query, a refined query, a model, a preset, a set of sources, a status, free-form tags, and an exportable Markdown summary. Investigations can be re-summarised on demand with a different model, prompt override, or custom instruction set; sources can be deep-crawled with Tier 1 selenium after the fact to upgrade their content. None of the surveyed systems offers this analyst-iteration loop.

- **Container-native reproducibility.** A single Docker image bundles the Tor daemon, Firefox ESR, geckodriver, and the Python runtime. The container's `entrypoint.sh` waits for Tor to reach *Bootstrapped 100%*, pre-warms a circuit with a test request, and reports its detected crawl tier — turning the "Tor setup" issue that the literature treats implicitly into a one-line `docker run` operation.

In short, OBSCURA does not aim to out-research the systems reviewed in Section 2.3; it aims to be the *analyst-usable* synthesis of the capabilities those systems demonstrate piecemeal.

---

## 2.6 Comparison Criteria

To make the positioning above defensible, this section defines the ten criteria against which the surveyed systems and OBSCURA are compared in Section 2.7. Each criterion is selected because it corresponds either to a functional requirement (Chapter 3) of a working analyst-facing dark-web CTI platform, or to a non-functional concern (deployment, vendor independence) raised in the gap analysis.

| # | Criterion | What is being assessed |
|---|---|---|
| C1 | **IOC Extraction** | Ability to surface concrete artefacts (IPs, domains, file hashes, CVEs, cryptocurrency wallets, email addresses, credentials) from scraped content. |
| C2 | **NLP / Entity Recognition** | Identification of higher-order entities (malware family names, threat-actor aliases, exploit names, marketplace identities) from unstructured text. |
| C3 | **Threat Classification** | Tagging or categorising content into threat types (e.g. credential dump, ransomware, exploit advert, identity exposure, corporate leak). |
| C4 | **Seed Federation & Discovery** | Whether the system queries multiple search backends and/or expands its own seed set, vs. operating on a single static seed list. |
| C5 | **Depth-Controlled Recursive Crawling** | Whether the system can crawl below the index-page level with explicit depth and bandwidth controls suitable for the Tor network. |
| C6 | **Resilience to Domain Churn / Mirrors** | How the system handles short-lived onion services, mirrored content, and duplicate domains. |
| C7 | **Structured Storage** | Whether output is captured in a queryable, durable schema (rather than printed to stdout or scattered across log files). |
| C8 | **Analyst UI / Dashboards** | Presence of an analyst-facing interactive surface for running, reviewing, tagging, and exporting investigations. |
| C9 | **Multi-Provider LLM Support** | Ability to swap or fall back across LLM providers (cloud and local) without code changes. |
| C10 | **Container-Native Deployment** | Whether the system ships as a single self-contained reproducible artefact (Docker image, all dependencies included). |

These criteria explicitly retire the *Visualization / Dashboard* and *Real-Time Streaming* criteria used in the mid-evaluation report. Visualization is folded into criterion C8 (Analyst UI), and real-time streaming is reframed as deliberately out-of-scope for the final platform — OBSCURA is on-demand by design, with live progress streaming inside an individual investigation rather than continuous background crawling.

---

## 2.7 Comparative Analysis of Existing Tools

Table 2.1 summarises the position of each surveyed system and OBSCURA against the ten criteria from Section 2.6. Entries are scored as **✓ Yes** (full support), **◑ Partial** (limited or indirect support), or **✗ No** (not supported).

**Table 2.1 — Comparison of Dark-Web CTI Systems against Ten Evaluation Criteria**

| Criterion | Dizzy | Snowball-Miner | ACHE | CRATOR | Ahmia | **OBSCURA (Proposed)** |
|---|---|---|---|---|---|---|
| **C1 — IOC Extraction** | ✗ | ✓ (Regex + semantics) | ✗ | ◑ (metadata only) | ✗ | **✓ (LLM-driven, preset-shaped)** |
| **C2 — NLP / Entity Recognition** | ◑ | ✓ (CNN-LSTM / CNN-GRU) | ✗ | ✗ | ✗ | **✓ (general-purpose LLM)** |
| **C3 — Threat Classification** | ✓ (site types) | ✓ (domain classification) | ✗ | ◑ (site categories) | ✗ | **✓ (4 presets + custom)** |
| **C4 — Seed Federation & Discovery** | ✓ (large-scale) | ✗ (fixed seed) | ◑ | ◑ | ✓ | **✓ (16 onion engines + seed manager)** |
| **C5 — Depth-Controlled Recursive Crawling** | ✓ | ✓ | ✓ | ✓ | ◑ (surface-only) | **✓ (per-tier timeouts + char budgets)** |
| **C6 — Resilience to Churn / Mirrors** | ◑ | ✗ | ✗ | ◑ | ✓ | **✓ (URL dedup + per-engine fallback)** |
| **C7 — Structured Storage** | Raw / graph | JSON / custom | Elasticsearch + files | Local / custom | Index | **SQLite (WAL) + on-disk audit dump** |
| **C8 — Analyst UI / Dashboards** | ✗ | ✗ | ✗ | ✗ | ◑ (public search UI only) | **✓ (chat SPA + modal manager)** |
| **C9 — Multi-Provider LLM Support** | ✗ | ✗ (single ML stack) | ✗ | ✗ | ✗ | **✓ (6 providers, 17 base models)** |
| **C10 — Container-Native Deployment** | ✗ | ✗ | ◑ (multi-container) | ✗ | ✗ | **✓ (single image, embedded Tor)** |

The pattern in Table 2.1 reinforces the gap analysis of Section 2.4. *Dizzy* and *Ahmia* score well on discovery and resilience but score zero on IOC extraction and present no analyst interface. *Snowball-Miner* is the closest peer on the CTI-extraction axis but is locked into a single bespoke ML stack and ships no UI. *CRATOR* sits in the middle without strongly differentiating on any criterion. *ACHE* is closest to OBSCURA on deployability but does no CTI work at all. OBSCURA is the only entry that satisfies every criterion, and uniquely supports the three properties — multi-provider LLM abstraction, integrated analyst UI, and single-image container deployment — that none of the surveyed systems supports at all.

---

## 2.8 Summary

This chapter has surveyed the existing landscape of dark-web threat-intelligence systems through five representative tools spanning reconnaissance crawlers (Dizzy, Ahmia, ACHE), partial-CTI systems (CRATOR), and dedicated CTI-extraction research (Snowball-Miner). A reading of the literature as a whole identified six structural gaps — integration, federation, operator-facing UX, vendor lock-in to bespoke ML, onboarding burden, and reproducibility — that no single existing system addresses end-to-end. OBSCURA's design responds to each of these gaps in turn: by integrating federated search, deep crawling, LLM-driven triage, and an analyst interface in a single deployable artefact; by substituting general-purpose large language models for project-specific ML stacks; by abstracting over six LLM providers to eliminate vendor lock-in; and by shipping as a single Docker image with an embedded Tor daemon. The ten-criterion comparative analysis in Table 2.1 shows that the final OBSCURA platform satisfies every criterion considered, including three (multi-provider LLM abstraction, integrated analyst UI, and container-native deployment) that none of the surveyed systems supports. The functional and non-functional requirements that operationalise this positioning are presented in Chapter 3.
