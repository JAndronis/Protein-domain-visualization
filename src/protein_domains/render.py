"""Layout of feature rows into one SVG figure."""

import math
import sys
from collections import OrderedDict, defaultdict
from dataclasses import dataclass
from pathlib import Path

from .canvas import Canvas, darker
from .geometry import pack, rect_hit, spread
from .metrics import Metrics


DOMAIN_PALETTE = [
    "#8ECAE6",
    "#FFC857",
    "#9BD3AE",
    "#F4A582",
    "#C7B8E0",
    "#F7B6C2",
    "#A6D9D4",
    "#E9D78E",
    "#B5C7E8",
    "#D9B38C",
]
TYPE_COLOR = {
    "Region": "#BDBDBD",
    "Disorder": "#BDBDBD",
    "Compositional bias": "#D9C99A",
    "Coiled coil": "#9FC5BE",
    "Motif": "#F2B880",
    "Modified residue": "#C8312F",
    "Glycosylation": "#2A9D8F",
    "Lipidation": "#C9A227",
    "Cross-link": "#6A4C93",
    "Active site": "#E07A1F",
    "Binding site": "#1D3557",
    "Site": "#6C757D",
    "Natural variant": "#7B2CBF",
    "Mutagenesis": "#7B2CBF",
    "Disulfide bond": "#B8860B",
    "Helix": "#D1495B",
    "Beta strand": "#00798C",
    "Turn": "#A0A0A0",
}


@dataclass
class Figure:
    svg: str
    overlaps: list  # text still touching other text, shapes or lines
    omitted: list  # boundary numbers left out for lack of room, as "protein:residue"
    warnings: list
    metrics: str  # font file the text was measured with, or "estimate"


def render(rows, out, quiet=False, **opts):
    """Write the figure to `out`, report problems on stderr and return the overlaps."""
    fig = layout(rows, **opts)
    Path(out).write_text(fig.svg, encoding="utf-8")
    if not quiet:
        for w in fig.warnings:
            print(f"warning: {w}", file=sys.stderr)
        print(f"text metrics: {fig.metrics}", file=sys.stderr)
        if fig.omitted:
            print(
                f"note: {len(fig.omitted)} boundary number(s) left out for lack of room "
                f"(adjacent or narrow domains): {', '.join(fig.omitted)}",
                file=sys.stderr,
            )
        if fig.overlaps:
            print(
                f"warning: {len(fig.overlaps)} overlap(s) left (fix in the CSV or the editor):",
                file=sys.stderr,
            )
            for p in fig.overlaps[:15]:
                print("  - " + p, file=sys.stderr)
    return fig.overlaps


