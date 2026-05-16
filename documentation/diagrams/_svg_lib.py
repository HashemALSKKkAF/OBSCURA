"""Shared SVG primitives for OBSCURA FYP diagrams.

All diagrams use a consistent palette, typography, and primitive set so they
look like a coherent series in the report. The OBSCURA brand red (#CC2222)
is reserved for emphasis / actor highlights only.
"""
from __future__ import annotations
from dataclasses import dataclass
from textwrap import dedent
from typing import Iterable
import html
import math

# --------------------------------------------------------------------------- #
# Style tokens (kept hex-strings; SVG doesn't need 0-1 floats)
# --------------------------------------------------------------------------- #

PALETTE = {
    # Brand & neutrals
    "bg":          "#FFFFFF",
    "ink":         "#111111",
    "body":        "#333333",
    "muted":       "#6B7280",
    "border":      "#D1D5DB",
    "border_d":    "#9CA3AF",
    "accent":      "#CC2222",   # OBSCURA red
    "accent_soft": "#FBE9E7",
    # Semantic categories used across diagrams
    "actor_fill":  "#FFE0B2",   "actor_border":  "#EF6C00",
    "usecase_fill":"#BBDEFB",   "usecase_border":"#1565C0",
    "internal_fill":"#C8E6C9",  "internal_border":"#2E7D32",
    "external_fill":"#E1BEE7",  "external_border":"#6A1B9A",
    "datastore_fill":"#FFCDD2", "datastore_border":"#C62828",
    "decision_fill":"#FFF59D",  "decision_border":"#F9A825",
    "process_fill":"#B3E5FC",   "process_border":"#0277BD",
    "io_fill":     "#FFE0E6",   "io_border":     "#B71C1C",
    "terminator":  "#212121",
    "shadow":      "rgba(0,0,0,0.08)",
}

FONT_STACK = "'Inter', 'Segoe UI', 'Helvetica Neue', Arial, sans-serif"

# --------------------------------------------------------------------------- #
# Core SVG document scaffolding
# --------------------------------------------------------------------------- #

SHARED_DEFS = f"""
  <defs>
    <marker id="arrow" viewBox="0 0 10 10" refX="9" refY="5"
            markerWidth="8" markerHeight="8" orient="auto-start-reverse">
      <path d="M0,0 L10,5 L0,10 z" fill="{PALETTE['body']}"/>
    </marker>
    <marker id="arrow-red" viewBox="0 0 10 10" refX="9" refY="5"
            markerWidth="8" markerHeight="8" orient="auto-start-reverse">
      <path d="M0,0 L10,5 L0,10 z" fill="{PALETTE['accent']}"/>
    </marker>
    <marker id="arrow-open" viewBox="0 0 10 10" refX="9" refY="5"
            markerWidth="9" markerHeight="9" orient="auto-start-reverse">
      <path d="M0,0 L10,5 L0,10" fill="none" stroke="{PALETTE['body']}" stroke-width="1.4"/>
    </marker>
    <marker id="diamond-open" viewBox="0 0 12 12" refX="11" refY="6"
            markerWidth="10" markerHeight="10" orient="auto">
      <path d="M0,6 L6,0 L12,6 L6,12 z" fill="{PALETTE['bg']}"
            stroke="{PALETTE['body']}" stroke-width="1"/>
    </marker>
    <marker id="erd-one" viewBox="0 0 12 12" refX="11" refY="6"
            markerWidth="14" markerHeight="14" orient="auto">
      <line x1="3" y1="0" x2="3" y2="12" stroke="{PALETTE['body']}" stroke-width="1.4"/>
      <line x1="7" y1="0" x2="7" y2="12" stroke="{PALETTE['body']}" stroke-width="1.4"/>
    </marker>
    <marker id="erd-many" viewBox="0 0 12 12" refX="11" refY="6"
            markerWidth="14" markerHeight="14" orient="auto">
      <path d="M2,2 L11,6 L2,10 M11,6 L2,6" fill="none"
            stroke="{PALETTE['body']}" stroke-width="1.4"/>
    </marker>
    <filter id="soft" x="-5%" y="-5%" width="110%" height="115%">
      <feGaussianBlur in="SourceAlpha" stdDeviation="1.2"/>
      <feOffset dx="0" dy="1.2"/>
      <feComponentTransfer><feFuncA type="linear" slope="0.18"/></feComponentTransfer>
      <feMerge><feMergeNode/><feMergeNode in="SourceGraphic"/></feMerge>
    </filter>
  </defs>
  <style>
    .title  {{ font: 700 30px {FONT_STACK}; fill: {PALETTE['ink']}; }}
    .subtitle {{ font: 400 14px {FONT_STACK}; fill: {PALETTE['muted']}; }}
    .footer {{ font: 400 11px {FONT_STACK}; fill: {PALETTE['muted']}; }}
    .label  {{ font: 600 13px {FONT_STACK}; fill: {PALETTE['ink']}; text-anchor:middle; }}
    .label-sm {{ font: 500 11px {FONT_STACK}; fill: {PALETTE['body']}; text-anchor:middle; }}
    .label-l {{ font: 700 14px {FONT_STACK}; fill: {PALETTE['ink']}; text-anchor:middle; }}
    .label-w {{ font: 600 13px {FONT_STACK}; fill: #FFFFFF; text-anchor:middle; }}
    .arrow-lbl {{ font: 500 11px {FONT_STACK}; fill: {PALETTE['body']}; }}
    .stereotype {{ font: 400 italic 10.5px {FONT_STACK}; fill: {PALETTE['muted']}; text-anchor:middle; }}
    .legend-t {{ font: 600 12px {FONT_STACK}; fill: {PALETTE['ink']}; }}
    .legend-b {{ font: 400 11px {FONT_STACK}; fill: {PALETTE['body']}; }}
    .erd-attr {{ font: 400 11px {FONT_STACK}; fill: {PALETTE['body']}; }}
    .erd-pk   {{ font: 700 11px {FONT_STACK}; fill: {PALETTE['accent']}; }}
    .mono     {{ font: 500 11px ui-monospace, 'Consolas', 'SF Mono', monospace; fill: {PALETTE['body']}; }}
  </style>
"""


