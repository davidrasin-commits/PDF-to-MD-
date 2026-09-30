"""Locate a pattern in the converted book corpus and report a citable hit:
book, enclosing section heading, PDF page, printed page, excerpt.

    python cite.py "prewhiten"                 # whole corpus
    python cite.py "taper" -b 11_0 -b 12_0     # restrict to books
    python cite.py "outlier" -C 300            # wider excerpt
"""
import argparse
import re
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

CONV = Path(__file__).parent / "converted"
PAGE = re.compile(r"^\{(\d+)\}-{5,}.*$", re.M)
HEAD = re.compile(r"^(#{1,4})\s+(.*?)\s*$", re.M)

# printed-page offset: printed = page_marker + offset.
# P&W files carry the printed range in the filename (pp_187_330 -> +187).
OFFSET = {"Nonlinear_Oscillations": -15, "Bendat_Piersol": -12}


def offset_for(stem: str):
    m = re.search(r"pp_(\d+)_\d+", stem)
    if m:
        return int(m.group(1))
    for k, v in OFFSET.items():
        if stem.startswith(k):
            return v
    return None


def anchors(text):
    """Sorted (pos, kind, value) for page markers and headings."""
    a = [(m.start(), "page", int(m.group(1))) for m in PAGE.finditer(text)]
    a += [(m.start(), "head", m.group(2)) for m in HEAD.finditer(text)]
    return sorted(a)


def main(argv):
    ap = argparse.ArgumentParser()
    ap.add_argument("pattern")
    ap.add_argument("-b", "--book", action="append", default=[],
                    help="substring of the book filename; repeatable")
    ap.add_argument("-C", "--context", type=int, default=200)
    ap.add_argument("-i", "--ignore-case", action="store_true", default=True)
    ap.add_argument("-m", "--max", type=int, default=25)
    args = ap.parse_args(argv)

    rx = re.compile(args.pattern, re.I if args.ignore_case else 0)
    files = sorted(CONV.glob("*.md"))
    if args.book:
        files = [f for f in files if any(b in f.stem for b in args.book)]

    n = 0
    for f in files:
        text = f.read_text(encoding="utf-8")
        anc = anchors(text)
        off = offset_for(f.stem)
        for m in rx.finditer(text):
            page, head = None, None
            for pos, kind, val in anc:
                if pos > m.start():
                    break
                if kind == "page":
                    page = val
                else:
                    head = val
            if n >= args.max:
                print(f"... (more hits suppressed; raise --max)")
                return 0
            n += 1
            printed = f"p.{page + off}" if (off is not None and page is not None) else "p.?"
            lo, hi = max(0, m.start() - args.context), m.end() + args.context
            ex = re.sub(r"\s+", " ", text[lo:hi]).strip()
            print(f"\n[{n}] {f.stem[:34]} | {head} | pdf {page} | {printed}")
            print(f"    ...{ex}...")
    if n == 0:
        print("no hits")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
