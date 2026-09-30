# PDF to MD

Convert book-length PDFs (textbooks, scanned scientific books) to Markdown with LaTeX maths intact,
using [marker](https://github.com/datalab-to/marker) + surya OCR locally on GPU.

Packaged as a Claude Code skill: see [SKILL.md](SKILL.md) for the run loop, the four silent failure modes,
QA checks, and page-accurate citation.

## Install

Requires **Windows + an NVIDIA GPU** (CUDA 13 driver) and Python 3.12.

1. Clone into your Claude Code skills folder (the folder name must match the skill name):
   ```
   git clone https://github.com/davidrasin-commits/PDF-to-MD-.git %USERPROFILE%\.claude\skills\pdf-book-to-markdown
   cd %USERPROFILE%\.claude\skills\pdf-book-to-markdown
   ```
2. Python environment, in `.venv-marker\` inside that folder (the scripts look for it there):
   ```
   py -3.12 -m venv .venv-marker
   .venv-marker\Scripts\pip install torch==2.13.0 torchvision==0.28.0 --index-url https://download.pytorch.org/whl/cu130
   .venv-marker\Scripts\pip install -r requirements.txt
   ```
3. llama.cpp, in `.llama-cpp\` inside that folder: from release
   [b10595](https://github.com/ggml-org/llama.cpp/releases/tag/b10595) download the Windows
   **CUDA 13 x64** zip and the matching **cudart** zip, and unzip both into `.llama-cpp\`
   so that `.llama-cpp\llama-server.exe` exists.

Model weights download automatically on the first run.

## Use

Ask Claude Code to convert a book PDF and it will follow the skill, or run the scripts yourself
with the venv's Python:
```
.venv-marker\Scripts\python run_all_books.py D:\books          # writes D:\books\converted\ 
.venv-marker\Scripts\python repair.py D:\books
python cite.py "spectral window" -d D:\books\converted -o MyBook=-12
```

| Script | Step |
|---|---|
| `survey.py [dir]` | page count + text-layer density per PDF |
| `run_all_books.py <src-dir> [filter] [--force-ocr]` | chunked, resumable conversion |
| `repair.py <src-dir>` | recover dropped pages, merge in page order |
| `garble.py`, `inline_health.py`, `collapse.py` `[converted-dir]` | output QA |
| `cite.py "term" [-d dir] [-o BOOK=N]` | search with printed-page citations |
