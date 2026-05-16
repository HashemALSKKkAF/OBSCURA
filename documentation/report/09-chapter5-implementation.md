<!--
  Chapter 5 — Implementation Details
  Realises each subsystem named in Chapter 4 in concrete code. Section numbering
  matches the forward-references made from §1.5 (Objectives).
-->

# Chapter 5 — Implementation Details

## 5.1 Introduction

This chapter describes how the design baseline established in Chapter 4 was realised in code. The discussion follows the layered architecture of Figure 4.6 from the inside out: Section 5.2 gives the codebase layout used as a map for the rest of the chapter; Section 5.3 covers the two-tier deep-crawl engine; Section 5.4 covers the federated search layer; Section 5.5 describes the three-stage LLM-driven investigation pipeline together with the four built-in prompt presets; Section 5.6 details the multi-provider LLM abstraction layer; Section 5.7 covers the SQLite persistence layer and the filesystem audit dump; Section 5.8 describes the Flask API and the single-page-application frontend that sits on top of it; and Section 5.9 covers the container-native deployment. Each section identifies the source-code modules involved so the implementation can be traced module-by-module.

OBSCURA's source is organised in a deliberately flat top-level layout — fourteen Python modules and three frontend files at the project root, with two runtime-managed sub-directories (`investigations/` for persistent state and `frontend/assets/` for static images). Module boundaries follow the layers of Figure 4.6 precisely: each subsystem occupies one or two clearly named modules, and cross-module communication is exclusively through documented top-level functions. No private state is shared across modules.

---

## 5.2 Project Structure and Codebase Layout

The full codebase layout at the project root is summarised below. Each entry is annotated with the architectural layer (from Figure 4.6) that it implements.

```
obscura/
├── app.py             # API layer        — Flask routes + SSE
├── llm.py             # Service / LLM    — pipeline stages (refine/filter/summary)
├── llm_utils.py       # LLM abstraction  — get_llm() factory, streaming, retry
├── crawler.py         # Service          — Deep-Crawl Engine (Tier 1 + Tier 2)
├── search.py          # Service          — Federated search across 16 engines
├── scrape.py          # Service          — Tor-routed HTTP scrape (used by Tier 2)
├── tor_utils.py       # Infrastructure   — NEWNYM circuit rotation
├── obscura_config.py  # Cross-cutting    — env loading, Tor port discovery
├── constants.py       # Cross-cutting    — USER_AGENTS list
├── investigations.py  # Data layer       — investigations + sources tables
├── presets.py         # Data layer       — custom_presets table
├── seeds.py           # Data layer       — seeds table
├── health.py          # Service          — Health-check probes
├── export.py          # Service          — ReportLab Markdown → PDF
├── index.html         # Presentation     — SPA shell + 3 modals
├── styles.css         # Presentation     — light / dark theme, responsive
├── script.js          # Presentation     — SPA logic + SSE reader
├── requirements.txt   # Dependencies     — 14 pinned packages
├── entrypoint.sh      # Infrastructure   — container Tor-bootstrap + tier probe
└── frontend/assets/   # Static assets    — logo.jpeg
```

At runtime the application creates an `investigations/` directory containing the SQLite database (`obscura.db`, in WAL mode) and a `crawled/` sub-directory in which each successful deep-crawl saves the rendered HTML (`<sha256>/rendered.html`) and a marker file (`tier.txt`). The `investigations/` directory is the only mutable runtime state; everything else is read-only after build time.

---

## 5.3 Deep-Crawl Engine

The deep-crawl engine is the single most important subsystem of OBSCURA — it is the one that actually retrieves content from the dark web — and it is the most operationally hardened. It is implemented in `crawler.py` (Tier 1 / Tier 2 dispatcher) with a small Tier 2 dependency on `scrape.py` (for the shared Tor session factory).

### 5.3.1 Tier Auto-Detection

