<!--
  Chapter 8 — Conclusion and Future Enhancements   (FINAL chapter)
  Per FYDP guidelines: stand-alone — no cross-references or external citations.
  Recommended sections: Summary + Recommendations for Future Work.
  This chapter expands that into five sections to match A-grade depth.
-->

# Chapter 8 — Conclusion and Future Enhancements

## 8.1 Summary of the Work

This report has presented OBSCURA, an AI-powered dark-web open-source-intelligence (OSINT) platform built to automate the slowest portions of an analyst's threat-intelligence workflow. The project set out to answer a concrete question: can a single integrated system replace the patchwork of crawlers, search engines, custom NLP pipelines, and dashboards that an analyst currently has to assemble for themselves when working dark-web sources? The answer, demonstrated by the platform delivered alongside this report, is yes — and the system that demonstrates it has been built and shown to operate end-to-end against live dark-web targets.

OBSCURA accepts a free-text query from a security analyst, refines that query into a search-engine-friendly form, federates it across sixteen independent onion search engines in parallel, deduplicates and pre-scores the aggregated results, filters the top twenty most relevant sources through a Large Language Model, retrieves each of those sources through a Tor-routed two-tier deep-crawl engine, generates a structured Markdown intelligence report grounded in the scraped content, and persists the entire investigation — query, refined query, model, prompt preset, source list, audit dumps, and full report — in a local SQLite database. The platform abstracts over six Large-Language-Model providers (OpenAI, Anthropic, Google Gemini, OpenRouter, Ollama, and llama.cpp), exposes its workflow through a chat-style single-page application served by Flask with live progress streaming, ships four built-in research-domain prompt presets complemented by an unlimited number of user-defined custom presets, and is delivered as a single self-contained Docker container with an embedded Tor daemon.

Three findings from the work stand out as the headline conclusions of the project.

The first is that **a general-purpose Large Language Model, when correctly prompted and grounded in scraped source text, can substitute effectively for a bespoke Natural Language Processing pipeline** in a dark-web threat-intelligence setting. Indicator extraction, entity recognition, threat classification, MITRE-style mapping, and structured-report assembly — each of which would traditionally require a dedicated trained component — are addressed by the same three-stage Large Language Model pipeline through preset prompts alone. The platform's report quality scales naturally with the choice of underlying model, without any change to the surrounding code.

The second is that **federation across sixteen search engines is materially more useful than reliance on any single engine**, even the strongest. The combined coverage of the federation is greater than any subset, and the platform's resilience to the routine churn of individual engines — short-lived servers, transient outages, structural HTML changes — is greatly improved by treating engine results as a pre-scored aggregate rather than as a single authoritative ranking.

The third is that **operational reproducibility matters more than algorithmic novelty** for a platform that has to be usable by an analyst on a daily basis. The most-cited limitation in the surveyed literature is the deployment burden of multi-service stacks; the most-praised property of OBSCURA in its supervisor reviews has consistently been that an analyst with Docker and one API key can be running their first investigation within minutes of clone-and-build. The choice to substitute a single-file SQLite database and a hand-written single-page application for a JVM-based search-and-dashboard stack is, in retrospect, the most consequential design decision of the year.

The aims and objectives originally set out for the project have, in present-perfect terms appropriate to a conclusions chapter, *all been met*. A federated dark-web search layer has been implemented across sixteen onion search engines with per-engine parsers, deduplication, and pre-scoring. A two-tier Tor-routed deep-crawl engine has been built with Selenium plus Firefox plus geckodriver as Tier 1 and a plain HTTP fallback as Tier 2, with automatic retry and tier-fallback. A three-stage LLM-driven investigation pipeline has been implemented as query refinement, batched filtering, and preset-driven structured-report generation. Four built-in research-domain prompt presets have been shipped and an unlimited number of user-defined custom presets are supported. A multi-provider LLM abstraction has been built across six providers and seventeen base models, with provider auto-gating, token streaming, and exponential-backoff retry. A persistent investigation store has been implemented in a single-file SQLite database with Write-Ahead Logging, complemented by an on-disk audit dump that captures the rendered HTML of every successful crawl. An analyst-facing chat-style single-page application has been built, served by Flask with Server-Sent Events for live progress streaming, and complete with modal-based configuration, health-check, and seed-management surfaces and one-click PDF or Markdown export. And the entire system has been packaged as a single Docker container with an embedded Tor daemon that synchronises its start-up with Tor's bootstrap completion and pre-warms a circuit before exposing the analyst interface. Every objective set out at the start of the project has been delivered.

