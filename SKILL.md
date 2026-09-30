---
name: pdf-book-to-markdown
description: Use when converting book-length PDFs (textbooks, monographs, scanned scientific books) to Markdown with LaTeX maths intact, using marker + surya OCR locally on GPU. Covers the chunked resumable run loop, the four failure modes that silently corrupt output, post-conversion quality grading, and page-accurate citation back to the printed page. Do NOT use for short PDFs or plain text extraction - use the `markitdown` or `pdf` skill instead.
---

# Book PDF -> Markdown

Scripts live alongside this file. Windows + NVIDIA GPU only; install steps in README.md.

Stack: `marker-pdf` 2.0 + `surya-ocr` on `torch+cu130`, in `.venv-marker/`, with a
llama.cpp CUDA build in `.llama-cpp/`.

## Four gotchas - all four are silent

The first three cost the original run a full day; the fourth was found
later, silently eating 10 pages of a 533-page book. Do not drop any of them.

1. **Force the backend.** `SURYA_INFERENCE_BACKEND=llamacpp`. On NVIDIA, surya
   autodetects `vllm`, which needs Docker and fails in a way marker swallows.
   Also set `LLAMA_CPP_BINARY` and prepend `.llama-cpp` to `PATH`.
2. **rc=0 is not success.** marker exits 0 after a backend crash and writes
   nothing (or an empty `.md`). Grade every chunk on *file content*:
   `.md` exists AND size > 0 AND page-marker count matches the requested range.
3. **Reap the server between chunks.** marker's Windows cleanup hits WinError 87
   and leaks `llama-server.exe` holding VRAM; chunk 3 or 4 then OOMs.
   `taskkill /F /IM llama-server.exe /T` after every chunk, pass or fail.

4. **marker drops whole page batches.** rc=0, markdown written, and a
   contiguous run of pages simply absent - 10 of 533 in one book (a single page,
   then runs of 6 and 3), all dense body text. Chunk size does not affect it.
   Catch it by comparing the `{N}-----` marker count against the requested
   range; re-running the narrow range recovers them 100% of the time
   (`repair.py`). Always diff pages present vs pages requested - a book can
   finish "OK" and be missing whole chapter sections.

## Run loop

1. **Survey** (`survey.py`) - page count + embedded-text density per PDF.
   >200 chars/page = TEXT, >20 = partial, else SCAN. A book with a *bad* text
   layer is the worst case: marker passes it through instead of OCRing, so
   check the garble score afterwards rather than trusting the TEXT label.
2. **Convert** (`run_all_books.py <src-dir> [name-filter] [--force-ocr]`) -
   100-page chunks. Bounded RAM, and a crash
   costs one chunk not a book. Resume by skipping any chunk dir with a non-empty
   `.md`, so the script is safe to re-run after any failure.
   Flags: `--page_range S-E --mode balanced --paginate_output --output_format markdown`.
   `--paginate_output` is mandatory - it emits `{N}-----` markers that everything
   downstream (merge verification, QA, citation) keys off. N is absolute and
   0-indexed: `{204}` is PDF page 205.
3. **Merge + repair** (`repair.py <src-dir>`) - harvests `{page: text}` from
   every chunk *and* repair dir, re-runs any missing page runs, then emits in
   page order. Rebuilding from a page map (rather than splicing) makes it
   idempotent and dedupes for free - safe to re-run any time. It copies images
   to `converted/images/<slug>/` and rewrites `](_page_` links to match; skip
   that and every image link in the corpus silently breaks. Prints
   `STILL MISSING [...]` per book, so unrecoverable pages get named.
4. **QA** - conversion can succeed and still be unusable:
   - `garble.py` - fraction of output that is passthrough of a bad text layer
     rather than clean OCR'd LaTeX.
   - `inline_health.py` - count of `$...$` spans vs `*italic*` pseudo-maths.
     Few `$` + many italics = the text layer was inherited, not OCR'd.
     **False-positives hard on biology.** Italics there are species and gene
     names (*Synechococcus*, *puf*), not lost maths. Always dump the actual
     italic spans before believing the flag.
   - `collapse.py` - consecutive display equations with identical LHS but
     differing RHS. Real maths does not restate a quantity with two values;
     it means a dot/sub/superscript distinction was lost. Check each hit by
     hand - successive refinements of one equation are a legitimate pattern.
   Bad pages get re-run alone and spliced back in (`repair.py`).
5. **Cite** (`cite.py`) - `python cite.py "prewhiten" -b 11_0 -C 300` returns
   book + enclosing heading + PDF page + *printed* page + excerpt. The
   PDF-to-printed page offset is per-book: pass `-o <book-prefix>=<N>`
   (find N by comparing one `{N}-----` marker with the page number printed on it).
   Use `-d <src-dir>/converted` when not running from the output folder.

## Bad text layer: how to spot it and what actually fixes it

`--mode balanced` is documented as "VLM layout model + full-page OCR", but on a
PDF carrying an embedded text layer it will still pass that layer through. If the
layer came from someone else's bad OCR (library scans, Anna's Archive rips), the
errors land in your markdown and `garble.py` will not see them - it looks for
U+FFFD and escaped `$`, and these are all *plausible ASCII*.

The signature is systematic character substitution, worst in notation:

    a/b     -> alb          (slash read as l)
    beta    -> {3  f3  af3
    menaquinone -> mcnaquinonc   (e -> c)

Find it by dumping the most common `*italic*` spans - real substitutions cluster
at the top with high counts. Confirm with a page-count-weighted grep of the
suspect tokens; 496 hits over 164 of 533 pages is a corpus-wide problem, 5 hits
is noise.

**Chunk size does not affect it** - a 6-page re-run in `balanced` reproduces the
identical garble, so do not waste a run testing that. `--force_ocr` is the only
fix: it ignores the text layer entirely.

Before committing the re-run, measure on ~6 of the worst pages:

- text fidelity: garble tokens should go to zero
- images: compare extracted file counts, not `![` counts - `force_ocr` can emit
  an empty `![]()` where `balanced` wrote a VLM figure description
- char delta: a *drop* under `force_ocr` is usually balanced's figure-caption
  padding disappearing, not lost text. Read the diff before concluding.

`force_ocr` trades marker's VLM figure descriptions for character accuracy.
When both matter, run it into a second file (`<name>.ocr.md` via `--force-ocr`)
and keep the balanced output as primary: prose and figures from one, grep and
citation from the other.

## Notes

- Split long books per chapter at the merge step when you want citable units;
  Name them `<chapter>_pp_<first>_<last>_...md` and `cite.py` derives the offset itself.
- Runtime is 2-3 s/page for books with a text layer (1105 pages took 46 min);
  budget 10 s/page under `--force_ocr`. Only genuine SCAN books approach a
  minute a page. Run in the background and grade chunks as they land.