Tier choice is automatic and conservative. At start-up — and on every invocation of `crawl_url()` that does not pass an explicit tier — the engine calls `probe_tier()`, which returns `"selenium"` if both the `selenium` Python package is importable *and* the `geckodriver` binary is findable on `PATH`, and `"requests"` otherwise. The Tor Browser binary is treated as a preferred but optional component: when it is present, `_torbrowser_binary()` returns its path and selenium uses Tor Browser's hardened build directly; when it is absent, selenium falls back to whichever Firefox build geckodriver discovers on the system and routes all of its traffic through the local SOCKS5 proxy regardless. For OSINT scraping the two paths are functionally equivalent — both go out via Tor, both render JavaScript, both can solve light CAPTCHAs — and the relaxed check is what allows the bundled Docker image to use selenium out of the box without redistributing the full Tor Browser bundle.

### 5.3.2 Tier 1 — Selenium + Firefox + Tor SOCKS5

Tier 1 launches a headless Firefox session through `selenium.webdriver.Firefox`, configured by `_crawl_selenium()`. Every Firefox preference relevant to dark-web crawling is set explicitly in code rather than relying on profile defaults:

- `network.proxy.type = 1` and `network.proxy.socks = 127.0.0.1` with `network.proxy.socks_port` set from the auto-discovered Tor SOCKS port — every outbound request goes through Tor.
- `network.proxy.socks_remote_dns = True` — DNS resolution is performed by the Tor exit node, not locally, eliminating the DNS leak that would otherwise reveal which `.onion` names the analyst is browsing.
- `network.proxy.socks_version = 5` — required for the `socks5h://` scheme that supports remote DNS.
- `browser.privatebrowsing.autostart = True` — every session starts in private-browsing mode so no history, cookies, or cache survive between crawls.
- `toolkit.telemetry.enabled = False` and `datareporting.healthreport.uploadEnabled = False` — Firefox itself emits no telemetry.

After the page loads, the engine performs minimal human-like interaction — a short randomised sleep, a small `ActionChains` mouse-move, and an incremental scroll through the first three thousand vertical pixels of the page — both to defeat naive "headless detection" scripts and to trigger lazy-loaded content. The rendered `driver.page_source` is then checked against an explicit block-keyword list (`captcha`, `are you human`, `cloudflare`, `ddos protection`, *etc.*); on match the engine raises a CAPTCHA error which is caught higher up and triggers a fall-back to Tier 2. The raw HTML is dumped to `investigations/crawled/<sha256>/rendered.html` with a sibling `tier.txt` marker, and the cleaned visible text (BeautifulSoup `get_text(separator=' ')` minus `script`, `style`, `noscript`, `head`, `meta`, and `link` tags) is returned to the caller capped at 8 000 characters per page.

### 5.3.3 Tier 2 — `requests` + SOCKS5

Tier 2 is a much lighter retrieval path implemented in `_crawl_requests()` and built on top of the shared Tor `requests.Session` returned by `scrape.get_tor_session()`. It uses the same SOCKS5 proxy and the same audit-dump path as Tier 1 but performs no JavaScript execution and no human-like interaction. Its purpose is twofold: it acts as the graceful-degradation fallback when Tier 1 fails (CAPTCHA, browser crash, geckodriver not present in the host environment), and it is the default crawl tier in production environments where shipping a 150 MB Firefox binary inside the Docker image is undesirable. The same per-page 8 000-character return cap and the same block-keyword detection apply.

### 5.3.4 Retry, Tier Fallback, and Batch Crawl

Per-URL crawls go through `crawl_url(url, title_hint, tier)`, which wraps the chosen tier in a small retry loop. On the first failure of a Tier 1 attempt, the dispatcher rewrites the next attempt to use Tier 2 — so even a complete selenium outage cannot stall a batch crawl. Each retry sleeps for `RETRY_DELAY + random.uniform(0, 2)` seconds (currently five seconds plus jitter) before re-attempting, and a maximum of two attempts is made per URL.

Batch crawling is exposed through `crawl_sources(sources, max_workers, tier, progress_callback)`, which dispatches up to ten concurrent crawls through a `ThreadPoolExecutor` and aggregates successes into a `{url: text}` dictionary. The optional `progress_callback` is the hook the Flask API uses to surface per-source progress upward via SSE.

---

## 5.4 Federated Search Layer

The federated search layer is implemented in `search.py`. Its task is to take the LLM-refined query produced by Stage 1 of the pipeline (§5.5.1) and return a ranked list of candidate `.onion` URLs that the LLM filter (§5.5.2) can shortlist.