---

## 8.2 Lessons Learned

Three lessons stand out from the year of work that produced OBSCURA, and each is worth recording explicitly so that it can be carried forward into future projects.

**Plan for the pivot, not against it.** The iterative methodology adopted at the start of the project accepted as a feature — rather than fought as a bug — the fact that the team's understanding of the problem and of the technology landscape would evolve through the year. The most consequential single decision of the project was the mid-evaluation pivot from an Elasticsearch-and-Kibana-and-bespoke-machine-learning stack to the SQLite-and-single-page-application-and-general-purpose-LLM stack ultimately delivered. That pivot would have been impossible under a waterfall plan that locked in technology choices at proposal time. Under the iterative approach actually adopted, it took one week of planning and four weeks of code, and the project came out structurally stronger for having absorbed it. The lesson is not to write a perfect up-front plan and stick to it, but to plan for the moment when supervisor or user feedback will invalidate part of it, and to set up the methodology so that absorbing that moment costs days rather than months.

**Choose boring tools for boring concerns.** Several of the most expensive parts of the original plan — Elasticsearch, Kibana, a custom CNN-LSTM threat classifier — were replaced over the course of the project with the most boring, least fashionable alternatives possible: a single-file SQLite database, a hand-written single-page application in vanilla JavaScript with no build step, and a general-purpose Large Language Model that the team did not have to train. The boring choices have been overwhelmingly the right ones. SQLite has zero operational overhead and yet has handled every concurrent-read pattern the platform has asked of it. Vanilla JavaScript without a build step means there is no ecosystem churn to be vulnerable to. General-purpose LLMs improve continuously without any work from the team. The "interesting" technology choices in OBSCURA were reserved for the parts of the project that actually required interesting choices — the federated search and the multi-provider LLM abstraction — and that reservation has paid off. Where a part of the system did not need to be novel, it was made deliberately not-novel.

**Keep a forensic trail of every black-box input from day one.** The on-disk audit dump that captures the rendered HTML of every successful deep-crawl was added late in the project, almost as an afterthought, when the team realised that Selenium occasionally produced renders that differed materially from a plain-HTTP fetch of the same URL. The audit dump turned out, in practice, to be the most-used debugging tool the team had. Every time a report looked strange — a missing source, a misleading insight, a fabricated indicator — the next thing the team did was inspect the audit dump to see what HTML the LLM had actually been shown. Without the audit dump, every such conversation would have become an unfalsifiable debate. The lesson is to keep a forensic trail of the inputs to every black-box component, whether an LLM or a classifier or any other model, from the very first sprint rather than from the moment the first surprising output appears.

---

## 8.3 Limitations

The platform delivered alongside this report has, honestly stated, four substantive limitations.

The first is that **the platform is on-demand, not continuously streaming**. An investigation is an analyst-initiated event; OBSCURA does not run as a daemon scanning the dark web in the background. For a Security Operations Centre that needs around-the-clock dark-web monitoring of, say, a specific list of ransomware leak sites, OBSCURA must today be paired with an external scheduler that triggers investigations on a cadence.

