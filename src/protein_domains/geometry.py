"""Interval packing, label spreading and the collision tests used by the overlap check."""

import math


def pack(items, key, gap=0.0):
    """Pack intervals greedily into lanes and return each item's lane index.

    Items must be sorted by start.
    """
    lanes_end, out = [], []
    for it in items:
        s, e = key(it)
        for k, end in enumerate(lanes_end):
            if s >= end + gap:
                lanes_end[k] = e
                out.append(k)
                break
        else:
            lanes_end.append(e)
            out.append(len(lanes_end) - 1)
    return out


def spread(xs, d, lo=None, hi=None):
    """Move positions apart by at least d, displacing them as little as possible.

    The result stays inside [lo, hi] when it fits.
    """
    clusters = []
    for x in xs:
        clusters.append([x, 1])
        while len(clusters) > 1:
            (s1, n1), (s2, n2) = clusters[-2], clusters[-1]
            if (s1 / n1 + (n1 - 1) * d / 2) + d > (s2 / n2 - (n2 - 1) * d / 2):
                clusters[-2:] = [[s1 + s2, n1 + n2]]
            else:
                break
    out = []
    for s, n in clusters:
        c = s / n
        out += [c - (n - 1) * d / 2 + k * d for k in range(n)]
    if lo is not None and hi is not None and (len(out) - 1) * d <= hi - lo:
        for i in range(len(out)):  # push right of lo
            out[i] = max(out[i], lo + i * d if i == 0 else out[i - 1] + d, lo)
        for i in range(len(out) - 1, -1, -1):  # push left of hi
            lim = hi if i == len(out) - 1 else out[i + 1] - d
            out[i] = min(out[i], lim)
    return out


def rect_poly(bb):
    return [(bb[0], bb[1]), (bb[2], bb[1]), (bb[2], bb[3]), (bb[0], bb[3])]


def poly_hit(P, Q, tol=0.2):
    """Return whether two convex polygons overlap by more than tol (separating axes)."""
    for poly in (P, Q):
        for i in range(len(poly)):
            (x1, y1), (x2, y2) = poly[i], poly[(i + 1) % len(poly)]
            nx, ny = y2 - y1, x1 - x2
            n = math.hypot(nx, ny)
            if n == 0:
                continue
            nx, ny = nx / n, ny / n
            a = [px * nx + py * ny for px, py in P]
            b = [px * nx + py * ny for px, py in Q]
            if max(a) - tol <= min(b) or max(b) - tol <= min(a):
                return False  # found a separating axis
    return True


def rect_hit(a, b, tol=0.0):
    return (
        a[0] < b[2] - tol
        and b[0] < a[2] - tol
        and a[1] < b[3] - tol
        and b[1] < a[3] - tol
    )


def seg_hits_rect(p, q, r, tol=0.3):
    """Return whether segment pq crosses rectangle r shrunk by tol (Liang-Barsky)."""
    x0, y0, x1, y1 = r[0] + tol, r[1] + tol, r[2] - tol, r[3] - tol
    if x0 >= x1 or y0 >= y1:
        return False
    dx, dy = q[0] - p[0], q[1] - p[1]
    t0, t1 = 0.0, 1.0
    for pp, qq in (
        (-dx, p[0] - x0),
        (dx, x1 - p[0]),
        (-dy, p[1] - y0),
        (dy, y1 - p[1]),
    ):
        if pp == 0:
            if qq < 0:
                return False
        else:
            t = qq / pp
            if pp < 0:
                t0 = max(t0, t)
            else:
                t1 = min(t1, t)
            if t0 > t1:
                return False
    return True
