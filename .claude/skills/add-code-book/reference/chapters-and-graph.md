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

**New book:**

1. **Pick the book id**: a short lowercase abbreviation of the code's name
   (`cfc` for the California Fire Code, `calgreen`, `cmc`, `cpc`). It
   names `<book>-graph/`, the webapp `Book` entry, and the prompts module,
   so it's hard to change later.
2. **Find the chapter level.** Run `init` without `--chapters-only` at a
   guessed `--level`. It lists the levels present if that one is empty.
   Open the manifest and look for the level whose entries are
   `CHAPTER …` / `APPENDIX …` (CRC and CEC: 1; CBC and CFC: 2).
3. **Draft the manifest:**
   ```bash
   python tools/split_chapters.py init --book <book> --pdf <path> --level <n> --chapters-only --force
   ```
   `--chapters-only` keeps chapter, appendix, article, annex, and part
   entries (ICC `[A]`-style tags allowed). It folds each **matrix adoption
   table** into the chapter that follows. California's ICC-based books
   bookmark these tables separately, before every chapter, and they say
   which state agencies adopt which sections, so they belong with their
   chapter. It drops `RESERVED` placeholders and any other non-chapter
   entry (front matter, index), printing each dropped title. Filenames get
   CBC-style tokens, for example `ch9_chapter_9_fire_protection….md` and
   `appp_appendix_p_….md`. Override the patterns with `--keep`, `--fold`,
   and `--drop` (regexes) if a book is laid out differently. `init` creates
   `<book>-graph/`. A PDF copied there stays untracked
   (`*-graph/*.pdf` is gitignored).
4. **Review the manifest:**
   - Read the dropped titles; restore anything that is really a chapter.
   - Split very large chapters into separate page ranges with `_a`/`_b`
     suffixes (CRC's `chapter_6_wall_construction_a.md`/`_b.md`).
     Existing books top out around 70–130 pages per file.
   - Every filename must keep its leading token (`NN_`, `chNN_`, or
     `appX_`) followed by `_`. graphify and `make_dispatch.py` map node ids
     to files by that token.

Run `build`, open two or three of the generated files to confirm each one
starts at its chapter heading, fix the page ranges, and rebuild with
`--overwrite`. Commit the manifest. In the private repo, commit `chapters/`
too. A public clone gitignores it.

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