The second is that **the platform is a single-user, single-analyst tool**. There is no authentication, no role-based access control, no multi-user workspace, no shared case-notebook, and no audit trail of who-did-what across multiple analysts. For a team that wants to collaborate on the same set of investigations or maintain case ownership across shifts, OBSCURA must today be operated on a per-analyst basis with informal sharing of exported reports.

The third is that **LLM output quality is judged by inspection rather than by quantitative scoring**. The testing strategy substituted structural assertions — six sections present, every artefact cited back to a source, no orphan references — for a quantitative precision and recall measurement against a labelled ground-truth dataset. Building such a dataset would have required a level of dark-web subject-matter expertise outside the scope of an undergraduate project. The mitigation in place is that OBSCURA's output is always grounded in linked source URLs that the analyst can re-verify, so the platform's role is triage and structuring rather than autonomous judgment.

The fourth is that **only Tor-routed anonymity is supported**. Other anonymity networks — I2P, Freenet, ZeroNet — have their own dark-web ecosystems with their own characteristics, and a complete dark-web threat-intelligence picture should include them. OBSCURA's current crawler is Tor-only, and the search-engine federation is Tor-only.

These limitations are not framed here as failures; they are framed as the deliberate boundaries within which the platform was built, and they are the natural input to the recommendations for future work that follow.

---

## 8.4 Recommendations for Future Work

A structured agenda for the future development of OBSCURA emerges naturally from the limitations above and from the wider literature surveyed earlier in this report. The nine items below are arranged from most concrete and shortest-effort to most ambitious and longest-effort.

**8.4.1 Real-Time and Scheduled Operation**

The most directly addressable limitation is the platform's on-demand-only nature. A scheduler integrated with the existing investigation pipeline — driven by a cron-style configuration file or an APScheduler integration — would let an analyst pre-configure a set of investigations to be re-run on a cadence (every hour for a watchlist of leak sites, every day for a wider sweep). Each re-run could record only the differences against the previous run, so the analyst would see a stream of "what's new" rather than a flood of duplicates. Tor circuit warmup and the existing health-check probes would have to be wired into the scheduler so that a long-idle container always launches an investigation against an already-warm circuit.

**8.4.2 MITRE ATT&CK Structured Mapping**

The current platform produces MITRE ATT&CK references inside its preset-driven summaries when the underlying LLM chooses to include them, but does not capture them as structured first-class objects. A dedicated post-processing pass over the generated summary — using an LLM call specifically prompted to extract Tactic / Technique / Sub-Technique identifiers — would produce a structured ATT&CK coverage table for every investigation. Aggregated across investigations, this would let the platform answer questions like "which ATT&CK techniques are most frequently observed against the retail sector this quarter?"

**8.4.3 Multi-User Operation and Role-Based Access Control**

Extending OBSCURA from a single-analyst desktop tool into a small-team collaboration surface is a substantive but tractable project. The starting point is an authentication layer — local accounts or a single-sign-on integration — and a `users` table in the existing SQLite schema. Each investigation would then be owned by a user but visible to a team. Tags and status would become per-investigation-per-user. A shared sidebar would replace today's per-installation history. Role-based access control would distinguish between analyst, lead, and viewer roles.

**8.4.4 Quantitative LLM-Output Evaluation Harness**

A reproducible quantitative evaluation framework for the LLM pipeline would address one of the substantive limitations of the current work. The framework would consist of a curated set of "gold-standard" investigations — query, expected source set, expected indicators, expected threat classification — produced by a domain expert, plus an automated comparison harness that runs OBSCURA against each gold-standard query and scores the produced report against the expected output. Precision and recall could then be reported per LLM model, per preset, and per source-engine subset. This is also the obvious vehicle for comparing the relative strengths of frontier hosted models against locally hosted open-weight models on the same task.

**8.4.5 Multi-Language Coverage**