### 5.4.1 Engine Registry

Sixteen onion search engines are registered in the module-level `SEARCH_ENGINES` list, each entry a `{name, url}` dict where the URL is a template containing a `{query}` placeholder. The list spans the well-known engines (Ahmia, Tor66, OnionLand, Excavator, Find Tor) as well as smaller ones (Torgle, Amnesia, Kaizer, Anima, Tornado, TorNet, Torland, Onionway, OSS, Torgol, The Deep Searches). New engines are added to the registry without touching any other module — this is the open–closed property called out as NFR2 in §3.3.

### 5.4.2 Per-Engine Parsers

The HTML layout of each search engine differs, often considerably. To preserve as much information as possible while still allowing the long tail of engines to be supported, the module ships *five* engine-specific parsers — `_parse_ahmia`, `_parse_tor66`, `_parse_onionland`, `_parse_excavator`, and `_parse_findtor` — each matched against the engine's actual result-card DOM (for example, `<li class="result">` for Ahmia, `<div class="result-block">` for Tor66, `<div class="g">` for OnionLand). For every other engine, a generic `_parse_generic` parser walks every `<a>` element on the page and extracts any anchor whose `href` contains a `.onion` URL of the canonical length. The `_ENGINE_PARSERS` registry maps engine name to parser function; lookup fall-through to the generic parser is automatic.

Every extracted candidate result goes through a small `_is_useful_result` quality gate that drops empty titles, short (< 4-character) titles, and URLs whose path contains the literal substring `"search"` (a heuristic that filters out same-engine recursive search-result links).

### 5.4.3 Concurrent Fetching, Deduplication, and Pre-Scoring

The public entry point `get_search_results(refined_query, max_workers)` dispatches one `fetch_search_results()` call per engine through a `ThreadPoolExecutor` (default five workers, one per concurrent connection), collects the raw candidate lists, deduplicates them by *normalised* URL (stripped trailing slash), and runs the combined list through `score_and_sort()`. The scorer splits the refined query on non-word characters, drops tokens of length ≤ 2, and gives each candidate result a score equal to the count of distinct query terms appearing in the candidate's title-plus-URL. Sorting is stable, so results with identical scores preserve their original engine-relative order. The pre-scoring step is critical for the downstream LLM filter (§5.5.2): even a relatively weak score-and-sort guarantees the strongest candidates appear in the *first batch* of twenty-five passed to the LLM, which both improves the quality of the eventual filter output and minimises wasted LLM tokens.

---

## 5.5 LLM-Driven Investigation Pipeline

The intelligence pipeline is implemented in `llm.py` and is the heart of OBSCURA's value proposition. It accepts a free-text analyst query and produces a structured Markdown intelligence report by chaining three LLM calls.

### 5.5.1 Stage 1 — Query Refinement (`refine_query`)

The first stage is a one-shot LLM call whose system prompt instructs the model to behave as a "Cybercrime Threat Intelligence Expert", to rewrite the analyst's free-text query into a five-words-or-fewer search-engine-friendly form, to avoid Boolean operators, and to output only the rewritten query itself with no preamble. The implementation is a LangChain `ChatPromptTemplate | llm | StrOutputParser` chain invoked through the shared `_invoke_with_retry()` wrapper (see §5.6.3). Refinement runs in milliseconds against modern models and dramatically improves the quality of downstream search results — a long natural-language analyst prompt like *"are there any recent ransomware leak sites currently hosting stolen healthcare records from US hospitals?"* is compressed to a search-engine-tuned form like *"healthcare ransomware leak hospital"* before any onion engine sees it.

### 5.5.2 Stage 2 — Result Filtering (`filter_results`)

The second stage takes the up-to-100 unique results from the federated search and reduces them to a top-twenty list that the deep-crawler will actually fetch. Filtering is *batched* — `FILTER_BATCH_SIZE = 25` — for two reasons. First, even modern models have a finite useful context window, and concatenating a hundred URL/title pairs into a single prompt is wasteful. Second, batching makes the system robust against the failure of any single batch: a batch that returns a malformed or empty index list contributes zero entries to the final shortlist instead of nuking the whole filter step.

