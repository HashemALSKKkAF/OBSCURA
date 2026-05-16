<!--
  Page iv — Executive Summary.
  FYDP guideline cap: 350 words, single-spaced, no citations or figure refs.
  Must cover: problem statement, background, methodology, findings, conclusions.
  This abstract is written fresh against the FINAL shipped product, not the
  mid-evaluation prototype.
-->

# Executive Summary

Cybercriminal activity has migrated decisively onto the dark web, with onion forums, illicit marketplaces, and ransomware leak sites becoming the trading floor for stolen credentials, exploits, and malware. The anonymity of the Tor network, the high churn of hidden services, and the operational risk of manual browsing leave security analysts with a structural visibility gap. Existing dark-web tools either focus on broad reconnaissance or on isolated cyber-threat-intelligence (CTI) extraction tasks; none deliver a fully integrated, analyst-facing workflow that combines federated search, AI-assisted triage, and a usable interface for day-to-day investigation.

This project, OBSCURA, presents an automated dark-web threat-intelligence platform that compresses what is traditionally a multi-tool manual investigation into a single conversational interface. The system federates search across sixteen onion search engines through a Tor SOCKS5 proxy, deduplicates and pre-scores results by keyword overlap, then drives a three-stage Large-Language-Model (LLM) pipeline — query refinement, LLM-based result filtering, and preset-driven summary generation — to produce structured Markdown intelligence reports. A two-tier deep-crawl engine routes all egress through Tor: Tier 1 uses Selenium with Firefox for JavaScript-rendered targets, while a Tier 2 requests-based fallback guarantees coverage even when Selenium is unavailable. All output is persisted in a four-table SQLite schema with raw-HTML audit dumps, and is exportable as PDF or Markdown for downstream reporting.

The platform abstracts six LLM providers (OpenAI, Anthropic, Google Gemini, OpenRouter, Ollama, and llama.cpp) behind a single dispatching layer with token streaming, exponential-backoff retry, and provider auto-gating by API key. Four built-in research-domain prompt presets — threat intelligence, ransomware and malware, identity exposure, and corporate espionage — are complemented by user-defined custom presets. The frontend is a chat-style single-page application served by Flask with Server-Sent Events for live progress streaming.

End-to-end validation demonstrates that OBSCURA replaces the slowest portions of analyst workflow — source discovery, triage, and structured note-taking — with reliable automated counterparts while preserving human oversight at every decision point. The system ships as a Docker container with an embedded Tor daemon, enabling reproducible deployment on a single analyst workstation.
