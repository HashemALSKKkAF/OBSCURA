<!--
  Chapter 7 — User Manual / System Walkthrough
  Analyst-facing walk-through of every UI surface in the final product.
  Screenshot placeholders are flagged inline so live captures can be slotted
  in before final submission without editing the prose.
-->

# Chapter 7 — User Manual and System Walkthrough

## 7.1 Introduction

This chapter is the analyst-facing companion to the technical chapters that precede it. Where Chapter 4 described what the system *is* and Chapter 5 described how it *works*, this chapter describes how to *use* it. It is organised as a step-by-step walk-through, beginning with installation and first launch (§7.2), tracing the main interface tour (§7.3), and then covering each of the platform's operational workflows in turn — running an investigation (§7.4), configuration (§7.5), health checks (§7.6), the seed manager (§7.7), working with the saved-investigation history including re-summarising and deep-crawling (§7.8), exporting reports (§7.9), theme and layout customisation (§7.10) — before closing with a short troubleshooting reference (§7.11) and a chapter summary (§7.12).

Every screenshot referenced in this chapter is a live capture of the deployed OBSCURA container running against real onion targets. Screenshot placeholders use the caption convention *"Figure 7.x — Description"* so the figures can be referenced from the *List of Figures* in the front matter.

---

## 7.2 Installation and First Launch

### 7.2.1 Prerequisites

OBSCURA is distributed as a single Docker image. The only host requirements are:

- **Docker** 20.10 or later (Docker Desktop on Windows / macOS or Docker Engine on Linux).
- **At least one LLM credential.** Either an API key for a hosted provider (OpenAI, Anthropic, Google Gemini, or OpenRouter) *or* a locally running Ollama / llama.cpp server reachable from the container. With no credentials configured, the UI will show no available models and investigations cannot be run.
- **A modern web browser** — Chrome 100+, Firefox 100+, Edge 100+, or Safari 15+.

Tor itself, Firefox ESR, geckodriver, and the Python runtime are all bundled inside the container; there is no need to install them separately on the host.

### 7.2.2 Container Start

The platform is launched with a single command from the project root:

```bash
docker run -d --rm \
    --name obscura \
    -p 8501:8501 \
    -v "$(pwd)/.env:/app/.env:ro" \
    -v "$(pwd)/investigations:/app/investigations" \
    obscura:latest
```

The two volume mounts are doing important work. The first mounts the `.env` file containing the analyst's LLM credentials read-only into the container, so the credentials never have to be baked into the image. The second mounts the `investigations/` directory back to the host, so the SQLite database, the persisted investigation summaries, and the audit dump survive across container restarts. With these in place, the analyst can `docker stop` and `docker start` the container freely without losing any state.

Container start-up takes between 30 and 90 seconds depending on Tor bootstrap speed. The full sequence visible in `docker logs obscura` is the one described in §5.9.1: Tor launch, SOCKS-port wait, *Bootstrapped 100%* wait, circuit pre-warm, tier probe, then Flask listening on port 8501.

*[Figure 7.1 — Sample `docker logs obscura` output showing the bootstrap banner.]*

### 7.2.3 First-Time Configuration

Once the banner reports `Starting OBSCURA: AI-Powered Dark Web OSINT Tool…`, the analyst opens `http://localhost:8501` in a browser. The first thing displayed is the welcome screen, which presents three suggested-prompt buttons and the input bar at the bottom of the screen.

If at this point the analyst has not yet populated `.env`, the model dropdown in the Configuration modal will be empty and any attempted submission will return an error. To proceed, the analyst either edits `.env` on the host (the file is mounted read-only into the container but is read every time the container starts, so a restart picks up the new keys) or starts a local Ollama / llama.cpp server and sets the corresponding base URL in `.env`.

The minimum viable `.env` content is shown below. Only the keys for providers that will actually be used need to be set; all others can be left blank.

```dotenv
# Hosted providers — set the ones you have credentials for.
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...
GOOGLE_API_KEY=AIza...
OPENROUTER_API_KEY=sk-or-...

# Local providers — set the base URL if you run them.
OLLAMA_BASE_URL=http://host.docker.internal:11434
LLAMA_CPP_BASE_URL=http://host.docker.internal:8080
```

---

## 7.3 Tour of the Main Interface

### 7.3.1 The Welcome Screen

