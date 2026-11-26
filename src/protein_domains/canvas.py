"""SVG fragment emission plus the geometry record that the overlap check runs on."""

import math
import re
from collections import defaultdict
from xml.sax.saxutils import escape

from .geometry import poly_hit, rect_hit, rect_poly, seg_hits_rect


def darker(hexcol, f=0.65):
    h = hexcol.lstrip("#")
    r, g, b = (int(h[i : i + 2], 16) for i in (0, 2, 4))
    return "#{:02X}{:02X}{:02X}".format(int(r * f), int(g * f), int(b * f))


class Canvas:
    """Collects SVG fragments plus the geometry of every element for the overlap check."""

    def __init__(self, M, font):
        self.M, self.A = M, f'font-family="{escape(font)}"'
        self.texts = []  # (bbox, owner, description)
        self.boxes = []  # (bbox, owner)        filled shapes
        self.segs = []  # (p, q, owner)        lines
        self.ext = [math.inf, math.inf, -math.inf, -math.inf]
        self._ids = defaultdict(int)

    def uid(self, *parts):
        """An SVG id unique within this figure."""
        base = re.sub(
            r"[^A-Za-z0-9_-]+", "_", "_".join(str(p) for p in parts if p)
        ).strip("_")
        if not base or not base[0].isalpha():
            base = "g_" + base
        self._ids[base] += 1
        return base if self._ids[base] == 1 else f"{base}_{self._ids[base]}"

    def _grow(self, b):
        self.ext = [
            min(self.ext[0], b[0]),
            min(self.ext[1], b[1]),
            max(self.ext[2], b[2]),
            max(self.ext[3], b[3]),
        ]

    def text(
        self, x, y, s, size, owner, anchor="start", rotate=0.0, weight=None, fill="#222"
    ):
        M = self.M
        w = M.w(s, size)
        x0 = {"start": 0, "middle": -w / 2, "end": -w}[anchor]
        corners = [
            (x0, -M.asc(size)),
            (x0 + w, -M.asc(size)),
            (x0 + w, M.desc(size)),
            (x0, M.desc(size)),
        ]
        th = math.radians(rotate)
        pts = [
            (
                x + dx * math.cos(th) - dy * math.sin(th),
                y + dx * math.sin(th) + dy * math.cos(th),
            )
            for dx, dy in corners
        ]
        bb = (
            min(p[0] for p in pts),
            min(p[1] for p in pts),
            max(p[0] for p in pts),
            max(p[1] for p in pts),
        )
        self.texts.append((bb, owner, s, pts))
        self._grow(bb)
        attrs = f'x="{x:.2f}" y="{y:.2f}" {self.A} font-size="{size:.3g}" fill="{fill}"'
        if anchor != "start":
            attrs += f' text-anchor="{anchor}"'
        if weight:
            attrs += f' font-weight="{weight}"'
        if rotate:
            attrs += f' transform="rotate({rotate:g} {x:.2f} {y:.2f})"'
        return f"<text {attrs}>{escape(str(s))}</text>"

    def rect(self, x, y, w, h, owner, fill, stroke=None, sw=0.6, rx=0, check=True):
        bb = (x, y, x + w, y + h)
        if check:
            self.boxes.append((bb, owner))
        self._grow(bb)
        s = f' stroke="{stroke}" stroke-width="{sw}"' if stroke else ""
        r = f' rx="{rx}" ry="{rx}"' if rx else ""
        return f'<rect x="{x:.2f}" y="{y:.2f}" width="{w:.2f}" height="{h:.2f}"{r} fill="{fill}"{s}/>'

    def circle(self, cx, cy, r, owner, fill, stroke=None):
        bb = (cx - r, cy - r, cx + r, cy + r)
        self.boxes.append((bb, owner))
        self._grow(bb)
        s = f' stroke="{stroke}" stroke-width="0.5"' if stroke else ""
        return f'<circle cx="{cx:.2f}" cy="{cy:.2f}" r="{r:.2f}" fill="{fill}"{s}/>'

    def path(self, pts, owner, stroke, sw=0.6, dash=None):
        for p, q in zip(pts, pts[1:]):
            self.segs.append((p, q, owner))
            self._grow(
                (min(p[0], q[0]), min(p[1], q[1]), max(p[0], q[0]), max(p[1], q[1]))
            )
        d = "M" + " L".join(f"{x:.2f},{y:.2f}" for x, y in pts)
        da = f' stroke-dasharray="{dash}"' if dash else ""
        return f'<path d="{d}" fill="none" stroke="{stroke}" stroke-width="{sw}"{da}/>'

    def overlaps(self):
        """Text that touches other text, or a shape/line it does not belong to.
        Uses the real (possibly rotated) text outline, not its axis-aligned box."""
        out = []
        T = self.texts
        for i in range(len(T)):
            bi, oi, si, pi = T[i]
            for j in range(i + 1, len(T)):
                bj, _, sj, pj = T[j]
                if rect_hit(bi, bj) and poly_hit(pi, pj):
                    out.append(f"text '{si}' overlaps text '{sj}'")
            for bb, own in self.boxes:
                if own != oi and rect_hit(bi, bb) and poly_hit(pi, rect_poly(bb)):
                    out.append(f"text '{si}' overlaps a shape ({own})")
            for p, q, own in self.segs:
                if (
                    own != oi
                    and seg_hits_rect(p, q, bi)
                    and poly_hit(pi, [p, q], tol=0.3)
                ):
                    out.append(f"text '{si}' is crossed by a line ({own})")
        return out