def svg_doc(width: int, height: int, title: str, subtitle: str, body: str) -> str:
    """Wrap body fragments in a full standalone SVG document."""
    return dedent(f"""<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}"
     width="{width}" height="{height}">
  <rect x="0" y="0" width="{width}" height="{height}" fill="{PALETTE['bg']}"/>
{SHARED_DEFS}
  <!-- Header -->
  <text x="40" y="48" class="title">{html.escape(title)}</text>
  <text x="40" y="72" class="subtitle">{html.escape(subtitle)}</text>
  <line x1="40" y1="86" x2="{width - 40}" y2="86" stroke="{PALETTE['accent']}" stroke-width="1.6"/>
{body}
  <!-- Footer -->
  <text x="40" y="{height - 22}" class="footer">OBSCURA — Threat Intelligence Automation from Dark Web Sources · NED University of Engineering and Technology · Group CS-22052</text>
</svg>
""").strip() + "\n"


# --------------------------------------------------------------------------- #
# Primitives — each returns an SVG fragment string
# --------------------------------------------------------------------------- #

def esc(t: str) -> str:
    return html.escape(t, quote=False)


def rect(x: float, y: float, w: float, h: float, *, fill: str, stroke: str,
         rx: float = 8, sw: float = 1.4, shadow: bool = True,
         dash: str | None = None) -> str:
    f = f' filter="url(#soft)"' if shadow else ""
    d = f' stroke-dasharray="{dash}"' if dash else ""
    return (f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{rx}" ry="{rx}" '
            f'fill="{fill}" stroke="{stroke}" stroke-width="{sw}"{d}{f}/>')


def text(x: float, y: float, content: str, cls: str = "label", anchor: str | None = None) -> str:
    a = f' text-anchor="{anchor}"' if anchor else ""
    return f'<text x="{x}" y="{y}" class="{cls}"{a}>{esc(content)}</text>'


def multiline(x: float, y: float, lines: list[str], cls: str = "label",
              line_height: float = 16, anchor: str = "middle") -> str:
    out = []
    for i, line in enumerate(lines):
        out.append(f'<text x="{x}" y="{y + i * line_height}" class="{cls}" text-anchor="{anchor}">{esc(line)}</text>')
    return "\n  ".join(out)