Internally, `_filter_batch()` builds a numbered list of candidate results (`1. https://… - Title text`), sends it to the LLM with a system prompt asking for "the indices of the top 10 results that best match", and parses the response with a strict-but-permissive regex that picks up any digit sequence. Local (batch-relative, 1-based) indices are converted to global indices, deduplicated while preserving order, and capped at twenty. If the LLM returns no usable indices at all (the rare worst case — every batch produced an unparseable response), the filter degrades gracefully by defaulting to the top twenty pre-scored results from §5.4.3.

A specific resilience touch in this stage: if the call raises an `openai.RateLimitError` mid-batch, the prompt is automatically re-built with `truncate=True`, which strips URLs and shortens titles to thirty characters before retrying — this minimises token use and is enough to clear the rate-limit cliff in practice.

### 5.5.3 Stage 3 — Preset-Driven Summary Generation (`generate_summary`)

The third stage takes the deep-crawl output (a `{url: plain_text}` dictionary produced by either `scrape.scrape_multiple()` or `crawler.crawl_sources()`) and the analyst's selected research-domain preset, and produces the final Markdown intelligence report. The model is instructed by the preset system prompt to emit a six-section structured Markdown document covering *(1) Input Query*, *(2) Source Links Referenced for Analysis* (as a three-column Markdown table), *(3) Investigation Artifacts* (a three-column Markdown table of IOC type / value / source context), *(4) Key Insights*, *(5) Solutions & Defensive Recommendations* (a four-column table), and *(6) Next Steps*, with an explicit disclaimer footer. The structured Markdown is what the frontend renders inline in the chat surface and what the PDF exporter (`export.py`) typesets.

Four built-in presets ship with the platform:

- **`threat_intel`** — generic dark-web threat intelligence, the default preset.
- **`ransomware_malware`** — focuses the model on ransomware groups, malware families, attack infrastructure, hashes, C2 IPs, victim sectors, and group aliases.
- **`personal_identity`** — focuses the model on PII exposure, breach sources, marketplace listings, and identity-hardening recommendations (MFA, dark-web monitoring, credit freezes).
- **`corporate_espionage`** — focuses the model on leaked credentials, source code, internal documents, and corporate-targeting recommendations (network segmentation, Zero Trust, IR actions).

Custom presets created by the analyst through the Configuration modal (see §5.8.4) are stored in the `custom_presets` table and resolved the same way — `generate_summary()` accepts a `preset` argument that is either a built-in key, a `custom:<id>` string (the convention introduced in §4.5.2), or an explicit `system_prompt_override` string passed directly from the *Re-summarise* dialog.

An optional `custom_instructions` parameter — passed through from the same dialog — is appended to the system prompt as `Additionally focus on: …`, allowing analysts to nudge the model toward case-specific concerns ("flag any Polish-language sites", "extract Telegram channel handles") without writing a full preset.

---

## 5.6 Multi-Provider LLM Abstraction Layer

LLM provider abstraction lives in `llm_utils.py`. Its job is to take an opaque model-name string from the UI dropdown and return a configured LangChain `BaseChatModel` instance that the pipeline stages of §5.5 can call without knowing which vendor is on the other end.

### 5.6.1 The `_llm_config_map` Registry

A module-level dictionary `_llm_config_map` registers the seventeen base models the platform supports out of the box:

- **OpenAI:** `gpt-4.1`, `gpt-5.2`, `gpt-5.1`, `gpt-5-mini`, `gpt-5-nano` — each registered with `ChatOpenAI` and the appropriate `model_name`.
- **Anthropic:** `claude-sonnet-4-5`, `claude-sonnet-4-0` — registered with `ChatAnthropic`.
- **Google:** `gemini-2.5-flash`, `gemini-2.5-flash-lite`, `gemini-2.5-pro` — registered with `ChatGoogleGenerativeAI` and the `GOOGLE_API_KEY` from `obscura_config`.
- **OpenRouter:** `qwen3-80b-openrouter`, `nemotron-nano-9b-openrouter`, `gpt-oss-120b-openrouter`, `gpt-5.1-openrouter`, `gpt-5-mini-openrouter`, `claude-sonnet-4.5-openrouter`, `grok-4.1-fast-openrouter` — each registered with `ChatOpenAI` but with `base_url` pointed at OpenRouter and `api_key` set from the `OPENROUTER_API_KEY` environment variable.

