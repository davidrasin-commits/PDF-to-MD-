# PDF to MD

Convert book-length PDFs (textbooks, scanned scientific books) to Markdown with LaTeX maths intact,
using [marker](https://github.com/datalab-to/marker) + surya OCR locally on GPU.

Packaged as a Claude Code skill: see [SKILL.md](SKILL.md) for the run loop, the four silent failure modes,
QA checks, and page-accurate citation.

Install as a skill: copy this folder to `~/.claude/skills/pdf-book-to-markdown/`.

| Script | Step |
|---|---|
| `survey.py` | page count + text-layer density per PDF |
| `run_all_books.py <src-dir> [filter] [--force-ocr]` | chunked, resumable conversion |
| `repair.py <src-dir>` | recover dropped pages, merge in page order |
| `garble.py`, `inline_health.py`, `collapse.py` | output QA |
| `cite.py "term"` | search with printed-page citations |
