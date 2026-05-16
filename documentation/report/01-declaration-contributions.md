<!--
  Pages ii (Author's Declaration) and iii (Statement of Contributions).
  Lower-case Roman numerals; single-spaced per FYDP guidelines.
-->

# Author's Declaration

We declare that we are the sole authors of this project. It is the actual copy of the project that was accepted by our advisor(s) including any necessary revisions. We also grant NED University of Engineering and Technology permission to reproduce and distribute electronic or paper copies of this project.

&nbsp;

| Signature and Date | Signature and Date |
|---|---|
| ................................. | ................................. |
| **Hafsa Ali** | **Dania Fazal** |
| CR-22006 | CR-22007 |
| hafsa.a.mehboob@gmail.com | daniafazal39@gmail.com |
|  |  |
| ................................. | ................................. |
| **Sarah Zafar** | **Hashem Raed Mohammed Alawi Al-Sakkaf** |
| CR-22025 | CR-22050 |
| sarahzafar101@gmail.com | hashem.alsakkaf2004@gmail.com |

---

# Statement of Contributions

The OBSCURA platform was delivered through a coordinated team effort. Individual responsibilities below summarise each member's principal contributions across the full project lifecycle — from the mid-evaluation crawler prototype through to the final integrated platform documented in this report.

**Hafsa Ali (CR-22006)**

- Owned the **testing and quality-assurance track** for the project. Designed and executed the integration-testing protocol used to validate the end-to-end investigation pipeline against live onion sources.
- Built and maintained the **health-check subsystem** (`health.py`) — per-engine latency probes for all 16 dark-web search engines, the Tor SOCKS5 reachability check, and the LLM round-trip probe.
- Documented the crawler's behavioural envelope (success/fail rates, Tier-1 vs Tier-2 fallback statistics, block/CAPTCHA detection accuracy) and contributed substantially to the background study, problem identification, and comparative review of existing dark-web crawlers presented in Chapter 2.

**Dania Fazal (CR-22007)**

- Led implementation of the **dark-web crawling subsystem**, including the unified `crawler.py` module with its two-tier strategy (Tier 1: Selenium + Firefox over Tor SOCKS5, Tier 2: `requests` + SOCKS5 fallback).
- Implemented `scrape.py` and the underlying Tor session factory, the per-tier retry-and-fallback logic, CAPTCHA / block-page detection, and the on-disk audit dump (`investigations/crawled/<sha256>/`).
- Owned `tor_utils.py` (NEWNYM circuit-rotation utility) and the Tor-related portions of `entrypoint.sh` that synchronise container start-up with Tor's bootstrap-100% signal.
- Curated and maintained the live seed file of `.onion` search-engine endpoints used by `search.py`.

**Sarah Zafar (CR-22025)**

- Led the **literature review and comparative-analysis** work that anchors Chapter 2, including the systematic positioning of OBSCURA against Dizzy, Snowball-Miner, CRATOR, Ahmia, and ACHE.
- Co-designed the **system documentation and UML deliverables** in Chapter 4 — use-case, sequence, activity, ERD, SDLC, and architectural diagrams — including the visual style, colour palette, and notation consistent across all six figures.
- Maintained the project's report-writing workflow, structured the chapter outline against the FYDP guidelines, and acted as scribe for advisor meetings and mid-evaluation feedback rounds.

**Hashem Raed Mohammed Alawi Al-Sakkaf (CR-22050)**

- Owned the **application backend and platform integration**: designed and implemented `app.py` (Flask REST API + SSE streaming), the LangChain multi-provider LLM abstraction in `llm.py` / `llm_utils.py` (OpenAI, Anthropic, Google Gemini, OpenRouter, Ollama, llama.cpp — 17 base models with dynamic local discovery), and the four built-in research-domain prompt presets.
- Migrated the project's persistence layer from flat-file JSON to **SQLite with WAL journalling**, designing the four-table schema (`investigations`, `sources`, `seeds`, `custom_presets`) and the one-time import migration.
- Implemented the **frontend single-page application** (`index.html`, `script.js`, `styles.css`) with the ChatGPT-style chat interface, SSE progress streaming, light/dark theme, modal-based seed manager / health-checks / configuration, and the PDF / Markdown export pipeline using ReportLab Platypus (`export.py`).
- Containerised the project (Dockerfile + `entrypoint.sh`) with the embedded Tor daemon, runtime-tier reporting, and the circuit pre-warm routine.

&nbsp;

All authors contributed equally to writing the final year project report.