def labeled_box(x: float, y: float, w: float, h: float, label: str,
                fill: str, stroke: str, *, rx: float = 10,
                cls: str = "label", line_height: float = 16,
                shadow: bool = True, sw: float = 1.4) -> str:
    """Rectangle with auto-wrapped (manually split) label centred inside."""
    lines = label.split("\n")
    r = rect(x, y, w, h, fill=fill, stroke=stroke, rx=rx, shadow=shadow, sw=sw)
    cx = x + w / 2
    total = (len(lines) - 1) * line_height
    start_y = y + h / 2 - total / 2 + 5
    txt = multiline(cx, start_y, lines, cls=cls, line_height=line_height)
    return r + "\n  " + txt


def ellipse(cx: float, cy: float, rx: float, ry: float, label: str,
            fill: str, stroke: str, *, sw: float = 1.4, shadow: bool = True,
            cls: str = "label", line_height: float = 14) -> str:
    f = f' filter="url(#soft)"' if shadow else ""
    e = (f'<ellipse cx="{cx}" cy="{cy}" rx="{rx}" ry="{ry}" '
         f'fill="{fill}" stroke="{stroke}" stroke-width="{sw}"{f}/>')
    lines = label.split("\n")
    total = (len(lines) - 1) * line_height
    start_y = cy - total / 2 + 4
    return e + "\n  " + multiline(cx, start_y, lines, cls=cls, line_height=line_height)


def diamond(cx: float, cy: float, w: float, h: float, label: str,
            *, fill: str | None = None, stroke: str | None = None,
            sw: float = 1.4, shadow: bool = True,
            cls: str = "label-sm", line_height: float = 13) -> str:
    fill = fill or PALETTE["decision_fill"]
    stroke = stroke or PALETTE["decision_border"]
    f = f' filter="url(#soft)"' if shadow else ""
    pts = f"{cx},{cy - h/2} {cx + w/2},{cy} {cx},{cy + h/2} {cx - w/2},{cy}"
    d = (f'<polygon points="{pts}" fill="{fill}" stroke="{stroke}" '
         f'stroke-width="{sw}"{f}/>')
    lines = label.split("\n")
    total = (len(lines) - 1) * line_height
    start_y = cy - total / 2 + 3
    return d + "\n  " + multiline(cx, start_y, lines, cls=cls, line_height=line_height)


def terminator(cx: float, cy: float, w: float, h: float, label: str,
               *, fill: str | None = None) -> str:
    """Pill-shaped Start/End node."""
    fill = fill or PALETTE["terminator"]
    rx = h / 2
    r = rect(cx - w/2, cy - h/2, w, h, fill=fill, stroke=fill, rx=rx, sw=1, shadow=True)
    t = f'<text x="{cx}" y="{cy + 5}" class="label-w" text-anchor="middle">{esc(label)}</text>'
    return r + "\n  " + t


def actor_stick(cx: float, cy: float, label: str, *,
                color: str | None = None, scale: float = 1.0) -> str:
    """UML-style stick-figure actor with label below."""
    color = color or PALETTE["actor_border"]
    head_r = 12 * scale
    body_top = cy - head_r * 0.4
    body_bot = body_top + 36 * scale
    arms_y = body_top + 10 * scale
    legs_y = body_bot + 22 * scale
    parts = [
        f'<circle cx="{cx}" cy="{cy - head_r * 1.6}" r="{head_r}" '
        f'fill="{PALETTE["bg"]}" stroke="{color}" stroke-width="2"/>',
        f'<line x1="{cx}" y1="{body_top}" x2="{cx}" y2="{body_bot}" '
        f'stroke="{color}" stroke-width="2"/>',
        f'<line x1="{cx - 18 * scale}" y1="{arms_y}" x2="{cx + 18 * scale}" '
        f'y2="{arms_y}" stroke="{color}" stroke-width="2"/>',
        f'<line x1="{cx}" y1="{body_bot}" x2="{cx - 14 * scale}" y2="{legs_y}" '
        f'stroke="{color}" stroke-width="2"/>',
        f'<line x1="{cx}" y1="{body_bot}" x2="{cx + 14 * scale}" y2="{legs_y}" '
        f'stroke="{color}" stroke-width="2"/>',
    ]
    lines = label.split("\n")
    base_y = legs_y + 18
    for i, ln in enumerate(lines):
        parts.append(f'<text x="{cx}" y="{base_y + i * 14}" class="label-sm" '
                     f'text-anchor="middle">{esc(ln)}</text>')
    return "\n  ".join(parts)


