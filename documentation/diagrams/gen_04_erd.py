"""Generate the Entity-Relationship Diagram SVG for OBSCURA."""
from pathlib import Path
from _svg_lib import (
    PALETTE, svg_doc, rect, text, line, annotate, legend,
)
import html

W, H = 1700, 1150


def entity(x, y, name, attrs, *, fill=None, stroke=None, header_fill=None):
    """attrs: list of (kind, name, type) where kind in {PK, FK, UK, ''}."""
    fill = fill or PALETTE["bg"]
    stroke = stroke or PALETTE["ink"]
    header_fill = header_fill or PALETTE["accent_soft"]
    row_h = 22
    name_h = 38
    w = 290
    h = name_h + 12 + row_h * len(attrs)

    out = [rect(x, y, w, h, fill=fill, stroke=stroke, rx=8, sw=1.6,
                shadow=True)]
    # Header band
    out.append(f'<rect x="{x + 1}" y="{y + 1}" width="{w - 2}" '
               f'height="{name_h - 1}" fill="{header_fill}" '
               f'stroke="none" rx="6"/>')
    out.append(f'<text x="{x + 14}" y="{y + 25}" class="label-l" '
               f'text-anchor="start">{html.escape(name)}</text>')
    # Divider under header
    out.append(line(x, y + name_h, x + w, y + name_h,
                    stroke=stroke, sw=1.2))
    # Attributes
    for i, (kind, attr, typ) in enumerate(attrs):
        ay = y + name_h + 18 + i * row_h
        prefix = f"{kind} " if kind else ""
        cls = "erd-pk" if kind == "PK" else "erd-attr"
        out.append(f'<text x="{x + 14}" y="{ay}" class="{cls}" '
                   f'text-anchor="start">{html.escape(prefix + attr)}</text>')
        out.append(f'<text x="{x + w - 14}" y="{ay}" class="mono" '
                   f'text-anchor="end">{html.escape(typ)}</text>')
    return "\n  ".join(out), {"x": x, "y": y, "w": w, "h": h}


