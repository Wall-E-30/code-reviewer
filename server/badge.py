"""
server/badge.py

Dynamic SVG Badge Generator for Aion Code Reviewer (GROWTH-01).
Generates GitHub README badges adhering to standard Shields.io flat format,
color-coded by live repository review precision.
"""

from __future__ import annotations

import html
from typing import Optional


COLOR_GREEN = "#2ea44f"   # >= 70% precision (PASS)
COLOR_YELLOW = "#dfb317"  # 50% - 69% precision (MONITORING)
COLOR_RED = "#cb2431"     # < 50% precision (FAIL)
COLOR_GRAY = "#9f9f9f"    # No data / unverified


def generate_svg_badge(
    left_text: str,
    right_text: str,
    color_hex: str,
) -> str:
    """
    Generate a clean, scalable SVG badge using flat Shields.io geometry.
    """
    safe_left = html.escape(left_text)
    safe_right = html.escape(right_text)

    # Approximate text measurement for Verdana 11px
    left_width = max(int(len(left_text) * 6.8) + 14, 40)
    right_width = max(int(len(right_text) * 6.8) + 14, 30)
    total_width = left_width + right_width

    left_x = int((left_width / 2.0) * 10)
    right_x = int((left_width + right_width / 2.0) * 10)
    left_len = max((left_width - 12) * 10, 100)
    right_len = max((right_width - 12) * 10, 100)

    svg = f"""<svg xmlns="http://www.w3.org/2000/svg" width="{total_width}" height="20" role="img" aria-label="{safe_left}: {safe_right}">
  <title>{safe_left}: {safe_right}</title>
  <linearGradient id="b" x2="0" y2="100%">
    <stop offset="0" stop-color="#bbb" stop-opacity=".1"/>
    <stop offset="1" stop-opacity=".1"/>
  </linearGradient>
  <clipPath id="a">
    <rect width="{total_width}" height="20" rx="3" fill="#fff"/>
  </clipPath>
  <g clip-path="url(#a)">
    <rect width="{left_width}" height="20" fill="#555"/>
    <rect x="{left_width}" width="{right_width}" height="20" fill="{color_hex}"/>
    <rect width="{total_width}" height="20" fill="url(#b)"/>
  </g>
  <g fill="#fff" text-anchor="middle" font-family="Verdana,Geneva,DejaVu Sans,sans-serif" text-rendering="geometricPrecision" font-size="110">
    <text x="{left_x}" y="150" fill="#010101" fill-opacity=".3" transform="scale(.1)" textLength="{left_len}">{safe_left}</text>
    <text x="{left_x}" y="140" transform="scale(.1)" textLength="{left_len}">{safe_left}</text>
    <text x="{right_x}" y="150" fill="#010101" fill-opacity=".3" transform="scale(.1)" textLength="{right_len}">{safe_right}</text>
    <text x="{right_x}" y="140" transform="scale(.1)" textLength="{right_len}">{safe_right}</text>
  </g>
</svg>"""
    return svg


def get_badge_for_precision(
    precision: Optional[float],
    label: str = "Reviewed by Aion",
    metric_type: str = "precision",
) -> str:
    """
    Generate an SVG badge representing a repository's review status or precision.

    Parameters:
        precision: Rolling precision in [0.0, 1.0], or None if no data.
        label: Left badge text (default: 'Reviewed by Aion').
        metric_type: 'precision' (e.g. '78%') or 'status' (e.g. 'passing').
    """
    if precision is None:
        return generate_svg_badge(label, "unverified", COLOR_GRAY)

    p = max(0.0, min(1.0, float(precision)))

    if p >= 0.70:
        color = COLOR_GREEN
        status_text = "passing"
    elif p >= 0.50:
        color = COLOR_YELLOW
        status_text = "monitoring"
    else:
        color = COLOR_RED
        status_text = "low precision"

    if metric_type == "status":
        right_text = status_text
    else:
        right_text = f"{int(round(p * 100))}% precision"

    return generate_svg_badge(label, right_text, color)