On a fresh container with no prior investigations, the main content area shows a centred welcome panel — the OBSCURA logo, the heading *"How can OBSCURA help your investigation?"*, and three large suggested-prompt buttons (*"Search for recent ransomware leaks"*, *"Investigate dark web identity sellers"*, *"Find mentions of corporate espionage"*). Clicking any suggested prompt immediately submits it as an investigation, which is the fastest path from container start to first usable result.

*[Figure 7.2 — Welcome screen with the three suggested-prompt buttons.]*

### 7.3.2 The Sidebar

The collapsible sidebar on the left side of the screen has four regions: the **brand header** (OBSCURA logo and name, plus a hamburger button that toggles the collapsed/expanded state), the **New Investigation** button that returns the chat surface to the welcome screen, a **search box** that filters the investigation history as the analyst types, and the **investigation history list** itself — a scrollable list of every saved investigation ordered newest first, each row carrying the original query text as its label and a trash-can icon for deletion.

At the bottom of the sidebar are three footer buttons that open the platform's three modal dialogs: **Seed Manager**, **Health Checks**, and **Configuration**. A small user-profile block (avatar + name + email placeholder) sits below the modal buttons.

The sidebar's collapsed state is persisted across sessions through `localStorage`, so an analyst who prefers more screen space for the chat surface can collapse the sidebar once and have it stay collapsed thereafter.

*[Figure 7.3 — Expanded sidebar showing investigation history, search box, and footer buttons.]*

### 7.3.3 The Main Chat Area

The main content area to the right of the sidebar has a fixed top bar and a scrollable chat container below it. The top bar shows the current investigation's query as a title (or *"New Investigation"* before submission), and three action buttons on the right: **Export PDF**, **Export Markdown**, and **Theme Toggle** (a moon icon for light mode, a sun icon for dark mode).

The chat container is where the conversation between the analyst and the system is rendered. Analyst messages are right-aligned with a small avatar; system messages are left-aligned with the OBSCURA logo as their avatar. During an in-flight investigation, the most recent system message displays a spinning loader and the current SSE status (*"Refining query…"*, *"Searching dark web for: …"*, *"Filtering N results…"*, *"Scraping N selected sources…"*, *"Generating final intelligence report…"*).

*[Figure 7.4 — Main chat area during an in-flight investigation showing a live SSE status line.]*

### 7.3.4 The Input Bar

The bottom of the screen carries the input bar: a textarea that auto-expands as the analyst types, a circular send button on the right (paper-plane icon), and a stop button (square icon) that only becomes visible while an investigation is in flight. Pressing **Enter** submits the query; pressing **Shift + Enter** inserts a newline without submitting. A small hint paragraph below the input bar reminds the analyst that *"OBSCURA can provide deep-web insights. Always verify critical findings."*

---

## 7.4 Running an Investigation

A full investigation is launched in three clicks or fewer from the welcome screen.

### 7.4.1 Submitting a Query

The analyst either clicks a suggested-prompt button or types a free-text query into the input bar and presses Enter. Typical queries are short natural-language questions: *"are credentials for example.com being sold?"*, *"recent DarkSide ransomware leak sites"*, *"corporate data leaks affecting financial services this month"*. The query does not need to be in any particular format — the LLM refinement stage will rewrite it into a search-engine-friendly form before any onion engine sees it.

Before submitting, the analyst can — but is not required to — open the Configuration modal (§7.5) to choose a specific model or research-domain preset. If the analyst makes no choice, the most recently used model and preset are reused; on a fresh container, the first model in the dropdown and the *Dark Web Threat Intel* preset are used by default.

### 7.4.2 Watching the Live Progress

After submission, the chat container immediately shows the analyst's query as a user message and a system message with the placeholder text *"Initialising investigation pipeline…"*. Within a second this placeholder is replaced by the first SSE status event, and from that point onward the status text updates live as the pipeline progresses through its five stages. The analyst is free to abandon the screen during this time — the pipeline runs on the backend regardless — and to return to find the rendered report waiting.

If the analyst wants to abort the in-flight investigation (for instance because they realise the query was wrong), clicking the **Stop** button to the right of the send button issues a `fetch` `AbortController.abort()` on the SSE stream. The chat then shows a warning message (*"Investigation stopped by user"*) and the platform returns to its idle state.

### 7.4.3 Reading the Report

When the pipeline completes, the system message replaces its progress line with the rendered Markdown summary. The report has the six sections described in §5.5.3:

