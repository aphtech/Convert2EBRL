# liblouis integration: page list titles

## Why

eBraille 1.0, section 8.3.2 (Page list):

> Each entry in the page list MUST include the print page number equivalent in a title attribute.

The spec's example puts the `title` on the `<a>` inside each `<li>`:

```html
<li><a href="chap01.html#p001" title="1">⠼⠁</a></li>
```

Before this change, `index.html` page list entries had no `title`. `PageRef.title` existed but was always set to `""` and never written out.

## What changed

### New: `vendor/liblouis` workspace package (distribution `liblouis`, import `louis`)

liblouis does not publish its Python bindings to PyPI. The `louis` and `pylouis` projects on PyPI are unrelated to liblouis and must not be used. Everything here comes from liblouis v3.39.0:

| File | Source |
| --- | --- |
| `src/louis/__init__.py` | Official ctypes bindings (`python/louis/__init__.py.in`). The only change is the library loading, marked with a `Convert2EBRL` comment: it loads `liblouis.dll` from the package directory on Windows and a system liblouis elsewhere. |
| `src/louis/liblouis.dll` | `bin/` of `liblouis-3.39.0-win64.zip`. The sha256 `64d669ac…fbc6591` matches the GitHub release asset digest. It only depends on `KERNEL32.dll` and `msvcrt.dll`. |
| `src/louis/tables/` | `unicode.dis`, `en-ueb-g1.ctb` and the 7 tables they include (about 95 KB, not the full 15 MB table set). |
| `src/louis/bundled.py` | New helper: `table_path(name)` returns the absolute path to a bundled table. |
| `COPYING.LESSER` | liblouis license (LGPL-2.1-or-later). |
| `README.md` | Provenance and update steps. |

Tables are passed to liblouis as absolute paths. Setting `LOUIS_TABLEPATH` from Python does not reach the DLL, because it keeps a separate `msvcrt` environment, and `lou_setDataPath` is deprecated.

### `brf2ebrl`

- `pyproject.toml`: depends on `liblouis`, with `[tool.uv.sources] liblouis = { workspace = true }`.
- New `src/brf2ebrl/utils/back_translation.py`: `back_translate_page_number(braille) -> str`. It back-translates with `unicode.dis` + `en-ueb-g1.ctb` and caches results. It uses grade 1 because page numbers are uncontracted, and grade 2 would turn roman numerals into words (`⠭` → "it", `⠇` → "like"). It logs a warning if liblouis returns untranslatable markers.
- `src/brf2ebrl/plugin.py`: `EBrlZippedBundler._create_navigation_html` fills `PageRef.title` with the back-translated page number.
- `src/brf2ebrl/utils/ebrl.py`: page list links are written as `<a href="…" title="…">`.
- New `tests/test_back_translation.py`: tests page number back-translation (arabic, roman, `W1`-style prefixes, continuation `a2`, ranges `1-2`) and checks that the nav page list outputs `title`.

### Workspace and GUI

- Root `pyproject.toml`: adds `vendor/liblouis` to the workspace members.
- `uv.lock`: adds the `liblouis` entry.
- `gui/Convert2EBRL.pyw`: new Nuitka options. `--include-package-data` copies the tables but never DLLs, so the DLL needs its own option:
  ```
  # nuitka-project: --include-package-data=louis
  # nuitka-project: --include-data-files={MAIN_DIRECTORY}/../vendor/liblouis/src/louis/liblouis.dll=louis/liblouis.dll
  ```
- Root `README.md`: lists the `vendor/liblouis` subproject.
- `.github/workflows/python-app.yml`: the "Collect files for artifact" step copies liblouis's `COPYING.LESSER` to `Convert2EBRL.dist\louis\` in the artifact and release zip, as the LGPL requires.

## Result

```html
<a href="ebraille/vol0.html#page_1" title="W1">⠠⠺⠼⠁</a>
<a href="ebraille/vol0.html#page_6" title="1-2">⠼⠁⠤⠼⠃</a>
<a href="ebraille/vol0.html#page_7" title="a2">⠁⠼⠃</a>
```

## Verification

- `uv run pytest` in `brf2ebrl`: 137 passed, 4 failed. The 4 failures are in `test_block_detectors.py` and also fail without these changes.
- CLI conversion of `A-B2517-V01.BRF` and `A-B2517-V02.BRF`: all 54 page list entries have a `title`, and none have untranslatable markers.
- Minimal Nuitka standalone build using the options above: the exe loads the bundled DLL and tables and back-translates correctly.
- Full GUI Nuitka build (`gui\Convert2EBRL.pyw`, same command as CI): succeeds, and `Convert2EBRL.dist/louis/` contains `liblouis.dll` and all 9 tables.

## Status

Committed on branch `liblouis-page-list-titles`, not yet pushed. The files touched are exactly those listed under "What changed" plus this file.

## Follow-ups

- Other braille codes (non-UEB plugins) will need their own tables. The table choice is currently fixed to UEB grade 1 in `back_translation.py`.
- The same mechanism can fill the nav `<title>` and `dc:title`, which are currently `"-"`. That needs `en-ueb-g2.ctb` added to the bundled tables.
