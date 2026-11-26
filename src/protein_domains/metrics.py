"""Text widths and heights in pt."""
from pathlib import Path


class Metrics:
    """Text widths from the real font (via matplotlib) when possible.

    Arial/Helvetica fall back to Liberation Sans / Arimo / Nimbus Sans, which are
    metric-compatible. Without matplotlib a deliberately generous estimate is used.
    Vertical metrics are Arial's (ascender 0.75 em incl. accents-free caps/ascenders,
    descender 0.22 em).
    """
    ASC, DESC = 0.75, 0.22
    SUBST = {"arial": ["Liberation Sans", "Arimo", "Helvetica", "Nimbus Sans"],
             "helvetica": ["Arial", "Liberation Sans", "Arimo", "Nimbus Sans"]}

    def __init__(self, font):
        self.source = "estimate"
        self._cache = {}
        try:
            from matplotlib.font_manager import FontProperties, findfont
            from matplotlib.textpath import TextToPath
            import logging
            logging.getLogger("matplotlib.font_manager").setLevel(logging.ERROR)
            path = None
            for fam in [font] + self.SUBST.get(font.lower(), []):
                try:
                    path = findfont(FontProperties(family=fam), fallback_to_default=False)
                    break
                except ValueError:
                    continue
            if path:
                self._fp = FontProperties(fname=path)
                self._t2p = TextToPath()
                self.source = Path(path).name
        except ImportError:
            pass

    def w(self, s, size):
        """Advance width in pt. Measured once per string at 1 pt, then scaled."""
        s = str(s)
        if s not in self._cache:
            if self.source != "estimate":
                fp = self._fp.copy()
                fp.set_size(100)
                w1 = self._t2p.get_text_width_height_descent(s, fp, ismath=False)[0] / 100
            else:   # generous Arial-like estimate
                narrow = sum(ch in "iljtfrI.,:;'|!()[] " for ch in s)
                wide = sum(ch in "mwMW@" for ch in s)
                w1 = 1.08 * (0.56 * len(s) - 0.27 * narrow + 0.3 * wide)
            self._cache[s] = w1
        return self._cache[s] * size

    def asc(self, size):
        return self.ASC * size

    def desc(self, size):
        return self.DESC * size

    def h(self, size):
        return (self.ASC + self.DESC) * size