1. **Input Query** — the original analyst query.
2. **Source Links Referenced for Analysis** — a Markdown table with one row per source: the index, the onion URL (typically truncated for readability), and a brief intelligence-style description of the content found at that URL.
3. **Investigation Artifacts** — a Markdown table listing every concrete indicator the LLM extracted: IPs, domains, file hashes, CVEs, cryptocurrency wallets, email addresses, marketplace names, threat-actor aliases, and so on. Each row links the artefact back to the source it came from.
4. **Key Insights** — three to five high-level observations, each with a *why-it-matters* column.
5. **Solutions and Defensive Recommendations** — a four-column table mapping each identified risk to a specific mitigation, with implementation detail and the security benefit it delivers.
6. **Next Steps** — a short table of suggested follow-up investigations the analyst might run, with proposed queries.

The report ends with the standard disclaimer footer reminding the analyst that all critical findings must be manually verified and that the tool is for lawful investigative purposes only.

*[Figure 7.5 — A completed investigation report rendered in the chat surface.]*

---

## 7.5 Configuration Modal

The Configuration modal is opened from the *Configuration* button at the bottom of the sidebar. It has three sections, each described below.

### 7.5.1 Model and Performance

The first section contains:

- **LLM Model** — a dropdown populated from `/api/models`. Only providers for which credentials are configured appear in the dropdown. Selecting a different model takes effect immediately for the next investigation; the choice is remembered for the rest of the session.
- **Scraping Threads** — a slider from 1 to 16 controlling the maximum number of concurrent crawl workers. Default is 4. Higher values reduce total investigation time at the cost of more parallel Tor circuits.
- **Max Results** — a slider from 10 to 100 controlling the maximum number of unique search-engine results to feed into the LLM filter step. Default is 50. Higher values give the filter more candidates to choose from at the cost of more LLM tokens.

*[Figure 7.6 — Configuration modal showing the model dropdown and the two performance sliders.]*

### 7.5.2 Prompt Domains

The second section is the *Prompt Domains* section. It contains a single dropdown listing every available preset — the four built-in domains and every custom preset the analyst has created — plus an inline editor for the currently selected preset (visible only when a custom preset is selected) and a form for creating a new custom domain.

The four built-in domains shape the LLM's voice and the artefact types it focuses on:

- **🔍 Dark Web Threat Intel** — generic threat-intelligence framing; the default and most broadly useful.
- **🦠 Ransomware / Malware Focus** — emphasises ransomware groups, malware families, hashes, command-and-control infrastructure, victim sectors, and group aliases. EDR / XDR / YARA recommendations.
- **👤 Personal / Identity Investigation** — emphasises PII exposure, breach sources, and identity-hardening recommendations (MFA, dark-web monitoring, credit freezes). Handles personal data with discretion.
- **🏢 Corporate Espionage / Data Leaks** — emphasises leaked credentials, source code, internal documents, and corporate-targeting recommendations (network segmentation, Zero Trust, IR actions, application whitelisting).

To create a custom preset, the analyst types a name and a system prompt into the *Create New Domain* form and clicks *Add Domain*. The new preset is persisted to the `custom_presets` table and immediately appears in the dropdown.

### 7.5.3 Active Providers

The third section is a small status grid showing each of the six LLM providers (OpenAI, Anthropic, Google, OpenRouter, Ollama, llama.cpp) and whether each is *configured* (green), *not set* (yellow), or *optional* (neutral). The grid is purely informational — it gives the analyst an at-a-glance view of which providers their `.env` supports without having to scroll the model dropdown.

---

## 7.6 Health Checks Modal

The Health Checks modal is opened from the *Health Checks* button at the bottom of the sidebar. It contains two buttons and an output area.

- **Check LLM** issues a `POST /api/health/llm` request with the currently selected model. The output area then shows one line of text: the provider name, the up/down status, and the round-trip latency in milliseconds. If the call failed, the error message is shown on a second line.
- **Check Engines** issues a `POST /api/health/search` request which runs a Tor-routed ping against the local SOCKS5 proxy and against each of the sixteen onion search engines in parallel. The output area then shows seventeen lines — one for Tor, one per engine — each annotated with up/down status and latency. Engines that are currently unreachable show their HTTP status code or socket error.

