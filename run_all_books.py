"""Convert every PDF under books/ to markdown, resumably.

Same hardening as the Nonlinear_Oscillations run:
  - SURYA_INFERENCE_BACKEND=llamacpp (NVIDIA autodetect picks vllm, which needs Docker)
  - marker exit code 0 is NOT proof of success -> every chunk graded on file content
  - llama-server reaped between chunks (marker's Windows cleanup bug leaks VRAM)
  - chunked at CHUNK pages: bounded RAM, and a crash costs one chunk not a book
"""
import os, re, shutil, subprocess, sys, time
from pathlib import Path

import pypdfium2 as pdfium

ROOT = Path(__file__).parent                       # install root: venv + llama.cpp
ARGS = [a for a in sys.argv[1:] if not a.startswith("--")]
FORCE = "--force-ocr" in sys.argv   # bypass a bad embedded text layer; drops VLM fig captions
FILTER = ARGS[1] if len(ARGS) > 1 else None       # substring match on filename
SRC = Path(ARGS[0]).resolve() if ARGS else ROOT   # where the PDFs are
SUB = "chunks_ocr" if FORCE else "chunks"
SUFFIX = ".ocr" if FORCE else ""
VENV = ROOT / ".venv-marker" / "Scripts"
MARKER = VENV / "marker_single.exe"
OUT = SRC / "converted"
CHUNK = 100

ENV = dict(os.environ)
ENV["SURYA_INFERENCE_BACKEND"] = "llamacpp"
ENV["LLAMA_CPP_BINARY"] = str(ROOT / ".llama-cpp" / "llama-server.exe")
ENV["PATH"] = str(ROOT / ".llama-cpp") + os.pathsep + ENV["PATH"]
ENV["HF_HUB_DISABLE_SYMLINKS_WARNING"] = "1"

SKIP = {"Nonlinear_Oscillations.pdf"}  # already done


def slug(p: Path) -> str:
    return re.sub(r"[^A-Za-z0-9]+", "_", p.stem).strip("_")[:60]


def survey(p: Path):
    d = pdfium.PdfDocument(p)
    n = len(d)
    idx = sorted({0, n // 4, n // 2, (3 * n) // 4, n - 1})
    chars = sum(len(d[i].get_textpage().get_text_range().strip()) for i in idx)
    per = chars / len(idx)
    return n, per, ("TEXT" if per > 200 else "partial" if per > 20 else "SCAN")


def reap():
    subprocess.run(["taskkill", "/F", "/IM", "llama-server.exe", "/T"],
                   capture_output=True)


def convert(pdf: Path, npages: int) -> Path:
    name = slug(pdf)
    chdir = OUT / SUB / name
    chdir.mkdir(parents=True, exist_ok=True)
    for start in range(0, npages, CHUNK):
        end = min(start + CHUNK - 1, npages - 1)
        tag = f"{start:04d}_{end:04d}"
        dest = chdir / tag
        mds = list(dest.rglob("*.md"))
        if mds and mds[0].stat().st_size > 0:
            print(f"    SKIP {tag} (done)", flush=True)
            continue
        t0 = time.time()
        cmd = [str(MARKER), str(pdf), "--page_range", f"{start}-{end}",
               "--mode", "balanced", "--paginate_output",
               "--output_format", "markdown", "--output_dir", str(dest)]
        if FORCE:
            cmd.append("--force_ocr")
        r = subprocess.run(cmd, env=ENV, capture_output=True, text=True)
        mds = [m for m in dest.rglob("*.md") if m.stat().st_size > 0]
        dt = time.time() - t0
        if mds:
            pgs = len(re.findall(r"^\{\d+\}-{5,}", mds[0].read_text(encoding="utf-8"), re.M))
            want = end - start + 1
            # rc=0 and a non-empty .md still hides dropped page batches - grade on count
            lbl = "OK  " if pgs == want else "SHORT"
            print(f"    {lbl} {tag} rc={r.returncode} {dt:.0f}s pages={pgs}/{want}", flush=True)
        else:
            tail = (r.stderr or "").strip().splitlines()[-1:] or ["(no stderr)"]
            print(f"    FAIL {tag} rc={r.returncode} {dt:.0f}s :: {tail[0][:140]}", flush=True)
        reap()
    return chdir


def merge(pdf: Path, chdir: Path, npages: int):
    name = slug(pdf)
    imgs = OUT / "images" / name
    parts, seen = [], {}
    for d in sorted(chdir.iterdir()):
        mds = [m for m in d.rglob("*.md") if m.stat().st_size > 0]
        if not mds:
            continue
        text = mds[0].read_text(encoding="utf-8")
        for pg in re.findall(r"^\{(\d+)\}-{5,}", text, re.M):
            seen.setdefault(int(pg), 0)
            seen[int(pg)] += 1
        parts.append(text)
        for img in mds[0].parent.glob("*.jpeg"):
            imgs.mkdir(parents=True, exist_ok=True)
            shutil.copy2(img, imgs / img.name)
    merged = "\n\n".join(p.strip("\n") for p in parts) + "\n"
    merged = merged.replace("](_page_", f"](images/{name}/_page_")
    dest = OUT / f"{name}{SUFFIX}.md"
    dest.write_text(merged, encoding="utf-8")
    missing = [p for p in range(npages) if p not in seen]
    dupes = [p for p, c in seen.items() if c > 1]
    print(f"    -> {dest.name}  {len(merged):,} chars  pages {len(seen)}/{npages}"
          f"  missing={len(missing)} dupes={len(dupes)}", flush=True)
    return len(missing), len(dupes)


def main():
    pdfs = sorted(p for p in SRC.rglob("*.pdf")
                  if ".venv-marker" not in p.parts and p.name not in SKIP
                  and (FILTER is None or FILTER.lower() in p.name.lower()))
    print(f"{'pages':>6} {'txt/pg':>7}  {'layer':<8} file", flush=True)
    info = []
    for p in pdfs:
        n, per, layer = survey(p)
        info.append((p, n, layer))
        print(f"{n:6d} {per:7.0f}  {layer:<8} {p.relative_to(SRC)}", flush=True)
    print(f"\nTOTAL {sum(i[1] for i in info)} pages across {len(info)} PDFs\n", flush=True)

    for p, n, layer in info:
        print(f"=== {p.name}  ({n}p, {layer}) {time.strftime('%H:%M:%S')}", flush=True)
        chdir = convert(p, n)
        merge(p, chdir, n)
    print(f"\nALL BOOKS DONE {time.strftime('%H:%M:%S')}", flush=True)


if __name__ == "__main__":
    sys.exit(main())
