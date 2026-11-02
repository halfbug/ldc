# Scout PDFs — source

Builds `../Scout-Developer-Guide.pdf` and `../Scout-Streaming-Guide.pdf`.

```bash
cd ~/ldc/feature-overview/book-source
uv venv .venv && uv pip install --python .venv/bin/python reportlab matplotlib
.venv/bin/python diagrams.py                                  # developer guide figures → fig/
.venv/bin/python book.py ../Scout-Developer-Guide.pdf          # developer guide
.venv/bin/python sse_diagrams.py                              # streaming guide figures → fig/s*.png
.venv/bin/python sse_guide.py ../Scout-Streaming-Guide.pdf     # streaming guide
```

- `book.py` — the developer guide: chapter text, code snippets and layout (self-contained).
- `bookkit.py` — shared layout helpers (styles, code blocks, figures, callouts, tables, page template), used by `sse_guide.py`.
- `diagrams.py`, `sse_diagrams.py` — every UML diagram and chart (matplotlib), written to `fig/`.
- Code snippets were taken from branch `ONLINE-5385_scout_release_2` in both repos; re-check them when the code moves.