This registry is the single source of truth — `get_llm()`, `get_model_choices()`, `resolve_model_config()`, and the health-check probe all read from it.

### 5.6.2 Dynamic Local-Provider Discovery

Two providers are *not* enumerated in the registry because their model lists are user-controlled: **Ollama** and **llama.cpp**. Both are queried dynamically at start-up. `fetch_ollama_models()` issues a `GET` against `<OLLAMA_BASE_URL>/api/tags` and returns the list of locally pulled model names; `fetch_llama_cpp_models()` issues a `GET` against `<LLAMA_CPP_BASE_URL>/v1/models` (OpenAI-compatible) and extracts the `data[*].id` field. Both functions tolerate the absence of the corresponding base URL or service — they return an empty list rather than raise — so a user who has neither runtime installed sees no Ollama / llama.cpp entries in the UI dropdown.

`get_model_choices()` combines the gated cloud entries (only included if the relevant API key is configured) with the dynamically discovered local entries, deduplicates by normalised name, and returns the final list to the `/api/models` endpoint.

### 5.6.3 Streaming, Retry, and Provider Auto-Gating

Every LLM instance returned by `get_llm()` is wired with a *fresh* `BufferedStreamingHandler` callback (a per-call object — the comment in `llm_utils.py` is explicit about why a shared singleton would be wrong: multiple pipeline stages would leak UI-callback state into each other). The handler buffers tokens in 60-character flush units and emits each flush both to stdout and, when configured, to an optional UI callback.

The retry wrapper `_invoke_with_retry(chain, inputs, stage)` lives in `llm.py` and is the single call site through which every LLM round-trip in the pipeline passes. It retries up to three times with exponential back-off (2 s → 4 s → 8 s) on any of:

- `openai.RateLimitError`, `openai.APITimeoutError`, `openai.APIConnectionError`, `openai.InternalServerError`
- (if `anthropic` is importable) `anthropic.RateLimitError`, `anthropic.APITimeoutError`, `anthropic.APIConnectionError`, `anthropic.InternalServerError`
- (if `google.api_core.exceptions` is importable) `ResourceExhausted` (429), `ServiceUnavailable` (503), `DeadlineExceeded` (504), `InternalServerError` (500)

Non-retryable exceptions (e.g. `openai.AuthenticationError`) raise immediately so the user gets a clear "API key is invalid" message rather than waiting through three pointless retries. The retryable list grows automatically as new SDKs are installed — `anthropic` and `google.api_core` are imported defensively at module load, and if either is missing its entries are simply omitted.

Provider auto-gating is implemented in `_ensure_credentials()`, called immediately after `get_llm()` resolves a config. If the resolved class is `ChatAnthropic` and `ANTHROPIC_API_KEY` is empty, the call raises a clear `ValueError`: *"Anthropic model 'claude-sonnet-4-5' selected but `ANTHROPIC_API_KEY` is not set. Add it to your .env file or export it before running the app."* The same pattern applies to OpenAI, Google, and OpenRouter; local providers (Ollama, llama.cpp) bypass the credentials check.

---

## 5.7 Persistence Layer

OBSCURA's persistence is a single SQLite database file at `investigations/obscura.db`, opened in WAL journal mode with foreign-key enforcement turned on. Three Python modules manage the four tables — `investigations.py` (the `investigations` and `sources` tables), `seeds.py` (the `seeds` table), and `presets.py` (the `custom_presets` table). The schema is exactly that of Figure 4.4.

### 5.7.1 Schema Initialisation and Migration

Each module's `init_*()` function is idempotent: it runs `CREATE TABLE IF NOT EXISTS` and `CREATE INDEX IF NOT EXISTS` statements on every call so the first request after a clean container start is functionally identical to the thousandth. The `init_db()` function in `investigations.py` additionally runs `_migrate_legacy_json()`, which scans the project root for legacy `investigation_*.json` files (the pre-SQLite flat-file format used in Sprint 1–3), imports each one into the new schema, and deletes the source file. Migration is opportunistic and bounded — if there are no legacy files, the function returns immediately.