def layout(
    rows,
    width=400,
    fs=8,
    font="Arial",
    numbers=False,
    label_angle=-90,
    min_label_scale=0.7,
    axis="full",
    sizes=None,
    tag_rows=False,
):
    """Lay out feature rows as one SVG document.

    tag_rows wraps each row's elements in <g data-row="i">, i indexing `rows`, so the GUI
    can map a click back to the row it came from. The CLI output leaves it off.
    """

    def tagged(i, svg):
        return f'<g data-row="{i}">{svg}</g>' if tag_rows else svg

    M = Metrics(font)
    C = Canvas(M, font)
    label_angle = max(-90.0, min(-20.0, label_angle))
    # every size below derives from fs, so changing the font keeps the layout clean
    # text sizes: each can be set on its own; unset ones follow fs
    S = dict(
        name=fs + 1,
        domain=fs,
        outside=None,
        site=fs * 0.875,
        region=fs * 0.875,
        number=fs * 0.75,
        axis=fs * 0.875,
        legend=fs * 0.875,
    )
    S.update({k: v for k, v in (sizes or {}).items() if v})
    if S["outside"] is None:
        S["outside"] = 0.875 * S["domain"]
    f_name, f_dom, f_out, f_site, f_region, f_num, f_axis, f_legend = (
        S[k]
        for k in (
            "name",
            "domain",
            "outside",
            "site",
            "region",
            "number",
            "axis",
            "legend",
        )
    )
    H = max(10.0, M.h(f_dom) + 0.6 * fs)  # domain box height
    BB = max(2.0, 0.45 * fs)  # backbone thickness
    BAR = max(2.5, 0.5 * fs)  # region bar thickness
    R = max(2.0, 0.33 * fs)  # lollipop head radius
    STEM, ELBOW = 1.2 * fs, 1.0 * fs
    G = 0.4 * fs  # generic small gap

    prots = OrderedDict()
    for i, r in enumerate(rows):
        if r["type"] == "Protein":
            prots[r["protein"]] = dict(
                name=r["label"] or r["protein"], L=int(float(r["end"])), feats=[], row=i
            )
    for i, r in enumerate(rows):
        if r["type"] == "Protein" or str(r["show"]).strip().lower() not in (
            "1",
            "1.0",
            "yes",
            "y",
            "true",
        ):
            continue
        if r["protein"] not in prots:
            sys.exit(f"feature for unknown protein '{r['protein']}' (no 'Protein' row)")
        f = dict(r, row=i)
        f["s"], f["e"] = int(float(r["start"])), int(float(r["end"]))
        f["shape"] = (r["shape"] or "box").strip().lower()
        f["label"] = f["label"].strip()
        prots[r["protein"]]["feats"].append(f)

    Lmax = max(p["L"] for p in prots.values())
    sx = width / Lmax
    left = max(M.w(p["name"], f_name) for p in prots.values()) + 1.0 * fs

    def X(pos):  # residue i spans [i-1, i]
        return left + pos * sx

    colour_key = {}

    def colour(f):
        if f["color"].strip():
            return f["color"].strip()
        if f["shape"] == "box":
            k = f["group"] or f["label"]
            if k not in colour_key:
                colour_key[k] = DOMAIN_PALETTE[len(colour_key) % len(DOMAIN_PALETTE)]
            return colour_key[k]
        return TYPE_COLOR.get(f["type"], "#888888")

    svg, legend = [], OrderedDict()
    omitted, warnings = [], []
    y = 0.0
    for pid, P in prots.items():
        F = P["feats"]
        for f in F:
            f["col"] = colour(f)
        boxes = sorted(
            [f for f in F if f["shape"] == "box"], key=lambda f: (f["s"], -f["e"])
        )
        bars = [f for f in F if f["shape"] == "bar"]
        pops = sorted([f for f in F if f["shape"] == "lollipop"], key=lambda f: f["s"])
        brks = [f for f in F if f["shape"] == "bracket"]
        sss = [f for f in F if f["shape"] == "ss"]
        g = C.uid(pid)
        parts = []

        # ---- lollipop geometry first: it sets the height above the backbone ----
        th = math.radians(label_angle)
        thick = M.h(f_site) * 1.15  # label line thickness + air
        d_min = max(2 * R + G, thick / abs(math.sin(th)))
        if pops:
            xs = [X(f["s"] - 0.5) for f in pops]
            # leftmost head: its (rotated) label must stay clear of the protein name
            perp0 = (M.asc(f_site) - M.desc(f_site)) / 2
            ext_left = min(
                -perp0 * math.sin(th) + dx * math.cos(th) - dy * math.sin(th)
                for f in pops
                for dx in (0, M.w(f["label"], f_site))
                for dy in (-M.asc(f_site), M.desc(f_site))
            )
            lo_head = max(X(0) + R, X(0) - 0.8 * fs + 0.3 * fs - ext_left)
            hx = spread(xs, d_min, lo_head, X(Lmax) - R)
            if len(pops) > 1 and (len(pops) - 1) * d_min > X(Lmax) - X(0):
                warnings.append(
                    f"{len(pops)} site labels for {pid} cannot all fit at "
                    f"font size {fs}; hide some in the CSV"
                )
            lab_h = max(
                M.w(f["label"], f_site) * abs(math.sin(th)) + thick * abs(math.cos(th))
                for f in pops
            )
            pop_zone = STEM + ELBOW + 2 * R + G + lab_h
        else:
            pop_zone = 0.0
        top = y + (G if y else 0)
        # the protein name sits on the backbone; keep room for it above and below
        name_half = max(H, M.h(f_name) + 0.3 * fs, M.h(f_num) + 0.3 * fs) / 2
        yb = top + max(pop_zone + H / 2, name_half)  # backbone centre

        # ---- name + backbone ---------------------------------------------------
        parts.append(
            tagged(
                P["row"],
                f'<g id="{C.uid(g, "name")}">'
                + C.text(
                    X(0) - 0.8 * fs,
                    yb + (M.asc(f_name) - M.desc(f_name)) / 2,
                    P["name"],
                    f_name,
                    "name",
                    anchor="end",
                    weight="bold",
                )
                + "</g>",
            )
        )
        parts.append(
            f'<g id="{C.uid(g, "backbone")}">'
            +
            # the backbone runs behind the domain boxes, so it is not an obstacle
            C.rect(
                X(0), yb - BB / 2, P["L"] * sx, BB, "backbone", "#CFCFCF", check=False
            )
            + C.text(
                X(P["L"]) + G,
                yb + (M.asc(f_num) - M.desc(f_num)) / 2,
                P["L"],
                f_num,
                "backbone",
                fill="#666",
            )
            + "</g>"
        )
        # name and length label are obstacles for everything placed later
        obstacles = [C.texts[-2][0], C.texts[-1][0]]
        clear = 0.3 * fs

        def blocked(bb):
            return any(
                rect_hit(
                    (bb[0] - clear, bb[1] - clear, bb[2] + clear, bb[3] + clear), ob
                )
                for ob in obstacles
            )

        # ---- domain boxes, lane by lane ----------------------------------------
        lanes = pack(boxes, key=lambda f: (f["s"], f["e"] + 1))
        n_lanes = max(lanes, default=-1) + 1
        biggest = {}
        for f in boxes:
            if f["group"]:
                b = biggest.get(f["group"])
                if b is None or (f["e"] - f["s"]) > (b["e"] - b["s"]):
                    biggest[f["group"]] = f
        dom, outside, nums, links = [], [], [], []
        frag = defaultdict(list)
        yc = yb
        for ln in range(n_lanes):
            lane = [f for f, k in zip(boxes, lanes) if k == ln]
            ybot = yc + H / 2
            # 1) boxes + inside labels; collect labels that do not fit
            pending = []
            for f in lane:
                x0, x1 = X(f["s"] - 1), X(f["e"])
                w = x1 - x0
                own = C.uid(g, "dom", f["label"])
                f["own"] = own
                el = [
                    C.rect(
                        x0,
                        yc - H / 2,
                        w,
                        H,
                        own,
                        f["col"],
                        darker(f["col"]),
                        rx=min(2.5, H / 5),
                    )
                ]
                if f["label"] and (not f["group"] or biggest.get(f["group"]) is f):
                    lf = f_dom
                    while (
                        lf - 0.25 >= min_label_scale * f_dom
                        and M.w(f["label"], lf) > w - 0.5 * fs
                    ):
                        lf -= 0.25
                    if M.w(f["label"], lf) <= w - 0.5 * fs:
                        el.append(
                            C.text(
                                (x0 + x1) / 2,
                                yc + (M.asc(lf) - M.desc(lf)) / 2,
                                f["label"],
                                lf,
                                own,
                                anchor="middle",
                                fill="#1A1A1A",
                            )
                        )
                    else:
                        pending.append(f)
                dom.append(tagged(f["row"], f'<g id="{own}">' + "".join(el) + "</g>"))
                if f["group"]:
                    frag[f["group"]].append((x0, x1, ybot, f["col"], own))
            leader_x = [(X(f["s"] - 1) + X(f["e"])) / 2 for f in pending]
            # 2) residue numbers under the box edges. Anchoring never changes with size:
            #    the start number begins at the domain's start edge, the end number ends
            #    at its end edge. A number that has no room is left out (and reported),
            #    never moved somewhere else where it could be read as a different boundary.
            cur = ybot
            if numbers:
                ytop_n = ybot + max(G, 0.3 * f_num)
                base = ytop_n + M.asc(f_num)
                spans = []
                lane_x = [(X(f["s"] - 1), X(f["e"])) for f in lane]
                cands = []
                for f, (x0, x1) in zip(lane, lane_x):
                    ws, we = M.w(f["s"], f_num), M.w(f["e"], f_num)
                    cands += [
                        (f["s"], x0, "start", x0, x0 + ws, (x0, x1)),
                        (f["e"], x1, "end", x1 - we, x1, (x0, x1)),
                    ]
                for val, xa, anc, lo, hi, own_span in cands:
                    ok = (
                        not any(
                            lo - 0.3 * f_num < h2 and hi + 0.3 * f_num > l2
                            for l2, h2 in spans
                        )
                        and not any(
                            lo - 0.2 * fs < lx < hi + 0.2 * fs for lx in leader_x
                        )
                        and not blocked(
                            (lo, base - M.asc(f_num), hi, base + M.desc(f_num))
                        )
                        # never under a different domain: it would read as that one's boundary
                        and not any(
                            sp != own_span and lo < sp[1] - 0.5 and hi > sp[0] + 0.5
                            for sp in lane_x
                        )
                    )
                    if not ok:
                        omitted.append(f"{P['name']}:{val}")
                        continue
                    spans.append((lo, hi))
                    nums.append(
                        C.text(xa, base, val, f_num, "numbers", anchor=anc, fill="#666")
                    )
                cur = ytop_n + M.h(f_num)
            # 3) labels that did not fit: rows below, with leader lines
            if pending:
                # Each label hangs under its box on a vertical leader. Rules: labels in a
                # row don't touch; a leader never crosses a label in a row above its own;
                # a label never covers a leader that continues below it. Labels are
                # placed right-to-left, centred if possible, else right-aligned on their
                # leader (so they extend away from leaders already placed). If no row
                # works, a new row is opened at the top - always valid.
                gap, pad = 0.6 * fs, 0.3 * fs
                placed = []  # [lo, hi, lx, row, f, anchor, ax]
                row_h = M.h(f_out) + G
                y0 = cur + G
                # rows needed to get below the name / length label, if they reach this far
                extra = max(
                    0, math.ceil((max(ob[3] for ob in obstacles) - y0) / row_h) + 1
                )
                for f, lx in sorted(zip(pending, leader_x), key=lambda t: -t[1]):
                    wl = M.w(f["label"], f_out)
                    nx = min([x for x in leader_x if x > lx + 1e-6], default=math.inf)
                    eo = min(
                        pad, 0.45 * (nx - lx)
                    )  # right-aligned: stop short of next leader
                    modes = [
                        (lx - wl / 2, lx + wl / 2, "middle", lx),
                        (lx + eo - wl, lx + eo, "end", lx + eo),
                    ]

                    def valid(lo, hi, r):
                        ry = y0 + r * row_h
                        return (
                            not blocked((lo, ry, hi, ry + M.h(f_out)))
                            and all(
                                not (lo - gap < p[1] and hi + gap > p[0])
                                for p in placed
                                if p[3] == r
                            )
                            and all(
                                not (p[0] - pad < lx < p[1] + pad)
                                for p in placed
                                if p[3] < r
                            )
                            and all(
                                not (lo - pad < p[2] < hi + pad)
                                for p in placed
                                if p[3] > r
                            )
                        )

                    nrow = max((p[3] for p in placed), default=-1) + 2 + extra
                    best = None
                    for lo, hi, anc, ax_ in modes:
                        for r in range(nrow):
                            if valid(lo, hi, r):
                                if best is None or r < best[0]:
                                    best = (r, lo, hi, anc, ax_)
                                break
                    if best is None:
                        # open a fresh row above all placed labels (so no leader crosses it),
                        # but low enough to clear the protein name / length label
                        lo, hi, anc, ax_ = modes[1]
                        r0 = 0
                        while blocked(
                            (lo, y0 + r0 * row_h, hi, y0 + r0 * row_h + M.h(f_out))
                        ):
                            r0 += 1
                        for p in placed:
                            p[3] += r0 + 1
                        best = (r0, lo, hi, anc, ax_)
                    r, lo, hi, anc, ax_ = best
                    placed.append([lo, hi, lx, r, f, anc, ax_])
                for lo, hi, lx, r, f, anc, ax_ in placed:
                    ty = y0 + r * row_h + M.asc(f_out)
                    outside.append(
                        tagged(
                            f["row"],
                            f'<g id="{C.uid(f["own"], "label")}">'
                            + C.path(
                                [(lx, ybot), (lx, ty - M.asc(f_out) - 0.15 * fs)],
                                f["own"],
                                "#777",
                                0.4,
                            )
                            + C.text(
                                ax_,
                                ty,
                                f["label"],
                                f_out,
                                f["own"],
                                anchor=anc,
                                fill="#1A1A1A",
                            )
                            + "</g>",
                        )
                    )
                cur = y0 + (max(p[3] for p in placed) + 1) * row_h
            yc = cur + G + H / 2  # next lane
        if boxes:
            ybox_end = yc - H / 2 - G
        else:
            ybox_end = yb + max(BB, H) / 2
        # dotted links between fragments of one discontinuous domain
        for grp, fr in frag.items():
            fr.sort()
            for (a0, a1, ya, c, own), (b0, b1, yb2, _, _) in zip(fr, fr[1:]):
                yy = max(ya, yb2) + 0.25 * G
                links.append(
                    C.path(
                        [
                            (a1 - 1.5, ya),
                            (a1 - 1.5, yy),
                            (b0 + 1.5, yy),
                            (b0 + 1.5, yb2),
                        ],
                        "link",
                        darker(c),
                        0.6,
                        "1.5,1.5",
                    )
                )
        for name, el in (
            ("domains", dom),
            ("domain_links", links),
            ("domain_labels_outside", outside),
            ("boundaries", nums),
        ):
            if el:
                parts.append(f'<g id="{C.uid(g, name)}">' + "".join(el) + "</g>")
        cur = max(ybox_end, yb + name_half) + 0.5 * G

        # ---- secondary structure ----------------------------------------------
        if sss:
            el = []
            for f in sss:
                h = 0.5 * fs if f["type"] != "Turn" else 0.25 * fs
                el.append(
                    tagged(
                        f["row"],
                        C.rect(
                            X(f["s"] - 1),
                            cur + (0.5 * fs - h) / 2,
                            (f["e"] - f["s"] + 1) * sx,
                            h,
                            "ss",
                            f["col"],
                        ),
                    )
                )
                legend[f["type"]] = f["col"]
            parts.append(
                f'<g id="{C.uid(g, "secondary_structure")}">' + "".join(el) + "</g>"
            )
            cur += 0.5 * fs + G

        # ---- region bars (packed by bar OR label width, whichever is wider) ----
        if bars:

            def extent(f):
                x0, x1 = X(f["s"] - 1), X(f["e"])
                c, half = (x0 + x1) / 2, M.w(f["label"], f_region) / 2
                return min(x0, c - half), max(x1, c + half)

            bars.sort(key=lambda f: extent(f)[0])
            lane_h = BAR + 0.15 * fs + M.h(f_region) + G
            lanes_end, bl = [], []
            for f in bars:  # interval packing that also avoids the obstacles
                lo, hi = extent(f)
                k = 0
                while True:
                    if k == len(lanes_end):
                        lanes_end.append(-math.inf)
                    ly = cur + k * lane_h
                    if lo >= lanes_end[k] + 0.8 * fs and not blocked(
                        (lo, ly, hi, ly + lane_h - G)
                    ):
                        lanes_end[k] = hi
                        bl.append(k)
                        break
                    k += 1
            el = []
            for f, ln in zip(bars, bl):
                x0, x1 = X(f["s"] - 1), X(f["e"])
                yy = cur + ln * lane_h
                own = C.uid(g, "bar", f["label"])
                el.append(
                    tagged(
                        f["row"],
                        f'<g id="{own}">'
                        + C.rect(x0, yy, x1 - x0, BAR, own, f["col"])
                        + C.text(
                            (x0 + x1) / 2,
                            yy + BAR + 0.15 * fs + M.asc(f_region),
                            f["label"],
                            f_region,
                            own,
                            anchor="middle",
                            fill="#444",
                        )
                        + "</g>",
                    )
                )
            parts.append(f'<g id="{C.uid(g, "regions")}">' + "".join(el) + "</g>")
            cur += (max(bl) + 1) * lane_h

        # ---- disulfide brackets (short bonds nearest the chain) ----------------
        if brks:
            levels, lvl = [], {}
            for f in sorted(brks, key=lambda f: f["e"] - f["s"]):
                for k, ivs in enumerate(levels):
                    if all(f["e"] < a or f["s"] > b for a, b in ivs) and all(
                        not (a < f["s"] < b) and not (a < f["e"] < b)
                        for lv in levels[k:]
                        for a, b in lv
                    ):
                        ivs.append((f["s"], f["e"]))
                        lvl[id(f)] = k
                        break
                else:
                    levels.append([(f["s"], f["e"])])
                    lvl[id(f)] = len(levels) - 1
            step = 0.5 * fs
            el = [
                tagged(
                    f["row"],
                    C.path(
                        [
                            (X(f["s"] - 0.5), cur),
                            (X(f["s"] - 0.5), cur + step * (lvl[id(f)] + 1)),
                            (X(f["e"] - 0.5), cur + step * (lvl[id(f)] + 1)),
                            (X(f["e"] - 0.5), cur),
                        ],
                        "ss_bond",
                        f["col"],
                        0.8,
                    ),
                )
                for f in brks
            ]
            legend["Disulfide bond"] = TYPE_COLOR["Disulfide bond"]
            parts.append(f'<g id="{C.uid(g, "disulfides")}">' + "".join(el) + "</g>")
            cur += step * len(levels) + G

        # ---- lollipops ----------------------------------------------------------
        if pops:
            ytop = yb - H / 2
            y1, y2 = ytop - STEM, ytop - STEM - ELBOW
            yh = y2 - R
            stems, heads, labs = [], [], []
            perp = (M.asc(f_site) - M.desc(f_site)) / 2  # centre glyphs on the stem
            for f, x, h in zip(pops, xs, hx):
                stems.append(
                    tagged(
                        f["row"], C.path([(x, ytop), (x, y1), (h, y2)], "stem", "#555")
                    )
                )
                heads.append(
                    tagged(
                        f["row"], C.circle(h, yh, R, "head", f["col"], darker(f["col"]))
                    )
                )
                # anchor so that the rotated label starts just above the head
                # centre the glyphs on the head (shift perpendicular to the text) and
                # lift the label until the lowest corner of its rotated box clears the head
                tx = h - perp * math.sin(th)
                w_l = M.w(f["label"], f_site)
                low = max(
                    dx * math.sin(th) + dy * math.cos(th)
                    for dx in (0, w_l)
                    for dy in (-M.asc(f_site), M.desc(f_site))
                )
                ty = yh - R - 0.25 * fs - low
                labs.append(
                    tagged(
                        f["row"],
                        C.text(
                            tx, ty, f["label"], f_site, "site_label", rotate=label_angle
                        ),
                    )
                )
                legend[f["type"]] = f["col"]
            parts.append(
                f'<g id="{C.uid(g, "sites")}"><g id="{C.uid(g, "site_stems")}">{"".join(stems)}</g>'
                f'<g id="{C.uid(g, "site_heads")}">{"".join(heads)}</g>'
                f'<g id="{C.uid(g, "site_labels")}">{"".join(labs)}</g></g>'
            )

        svg.append(f'<g id="{g}">' + "".join(parts) + "</g>")
        y = max(cur, C.ext[3]) + 1.2 * fs

    # ---- shared residue axis (tick spacing chosen so labels never collide) ------
    #   axis="full": line + ticks + numbers | "labels": numbers only | "none": nothing
    if axis != "none":
        f_ax = f_axis
        for step in (10, 20, 25, 50, 100, 200, 250, 500, 1000, 2000, 2500, 5000, 10000):
            widest = M.w(str((Lmax // step) * step), f_ax)
            if (
                step * sx >= widest + 0.8 * fs
                and (step - 1) * sx
                >= (M.w("1", f_ax) + M.w(str(step), f_ax)) / 2 + 0.6 * fs
            ):
                break
        tl = 0.35 * fs if axis == "full" else 0.0
        ax = (
            [C.path([(X(0), y), (X(Lmax), y)], "axis", "#444")]
            if axis == "full"
            else []
        )
        for k in [1] + list(range(step, Lmax + 1, step)):
            xx = X(k - 0.5)
            if axis == "full":
                ax.append(C.path([(xx, y), (xx, y + tl)], "axis", "#444"))
            ax.append(
                C.text(
                    xx,
                    y + tl + 0.2 * fs + M.asc(f_ax),
                    k,
                    f_ax,
                    "axis",
                    anchor="middle",
                    fill="#444",
                )
            )
        svg.append(f'<g id="axis">{"".join(ax)}</g>')
        y += tl + 0.2 * fs + M.h(f_ax) + G * 2

    # ---- legend for site/track types (wraps to stay within the drawing width) ----
    if legend:
        el, lx, row_h = [], X(0), M.h(f_legend) + G
        for t, c in legend.items():
            wi = 2 * R + G + M.w(t, f_legend)
            if lx > X(0) and lx + wi > X(Lmax):
                lx, y = X(0), y + row_h
            el.append(C.circle(lx + R, y + M.h(f_legend) / 2, R, "legend", c))
            el.append(
                C.text(
                    lx + 2 * R + G,
                    y + M.asc(f_legend),
                    t,
                    f_legend,
                    "legend",
                    fill="#333",
                )
            )
            lx += wi + 1.2 * fs
        svg.append(f'<g id="legend">{"".join(el)}</g>')

    # ---- canvas = bounding box of everything + margin --------------------------
    pad = fs
    x0, y0, x1, y1 = C.ext
    vb = (x0 - pad, y0 - pad, x1 - x0 + 2 * pad, y1 - y0 + 2 * pad)
    doc = (
        f'<?xml version="1.0" encoding="UTF-8"?>\n'
        f'<svg xmlns="http://www.w3.org/2000/svg" version="1.1" '
        f'width="{vb[2]:.1f}pt" height="{vb[3]:.1f}pt" '
        f'viewBox="{vb[0]:.2f} {vb[1]:.2f} {vb[2]:.2f} {vb[3]:.2f}">\n'
        + "\n".join(svg)
        + "\n</svg>\n"
    )
    return Figure(doc, C.overlaps(), omitted, warnings, M.source)
