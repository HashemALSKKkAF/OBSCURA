"""Generate the Sequence Diagram SVG for OBSCURA.

Models the primary "Run a new investigation" flow end-to-end.
"""
from pathlib import Path
from _svg_lib import (
    PALETTE, svg_doc, rect, text, labeled_box, line, message,
    self_message, activation, lifeline, frame_box, annotate, legend,
)

W, H = 1900, 1600


def build() -> str:
    out: list[str] = []

    # ---------- Participants (lifelines) ----------
    # x-centers chosen to spread evenly across canvas width (1900px wide)
    # so all 7 lifeline headers fit without colliding with each other or the legend.
    parts = [
        # (cx, name, fill, stroke)
        (150,  "Security\nAnalyst",          PALETTE["actor_fill"],    PALETTE["actor_border"]),
        (390,  "Browser SPA\n(index.html + script.js)", PALETTE["usecase_fill"], PALETTE["usecase_border"]),
        (650,  "Flask API\n(app.py)",        PALETTE["internal_fill"], PALETTE["internal_border"]),
        (920,  "LangChain LLM\n(get_llm → invoke)", PALETTE["internal_fill"], PALETTE["internal_border"]),
        (1190, "Dark-Web\nSearch Engines",   PALETTE["external_fill"], PALETTE["external_border"]),
        (1450, ".onion Sources\n(via Tor SOCKS)",  PALETTE["external_fill"], PALETTE["external_border"]),
        (1730, "SQLite DB\n(obscura.db)",    PALETTE["datastore_fill"], PALETTE["datastore_border"]),
    ]
    top, bottom = 130, 1480
    centers = {}
    for cx, name, fill, stroke in parts:
        out.append(lifeline(cx, top, bottom, name, fill=fill, stroke=stroke,
                            w=190, header_h=58))
        centers[name.split("\n")[0]] = cx

    A = centers["Security"]
    S = centers["Browser SPA"]
    F = centers["Flask API"]
    L = centers["LangChain LLM"]
    E = centers["Dark-Web"]
    O = centers[".onion Sources"]
    D = centers["SQLite DB"]

    # ---------- Message sequence ----------
    y = top + 80          # first message
    step = 38             # vertical spacing per message

    def msg(x1, x2, label, dashed=False, color=None, jump=step):
        nonlocal y
        out.append(message(x1, x2, y, label, dashed=dashed, color=color))
        y += jump

    def gap(amount=14):
        nonlocal y
        y += amount

    # 1. Analyst types a query
    msg(A, S, "1. types query, picks model + preset")
    # 2. SPA opens SSE POST
    msg(S, F, "2. POST /api/investigate (SSE)")

    # 3. Refine query
    out.append(activation(F, y - 4, y + 78))   # short activation on Flask
    msg(F, L, "3. refine_query(query)")
    msg(L, F, "4. refined_query (≤5 words)", dashed=True)
    msg(F, S, "5. SSE 'Refining query…'")

    # 6. Federated search (par fragment)
    frame_y = y + 6
    out.append(frame_box(F - 130, frame_y, (E + 130) - (F - 130), 110,
                         label="across 16 onion search engines", kind="par"))
    y += 28
    msg(F, E, "6. GET /search?q=<refined>  (×16 parallel)")
    msg(E, F, "7. HTML results", dashed=True)
    out.append(annotate(F + 20, y + 4,
                        "dedupe + keyword pre-scoring (score_and_sort)"))
    gap(60)

    # 8. Filter results in batches (loop fragment)
    frame_y = y
    out.append(frame_box(F - 130, frame_y, (L + 130) - (F - 130), 80,
                         label="batches of 25 results", kind="loop"))
    y += 26
    msg(F, L, "8. filter_batch(query, batch)")
    msg(L, F, "9. selected indices (top-10/batch)", dashed=True)
    gap(20)

    # 10. Top-20 picked, SSE update
    msg(F, S, "10. SSE 'Filtering N results…'")
    gap(6)

    # 11–12. Scrape sources (par)
    frame_y = y
    out.append(frame_box(F - 130, frame_y, (O + 130) - (F - 130), 110,
                         label="for each top-20 source", kind="par"))
    y += 28
    msg(F, O, "11. GET URL through Tor SOCKS5  (Tier 2 / Tier 1 selenium)")
    msg(O, F, "12. HTML content", dashed=True)
    out.append(annotate(F + 20, y + 4,
                        "BeautifulSoup → strip scripts/styles → plaintext"))
    gap(60)
    msg(F, S, "13. SSE 'Scraping N selected sources…'")

    # 14. Generate summary
    msg(F, L, "14. generate_summary(query, scraped, preset_prompt)")
    msg(L, F, "15. markdown report (streaming tokens)", dashed=True)

    # 16. Persist
    msg(F, D, "16. INSERT investigation + sources")
    msg(D, F, "17. inv_id", dashed=True)

    # 18. Final SSE + UI render
    msg(F, S, "18. SSE done — {investigation, sources, summary}")
    msg(S, A, "19. render markdown chat + sidebar entry")

    # ---------- Legend ----------
    leg_items = [
        ("line-solid", "", PALETTE["body"], "Synchronous call / message"),
        ("line-dash",  "", PALETTE["body"], "Return value (LangChain output / HTML)"),
        ("rect", PALETTE["bg"], PALETTE["border_d"], "Interaction frame (loop / par)"),
    ]
    # Place legend at bottom-left so it doesn't collide with the DB lifeline header.
    out.append(legend(40, H - 200, leg_items,
                      title="Notation", w=320))

    body = "\n  ".join(out)
    return svg_doc(W, H, "Figure 4.2 — Sequence Diagram",
                   "End-to-end \"Run a New Investigation\" flow",
                   "  " + body)


def main():
    svg = build()
    out_path = Path(__file__).with_name("02-sequence-diagram.svg")
    out_path.write_text(svg, encoding="utf-8")
    print(f"OK: wrote {out_path} ({len(svg):,} chars)")


if __name__ == "__main__":
    main()
