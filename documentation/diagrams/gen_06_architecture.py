"""Generate the Architectural Diagram SVG for OBSCURA.

A layered architecture showing the five application tiers, the LLM
abstraction with its six providers, the Tor-based infrastructure, and the
external systems OBSCURA depends on.
"""
from pathlib import Path
from _svg_lib import (
    PALETTE, svg_doc, rect, text, labeled_box, line, path, annotate, legend,
    multiline,
)
import html

W, H = 1900, 1400


def build() -> str:
    out: list[str] = []

    # ---------- Inner-area frame for the OBSCURA system ----------
    sys_x, sys_y, sys_w, sys_h = 130, 150, 1180, 1160
    out.append(rect(sys_x, sys_y, sys_w, sys_h,
                    fill=PALETTE["bg"], stroke=PALETTE["ink"],
                    rx=18, sw=1.8, shadow=True))
    out.append(f'<text x="{sys_x + 24}" y="{sys_y + 30}" class="label-l" '
               f'text-anchor="start">OBSCURA — local desktop deployment</text>')
    out.append(annotate(sys_x + 24, sys_y + 48,
                        "Docker container · Tor daemon embedded · single-analyst workstation",
                        anchor="start"))

    # ---------- Helper: full-width layer band ----------
    def layer(x, y, w, h, title, fill, stroke, *, subtitle=""):
        out.append(rect(x, y, w, h, fill=fill, stroke=stroke,
                        rx=10, sw=1.4, shadow=False))
        out.append(f'<text x="{x + 14}" y="{y + 22}" class="label-l" '
                   f'text-anchor="start">{html.escape(title)}</text>')
        if subtitle:
            out.append(f'<text x="{x + 14}" y="{y + 40}" class="legend-b" '
                       f'text-anchor="start">{html.escape(subtitle)}</text>')

    def component(x, y, w, h, name, details, fill, stroke,
                  detail_cls="legend-b"):
        out.append(rect(x, y, w, h, fill=fill, stroke=stroke, rx=8, sw=1.2,
                        shadow=True))
        out.append(f'<text x="{x + w/2}" y="{y + 22}" class="label" '
                   f'text-anchor="middle">{html.escape(name)}</text>')
        for i, ln in enumerate(details):
            out.append(f'<text x="{x + 10}" y="{y + 42 + i * 14}" '
                       f'class="{detail_cls}" text-anchor="start">'
                       f'{html.escape("• " + ln)}</text>')

    # Layer geometry — generous internal padding so component bullets fit
    LX = sys_x + 24
    LW = sys_w - 48

    # ---------- LAYER 1 — Presentation ----------
    L1y = sys_y + 90
    layer(LX, L1y, LW, 130,
          "1. Presentation Layer", PALETTE["actor_fill"], PALETTE["actor_border"],
          subtitle="single-page application served by Flask")
    comp_w = (LW - 60) / 3
    for i, (name, det) in enumerate([
        ("Browser SPA",
         ["index.html · script.js · styles.css",
          "Chat UI, light/dark theme, modals"]),
        ("SSE Streaming Reader",
         ["Live pipeline status events",
          "AbortController-based cancel"]),
        ("Local State + Persistence",
         ["localStorage: theme, sidebar",
          "in-memory: investigations, seeds, presets"]),
    ]):
        component(LX + 15 + i * (comp_w + 15), L1y + 56,
                  comp_w, 64, name, det,
                  PALETTE["bg"], PALETTE["actor_border"])

    # ---------- LAYER 2 — API / Transport ----------
    L2y = L1y + 150
    layer(LX, L2y, LW, 110,
          "2. API Layer", PALETTE["usecase_fill"], PALETTE["usecase_border"],
          subtitle="Flask routes — REST + Server-Sent Events")
    api_endpoints = [
        "GET /api/models, /api/providers, /api/presets",
        "GET/POST/DELETE /api/investigations[…]",
        "POST /api/investigate  (SSE stream)",
        "GET/POST/DELETE /api/seeds[…]",
        "POST /api/health/{llm,search}",
        "POST /api/export/pdf",
    ]
    for i, ep in enumerate(api_endpoints):
        col = i % 3
        row = i // 3
        ex = LX + 24 + col * (LW / 3)
        ey = L2y + 56 + row * 24
        out.append(f'<text x="{ex}" y="{ey}" class="mono" '
                   f'text-anchor="start">{html.escape(ep)}</text>')

    # ---------- LAYER 3 — Service / Domain ----------
    L3y = L2y + 130
    layer(LX, L3y, LW, 200,
          "3. Service Layer", PALETTE["internal_fill"], PALETTE["internal_border"],
          subtitle="orchestration of every business operation")
    svc_specs = [
        ("Investigation Pipeline",
         ["refine_query", "filter_results", "generate_summary",
          "SSE progress events"]),
        ("Deep-Crawl Engine",
         ["Tier 1: Selenium+Firefox", "Tier 2: requests+SOCKS5",
          "retry + tier fallback", "block / CAPTCHA detection"]),
        ("Seed Manager",
         ["add_seed → background thread",
          "mark_crawled / mark_loaded", "auto-crawl on add"]),
        ("Health Service",
         ["check_tor_proxy", "check_llm_health",
          "ping 16 search engines"]),
        ("Export Service",
         ["reportlab Platypus",
          "MD → PDF (tables, lists, headings)"]),
    ]
    svc_w = (LW - 90) / 5
    for i, (name, det) in enumerate(svc_specs):
        component(LX + 18 + i * (svc_w + 18), L3y + 60,
                  svc_w, 130, name, det,
                  PALETTE["bg"], PALETTE["internal_border"])

    # ---------- LAYER 4 — LLM Abstraction ----------
    L4y = L3y + 220
    layer(LX, L4y, LW, 140,
          "4. LLM Abstraction Layer",
          PALETTE["process_fill"], PALETTE["process_border"],
          subtitle="LangChain · streaming · exponential-backoff retry · provider auto-gating")
    providers = [
        ("OpenAI",    "GPT-4.1, GPT-5.x"),
        ("Anthropic", "Claude Sonnet 4.x"),
        ("Google",    "Gemini 2.5 Flash/Pro"),
        ("OpenRouter","Qwen, Grok, gpt-oss…"),
        ("Ollama",    "(local discovery)"),
        ("llama.cpp", "(local discovery)"),
    ]
    prov_w = (LW - 90) / 6
    for i, (name, sub) in enumerate(providers):
        component(LX + 18 + i * (prov_w + 12), L4y + 60,
                  prov_w, 74, name, [sub],
                  PALETTE["bg"], PALETTE["process_border"])

    # ---------- LAYER 5 — Data ----------
    L5y = L4y + 160
    layer(LX, L5y, LW, 120,
          "5. Data Layer", PALETTE["datastore_fill"], PALETTE["datastore_border"],
          subtitle="single-file SQLite + filesystem audit dump")
    data_specs = [
        ("SQLite — obscura.db",
         ["4 tables: investigations · sources · seeds · custom_presets · WAL"]),
        ("Filesystem Audit",
         ["investigations/crawled/<sha256>/{rendered.html, tier.txt}"]),
        ("Migration Layer",
         ["one-time JSON → SQLite import on first run"]),
    ]
    dw = (LW - 60) / 3
    for i, (name, det) in enumerate(data_specs):
        component(LX + 15 + i * (dw + 15), L5y + 56,
                  dw, 56, name, det,
                  PALETTE["bg"], PALETTE["datastore_border"])

    # ---------- Infrastructure side rail (right of system box) ----------
    inf_x = sys_x + sys_w + 30
    out.append(rect(inf_x, sys_y + 30, 230, 240,
                    fill=PALETTE["accent_soft"], stroke=PALETTE["accent"],
                    rx=12, sw=1.4, shadow=True))
    out.append(f'<text x="{inf_x + 18}" y="{sys_y + 58}" class="label-l" '
               f'text-anchor="start">Infrastructure</text>')
    notes = [
        "Tor daemon (embedded)",
        "SOCKS5 → 127.0.0.1:9150",
        "Control → 127.0.0.1:9151",
        "NEWNYM circuit refresh",
        "Docker container",
        "entrypoint.sh waits for",
        "Bootstrapped 100%",
    ]
    for i, ln in enumerate(notes):
        out.append(f'<text x="{inf_x + 18}" y="{sys_y + 88 + i * 22}" '
                   f'class="legend-b" text-anchor="start">'
                   f'{html.escape("• " + ln)}</text>')

    # ---------- External services on the right ----------
    ext_x = inf_x
    out.append(f'<text x="{ext_x}" y="{sys_y + 300}" class="label-l">'
               f'External Services</text>')
    externals = [
        ("16 Dark-Web Search\nEngines",
         "Ahmia, Tor66, OnionLand,\nExcavator, Find Tor, … (×11)"),
        (".onion Sites\n(target sources)",
         "JS-rendered via Tier 1\nplain HTML via Tier 2"),
        ("Cloud LLM APIs",
         "OpenAI · Anthropic ·\nGoogle · OpenRouter"),
        ("Local LLM Runtimes",
         "Ollama (HTTP API) /\nllama.cpp (OpenAI-compat)"),
    ]
    for i, (name, sub) in enumerate(externals):
        ey = sys_y + 320 + i * 150
        out.append(rect(ext_x, ey, 230, 130,
                        fill=PALETTE["external_fill"],
                        stroke=PALETTE["external_border"],
                        rx=10, sw=1.4, shadow=True))
        for j, ln in enumerate(name.split("\n")):
            out.append(f'<text x="{ext_x + 115}" y="{ey + 30 + j * 18}" '
                       f'class="label" text-anchor="middle">'
                       f'{html.escape(ln)}</text>')
        for j, ln in enumerate(sub.split("\n")):
            out.append(f'<text x="{ext_x + 115}" y="{ey + 80 + j * 16}" '
                       f'class="legend-b" text-anchor="middle">'
                       f'{html.escape(ln)}</text>')

    # ---------- Layer-to-layer arrows (HTTP/SSE on the inner-left margin) ----------
    arrow_x = LX - 6
    layer_y = [(L1y, L1y + 130), (L2y, L2y + 110), (L3y, L3y + 200),
               (L4y, L4y + 140), (L5y, L5y + 120)]
    for i in range(len(layer_y) - 1):
        out.append(line(arrow_x, layer_y[i][1] + 4,
                        arrow_x, layer_y[i + 1][0] - 4,
                        stroke=PALETTE["accent"], sw=1.6, marker="arrow-red"))

    # ---------- Cross-cutting connections to external services ----------
    # Draw clean horizontal arrows from the right edge of the system box to
    # the left edge of each external service card, labelled with the protocol.
    def cross_arrow(src_layer_y_top, src_layer_h, ext_idx, label):
        sy = src_layer_y_top + src_layer_h / 2
        ey = sys_y + 320 + ext_idx * 150 + 65
        sx = sys_x + sys_w
        tx = ext_x
        midx = (sx + tx) / 2
        out.append(path(f"M {sx} {sy} C {sx + 18} {sy}, {tx - 18} {ey}, {tx} {ey}",
                        stroke=PALETTE["body"], sw=1.4, marker="arrow"))
        out.append(annotate(midx, (sy + ey) / 2 - 6, label, anchor="middle"))

    cross_arrow(L3y, 200, 0, "search via Tor SOCKS5")   # → Search Engines
    cross_arrow(L3y, 200, 1, "crawl via Tor SOCKS5")    # → .onion Sites
    cross_arrow(L4y, 140, 2, "HTTPS")                   # → Cloud LLMs
    cross_arrow(L4y, 140, 3, "HTTP localhost")          # → Local LLMs

    # ---------- User actor on the left (centred next to Layer 1) ----------
    user_x = 70
    user_y = L1y + 70
    out.append(f'<circle cx="{user_x}" cy="{user_y}" r="14" fill="{PALETTE["bg"]}" '
               f'stroke="{PALETTE["accent"]}" stroke-width="2.2"/>')
    out.append(f'<line x1="{user_x}" y1="{user_y + 14}" x2="{user_x}" '
               f'y2="{user_y + 56}" stroke="{PALETTE["accent"]}" stroke-width="2.2"/>')
    out.append(f'<line x1="{user_x - 20}" y1="{user_y + 26}" '
               f'x2="{user_x + 20}" y2="{user_y + 26}" '
               f'stroke="{PALETTE["accent"]}" stroke-width="2.2"/>')
    out.append(f'<line x1="{user_x}" y1="{user_y + 56}" '
               f'x2="{user_x - 14}" y2="{user_y + 80}" '
               f'stroke="{PALETTE["accent"]}" stroke-width="2.2"/>')
    out.append(f'<line x1="{user_x}" y1="{user_y + 56}" '
               f'x2="{user_x + 14}" y2="{user_y + 80}" '
               f'stroke="{PALETTE["accent"]}" stroke-width="2.2"/>')
    out.append(f'<text x="{user_x}" y="{user_y + 102}" class="label-sm" '
               f'text-anchor="middle">Security</text>')
    out.append(f'<text x="{user_x}" y="{user_y + 116}" class="label-sm" '
               f'text-anchor="middle">Analyst</text>')
    out.append(line(user_x + 20, user_y + 26, sys_x, user_y + 26,
                    stroke=PALETTE["accent"], sw=1.8, marker="arrow-red"))

    # ---------- Legend ----------
    leg_items = [
        ("rect", PALETTE["actor_fill"],   PALETTE["actor_border"],   "Presentation"),
        ("rect", PALETTE["usecase_fill"], PALETTE["usecase_border"], "API / transport"),
        ("rect", PALETTE["internal_fill"],PALETTE["internal_border"],"Service / domain"),
        ("rect", PALETTE["process_fill"], PALETTE["process_border"], "LLM abstraction"),
        ("rect", PALETTE["datastore_fill"],PALETTE["datastore_border"],"Data"),
        ("rect", PALETTE["external_fill"],PALETTE["external_border"], "External service"),
        ("line-solid", "", PALETTE["accent"], "Intra-layer / synchronous"),
        ("line-solid", "", PALETTE["body"],   "Cross-cutting / via Tor"),
    ]
    out.append(legend(inf_x, sys_y + 970, leg_items,
                      title="Layer Notation", w=230))

    body = "\n  ".join(out)
    return svg_doc(W, H, "Figure 4.6 — Architectural Diagram",
                   "Layered architecture of the OBSCURA system",
                   "  " + body)


def main():
    svg = build()
    out_path = Path(__file__).with_name("06-architectural-diagram.svg")
    out_path.write_text(svg, encoding="utf-8")
    print(f"OK: wrote {out_path} ({len(svg):,} chars)")


if __name__ == "__main__":
    main()
