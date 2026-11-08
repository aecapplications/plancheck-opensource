# Steps 1–2: chapter text and knowledge graph

## Step 1 — Manifest and chapters

Code-book text is copyrighted and never committed. A book ships
`<book>-graph/chapters.manifest.json` (filenames, titles, 1-based inclusive
PDF page ranges, source page count, no text). `chapters/` is rebuilt
locally from the user's own copy of the PDF.

First confirm the PDF path the user gave exists (`ls -l <path>`). If it
doesn't, ask for the correct one. The PDF can live anywhere; `--pdf` takes
any path.

**Existing book** (manifest already committed):

```bash
python tools/split_chapters.py build --book <book> --pdf <path-to-user-pdf>
python tools/split_chapters.py check --book <book>
```

`build` refuses a PDF whose page count differs from `source.page_count`.
A different printing shifts every page range, so ask the user for the
matching printing instead of passing `--force`. Existing files are kept
unless you pass `--overwrite`.

**New book:** draft a manifest from the PDF's bookmarks. `init` creates
`<book>-graph/`. If you copy the PDF into that directory, it stays
untracked (`*-graph/*.pdf` is gitignored).

```bash
python tools/split_chapters.py init --book <book> --pdf <path> --level 1
```

`--level` is the bookmark depth where chapters sit: 1 for CRC and CEC, 2
for CBC. For an unknown book, start with 1. If that level is empty, the
tool lists the levels that exist. If level 1 holds only front matter, try
the next level and pick the one whose entries are the chapters and
appendices. Then
edit the manifest:

- Drop front matter, tables of contents, and indexes.
- Split very large chapters into separate page ranges with `_a`/`_b`
  suffixes (CRC's `chapter_6_wall_construction_a.md`/`_b.md` is the
  example).
- Every filename needs a leading `NN_` or `chNN_`-style token followed by
  `_`. graphify and `make_dispatch.py` map node ids to files by that token.

Run `build`, open two or three of the generated files to confirm each one
starts at its chapter heading, fix the page ranges, and rebuild with
`--overwrite`. Commit the manifest; `chapters/` is gitignored in the public
repo.

## Step 2 — Graphify

Run graphify from **inside** the book directory, because it writes
`graphify-out/` into the current directory and records `source_file` paths
relative to it (`chapters/...`):

```
cd <book>-graph
/graphify chapters --obsidian
```

`--obsidian` also builds the local Obsidian vault the repo's books were
made with; it is optional. This produces
`<book>-graph/graphify-out/graph.json`, `GRAPH_REPORT.md`, and
`cost.json`, which are committed. The obsidian vault, caches, and
`chunk_*.json` stay local; `.gitignore` already covers them.

- Budget about 3–3.5M agent tokens for a full code book. CBC logged about
  1.42M for 11 of 26 chunks.
- Split big chapter sets before dispatching graphify subagents.
  `cec-graph/extract_chunks.py`, `merge_chunks.py`, and
  `relabel_and_export.py` are a worked example of a chunked run.
- Node ids must carry the chapter-file token prefix (for example
  `ch15_section_1501_general` in CBC). Step 3's `chain.py` adaptation and
  step 4's file resolution depend on it.