The most useful workflow for the analyst is to run **Check Engines** before launching a long-running investigation, especially after a long period of inactivity. If the analyst sees that a substantial fraction of the engines are currently down, they can adjust their expectations (or wait a few minutes for the dark-web ecosystem to stabilise) before committing to a slow run.

*[Figure 7.7 — Health Checks modal after running both probes.]*

---

## 7.7 Seed Manager Modal

The Seed Manager modal is opened from the *Seed Manager* button at the bottom of the sidebar. It supports four operations.

### 7.7.1 Adding a Seed

The form at the top of the modal accepts a URL (required, must be a full HTTP/HTTPS URL — typically a `.onion` URL) and an optional human-readable label. Clicking *Add* persists the seed to the `seeds` table and immediately kicks off a background auto-crawl thread (see §5.7.4). The seed appears in the list below with a *crawled = false* status and the auto-refresh timer (running every five seconds while the modal is open) updates the status to *crawled = true* once the background thread completes.

### 7.7.2 Browsing Seeds

The seed list shows every persisted seed with its URL, label, last-known status code, *crawled* and *loaded* status badges, and the timestamp of the last successful crawl. A filter dropdown at the top of the list narrows the view to *All*, *Crawled*, or *Uncrawled* seeds.

### 7.7.3 Re-Crawling a Seed

The refresh button on each seed row triggers a fresh `POST /api/seeds/<id>/crawl` request, which forces a synchronous re-crawl of that single seed. The seed's status updates to reflect the new outcome — useful when an analyst suspects an `.onion` URL has come back online after previously failing.

### 7.7.4 Deleting a Seed

The trash icon on each seed row deletes the seed from the `seeds` table after a confirmation dialog. The audit-dump directory associated with the seed is not deleted — the forensic trail is preserved even if the seed itself is no longer of interest.

*[Figure 7.8 — Seed Manager modal showing the add form, the filter dropdown, and the seed list with status badges.]*

---

## 7.8 Working with Saved Investigations

Every completed investigation is persisted to the database and immediately appears in the sidebar history (most recent first). Clicking any history entry loads that investigation back into the chat surface for review.

### 7.8.1 Opening a Past Investigation

Clicking a history-list row immediately renders the past investigation's query as a user message and its full Markdown summary as a system message — exactly as the chat surface looked when the investigation first completed. The sources list, the model used, and the preset used are all available through the export pipeline (§7.9) and through the in-flight metadata.

### 7.8.2 Re-Summarising an Investigation

The re-summarise capability lets the analyst regenerate the summary of an existing investigation without re-running the full pipeline. This is useful when the analyst has the *source set* they want but wants to:

- try a different LLM model (for instance, a more capable frontier model on a summary previously generated against a smaller local model);
- use a different research-domain preset (for instance, re-cast a `threat_intel` summary as a `personal_identity` one);
- supply a custom-instruction tweak (*"focus on Polish-language listings"*, *"extract every Telegram channel handle"*); or
- provide an entirely overridden system prompt for a one-off case.

Re-summarisation reuses the saved seed content where possible and avoids re-crawling unless the analyst sets `force_rescrape=true`. The new summary replaces the old one in the database in place.

### 7.8.3 Triggering a Deep-Crawl

The deep-crawl capability lets the analyst re-fetch every source URL of an investigation using the Tier 1 selenium path. This is useful when the analyst notices a source's preview content looks thin or wants to refresh the captured HTML against the current state of the page. After the crawl completes, the refreshed source content can be fed into a re-summarisation if desired.

### 7.8.4 Tags and Status

Two pieces of metadata are editable after the fact. **Status** can be set to `active`, `pending`, `closed`, or `complete` to track case-management state. **Tags** can be any comma-separated list (e.g. `retail,credentials,2026-Q1`). Both are persisted to the `investigations` table and are usable as filters elsewhere in the UI.

### 7.8.5 Searching History

The search box at the top of the sidebar filters the history list as the analyst types, matching against the original query text and the assigned tags. The search is case-insensitive and substring-based; it runs entirely in the browser against the in-memory state object and is instant.

---

## 7.9 Exporting Reports

Every completed investigation can be exported in either of two formats from the top-bar buttons in the main content area.

