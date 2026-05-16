"""Generate the Use-Case Diagram SVG for OBSCURA."""
from pathlib import Path
from _svg_lib import (
    PALETTE, svg_doc, rect, text, multiline, labeled_box,
    ellipse, line, path, actor_stick, system_actor,
    annotate, legend,
)

W, H = 1800, 1300


def build() -> str:
    out: list[str] = []

    # ---------- Primary actor (Security Analyst) on the LEFT ----------
    analyst_x, analyst_y = 110, 600
    out.append(actor_stick(analyst_x, analyst_y, "Security Analyst\n(Primary User)",
                           color=PALETTE["accent"], scale=1.4))

    # ---------- System boundary ----------
    box_x, box_y, box_w, box_h = 280, 130, 1010, 1010
    out.append(rect(box_x, box_y, box_w, box_h,
                    fill=PALETTE["bg"], stroke=PALETTE["ink"],
                    rx=18, sw=1.6, shadow=True, dash=None))
    out.append(text(box_x + box_w / 2, box_y + 32,
                    "OBSCURA — Threat-Intelligence Automation Platform",
                    cls="label-l"))
    # Divider between primary and supporting use cases
    out.append(line(box_x + 30, 770, box_x + box_w - 30, 770,
                    stroke=PALETTE["border"], sw=1, dash="6,5"))
    out.append(text(box_x + box_w / 2, 800,
                    "Supporting (system-internal) use cases",
                    cls="stereotype"))

    # ---------- Primary use cases ----------
    UC_FILL, UC_STROKE = PALETTE["usecase_fill"], PALETTE["usecase_border"]
    primaries = [
        # (cx, cy, label)
        (540, 230, "Submit Investigation\nQuery"),
        (1040, 230, "Configure Model,\nProviders & Presets"),
        (540, 360, "View / Manage\nInvestigation History"),
        (1040, 360, "Run Health Checks"),
        (540, 490, "Manage Seed URLs"),
        (1040, 490, "Export Report\n(PDF / Markdown)"),
        (540, 620, "Trigger Deep-Crawl\non Investigation"),
        (1040, 620, "Re-summarize\nInvestigation"),
    ]
    uc_centers: dict[str, tuple[float, float]] = {}
    for cx, cy, lbl in primaries:
        out.append(ellipse(cx, cy, 165, 46, lbl, UC_FILL, UC_STROKE,
                           cls="label", line_height=15))
        uc_centers[lbl.replace("\n", " ")] = (cx, cy)

    # ---------- Supporting use cases (internal pipeline steps) ----------
    INT_FILL, INT_STROKE = PALETTE["internal_fill"], PALETTE["internal_border"]
    supporting = [
        (380, 880, "Refine Query"),
        (580, 880, "Federate\nSearch"),
        (780, 880, "Filter Search\nResults"),
        (980, 880, "Scrape Sources\nvia Tor"),
        (1180, 880, "Generate\nIntelligence Summary"),
    ]
    sup_centers: dict[str, tuple[float, float]] = {}
    for cx, cy, lbl in supporting:
        out.append(ellipse(cx, cy, 95, 38, lbl, INT_FILL, INT_STROKE,
                           cls="label-sm", line_height=13))
        sup_centers[lbl.replace("\n", " ")] = (cx, cy)

    # ---------- Supporting actors on the RIGHT ----------
    EXT_FILL, EXT_STROKE = PALETTE["external_fill"], PALETTE["external_border"]
    out.append(system_actor(1450, 200, 240, 80,
                            "LLM Service\n(LangChain · 6 providers)"))
    out.append(system_actor(1450, 380, 240, 80,
                            "Tor Network\n(SOCKS5 + ControlPort)"))
    out.append(system_actor(1450, 560, 240, 80,
                            "Dark-Web Search Engines\n(16 onion engines)"))
    out.append(system_actor(1450, 740, 240, 80,
                            ".onion Sites\n(target dark-web sources)"))

    # ---------- Associations: Analyst ↔ primary use cases ----------
    ax = analyst_x + 40   # right edge of actor
    ay = analyst_y - 10
    for label, (cx, cy) in uc_centers.items():
        out.append(line(ax, ay, cx - 165, cy,
                        stroke=PALETTE["body"], sw=1.3, arrow=False))

    # ---------- Right-side associations: external actors ↔ supporting UCs ----------
    # LLM Service ↔ Refine, Filter, Generate
    llm_x, llm_y = 1450, 240
    for lbl in ["Refine Query", "Filter Search Results", "Generate Intelligence Summary"]:
        cx, cy = sup_centers[lbl]
        out.append(line(cx + 95, cy, llm_x, llm_y,
                        stroke=PALETTE["body"], sw=1.2))
    # Tor Network ↔ Federate, Scrape
    tor_x, tor_y = 1450, 420
    for lbl in ["Federate Search", "Scrape Sources via Tor"]:
        cx, cy = sup_centers[lbl]
        out.append(line(cx + 95, cy, tor_x, tor_y,
                        stroke=PALETTE["body"], sw=1.2))
    # Search Engines ↔ Federate Search
    cx, cy = sup_centers["Federate Search"]
    out.append(line(cx + 95, cy + 8, 1450, 600,
                    stroke=PALETTE["body"], sw=1.2))
    # .onion Sites ↔ Scrape, Trigger Deep-Crawl
    cx, cy = sup_centers["Scrape Sources via Tor"]
    out.append(line(cx + 95, cy, 1450, 780,
                    stroke=PALETTE["body"], sw=1.2))
    cx, cy = uc_centers["Trigger Deep-Crawl on Investigation"]
    out.append(line(cx + 165, cy + 15, 1450, 760,
                    stroke=PALETTE["body"], sw=1.2))

    # ---------- «include» relationships (dashed open arrow) ----------
    def include(src_label_primary: str, dst_label_supporting: str,
                src_in_primary: bool = True):
        if src_in_primary:
            sx, sy = uc_centers[src_label_primary]
        else:
            sx, sy = sup_centers[src_label_primary]
        dx, dy = sup_centers[dst_label_supporting]
        out.append(line(sx, sy + 46, dx, dy - 38, stroke=PALETTE["muted"],
                        sw=1.2, dash="5,4", arrow_open=True))
        midx, midy = (sx + dx) / 2, (sy + 46 + dy - 38) / 2
        out.append(f'<text x="{midx}" y="{midy}" class="stereotype">'
                   f'«include»</text>')

    # Submit Investigation Query includes all 5 supporting use cases
    for sup in ["Refine Query", "Federate Search", "Filter Search Results",
                "Scrape Sources via Tor", "Generate Intelligence Summary"]:
        include("Submit Investigation Query", sup)
    # Re-summarize includes Generate Summary
    include("Re-summarize Investigation", "Generate Intelligence Summary")
    # Trigger Deep-Crawl includes Scrape Sources
    include("Trigger Deep-Crawl on Investigation", "Scrape Sources via Tor")

    # ---------- Legend (bottom-left, inside canvas margin) ----------
    leg_items = [
        ("actor",     "",                       PALETTE["accent"],          "Primary actor"),
        ("rect",      PALETTE["external_fill"], PALETTE["external_border"], "Supporting / external actor"),
        ("ellipse",   PALETTE["usecase_fill"],  PALETTE["usecase_border"],  "Primary use case (user-visible)"),
        ("ellipse",   PALETTE["internal_fill"], PALETTE["internal_border"], "Supporting use case (system-internal)"),
        ("line-solid","",                       PALETTE["body"],            "Association"),
        ("line-dash", "",                       PALETTE["muted"],           "«include» relationship"),
    ]
    out.append(legend(70, 1010, leg_items, title="Notation", w=270))

    body = "\n  ".join(out)
    return svg_doc(W, H, "Figure 4.1 — Use-Case Diagram",
                   "Actors and their interactions with OBSCURA",
                   "  " + body)


def main():
    svg = build()
    out_path = Path(__file__).with_name("01-use-case-diagram.svg")
    out_path.write_text(svg, encoding="utf-8")
    print(f"OK: wrote {out_path} ({len(svg):,} chars)")


if __name__ == "__main__":
    main()
