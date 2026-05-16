"""Generate the SDLC Diagram SVG for OBSCURA.

Models an iterative / agile-style software development life cycle as a
six-phase clockwise cycle. Inner ring shows the per-phase activities;
outer annotations show the concrete deliverables for each phase.
"""
from pathlib import Path
import math
from _svg_lib import (
    PALETTE, svg_doc, rect, text, labeled_box, line, path, annotate,
    legend, multiline,
)
import html

W, H = 1900, 1200


def build() -> str:
    out: list[str] = []

    cx, cy = 950, 620
    r = 340                  # radius of phase-box centers
    box_w, box_h = 280, 130

    # ---------- Central hub ----------
    out.append(f'<circle cx="{cx}" cy="{cy}" r="118" '
               f'fill="{PALETTE["accent_soft"]}" stroke="{PALETTE["accent"]}" '
               f'stroke-width="1.6"/>')
    out.append(text(cx, cy - 10, "OBSCURA", cls="label-l"))
    out.append(text(cx, cy + 14, "Agile / Iterative", cls="label-sm"))
    out.append(text(cx, cy + 34, "SDLC", cls="label-sm"))

    # ---------- Phase boxes at 6 angles around the hub ----------
    # Math angles (degrees), 0°=right, increasing counter-clockwise.
    # Clockwise sequence starting at the top: 90, 30, -30, -90, -150, 150.
    phases = [
        ("90",  "1. Plan & Requirements",
                "• FYP brief & supervisor goals\n• Mid-eval scope & literature review\n• Functional + non-functional reqs",
                PALETTE["actor_fill"], PALETTE["actor_border"]),
        ("30",  "2. System Design",
                "• Use-case / Sequence / Activity UML\n• ERD: investigations, sources, seeds\n• Tech-stack decisions (Flask, SQLite, LangChain, Tor)",
                PALETTE["usecase_fill"], PALETTE["usecase_border"]),
        ("-30", "3. Implementation",
                "• crawler.py (Tier-1/Tier-2)\n• search.py + 16 onion engines\n• LangChain pipeline + 4 preset prompts\n• Flask API + SPA chat UI",
                PALETTE["internal_fill"], PALETTE["internal_border"]),
        ("-90", "4. Integration & Testing",
                "• End-to-end investigation smoke tests\n• Health checks: Tor, LLM, search engines\n• Tier-fallback validation\n• Re-summarize / Deep-Crawl regression",
                PALETTE["process_fill"], PALETTE["process_border"]),
        ("-150","5. Deployment & Hardening",
                "• Dockerfile + embedded Tor daemon\n• entrypoint.sh — wait Tor bootstrap, pre-warm\n• PDF/MD export, retry & backoff\n• Runtime tier reporting",
                PALETTE["datastore_fill"], PALETTE["datastore_border"]),
        ("150", "6. Review & Iteration",
                "• Supervisor demos & feedback\n• Mid-evaluation deliverable\n• Bug fixes, polish, prompt-engineering tweaks\n• Loop back into Plan for next sprint",
                PALETTE["external_fill"], PALETTE["external_border"]),
    ]

    phase_centers = []
    for ang_str, name, deliverables, fill, stroke in phases:
        ang_deg = float(ang_str)
        ang = math.radians(ang_deg)
        px = cx + r * math.cos(ang)
        py = cy - r * math.sin(ang)
        out.append(rect(px - box_w / 2, py - box_h / 2, box_w, box_h,
                        fill=fill, stroke=stroke, rx=12, sw=1.6,
                        shadow=True))
        # Phase title
        out.append(f'<text x="{px}" y="{py - box_h/2 + 28}" class="label-l" '
                   f'text-anchor="middle">{html.escape(name)}</text>')
        # Deliverable bullets
        del_lines = deliverables.split("\n")
        start = py - box_h / 2 + 50
        for i, ln in enumerate(del_lines):
            out.append(f'<text x="{px - box_w/2 + 14}" y="{start + i * 16}" '
                       f'class="legend-b" text-anchor="start">'
                       f'{html.escape(ln)}</text>')
        phase_centers.append((px, py, name))

    # ---------- Clockwise arrows between consecutive phases ----------
    for i in range(len(phase_centers)):
        x1, y1, _ = phase_centers[i]
        x2, y2, _ = phase_centers[(i + 1) % len(phase_centers)]
        # Move endpoints inward toward neighboring box edges
        dx, dy = x2 - x1, y2 - y1
        dist = math.hypot(dx, dy)
        ux, uy = dx / dist, dy / dist
        # Start just outside source box and end just before target box
        sx, sy = x1 + ux * (box_w / 2 + 6), y1 + uy * (box_h / 2 + 6)
        ex, ey = x2 - ux * (box_w / 2 + 6), y2 - uy * (box_h / 2 + 6)
        # Curve outward away from the center for visual clarity
        midx, midy = (sx + ex) / 2, (sy + ey) / 2
        outward = ((midx - cx), (midy - cy))
        olen = math.hypot(*outward) or 1
        bend = 38
        cxp = midx + outward[0] / olen * bend
        cyp = midy + outward[1] / olen * bend
        out.append(path(f"M {sx} {sy} Q {cxp} {cyp}, {ex} {ey}",
                        stroke=PALETTE["accent"], sw=2, marker="arrow-red"))

    # ---------- Iteration / feedback inner loop ----------
    out.append(path(f"M {cx - 60} {cy + 75} A 60 60 0 1 0 {cx + 60} {cy + 75}",
                    stroke=PALETTE["body"], sw=1.4, dash="5,4",
                    marker="arrow"))
    out.append(annotate(cx, cy + 100, "continuous feedback", anchor="middle"))

    # ---------- Timeline strip below the cycle ----------
    tl_y = 1010
    out.append(text(40, tl_y, "Project Timeline (project-level milestones)",
                    cls="legend-t"))
    out.append(line(40, tl_y + 18, W - 40, tl_y + 18,
                    stroke=PALETTE["border_d"], sw=2))
    milestones = [
        (120,  "Proposal\n(2024-Oct)"),
        (380,  "Architecture\n& UML drafts"),
        (640,  "Mid-Evaluation\n(2025-Mid)"),
        (920,  "Multi-LLM &\nFrontend SPA"),
        (1180, "Selenium Tier-1\n+ Docker"),
        (1440, "Final Eval\n(2026)"),
    ]
    for x, lbl in milestones:
        out.append(f'<circle cx="{x}" cy="{tl_y + 18}" r="7" '
                   f'fill="{PALETTE["accent"]}" stroke="{PALETTE["bg"]}" '
                   f'stroke-width="2"/>')
        for i, ln in enumerate(lbl.split("\n")):
            out.append(f'<text x="{x}" y="{tl_y + 50 + i * 16}" '
                       f'class="label-sm" text-anchor="middle">'
                       f'{html.escape(ln)}</text>')

    # ---------- Legend ----------
    leg_items = [
        ("rect", PALETTE["accent_soft"], PALETTE["accent"], "Project hub"),
        ("rect", PALETTE["usecase_fill"], PALETTE["usecase_border"], "SDLC phase"),
        ("line-solid", "", PALETTE["accent"], "Phase progression (clockwise)"),
        ("line-dash", "", PALETTE["body"], "Continuous feedback loop"),
    ]
    out.append(legend(40, 130, leg_items, title="Notation", w=260))

    body = "\n  ".join(out)
    return svg_doc(W, H, "Figure 4.5 — SDLC Diagram",
                   "Iterative agile SDLC adopted for OBSCURA",
                   "  " + body)


def main():
    svg = build()
    out_path = Path(__file__).with_name("05-sdlc-diagram.svg")
    out_path.write_text(svg, encoding="utf-8")
    print(f"OK: wrote {out_path} ({len(svg):,} chars)")


if __name__ == "__main__":
    main()