- **Export PDF** issues a `POST /api/export/pdf` with the active investigation's content and metadata. The backend uses ReportLab Platypus to typeset a paginated A4 document containing the header (project title, generation timestamp), a meta-data table (query, refined query, model, domain, status, tags), the source list, the full Markdown findings (with tables, bullets, and headings rendered into proper PDF flowables), and the standard disclaimer footer. The browser downloads the resulting `obscura_report_YYYY-MM-DD.pdf` file directly.
- **Export Markdown** is a pure client-side operation: the active summary's Markdown is wrapped in a `Blob` and downloaded as `<query_slug>_YYYY-MM-DD.md`. This is the format an analyst would attach to a JIRA ticket, a Slack message, or an incident-response chat.

Both export buttons are also active for the currently selected seed if no investigation is in focus — in that case the seed's `content` field is exported.

*[Figure 7.9 — A PDF export rendered in Acrobat Reader showing the meta-data block, the sources list, and the first investigation-artefact table.]*

---

## 7.10 Theme and Layout Customisation

Two persistent preferences are available, each stored in `localStorage` so they survive across browser sessions on the same host.

- **Theme**: light or dark. Toggled with the moon / sun icon at the top right of the chat area. The selection persists immediately.
- **Sidebar State**: expanded or collapsed. Toggled with the hamburger icon at the top of the sidebar. The collapsed state shrinks the sidebar to a narrow icon-only strip, freeing horizontal space for the chat surface — useful on smaller screens or when the analyst is reviewing a particularly long report.

The interface is responsive down to a 768-pixel-wide viewport, at which point the sidebar collapses to a slide-out overlay that the user opens with the top-bar hamburger icon. Both themes have been visually tuned for daytime and evening operation; the dark theme is also kinder when the screen is being shared in a SOC or training environment.

---

## 7.11 Troubleshooting

The most common analyst-visible failure modes and their resolutions are summarised in Table 7.1.

**Table 7.1 — Common Issues and Resolutions**

| Symptom | Likely cause | Resolution |
|---|---|---|
| Model dropdown is empty | No LLM credentials configured | Populate `.env` with at least one of `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, `GOOGLE_API_KEY`, `OPENROUTER_API_KEY`; or start a local Ollama / llama.cpp server and set the corresponding base URL. Restart the container. |
| *"API key is not set"* error on submission | Selected model's credential is missing | Either configure that provider's key or pick a different model. |
| Investigation hangs on *"Searching dark web for…"* for > 60 s | Tor circuit not yet established | Open the Health Checks modal, run *Check Engines*. If most engines are down, Tor is not yet bootstrapped — wait 30–60 seconds and retry. |
| Health check shows most engines down | Onion search-engine churn (normal) | Wait several minutes; engines come and go. As long as at least 4–5 engines are up, federated search will still produce a usable shortlist. |
| Investigation completes with a structurally wrong summary | Model produced free-form text instead of the preset-required Markdown | Open the past investigation, click *Re-summarise*, select a more capable model (e.g. a frontier hosted model rather than a small local one). |
| PDF export fails | Malformed Markdown in the summary (very rare) | The export pipeline falls back to a plain-text recovery PDF automatically; if even that fails, check the container log for a `reportlab` error. |
| Seed remains *uncrawled* indefinitely | URL unreachable through Tor / unresolvable onion | Click the seed's refresh icon to retry; if still failing, the URL is likely dead. |
| Chat surface and sidebar look broken on a small screen | Viewport below 768 px wide | This is below the platform's supported responsive breakpoint; resize the window or open the sidebar through the hamburger icon. |

If a failure mode persists after the resolution above, the container's log (`docker logs obscura`) is the next place to look: the structured `logging` output from every subsystem will name the failing module and the underlying error.

---

## 7.12 Summary

This chapter has presented OBSCURA from the analyst's perspective as a step-by-step user manual. After installation and first-launch (§7.2), the chapter toured the main interface (§7.3) — sidebar, chat area, input bar — and then covered each of the platform's operational workflows in turn: running a new investigation with live SSE progress and the six-section structured report (§7.4), configuring the model / threads / max-results / research-domain preset (§7.5), running the Tor / LLM / search-engine health checks (§7.6), managing seeds with background auto-crawl (§7.7), working with the saved investigation history including re-summarising and deep-crawling (§7.8), exporting reports as PDF or Markdown (§7.9), and customising the theme and sidebar layout (§7.10). The troubleshooting table (Table 7.1) records the most common operational issues and their resolutions. The chapter that follows steps back from the platform itself to describe how the project was managed across the year, the tools and conventions used, and the milestones along the way.