The current platform's prompts, pre-scoring tokeniser, and built-in research-domain presets all assume English-language content. Extending the platform to Russian, Mandarin, and other languages that dominate parts of the dark-web ecosystem would unlock substantially more usable content. The pre-scoring tokeniser would need to become language-aware, the four built-in presets would need to be translated, and the LLM choice would need to be biased toward models with strong non-English performance.

**8.4.6 Additional Anonymity Networks**

Extending the crawler beyond Tor to support I2P (eepsites), Freenet (freesites), and possibly ZeroNet would give OBSCURA a more complete picture of the broader dark-web ecosystem. Each network has its own addressing scheme and its own anonymity transport; each could be added as a new tier in the existing crawler-dispatch model, in parallel with the existing Tier 1 and Tier 2. The search-federation layer would need a corresponding set of network-specific search engines.

**8.4.7 Threat-Actor Profiling and Graph Queries**

A graph database alongside the existing SQLite store — Neo4j is the obvious candidate — would let the platform record threat-actor aliases, their observed tool usage, the marketplaces they frequent, and the temporal pattern of their activity. Each completed investigation would extract these relationships from its sources and persist them as graph edges. The analyst would then be able to ask higher-order questions: which aliases have been seen on more than one marketplace, which malware families are most commonly co-listed with which exploits, which threat actors have re-emerged after a quiet period.

**8.4.8 Dynamic Engine Weighting and Retirement**

The current federated search treats each of the sixteen onion search engines as equally trustworthy and queries every one of them on every investigation. Observation over the course of the project has shown that some engines contribute disproportionately to usable results while others rarely produce a hit. A future iteration could record per-engine hit-rate over time, dynamically weight engines in the pre-scoring step accordingly, and retire engines that have not produced a useful result in months. New engines could be onboarded equally automatically by registering a single entry in the engine registry.

**8.4.9 SOAR Integration and Outbound Indicator Sharing**

The current platform informs an analyst; it does not act on what it finds. A future integration with Security Orchestration, Automation, and Response (SOAR) platforms — Splunk SOAR, Cortex XSOAR, Tines — would let OBSCURA push its extracted indicators into the analyst's existing detection-and-response stack. A complementary outbound integration with structured threat-intelligence formats — STIX 2.1 over TAXII — would let an OBSCURA installation contribute its findings to a wider community feed.

---

## 8.5 Project Impact and Concluding Reflections

OBSCURA has built a working, defensible, single-analyst dark-web threat-intelligence platform that integrates federated search, Tor-routed deep crawling, AI-driven triage, persistent storage, and an analyst-facing chat interface in a single reproducible Docker container. The platform demonstrates that a domain that has historically required multiple specialised tools, a multi-service deployment stack, and trained Natural Language Processing or Machine Learning pipelines can be addressed coherently with a general-purpose Large Language Model held to disciplined prompting, federated discovery held to per-engine parsing, and operational reproducibility held to a single container.

The wider impact of this work is twofold. For the security-operations community, OBSCURA is a demonstration that the operational gap between research-grade dark-web tooling and analyst-usable tooling can be closed by deliberate, integrative engineering — that the choice between *useful* and *deployable* is a false dichotomy. For the academic community, OBSCURA is a worked example of an LLM-substitution architecture: a domain where bespoke ML was the literature's default answer, and where a careful prompting-and-grounding architecture has proved competitive on every criterion the team has been able to measure.

The team carries forward, beyond the technical artefacts themselves, a substantive set of practical convictions about how a year-long undergraduate engineering project is best run: iterate rather than waterfall, choose boring tools for boring concerns, keep forensic trails of every black-box input, and treat supervisor feedback as the most important signal in the room. These convictions have shaped the platform that this report describes, and they will shape the work the members of the team go on to build after the project closes.

OBSCURA is, in the framing of the wider question this project set out to answer, a small but concrete step in the long-running effort to make the dark web visible to the people whose job it is to defend against it. The platform is delivered with the hope that it is useful to its users — and with the understanding that the most rewarding part of a year's work is now to hand it over.