def system_actor(x: float, y: float, w: float, h: float, name: str,
                 stereotype: str = "<<system>>") -> str:
    """Rectangular actor box with «stereotype» label, used for non-human actors."""
    body = labeled_box(x, y, w, h, name,
                       fill=PALETTE["external_fill"], stroke=PALETTE["external_border"],
                       rx=10, shadow=True, sw=1.4, cls="label", line_height=15)
    stereo = f'<text x="{x + w/2}" y="{y - 8}" class="stereotype">{esc(stereotype)}</text>'
    return body + "\n  " + stereo


def line(x1: float, y1: float, x2: float, y2: float, *,
         stroke: str | None = None, sw: float = 1.4,
         dash: str | None = None, arrow: bool = False,
         arrow_open: bool = False, arrow_end_only: bool = True,
         marker: str | None = None) -> str:
    stroke = stroke or PALETTE["body"]
    d = f' stroke-dasharray="{dash}"' if dash else ""
    m = ""
    if marker:
        m = f' marker-end="url(#{marker})"'
    elif arrow:
        m = ' marker-end="url(#arrow)"' if arrow_end_only else (
            ' marker-start="url(#arrow)" marker-end="url(#arrow)"'
        )
    elif arrow_open:
        m = ' marker-end="url(#arrow-open)"'
    return (f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" '
            f'stroke="{stroke}" stroke-width="{sw}"{d}{m}/>')


def path(d: str, *, stroke: str | None = None, sw: float = 1.4,
         fill: str = "none", dash: str | None = None,
         marker: str | None = None) -> str:
    stroke = stroke or PALETTE["body"]
    da = f' stroke-dasharray="{dash}"' if dash else ""
    m = f' marker-end="url(#{marker})"' if marker else ""
    return (f'<path d="{d}" stroke="{stroke}" stroke-width="{sw}" '
            f'fill="{fill}"{da}{m}/>')


def annotate(x: float, y: float, txt: str, *, anchor: str = "start") -> str:
    return (f'<text x="{x}" y="{y}" class="arrow-lbl" text-anchor="{anchor}">'
            f'{esc(txt)}</text>')


def legend(x: float, y: float, items: list[tuple[str, str, str, str]], *,
           title: str = "Legend", w: float = 220) -> str:
    """items: list of (swatch_kind, fill, stroke, label)
       swatch_kind in {'rect','ellipse','diamond','line-solid','line-dash','arrow','actor'}.
    """
    row_h = 22
    h = 26 + row_h * len(items) + 14
    out = [rect(x, y, w, h, fill=PALETTE["bg"], stroke=PALETTE["border"], rx=8,
                sw=1, shadow=True)]
    out.append(f'<text x="{x + 12}" y="{y + 22}" class="legend-t">{esc(title)}</text>')
    for i, (kind, fill, stroke, lbl) in enumerate(items):
        cy = y + 26 + 14 + i * row_h
        sx = x + 14
        if kind == "rect":
            out.append(rect(sx, cy - 8, 20, 14, fill=fill, stroke=stroke, rx=3,
                            sw=1.2, shadow=False))
        elif kind == "ellipse":
            out.append(f'<ellipse cx="{sx + 10}" cy="{cy - 1}" rx="14" ry="8" '
                       f'fill="{fill}" stroke="{stroke}" stroke-width="1.2"/>')
        elif kind == "diamond":
            pts = f"{sx + 10},{cy - 9} {sx + 22},{cy - 1} {sx + 10},{cy + 7} {sx - 2},{cy - 1}"
            out.append(f'<polygon points="{pts}" fill="{fill}" stroke="{stroke}" '
                       f'stroke-width="1.2"/>')
        elif kind == "line-solid":
            out.append(f'<line x1="{sx}" y1="{cy - 1}" x2="{sx + 26}" y2="{cy - 1}" '
                       f'stroke="{stroke}" stroke-width="1.6" marker-end="url(#arrow)"/>')
        elif kind == "line-dash":
            out.append(f'<line x1="{sx}" y1="{cy - 1}" x2="{sx + 26}" y2="{cy - 1}" '
                       f'stroke="{stroke}" stroke-width="1.6" stroke-dasharray="5,4" '
                       f'marker-end="url(#arrow-open)"/>')
        elif kind == "actor":
            out.append(f'<circle cx="{sx + 6}" cy="{cy - 5}" r="4" fill="none" '
                       f'stroke="{stroke}" stroke-width="1.5"/>')
            out.append(f'<line x1="{sx + 6}" y1="{cy - 1}" x2="{sx + 6}" y2="{cy + 6}" '
                       f'stroke="{stroke}" stroke-width="1.5"/>')
            out.append(f'<line x1="{sx}" y1="{cy + 1}" x2="{sx + 12}" y2="{cy + 1}" '
                       f'stroke="{stroke}" stroke-width="1.5"/>')
        out.append(f'<text x="{sx + 36}" y="{cy + 3}" class="legend-b">{esc(lbl)}</text>')
    return "\n  ".join(out)


