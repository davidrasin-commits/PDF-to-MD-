"""Page count + embedded-text check for every PDF under books/."""
from pathlib import Path
import pypdfium2 as pdfium

ROOT = Path(__file__).parent
pdfs = sorted(p for p in ROOT.rglob("*.pdf") if ".venv-marker" not in p.parts)

print(f"{'pages':>6} {'txt/page':>9}  {'layer':<9} file")
total = 0
for p in pdfs:
    try:
        d = pdfium.PdfDocument(p)
        n = len(d)
        idx = sorted({0, n // 4, n // 2, (3 * n) // 4, n - 1})
        chars = sum(len(d[i].get_textpage().get_text_range().strip()) for i in idx)
        per = chars / len(idx)
        layer = "TEXT" if per > 200 else ("partial" if per > 20 else "SCAN")
        total += n
        print(f"{n:6d} {per:9.0f}  {layer:<9} {p.relative_to(ROOT)}")
    except Exception as e:
        print(f"{'ERR':>6} {'':>9}  {'':<9} {p.relative_to(ROOT)}  ({e})")
print(f"\ntotal pages across all PDFs: {total}")
