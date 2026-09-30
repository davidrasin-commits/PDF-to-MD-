"""Measure how much of each conversion is garbled passthrough of a bad embedded
text layer, rather than clean OCR'd LaTeX."""
import re, sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
PAGE = re.compile(r"^\{(\d+)\}-{5,}\s*$", re.M)

SIGNS = {
    "esc-$": re.compile(r"\\\$"),          # \$ : dollar that is not math
    "U+FFFD": re.compile("�"),         # replacement char = lost glyph
    "<sup>": re.compile(r"<sup>|<sub>"),    # html sub/sup = text-layer passthrough
}

print(f"{'esc$':>6} {'FFFD':>6} {'sup':>6} {'/page':>7}  book")
rows = []
for f in sorted(Path("converted").glob("*.md")):
    txt = f.read_text(encoding="utf-8")
    n = max(1, len(PAGE.findall(txt)))
    c = {k: len(p.findall(txt)) for k, p in SIGNS.items()}
    tot = sum(c.values())
    rows.append((tot / n, c, n, f.stem))
for per, c, n, name in sorted(rows, reverse=True):
    print(f"{c['esc-$']:6d} {c['U+FFFD']:6d} {c['<sup>']:6d} {per:7.1f}  {name[:52]} ({n}p)")