# --------------------------------------------------------------------------- #
# Helpers for sequence-diagram lifelines, swimlanes, etc.
# --------------------------------------------------------------------------- #

def lifeline(cx: float, top: float, bottom: float, name: str, *,
             fill: str | None = None, stroke: str | None = None,
             w: float = 160, header_h: float = 40) -> str:
    fill = fill or PALETTE["external_fill"]
    stroke = stroke or PALETTE["external_border"]
    head = labeled_box(cx - w/2, top, w, header_h, name,
                       fill=fill, stroke=stroke, rx=6, sw=1.2,
                       cls="label-l", shadow=True)
    line_ = f'<line x1="{cx}" y1="{top + header_h}" x2="{cx}" y2="{bottom}" ' \
            f'stroke="{PALETTE["border_d"]}" stroke-width="1.2" stroke-dasharray="4,4"/>'
    return head + "\n  " + line_


def activation(cx: float, top: float, bottom: float, *,
               width: float = 14, fill: str | None = None) -> str:
    fill = fill or PALETTE["accent_soft"]
    return (f'<rect x="{cx - width/2}" y="{top}" width="{width}" '
            f'height="{bottom - top}" fill="{fill}" '
            f'stroke="{PALETTE["accent"]}" stroke-width="1"/>')


def message(x1: float, x2: float, y: float, label: str, *,
            dashed: bool = False, color: str | None = None,
            arrow: bool = True, bottom_lbl: bool = False) -> str:
    color = color or PALETTE["body"]
    dash = "6,4" if dashed else None
    ln = line(x1, y, x2, y, stroke=color, sw=1.5, dash=dash,
              marker="arrow" if arrow else None)
    cx = (x1 + x2) / 2
    lbl_y = y - 6 if not bottom_lbl else y + 14
    return ln + "\n  " + (
        f'<text x="{cx}" y="{lbl_y}" class="arrow-lbl" text-anchor="middle">'
        f'{esc(label)}</text>'
    )


def self_message(x: float, y: float, label: str, *,
                 reach: float = 40, color: str | None = None) -> str:
    color = color or PALETTE["body"]
    d = f"M {x},{y} h {reach} v 24 h -{reach}"
    p = path(d, stroke=color, marker="arrow")
    t = f'<text x="{x + reach + 6}" y="{y + 4}" class="arrow-lbl">{esc(label)}</text>'
    return p + "\n  " + t


def frame_box(x: float, y: float, w: float, h: float, label: str, *,
              kind: str = "loop") -> str:
    """UML interaction frame (loop / par / alt) with cornered label."""
    body = rect(x, y, w, h, fill="none", stroke=PALETTE["border_d"], rx=4,
                sw=1.2, shadow=False, dash="6,4")
    tag_w = max(60, 22 + len(label) * 7)
    tag = (f'<polygon points="{x},{y} {x + tag_w},{y} '
           f'{x + tag_w - 10},{y + 18} {x},{y + 18}" '
           f'fill="{PALETTE["bg"]}" stroke="{PALETTE["border_d"]}" stroke-width="1.2"/>')
    tag_label = (f'<text x="{x + 6}" y="{y + 13}" class="legend-t" '
                 f'style="font-size:11px">{esc(kind)}</text>')
    msg_label = (f'<text x="{x + tag_w + 8}" y="{y + 13}" class="arrow-lbl">'
                 f'[{esc(label)}]</text>')
    return "\n  ".join([body, tag, tag_label, msg_label])