def build() -> str:
    out: list[str] = []

    # ---------- Investigation ----------
    inv_svg, inv = entity(140, 160, "Investigation", [
        ("PK", "id",            "INTEGER, AUTOINCREMENT"),
        ("",   "timestamp",     "TEXT (ISO-8601)"),
        ("",   "query",         "TEXT, NOT NULL"),
        ("",   "refined_query", "TEXT"),
        ("",   "model",         "TEXT"),
        ("",   "preset",        "TEXT  (built-in key | custom:<id>)"),
        ("",   "summary",       "TEXT (markdown)"),
        ("",   "status",        "TEXT (active|pending|closed|complete)"),
        ("",   "tags",          "TEXT (comma-separated)"),
    ], header_fill=PALETTE["actor_fill"])
    out.append(inv_svg)

    # ---------- Source ----------
    src_svg, src = entity(770, 160, "Source", [
        ("PK", "id",                "INTEGER, AUTOINCREMENT"),
        ("FK", "investigation_id",  "INTEGER  → Investigation.id"),
        ("",   "title",             "TEXT"),
        ("",   "link",              "TEXT  (.onion URL)"),
    ], header_fill=PALETTE["usecase_fill"])
    out.append(src_svg)

    # ---------- Seed ----------
    seed_svg, seed = entity(140, 660, "Seed", [
        ("PK", "id",          "INTEGER, AUTOINCREMENT"),
        ("UK", "url",         "TEXT, UNIQUE NOT NULL"),
        ("",   "hash",        "TEXT (SHA-256 of url)"),
        ("",   "name",        "TEXT"),
        ("",   "status_code", "INTEGER  (last HTTP status)"),
        ("",   "crawled",     "INTEGER (0/1)"),
        ("",   "loaded",      "INTEGER (0/1)"),
        ("",   "content",     "TEXT  (extracted plaintext)"),
        ("",   "crawled_at",  "TEXT (ISO-8601)"),
        ("",   "added_at",    "TEXT (ISO-8601)"),
    ], header_fill=PALETTE["internal_fill"])
    out.append(seed_svg)

    # ---------- CustomPreset ----------
    cp_svg, cp = entity(770, 660, "CustomPreset", [
        ("PK", "id",            "INTEGER, AUTOINCREMENT"),
        ("UK", "name",          "TEXT, UNIQUE NOT NULL"),
        ("",   "description",   "TEXT"),
        ("",   "system_prompt", "TEXT, NOT NULL"),
        ("",   "created_at",    "TEXT (ISO-8601)"),
        ("",   "updated_at",    "TEXT (ISO-8601)"),
    ], header_fill=PALETTE["external_fill"])
    out.append(cp_svg)

    # ---------- Relationship: Investigation 1 -- *N* Source (crow's foot) ----------
    # Connection from right edge of Investigation to left edge of Source
    inv_right_x = inv["x"] + inv["w"]
    src_left_x = src["x"]
    # Vertical center: use the row corresponding to investigation_id in Source
    # Source y is 160; rows are ~22 each. investigation_id is 2nd row.
    rel_y = 235  # ~ second attribute row of Source
    inv_pk_y = 230   # id row of Investigation
    # Draw line with crow's foot markers
    out.append(line(inv_right_x, inv_pk_y, src_left_x, rel_y,
                    stroke=PALETTE["body"], sw=1.6,
                    marker="erd-many"))
    # Add the "one" marker manually on the Investigation side
    # by drawing two short bars perpendicular to the line just outside the box
    out.append(f'<line x1="{inv_right_x + 8}" y1="{inv_pk_y - 7}" '
               f'x2="{inv_right_x + 8}" y2="{inv_pk_y + 7}" '
               f'stroke="{PALETTE["body"]}" stroke-width="1.6"/>')
    out.append(f'<line x1="{inv_right_x + 14}" y1="{inv_pk_y - 7}" '
               f'x2="{inv_right_x + 14}" y2="{inv_pk_y + 7}" '
               f'stroke="{PALETTE["body"]}" stroke-width="1.6"/>')
    # Relationship label above the line
    midx = (inv_right_x + src_left_x) / 2
    out.append(annotate(midx, (inv_pk_y + rel_y) / 2 - 12,
                        "  has   (1 — N, ON DELETE CASCADE)",
                        anchor="middle"))

    # ---------- Soft reference: Investigation.preset --> CustomPreset.id ----------
    # Investigation.preset row is the 6th attribute row, at y ~ 320
    pre_row_y = 350
    out.append(line(inv["x"] + inv["w"], pre_row_y,
                    cp["x"], cp["y"] + 65,
                    stroke=PALETTE["muted"], sw=1.4,
                    dash="6,4", marker="arrow-open"))
    out.append(annotate(midx, (pre_row_y + cp["y"] + 65) / 2 - 12,
                        "soft reference (when preset starts with \"custom:\")",
                        anchor="middle"))

    # ---------- On-disk audit dump note ----------
    note_x, note_y, note_w, note_h = 1180, 160, 380, 210
    out.append(rect(note_x, note_y, note_w, note_h,
                    fill=PALETTE["accent_soft"], stroke=PALETTE["accent"],
                    rx=10, sw=1.2, shadow=True))
    out.append(f'<text x="{note_x + 16}" y="{note_y + 26}" class="legend-t" '
               f'text-anchor="start">Filesystem (not in SQLite)</text>')
    notes = [
        "• investigations/obscura.db  (single DB, WAL mode)",
        "• investigations/crawled/<sha256>/rendered.html",
        "• investigations/crawled/<sha256>/tier.txt",
        "  → audit dump per Deep-Crawl;",
        "    keyed by SHA-256 of source URL.",
    ]
    for i, ln in enumerate(notes):
        out.append(f'<text x="{note_x + 16}" y="{note_y + 56 + i * 22}" '
                   f'class="legend-b" text-anchor="start">{html.escape(ln)}</text>')

    # ---------- Legend ----------
    leg_items = [
        ("rect", PALETTE["accent_soft"], PALETTE["accent"], "Entity (table)"),
        ("rect", "#FFFFFF",              PALETTE["ink"],    "Attribute"),
        ("line-solid", "",               PALETTE["body"],   "Crow's-foot relationship (1—N)"),
        ("line-dash",  "",               PALETTE["muted"],  "Soft (non-FK) reference"),
    ]
    out.append(legend(1180, 470, leg_items, title="ERD Notation", w=380))

    # Show PK / FK / UK conventions
    conv_x, conv_y = 1180, 660
    out.append(rect(conv_x, conv_y, 380, 220,
                    fill=PALETTE["bg"], stroke=PALETTE["border"],
                    rx=8, sw=1.2, shadow=True))
    out.append(f'<text x="{conv_x + 16}" y="{conv_y + 26}" class="legend-t" '
               f'text-anchor="start">Attribute Conventions</text>')
    rows = [
        ("PK", "Primary Key  (integer surrogate)"),
        ("FK", "Foreign Key  (referential integrity)"),
        ("UK", "Unique constraint"),
        ("",   "All timestamps stored as ISO-8601 strings"),
        ("",   "All booleans stored as INTEGER 0 / 1"),
        ("",   "Indexes: idx_inv_timestamp, idx_inv_status,"),
        ("",   "         idx_seeds_crawled, idx_seeds_loaded,"),
        ("",   "         idx_custom_presets_name"),
    ]
    for i, (tag, desc) in enumerate(rows):
        ry = conv_y + 56 + i * 20
        cls = "erd-pk" if tag == "PK" else "legend-b"
        out.append(f'<text x="{conv_x + 16}" y="{ry}" class="{cls}" '
                   f'text-anchor="start">{html.escape(tag or "•")}</text>')
        out.append(f'<text x="{conv_x + 50}" y="{ry}" class="legend-b" '
                   f'text-anchor="start">{html.escape(desc)}</text>')

    body = "\n  ".join(out)
    return svg_doc(W, H, "Figure 4.4 — Entity-Relationship Diagram",
                   "SQLite schema for OBSCURA — investigations, sources, seeds, custom presets",
                   "  " + body)


def main():
    svg = build()
    out_path = Path(__file__).with_name("04-erd.svg")
    out_path.write_text(svg, encoding="utf-8")
    print(f"OK: wrote {out_path} ({len(svg):,} chars)")


if __name__ == "__main__":
    main()
