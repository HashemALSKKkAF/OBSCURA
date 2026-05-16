"""Generate the Activity Diagram SVG for OBSCURA.

Models the end-to-end activity flow of running and reviewing an investigation,
including parallel fork/join for federated search and source scraping, decision
branches for empty inputs / no-result paths, and post-completion analyst
actions (re-summarize, deep-crawl, export, status update).
"""
from pathlib import Path
from _svg_lib import (
    PALETTE, svg_doc, rect, text, labeled_box, line, path, diamond,
    terminator, annotate, legend,
)

W, H = 1700, 1900


def build() -> str:
    out: list[str] = []
    cx = 720  # center column for the main flow
    PFill, PStroke = PALETTE["process_fill"], PALETTE["process_border"]
    IOFill, IOStroke = PALETTE["io_fill"], PALETTE["io_border"]
    DSFill, DSStroke = PALETTE["datastore_fill"], PALETTE["datastore_border"]

    # ---------- Helpers local to this diagram ----------
    def act(x, y, w, h, lbl, fill=PFill, stroke=PStroke, rx=22, cls="label",
            line_height=15):
        out.append(labeled_box(x - w/2, y - h/2, w, h, lbl, fill=fill,
                               stroke=stroke, rx=rx, cls=cls,
                               line_height=line_height))

    def io(x, y, w, h, lbl):
        # Parallelogram (input/output)
        pts = f"{x - w/2 + 16},{y - h/2} {x + w/2},{y - h/2} " \
              f"{x + w/2 - 16},{y + h/2} {x - w/2},{y + h/2}"
        out.append(f'<polygon points="{pts}" fill="{IOFill}" stroke="{IOStroke}" '
                   f'stroke-width="1.4" filter="url(#soft)"/>')
        out.append(text(x, y + 5, lbl, cls="label"))

    def datastore(x, y, w, h, lbl):
        # Cylinder shape
        ry = 12
        out.append(f'<rect x="{x - w/2}" y="{y - h/2 + ry}" width="{w}" '
                   f'height="{h - ry * 2}" fill="{DSFill}" '
                   f'stroke="{DSStroke}" stroke-width="1.4"/>')
        out.append(f'<ellipse cx="{x}" cy="{y - h/2 + ry}" rx="{w/2}" ry="{ry}" '
                   f'fill="{DSFill}" stroke="{DSStroke}" stroke-width="1.4"/>')
        out.append(f'<ellipse cx="{x}" cy="{y + h/2 - ry}" rx="{w/2}" ry="{ry}" '
                   f'fill="{DSFill}" stroke="{DSStroke}" stroke-width="1.4"/>')
        out.append(text(x, y + 5, lbl, cls="label"))

    def fork_bar(y, x_from, x_to, lbl=None):
        out.append(f'<rect x="{x_from}" y="{y - 5}" width="{x_to - x_from}" '
                   f'height="10" fill="{PALETTE["terminator"]}"/>')
        if lbl:
            out.append(annotate(x_to + 8, y + 4, lbl))

    def arrow(x1, y1, x2, y2, label=None, side="left", color=None):
        color = color or PALETTE["body"]
        out.append(line(x1, y1, x2, y2, stroke=color, sw=1.4, marker="arrow"))
        if label:
            tx = (x1 + x2) / 2 + (10 if side == "right" else -10)
            ty = (y1 + y2) / 2 + 4
            anchor = "start" if side == "right" else "end"
            out.append(f'<text x="{tx}" y="{ty}" class="arrow-lbl" '
                       f'text-anchor="{anchor}">{label}</text>')

    # ---------- 1. Start ----------
    y = 130
    out.append(terminator(cx, y, 110, 40, "Start"))
    last_y = y + 20

    # ---------- 2. Analyst input ----------
    y = 200
    io(cx, y, 360, 50, "Analyst submits query, model & preset")
    arrow(cx, last_y, cx, y - 25)
    last_y = y + 25

    # ---------- 3. Decision: query empty? ----------
    y = 290
    diamond_w, diamond_h = 200, 90
    out.append(diamond(cx, y, diamond_w, diamond_h, "Query\nempty?"))
    arrow(cx, last_y, cx, y - diamond_h/2)
    # Yes branch (right) -> Show toast -> End
    tx = cx + 360
    out.append(labeled_box(tx - 110, y - 25, 220, 50,
                           "Show toast: \"Query is required\"",
                           fill=IOFill, stroke=IOStroke, rx=22, cls="label-sm",
                           line_height=13))
    arrow(cx + diamond_w/2, y, tx - 110, y, label="Yes", side="right")
    # End right
    out.append(terminator(tx, y + 130, 110, 40, "End"))
    arrow(tx, y + 25, tx, y + 110)
    last_y = y + diamond_h/2

    # ---------- 4. Refine query ----------
    y = 430
    act(cx, y, 420, 60, "LLM refines query (≤5 words, no operators)")
    arrow(cx, last_y, cx, y - 30, label="No", side="left")
    last_y = y + 30

    # ---------- 5. Decision: refine OK? ----------
    y = 540
    out.append(diamond(cx, y, diamond_w, 80, "Refine\nsucceeded?"))
    arrow(cx, last_y, cx, y - 40)
    # No branch (right) -> Fallback to raw query -> rejoin
    fx = cx + 360
    out.append(labeled_box(fx - 110, y - 25, 220, 50, "Fallback to raw query",
                           fill=PFill, stroke=PStroke, rx=22, cls="label-sm"))
    arrow(cx + diamond_w/2, y, fx - 110, y, label="No", side="right")
    arrow(fx, y + 25, fx, y + 65)
    arrow(fx, y + 65, cx, y + 65, label="rejoin", side="left")
    last_y = y + diamond_h/2

    # ---------- 6. Fork: federated search ----------
    y = 660
    fork_bar(y, 240, 1180, "fork")
    arrow(cx, last_y, cx, y - 8, label="Yes", side="left")
    # 3 parallel branches representing the 16-engine federation
    out.append(labeled_box(290, y + 20, 190, 50,
                           "Search Ahmia / Tor66\n(Tor SOCKS5)",
                           fill=PFill, stroke=PStroke, rx=22, cls="label-sm",
                           line_height=13))
    out.append(labeled_box(620, y + 20, 200, 50,
                           "Search OnionLand /\nExcavator / Find Tor / …",
                           fill=PFill, stroke=PStroke, rx=22, cls="label-sm",
                           line_height=13))
    out.append(labeled_box(980, y + 20, 190, 50,
                           "Search remaining\n11 onion engines",
                           fill=PFill, stroke=PStroke, rx=22, cls="label-sm",
                           line_height=13))
    arrow(385, y + 5, 385, y + 20)
    arrow(720, y + 5, 720, y + 20)
    arrow(1075, y + 5, 1075, y + 20)
    # Join bar
    fork_bar(y + 100, 240, 1180, "join")
    arrow(385, y + 45, 385, y + 92)
    arrow(720, y + 45, 720, y + 92)
    arrow(1075, y + 45, 1075, y + 92)
    last_y = y + 105

    # ---------- 7. Aggregate + dedupe + score ----------
    y = 820
    act(cx, y, 420, 60, "Aggregate, deduplicate by URL, pre-score by keyword overlap")
    arrow(cx, last_y, cx, y - 30)
    last_y = y + 30

    # ---------- 8. Decision: any results? ----------
    y = 925
    out.append(diamond(cx, y, diamond_w, 80, "Any\nresults?"))
    arrow(cx, last_y, cx, y - 40)
    # No -> emit 'no results' -> End (right side)
    rx = cx + 360
    out.append(labeled_box(rx - 120, y - 25, 240, 50,
                           "Emit \"no results\" SSE event",
                           fill=IOFill, stroke=IOStroke, rx=22, cls="label-sm"))
    arrow(cx + diamond_w/2, y, rx - 120, y, label="No", side="right")
    out.append(terminator(rx, y + 110, 110, 40, "End"))
    arrow(rx, y + 25, rx, y + 90)
    last_y = y + 40

    # ---------- 9. Filter loop ----------
    y = 1045
    act(cx, y, 460, 60,
        "LLM filter loop: batches of 25 → top-10 per batch (capped at top-20)",
        cls="label", line_height=14)
    arrow(cx, last_y, cx, y - 30, label="Yes", side="left")
    last_y = y + 30

    # ---------- 10. Fork: scrape sources ----------
    y = 1160
    fork_bar(y, 320, 1120, "fork (parallel scrape)")
    arrow(cx, last_y, cx, y - 8)
    out.append(labeled_box(360, y + 22, 200, 60,
                           "Tier 1: Selenium +\nFirefox via Tor SOCKS",
                           fill=PFill, stroke=PStroke, rx=22, cls="label-sm",
                           line_height=14))
    out.append(labeled_box(700, y + 22, 200, 60,
                           "Tier 2 fallback:\nrequests + SOCKS5",
                           fill=PFill, stroke=PStroke, rx=22, cls="label-sm",
                           line_height=14))
    out.append(labeled_box(1020, y + 22, 200, 60,
                           "Save audit dump:\nrendered.html / tier.txt",
                           fill=DSFill, stroke=DSStroke, rx=22, cls="label-sm",
                           line_height=14))
    arrow(460, y + 5, 460, y + 22)
    arrow(800, y + 5, 800, y + 22)
    arrow(1120, y + 5, 1120, y + 22)
    fork_bar(y + 110, 320, 1120, "join")
    arrow(460, y + 52, 460, y + 102)
    arrow(800, y + 52, 800, y + 102)
    arrow(1120, y + 52, 1120, y + 102)
    last_y = y + 115

    # ---------- 11. Extract text + LLM summary ----------
    y = 1330
    act(cx, y, 460, 60, "Strip HTML → plaintext → LLM generate_summary(preset)")
    arrow(cx, last_y, cx, y - 30)
    last_y = y + 30

    # ---------- 12. Persist ----------
    y = 1430
    datastore(cx, y, 200, 60, "SQLite\nINSERT")
    arrow(cx, last_y, cx, y - 30)
    last_y = y + 30

    # ---------- 13. Render ----------
    y = 1530
    io(cx, y, 360, 50, "Render markdown report in chat UI")
    arrow(cx, last_y, cx, y - 25)
    last_y = y + 25

    # ---------- 14. Post-action decision ----------
    y = 1640
    out.append(diamond(cx, y, 220, 90, "Analyst\naction?"))
    arrow(cx, last_y, cx, y - 45)

    # Branches: Done (down to End), Re-summarize, Deep-crawl, Export, Tag/Status
    # Left side
    out.append(labeled_box(140, y - 130, 200, 50, "Re-summarize",
                           fill=PFill, stroke=PStroke, rx=22, cls="label-sm"))
    arrow(cx - 110, y - 20, 240, y - 105, label="Re-sum", side="left")
    # Loop arrow back up to LLM summary step
    out.append(path(f"M 140 {y - 105} C 60 {y - 105}, 60 1330, 490 1330",
                    stroke=PALETTE["accent"], sw=1.5, marker="arrow-red",
                    dash="6,4"))

    out.append(labeled_box(140, y + 20, 200, 50, "Trigger Deep-Crawl",
                           fill=PFill, stroke=PStroke, rx=22, cls="label-sm"))
    arrow(cx - 110, y + 20, 240, y + 45, label="Deep-crawl", side="left")
    out.append(path(f"M 140 {y + 45} C 50 {y + 45}, 50 1160, 320 1160",
                    stroke=PALETTE["accent"], sw=1.5, marker="arrow-red",
                    dash="6,4"))

    out.append(labeled_box(1130, y - 130, 220, 50, "Export PDF / Markdown",
                           fill=IOFill, stroke=IOStroke, rx=22, cls="label-sm"))
    arrow(cx + 110, y - 20, 1240, y - 105, label="Export", side="right")
    out.append(labeled_box(1130, y + 20, 220, 50, "Update tags / status",
                           fill=DSFill, stroke=DSStroke, rx=22, cls="label-sm"))
    arrow(cx + 110, y + 20, 1130, y + 45, label="Tag/Status", side="right")

    # Done branch -> End
    out.append(terminator(cx, y + 180, 110, 40, "End"))
    arrow(cx, y + 45, cx, y + 160, label="Done", side="left")

    # ---------- Legend ----------
    leg_items = [
        ("rect",      PFill,  PStroke,                 "Action / activity"),
        ("rect",      IOFill, IOStroke,                "Input / output"),
        ("rect",      DSFill, DSStroke,                "Datastore action"),
        ("diamond",   PALETTE["decision_fill"], PALETTE["decision_border"], "Decision"),
        ("line-solid","",     PALETTE["body"],         "Control flow"),
        ("line-dash", "",     PALETTE["accent"],       "Iterative loop back"),
    ]
    out.append(legend(40, 130, leg_items, title="Notation", w=240))

    body = "\n  ".join(out)
    return svg_doc(W, H, "Figure 4.3 — Activity Diagram",
                   "Operational workflow of an OBSCURA investigation",
                   "  " + body)


def main():
    svg = build()
    out_path = Path(__file__).with_name("03-activity-diagram.svg")
    out_path.write_text(svg, encoding="utf-8")
    print(f"OK: wrote {out_path} ({len(svg):,} chars)")


if __name__ == "__main__":
    main()