The `seeds.py` module includes a small in-place migration for older `seeds` tables that pre-date the `content` and `crawled_at` columns: it inspects `PRAGMA table_info(seeds)` and emits the corresponding `ALTER TABLE ADD COLUMN` statements when needed. This guards against the case where an analyst upgrades the platform without wiping their existing database.

### 5.7.2 WAL Mode and Concurrency

Every `_connect()` helper across the three persistence modules opens the database with `check_same_thread=False`, enables WAL mode (`PRAGMA journal_mode=WAL`), and turns on foreign-key enforcement (`PRAGMA foreign_keys=ON`). WAL mode is what allows the *background-thread auto-crawl* (described in §5.7.4) to write seed updates while the main Flask request thread is concurrently reading from the investigations table — the two never block each other.

### 5.7.3 CRUD Surface

Each table exposes a thin functional CRUD surface:

- `investigations.py` provides `save_investigation`, `update_status`, `update_tags`, `update_summary`, `delete_investigation`, `load_all` (with optional `status_filter`, `tag_filter`, `limit`), `load_one`, and `get_all_tags`.
- `seeds.py` provides `add_seed`, `mark_crawled`, `mark_loaded`, `delete_seed`, `get_seed_by_url`, `get_all_seeds`, `get_uncrawled`, `get_unloaded`, and `seed_urls_from_sources` (a bulk-add convenience used when promoting an investigation's source list into the seed table).
- `presets.py` provides `list_presets`, `get_preset`, `get_preset_by_key`, `create_preset`, `update_preset`, and `delete_preset`, with a `CUSTOM_KEY_PREFIX = "custom:"` constant used consistently across the codebase to disambiguate custom-preset keys from built-in keys.

Each `load_*` function returns a plain Python `dict` (constructed by `_row_to_dict`), making the API layer's job a simple `jsonify(result)`.

### 5.7.4 Background Auto-Crawl of New Seeds

When the analyst adds a seed URL through the Seed Manager (the `POST /api/seeds` endpoint), the API layer immediately spawns a daemon thread that runs `crawl_sources([{"link": seed_url, "title": seed_name}])`, calls `seed_db.mark_crawled()` on success, and marks the seed crawled-with-empty-content on failure (so the same dead URL isn't retried indefinitely). The frontend polls the seeds endpoint on a five-second timer while the Seeds modal is open, so the *"crawled / loaded"* status updates appear in the UI without any user action.

### 5.7.5 On-Disk Audit Dump

In parallel with the database writes, every successful deep-crawl writes its raw rendered HTML to `investigations/crawled/<sha256>/rendered.html` and a one-line tier marker to `investigations/crawled/<sha256>/tier.txt`. The directory is keyed by the SHA-256 hash of the source URL, so the same source always maps to the same audit directory regardless of which investigation triggered the crawl. This is the artefact that satisfies NFR11 (Auditability): a post-hoc analyst can re-derive the LLM's input from the exact HTML captured at the time of the original investigation.

---

## 5.8 Flask API and Frontend SPA

OBSCURA's user-facing surface is a single-page application served by Flask. The two co-operate over a small REST + Server-Sent-Events interface; together they realise the *Analyst-friendly user interface* objective from §1.5.

### 5.8.1 Flask Routes (`app.py`)

The Flask application registers nineteen routes split across seven groups: catalogue endpoints (`/api/models`, `/api/providers`); preset management (`GET/POST /api/presets`, `PUT/DELETE /api/presets/<id>`); investigation management (`GET /api/investigations`, `GET/DELETE /api/investigations/<id>`, `PUT /api/investigations/<id>/metadata`, `POST /api/investigations/<id>/resummarize`, `POST /api/investigations/<id>/deep-crawl`); seed management (`GET/POST /api/seeds`, `POST /api/seeds/<id>/crawl`, `DELETE/POST /api/seeds/<id>`); diagnostics (`POST /api/health/llm`, `POST /api/health/search`); the main investigation entry point (`POST /api/investigate`); and the export sink (`POST /api/export/pdf`). The SPA is served from `GET /` and static assets from `GET /<path>`.

The most important route is `POST /api/investigate`, which returns a Flask `Response` with `mimetype='text/event-stream'` and a Python generator that yields five SSE events as the pipeline progresses — *"Refining query…"*, *"Searching dark web for: …"*, *"Filtering N results…"*, *"Scraping N selected sources…"*, *"Generating final intelligence report…"* — followed by a final event carrying the saved investigation, sources, and summary. This is the mechanism that drives the live status line in the SPA chat surface.

The re-summarise route is worth a specific mention because it implements the analyst-iteration loop without any extra crawling: it loads the existing investigation, looks up the saved seed content for each source, calls `generate_summary()` on the in-memory map (falling back to the *existing* saved summary if the seed content has been purged), and writes the new summary back over the old one. The optional `force_rescrape=true` flag re-scrapes any missing sources before regeneration.

### 5.8.2 SPA Shell (`index.html`)

The HTML shell defines the overall layout — a collapsible sidebar (brand, *New Investigation* button, history list, footer buttons), a main content area (top bar with title and export buttons, scrollable chat container, and a textarea-based input area with send and stop buttons), three modal dialogs (Configuration, Health Checks, Seed Manager), and a toast notification region. Font Awesome 6.4 is loaded from CDN for icons. The body element starts in `light-mode` and is flipped to `dark-mode` by the theme toggle.

### 5.8.3 SPA Logic and SSE Reader (`script.js`)

The SPA's state is a single module-level `state` object that holds the model list, providers, presets, investigations, tags, seeds, the current selections, performance sliders (threads, max-results, max-scrape, max-content-chars), and the cached health-check results. `init()` runs `setupEventListeners()` and `reloadAppState()` (a `Promise.allSettled` over the four catalogue endpoints) at page load, then applies the persisted theme and sidebar-collapse state from `localStorage`.

The SSE reader is implemented inside `handleSearch()`. It opens a `fetch` with an `AbortController.signal`, reads the response body through a `ReadableStream` reader, decodes UTF-8 chunks, splits on `\n\n`, parses each `data: …` event as JSON, and updates the chat surface accordingly — a status event replaces the *"Initialising investigation pipeline…"* placeholder with the new status, the final event triggers a Markdown render of the summary and a sidebar refresh. The stop button calls `investigationAbortController.abort()`, which causes `fetch` to reject with an `AbortError` that is caught and displayed as a friendly warning.

The Markdown renderer is a hand-rolled `formatMarkdown(text)` that handles bold, italic, inline code, tables, bullets, and numbered lists. It is intentionally minimal — the LLM output structure is constrained by the preset prompts, so a full CommonMark parser would be over-engineered.

### 5.8.4 Modal Workflows

Three modal dialogs cover the remaining UI surface:

- **Configuration.** Model dropdown (`<select id="modelSelect">` populated from `/api/models`), thread / max-results sliders, the preset dropdown, the custom-prompt editor for editing/deleting the currently selected custom preset, a "Create New Domain" form for adding presets, and a per-provider status grid.
- **Health Checks.** Two buttons — *Check LLM* and *Check Engines* — backed by `POST /api/health/llm` and `POST /api/health/search` respectively. Output is rendered into a fixed-width `<div>` line by line.
- **Seed Manager.** An add-seed form (URL + label), a filter dropdown (all / crawled / uncrawled), and a dynamic list of seeds with status and delete actions. The list is refreshed every five seconds while any uncrawled seed is pending so the auto-crawl progress is visible without manual refresh.

---

## 5.9 Containerised Deployment

The final deployment artefact is a Docker container that bundles the Tor daemon, Firefox ESR, geckodriver, and the Python 3 runtime, and is started by the `entrypoint.sh` script.

### 5.9.1 `entrypoint.sh` Bootstrap Sequence

The script executes six discrete steps on every container start, each carefully ordered to avoid the silent failures that bedevil naive Tor + crawler setups:

1. **Launch Tor in the background**, piping stdout / stderr through `tee /tmp/tor.log` so the bootstrap state can be grep-ed.
2. **Wait up to sixty seconds** for the SOCKS port (`127.0.0.1:9150`) to *open* — a Python one-liner repeatedly attempts a socket connection until it succeeds.
3. **Wait up to four minutes** for the Tor log to report *Bootstrapped 100%* (or, earlier, *"current consensus contains exit nodes"* — an earlier indicator that clearweb circuits can already be built). A warning is printed if neither signal arrives within the timeout, but start-up continues so a healthy Tor service that is just slow to fully bootstrap does not block the analyst from reaching the SPA.
4. **Pre-warm the circuit** by issuing a single `curl --socks5-hostname 127.0.0.1:9150 -fsS --max-time 45 https://check.torproject.org/`. The script's comment makes the rationale explicit: the very first request through a fresh circuit can take 20–40 seconds while exit-node descriptors load, which would otherwise blow the 45-second selenium page-load timeout on the user's *first* investigation.
5. **Probe and print the runtime tier**, naming the detected Firefox and geckodriver versions and the chosen Deep-Crawl tier (Tier 1 ready, or Tier 2 fallback). The banner is intentionally verbose so a misbuilt image is obvious in `docker logs`.
6. **`exec python app.py`**, replacing the shell process with the Flask server. The Flask app listens on `0.0.0.0:8501`.

### 5.9.2 Configuration via `.env`

Runtime configuration is supplied through an `.env` file mounted into the container or through process environment variables. `obscura_config.py` calls `python-dotenv`'s `load_dotenv()` at import time and exposes seven configuration entries: `OPENAI_API_KEY`, `GOOGLE_API_KEY`, `ANTHROPIC_API_KEY`, `OLLAMA_BASE_URL`, `OPENROUTER_BASE_URL` (default `https://openrouter.ai/api/v1`), `OPENROUTER_API_KEY`, and `LLAMA_CPP_BASE_URL`. A small `_clean_env()` helper trims whitespace and unwraps accidentally quoted values — a common copy-paste mistake when populating `.env` files.

Tor ports are auto-discovered by `find_tor_socks_port()` and `find_tor_control_port()`: each tries an environment-provided value first (`TOR_SOCKS_PORT`, `TOR_CONTROL_PORT`), then probes the standard system-Tor ports (9050 / 9051) and the standard Tor-Browser ports (9150 / 9151) in turn, returning whichever responds first. This makes OBSCURA function out-of-the-box on a host where Tor Browser is the only Tor available, on a host where a system Tor daemon is running, and inside the container where the bundled daemon runs on the Tor-Browser default ports.

---

## 5.10 Summary

This chapter has walked the implementation of OBSCURA from the inside out, layer by layer, module by module. The two-tier deep-crawl engine (`crawler.py` + `scrape.py`) gives the platform anonymity-preserving access to dark-web content with graceful fallback when JavaScript-rendering tooling is unavailable. The federated search layer (`search.py`) aggregates and pre-ranks candidate URLs from sixteen onion search engines through parser-per-engine extraction and keyword-overlap scoring. The three-stage LLM pipeline (`llm.py`) turns a free-text analyst query into a structured intelligence report through query refinement, batched LLM filtering, and preset-driven summary generation across four built-in research domains. The multi-provider abstraction (`llm_utils.py`) lets the same pipeline call out to six different LLM providers — including locally hosted Ollama and llama.cpp instances — behind a single dispatching layer with streaming, exponential-backoff retry, and provider-by-credential gating. The persistence layer (`investigations.py`, `seeds.py`, `presets.py`) stores every investigation, every source, every seed, and every custom preset in a four-table SQLite database with WAL journalling, complemented by an on-disk audit dump of the rendered HTML of every successful crawl. The Flask + SPA frontend (`app.py`, `index.html`, `script.js`, `styles.css`) exposes all of this as a conversational chat surface with live SSE progress streaming, modal-driven configuration / health / seed management, and one-click PDF or Markdown export. And the container deployment (`entrypoint.sh` + Dockerfile) packages the entire system — including the Tor daemon itself — into a single reproducible artefact that synchronises with Tor's bootstrap signal and pre-warms a circuit before exposing the analyst UI. The chapter that follows describes how each of these subsystems was tested and evaluated.
