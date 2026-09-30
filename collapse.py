"""Detect collapsed notation: consecutive display equations whose LHS is
identical but whose RHS differs. Real maths does not restate the same quantity
with different values -- it means a distinction (usually dot count in a
subscript, or a sub/superscript) was lost in OCR."""
import re, sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
PAGE = re.compile(r"^\{(\d+)\}-{5,}\s*$", re.M)
DD = re.compile(r"\$\$(.+?)\$\$", re.S)
TAG = re.compile(r"\\quad\s*\(\d[\d.]*\)\s*$")


def lhs_rhs(eq):
    eq = TAG.sub("", eq).strip()
    if eq.count("=") != 1:
        return None
    l, r = eq.split("=", 1)
    return l.strip(), r.strip()


total = 0
for f in sorted(Path("converted").glob("*.md")):
    parts = PAGE.split(f.read_text(encoding="utf-8"))
    pages = {int(parts[i]): parts[i + 1] for i in range(1, len(parts), 2)}
    hits = []
    for p, s in sorted(pages.items()):
        eqs = [lhs_rhs(m.group(1)) for m in DD.finditer(s)]
        eqs = [e for e in eqs if e]
        for a, b in zip(eqs, eqs[1:]):
            if a[0] == b[0] and a[1] != b[1] and len(a[0]) > 6:
                hits.append((p + 1, a[0][:52], a[1][:26], b[1][:26]))
    if hits:
        total += len(hits)
        print(f"== {f.stem[:46]}: {len(hits)}")
        for pg, l, r1, r2 in hits[:4]:
            print(f"   p{pg}: {l}=  {r1}   VS   {r2}")
print(f"\nTOTAL collapsed-notation suspects: {total}")
