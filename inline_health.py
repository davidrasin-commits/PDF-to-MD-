"""Inline-math health: a book whose inline maths was OCR'd has many $...$ spans;
one that inherited a bad text layer has few, and lots of *italic* pseudo-math."""
import re, sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
PAGE = re.compile(r"^\{(\d+)\}-{5,}\s*$", re.M)
DD = re.compile(r"\$\$.*?\$\$", re.S)
INLINE = re.compile(r"(?<!\$)\$[^$\n]{1,200}\$(?!\$)")
# italic run containing maths-ish junk = text-layer passthrough of inline maths
JUNK = re.compile(r"\*[^*\n]{2,60}\*")
JUNKY = re.compile(r"[=^_{}\\]|[0-9]\s*[a-zA-Z]|[a-zA-Z]\s*[0-9]")

print(f"{'inline/pg':>9} {'junk/pg':>8} {'ratio':>7}  book")
rows = []
for f in sorted(Path("converted").glob("*.md")):
    txt = f.read_text(encoding="utf-8")
    n = max(1, len(PAGE.findall(txt)))
    prose = DD.sub("", txt)
    inline = len(INLINE.findall(prose))
    junk = sum(1 for m in JUNK.findall(prose) if JUNKY.search(m))
    ratio = inline / max(1, junk)
    rows.append((ratio, inline / n, junk / n, f.stem, n))
for ratio, ipp, jpp, name, n in sorted(rows):
    flag = "  <-- text-layer passthrough" if ratio < 3 and jpp > 1 else ""
    print(f"{ipp:9.1f} {jpp:8.1f} {ratio:7.1f}  {name[:48]} ({n}p){flag}")
