"""Re-run pages that marker silently dropped, then rebuild the merged markdown.

marker loses whole internal batches: rc=0, output written, a contiguous run of
pages simply absent. Re-running a narrow range batches differently and recovers
them. Rebuilds the merged .md from a {page: text} map over every chunk + repair
dir, so it is idempotent and dedupes by construction.

    python repair.py "photosynthesis books"
"""
import os, re, shutil, subprocess, sys, time
from pathlib import Path

import pypdfium2 as pdfium

ROOT = Path(__file__).parent
SRC = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else ROOT
OUT = SRC / "converted"
MARKER = ROOT / ".venv-marker" / "Scripts" / "marker_single.exe"
PAGE = re.compile(r"^\{(\d+)\}-{5,}\s*$", re.M)

ENV = dict(os.environ)
ENV["SURYA_INFERENCE_BACKEND"] = "llamacpp"
ENV["LLAMA_CPP_BINARY"] = str(ROOT / ".llama-cpp" / "llama-server.exe")
ENV["PATH"] = str(ROOT / ".llama-cpp") + os.pathsep + ENV["PATH"]
ENV["HF_HUB_DISABLE_SYMLINKS_WARNING"] = "1"


def slug(p): return re.sub(r"[^A-Za-z0-9]+", "_", p.stem).strip("_")[:60]


def pages_in(text):
    """{page_number: body} from one marker markdown."""
    parts = PAGE.split(text)
    return {int(parts[i]): parts[i + 1] for i in range(1, len(parts), 2)}


def harvest(d):
    """Merge every non-empty .md under d into one {page: body} map."""
    out = {}
    for md in sorted(d.rglob("*.md")):
        if md.stat().st_size:
            out.update(pages_in(md.read_text(encoding="utf-8")))
    return out


def runs(nums):
    """[1,2,3,7] -> [(1,3),(7,7)]"""
    out = []
    for n in sorted(nums):
        if out and n == out[-1][1] + 1:
            out[-1][1] = n
        else:
            out.append([n, n])
    return [tuple(r) for r in out]


def reap():
    subprocess.run(["taskkill", "/F", "/IM", "llama-server.exe", "/T"],
                   capture_output=True)


def main():
    for pdf in sorted(SRC.glob("*.pdf")):
        name = slug(pdf)
        chunks = OUT / "chunks" / name
        if not chunks.exists():
            continue
        npages = len(pdfium.PdfDocument(pdf))
        got = harvest(chunks)
        rep = OUT / "repair" / name
        if rep.exists():
            got.update(harvest(rep))
        missing = [p for p in range(npages) if p not in got]
        print(f"=== {name[:50]}  {len(got)}/{npages} present, {len(missing)} missing",
              flush=True)

        for a, b in runs(missing):
            dest = rep / f"{a:04d}_{b:04d}"
            dest.mkdir(parents=True, exist_ok=True)
            t0 = time.time()
            r = subprocess.run(
                [str(MARKER), str(pdf), "--page_range", f"{a}-{b}",
                 "--mode", "balanced", "--paginate_output",
                 "--output_format", "markdown", "--output_dir", str(dest)],
                env=ENV, capture_output=True, text=True)
            new = harvest(dest)
            hit = sorted(set(range(a, b + 1)) & set(new))
            print(f"    {a}-{b}: rc={r.returncode} {time.time()-t0:.0f}s "
                  f"recovered {len(hit)}/{b-a+1}", flush=True)
            got.update(new)
            reap()

        # images sit beside the chunk markdown; collect them, then point links at them
        imgs = OUT / 'images' / name
        for d in (chunks, rep):
            for pat in ('*.jpeg', '*.jpg', '*.png'):
                for img in (d.rglob(pat) if d.exists() else ()):
                    imgs.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(img, imgs / img.name)

        still = [p for p in range(npages) if p not in got]
        body = "\n\n".join(f"{{{p}}}" + "-" * 48 + "\n" + got[p].strip("\n")
                           for p in sorted(got))
        body = body.replace("](_page_", f"](images/{name}/_page_")
        dest = OUT / f"{name}.md"
        dest.write_text(body + "\n", encoding="utf-8")
        print(f"    -> {dest.name}  {len(body):,} chars  "
              f"{len(got)}/{npages} pages  STILL MISSING {still}", flush=True)


def demo():
    assert runs([1, 2, 3, 7]) == [(1, 3), (7, 7)]
    assert runs([84]) == [(84, 84)]
    assert runs([225, 226, 280]) == [(225, 226), (280, 280)]
    assert runs([]) == []
    nl = chr(10)
    t = "{0}-----" + nl + "alpha" + nl + nl + "{1}-----" + nl + "beta" + nl
    assert pages_in(t) == {0: nl + "alpha" + nl + nl, 1: nl + "beta" + nl}
    print("self-check OK")


if __name__ == "__main__":
    sys.exit(demo() if "--demo" in sys.argv else main())
