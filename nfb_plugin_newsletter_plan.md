# Plan: NFB Braille Monitor plugin and plugin selector (issue-71043)

Two pieces of work, kept as small as possible:

1. **GUI:** add a combo box that picks the conversion plugin (BANA or NFB).
2. **NFB plugin:** finish `plugins/brf2ebrl_nfb` so it converts the *NFB Braille Monitor* newsletter. It reuses the BANA pipeline and changes only what the newsletter format needs.

Inputs reviewed: `issue-71043/07-26.zip`, `08-26.zip`, `10-26.zip` (the source BRFs plus the hand-made target `.ebrl`), and `issue-71043/Editing notes for NFB Braille Monitor periodicals.docx`. I also ran the current BANA converter on the October issue (`bm2610v01.brf` + `bm2610v02.brf`) and compared its output with the target.

## Implementation status

Implemented on branch `nfb-newsletter-plugin`. Each commit is a point you can test.

| Commit | What | How to test |
|---|---|---|
| Plan and test script | this plan, `issue-71043/run_issue71043.ps1` | `.\issue-71043\run_issue71043.ps1 -Parser BANA` |
| NFB plugin with linked TOC | `plugins/brf2ebrl_nfb`, registered in the workspace, GUI dependencies and Nuitka build; CLI default stays BANA | `uv run pytest` in `plugins/brf2ebrl_nfb`; `.\issue-71043\run_issue71043.ps1` |
| GUI Converter combo box | `general_tab.py`, `brf_to_ebrf.py`, `settings/keys.py` | `uv run Convert2EBRL.pyw` in `gui`, choose NFB, restart, convert |
| Contracted back-translation | `en-ueb-g2.ctb` vendored, `back_translate_contracted()` | `uv run pytest` in `brf2ebrl` |
| Links and optional print HTML | `links.py`, `print_source.py` | `.\issue-71043\run_issue71043.ps1` and `… -NoPrint` |

Results on the three samples (ours / target, for July, Aug/Sept and October):
- **Separators:** 13/11, 16/16, 9/9.
- **Captions:** 9/9, 26/26, 14/14.
- **Bylines:** 10/10, 8/8, 7/7.
- **Dialogue:** October 159/145, Aug/Sept 115/112. July has 20 speaker and continuation paragraphs, which its target does not mark.
- **TOC links:** every entry is linked to the right article (52 links, each checked by following it).
- **With the print file:** the braille text is byte-identical to the run without it.
- **BANA:** output unchanged for the 42 books in `work/ebrl-test-files/books` (§7).

**Changes from the plan, found while implementing:**
- **Page layout:** the plugin forces its own page number positions (odd top right, no print pages). No CLI page layout or GUI profile is needed, and none was added.
- **Page numbers:** BANA's braille page detector only knows Arabic numbers. `brf2ebrl_nfb/pages.py` also accepts the roman numerals of the preliminary pages, which otherwise stay in the text.
- **Paragraphs:** the shared paragraph finder rejects a paragraph that starts on the line holding the top right page number, because it measures the first line without the page number. NFB paragraphs (3-1, 1-3, 5-3, 7-5) are found by indent shape instead. This is safe because the newsletter has no blank lines.
- **Page breaks:** there are none in the output. BANA only turns *print* pages into `doc-pagebreak`, and the newsletter has none, which matches the target. The TOC therefore matches entries to titles by text, with a fuzzy fallback instead of a page number fallback.
- **Captions:** also recognised without brackets (`,,PHOTO ,,CAP;N3`), one cell late, and continued into a second 7-5 paragraph. Other bracketed 7-5 text, such as "[Video begins]", becomes `p.direction`.
- **Bylines:** also "Presented by …" and "An Address Delivered by" with the names on the next line.
- **Print file encoding:** the sample print files are UTF-8, not Windows-1252. The reader uses the declared charset, then UTF-8, then Windows-1252.
- **Print messages:** the "using print file" message and the match summary go to the log, not to notifications, because the GUI and CLI show any notification as a warning.
- **Not done:**
  - the book title from print `<title>`;
  - "skip print when under half the titles match";
  - the link-only fallback for addresses whose back-translation fails.
- **BANA check:** the PDF graphic matcher can place a tactile graphic `<object>` differently between two runs with no code change (A-B2513, A-B2533). The check treats that alone as unchanged.

**Known gaps (left for later):**
- ~~letter salutations and signatures at cell 5 become `h2`~~ (fixed: `p.salutation`, `p.closing`);
- ~~numbered steps become lists~~ (fixed: `ul.steps`);
- bold editor's notes at the margin become `p.left-justified`.

**Round 2 review (`Round 2/*.txt`):**
- **Fixed by pattern:** 5-3 paragraphs starting at the top of a page; headings after a blank first line on an unnumbered page; cell 7 letter closings; quoted article and press release titles (`h1.article-title`); a dateline that happens to fall in centered position; a cell 5 heading followed by a 3-1 paragraph; consecutive photo captions; the special symbols as `<ul>`; a title-page web address over two lines.
- **Sets of blocks** are wrapped by `brf2ebrl_nfb/groups.py` (`div.fm-group`, `blockquote`, `div.letter`, `div.event-details`, `div.roster`, `div.transcript`), and spaced by the plugin's `css/default.css`.
- **June 2026** has no BRF in the repository, so its items are fixed by pattern only and are not checked against the June issue.
- The optional `div.fm-group.issn` (two blank lines before the ISSN) is not done.

**Risk found:** `find_plugins()` imports every installed plugin, so a plugin that fails to import stops the CLI and GUI for BANA too. Making it skip a broken plugin with a warning would be a small change to `brf2ebrl/plugin.py`.

---

## 1. What is different about the newsletter BRFs

From the transcription notes and the samples (40 cells × 25 lines, interpoint, contracted UEB):

| Feature | NFB newsletter BRF | What BANA produces today | What the target `.ebrl` has |
|---|---|---|---|
| Blank lines | Almost none. Centered headings have no blank line before or after. | Treats consecutive centered lines as one block | Separate elements |
| Running heads | None (per the notes) | Running-head pass runs | n/a |
| Braille page numbers | Odd pages only, **top right**. Roman numerals in front matter, Arabic in the body. Numbering continues across volumes. | Detected, but only by luck (the CLI's `interpoint` layout says bottom right) | Not kept |
| Print page numbers | None | Print-page pass runs | n/a |
| Title page (page 1 of each volume) | Lines centered one after another | Merged into a few huge `<h1>`. The ISSN line becomes a `<!-- guide words -->` comment and is lost. | One `<p class="titlepage">` per line |
| Article divider | Centered `"333333333333` (⠐⠒⠒…) at the end of every article | `<pre>` | `<p class="separator">` |
| Article title + byline | Centered title (may wrap to 2 lines), then centered `BY …` (may wrap) with no blank line between | One `<h1>` holding both the title and the byline | `<h1 class="article-title">` + `<p class="byline">` |
| Photo captions | `.<,,PHOTO ,,CAP;N3 … .>` in 7-5 margins at the **start** of an article, often several in a row with no blank lines | The first becomes a `<figure>`. Later ones become `<h3>`/`<h2>`, or are merged into the next heading. | One `<p class="caption">` each |
| Transcripts (dialogue) | Speaker paragraph in 1-3 (`,LIA ,/"O3 …`), continuation paragraph in 5-3 | Nested `<ul>/<li>`, one `<li>` per line (≈1,300 `<li>` in vol 1) | `<p class="dialogue">` / `<p class="dialogue-cont">` |
| Body paragraphs | 3-1, no blank lines | Correct `<p>` (already works) | `<p>` |
| Cell-5/7 subheadings | Blank line before | `create_cell_heading` already works | `<h2>`/`<h3>` |
| TOC | `,3T5TS` plus centered `,"P #A` ("Part 1") dividers. Each entry is "title BY author" at cell 1 with run-overs at cell 3, then guide dots `"""` and the braille page number. Volume 2+ starts "Contents—Part N". | `<ol class="toc">`, but every run-over line becomes a **nested** entry, and short entries lose the page-number span (`,X'S ,\R ,TURN … #GA`) | `<nav>` + `<ul class="toc">`, **each entry a link to its article**, including across volumes (`vol1.xhtml#…`) |
| Special symbols page | Same as BANA | Works well enough | list |
| End of volume | Optional centered TN "Continued in Part XX" | Existing TN detectors | — |

The target `.ebrl` also turns URLs and email addresses into `<a href>` links. **We will do this, in the NFB plugin only** (see 3.4).

TOC entries will also **link to their articles**, including articles in later volumes (see 3.6).

Things in the target that we will **not** try to match: lines joined into one line per paragraph, and dropped page breaks. The target was clearly built from the print HTML, not from the BRF. Our output should keep the braille page breaks, as BANA output does.

### Input: BRF always; print HTML automatically when it is present

The conversion **always works from the BRF files alone**. If the issue's print HTML (`Complete Braille Monitor … .htm`/`.html`) is in the same folder as the BRFs, the NFB plugin **uses it automatically** to improve a few things (see 3.7). If it is not there, nothing changes, the user is not asked anything, and nothing is required. Without print, everything comes from the braille:

| Output | Comes from |
|---|---|
| Structure: headings, bylines, captions, separators, dialogue, TOC | braille layout (centering, indents, `"333…` lines, `.<….>`, speaker colons) |
| Link `href`s | grade 2 back-translation of the braille URL/email (3.4) |
| TOC link targets | matching TOC text to article headings in braille (3.6) |
| Page list | braille page numbers (NFB has no print page numbers) |

Without the print file, a few things in the target cannot be reproduced, and we accept that:
- the h2/h3 distinction between front-matter subheadings, which look the same in braille;
- special classes the target took from the print styling (`attribution`, `salutation`, `plaque`, `steps`, `blocked`);
- readable ids such as `from-the-editor`, unless they are back-translated (optional, 3.6c).

With the print file present, 3.7 recovers the first and third of these and also corrects link addresses. The special classes stay out of scope either way.

## Decisions (answered)

| Question | Decision |
|---|---|
| Caption markup | `<p class="caption">`, matching the client's sample (no image exists) |
| Heading levels | Centered heading after an article separator, or the first in the body = `<h1 class="article-title">`. Other centered headings = `<h2>`. Cell-5/7 headings stay `h2`/`h3` as in BANA. |
| URLs and emails | Turn them into links **now, in the NFB plugin only** |
| Plugin in profiles | No. The combo box has its own `QSettings` key, and the profile file format is unchanged. |
| TOC entries | Link each one to its article's `<h1>`, across volumes too |
| Print HTML | Optional. Use it automatically when it is next to the BRFs; otherwise convert from braille only. |

---

## 2. GUI: plugin selector combo box

Files: `gui/src/convert2ebrl/tabs/general_tab.py`, `gui/src/convert2ebrl/brf_to_ebrf.py`.

1. **`ConversionGeneralSettingsWidget.__init__`** takes a new argument, `plugins: dict[str, Plugin]` (the result of `find_plugins()`).
   - Add a non-editable `QComboBox` labelled "Converter" as the first row of the form. Each item is `plugin.name`, with `plugin.id` stored as item data.
   - Sort the items so that BANA comes first. Entry-point order is not guaranteed.
   - Restore the choice from `QSettings` key `Conversion/plugin` (stores the plugin id). Default to `BANA`, or the first plugin if BANA is missing. Save the id on `currentIndexChanged`, in the same way `Conversion/input_type` is handled today.
   - Expose it as a read-only property `selected_plugin_id`.
2. **`Brf2EbrfWidget`** passes `DISCOVERED_PARSER_PLUGINS` into the general tab.
3. **`on_apply`**: replace `list(DISCOVERED_PARSER_PLUGINS.values())[0]` (line 271) with `DISCOVERED_PARSER_PLUGINS[...]`, looked up by the selected id. `find_plugins()` keys by entry-point name (`bana`, `nfb`), so either key the dict by `plugin.id` or keep a small id→plugin map.
4. **Profile:** not needed. The NFB plugin sets its own page number positions and ignores running heads, so no NFB profile is added and `settings/defaults.py` does not change.

There is no GUI test coverage today (`gui/tests` has only `__init__.py`), so test this by hand: run `uv run Convert2EBRL.pyw`, switch the combo, restart the app and check the choice is remembered, then convert once with each plugin.

### CLI default (one-line safety fix in `brf2ebrl/scripts/brf2ebrl.py`)
`default_plugin_id = parser_modules[0].id` will pick a random plugin once two are installed. Change it to `"BANA"` when BANA is present, otherwise the first plugin. `--parser NFB` then works with no other CLI change.

**Page layout for NFB:** the NFB plugin **forces** its page number positions (odd braille pages top right, even none, no print page numbers), keeping only the page size from the caller. So no CLI layout standard or GUI profile is needed, and a profile meant for books cannot break NFB page detection. *(Changed during implementation: there is no shared CLI layout change.)*

The CLI page-layout option is literally named `"-pl, --page-layout"` (one string, a quirk of the current argparse call). The test script passes it that way only when `-PageLayout` is given. Leave the quirk alone; renaming it is outside this issue.

---

## 3. NFB plugin

### 3.1 Package scaffolding (copy of `plugins/brf2ebrl_bana`)
- `plugins/brf2ebrl_nfb/pyproject.toml`: name `brf2ebrl-nfb`, depends on `brf2ebrl` and `brf2ebrl-bana` (to reuse the `pages` and `tn_detectors` helpers), entry point `nfb = "brf2ebrl_nfb:PLUGIN"`, `uv_build` backend, `tool.uv.sources` workspace entries.
- `plugins/brf2ebrl_nfb/README.md` (short).
- `src/brf2ebrl_nfb/__init__.py` defines `PLUGIN = create_plugin(plugin_id="NFB", name="Convert NFB Braille Monitor BRF to eBraille", brf_parser_factory=create_brf2ebrl_parser, file_mapper=lambda f, i: f"vol{i}.html", bundler_factory=NfbZippedBundler)`. `create_plugin` already accepts `bundler_factory`, so this needs no library change (see 3.6).
- `src/brf2ebrl_nfb/detectors.py` holds the NFB-only block detectors. `links.py` (3.4), `toc.py` (3.6a) and `bundler.py` (3.6b) hold the rest.
- Root `pyproject.toml`: add `"plugins/brf2ebrl_nfb"` to workspace `members`.
- `gui/pyproject.toml`: add the `brf2ebrl-nfb` dependency and `brf2ebrl_nfb = { workspace = true }`.
- `gui/Convert2EBRL.pyw`: add `# nuitka-project: --include-package=brf2ebrl_nfb`. **Verify** the packaged exe lists NFB in the combo, because discovery uses entry-point metadata. If it is missing, add `--include-distribution-metadata=brf2ebrl-nfb`, and also for bana if needed.
- Run `uv lock` and commit `uv.lock`. CI runs `uv sync --frozen`.

### 3.2 Parser pipeline
`create_brf2ebrl_parser` starts as a copy of the BANA list, with these changes:

| BANA pass | NFB change |
|---|---|
| ASCII clean, uppercase, to Unicode, remove volume markers | unchanged |
| Detect Braille pages | **NFB copy** (`brf2ebrl_nfb/pages.py`). It reuses BANA's page splitting but also accepts roman numerals (`III`, `;V`, `VII`), which BANA's detector leaves in the text. |
| Detect print pages | **drop.** NFB has no print page numbers. |
| Running head | **drop**, whatever `detect_running_heads` says |
| Remove form feeds, blank lines → PI, box lines, Nemeth | unchanged |
| **New pass, before "Detect blocks": "Detect article separators"** | see 3.3a |
| Detect blocks | NFB detector list, see 3.3 |
| TNs, inline Nemeth, emphasis, restore Nemeth | unchanged |
| **New pass, after "Restore Nemeth braille": "Detect links"** | see 3.4 |
| Images, ebrf page tags, PI removal, XHTML fixup, U+2800→space | unchanged |

### 3.3 NFB detectors (in `brf2ebrl_nfb/detectors.py`)

**a. Article separator.** Regex `^⠀+⠐⠒{6,}⠀*$`, i.e. a centered `"3333…`, optionally followed by a top-right page number on the same line, which the page pass has already removed. Output `<p class="separator">⠐⠒⠒…</p>` and set `state["article_start"] = True`. Run it as its own `Parser` pass before block detection so the centered and pre detectors never see it.

**b. Centered blocks: title page, article title, byline, section heading.** Do this with an **NFB-only copy** of the centered detector in `brf2ebrl_nfb/centered.py`, not by editing `create_centered_detector`. `brf2ebrl/common/block_detectors.py` is **not touched** (see §7, BANA safety).
- Start from `create_centered_detector` (about 90 lines). Keep its line-matching and its ±1-cell tolerance with low-confidence notifications. The shared helpers it uses (`_notify_low_confidence_match`, `_BLANK_LINE_RE`) are imported, not changed.
- Remove the guide-words branch, so the ISSN line is kept.
- Keep the matched lines as a list instead of joining them with ⠀, so the rules below can split them.
- NFB rules, applied to a group of consecutive centered lines:
  1. **Title page** (`state["title_page"]` is true until the second `<?braille-page …?>` PI of the file has been passed): one `<p class="titlepage">` per line.
  2. Otherwise, split the group at the first line that starts with `⠃⠽⠀` ("BY "). Lines before it form the heading and the rest form `<p class="byline">`.
  3. The heading is `<h1 class="article-title">` if `state["article_start"]` is set (after a separator, or the first body heading of a volume). After use, clear the flag. In every other case the heading is `<h2>` (for example "Ways to Access the Monitor").
  4. TOC title `,3T5TS` and the "Part N" dividers are left to the TOC detector. Make sure the TOC detector keeps winning there, as it does today.
- To track `title_page`, add a tiny detector that matches the `<?braille-page …?>` PI, counts pages in state, and passes the PI through. It goes ahead of `detect_and_pass_processing_instructions` in the "Detect blocks" list.

**c. Photo captions.** `create_paragraph_detector(first_line_indent=6, run_over=4, indicator_matcher=_caption_matcher, confidence=0.96)`, where `_caption_matcher` accepts blocks that start with `⠨⠣` (`.<`) and outputs `<p class="caption">…</p>`. It works for single-line captions too, unlike BANA's run-over-only rule. Each caption starts again at cell 7, so consecutive captions need to come out as separate blocks. **Verify** that `_create_indented_block_finder` splits on a new first-line indent. If it does not, split inside the matcher on lines that start with `⠨⠣`.

**d. Dialogue.**
- `create_paragraph_detector(first_line_indent=0, run_over=2, indicator_matcher=_speaker_matcher, confidence=0.95)` → `<p class="dialogue">`. `_speaker_matcher` requires the first line to start with a capitalised name of 1–4 words ending in `⠒` (`3`, the colon), for example `,LIA ,/"O3`. This keeps real 1-3 lists for the list detector.
- `create_paragraph_detector(first_line_indent=4, run_over=2, indicator_matcher=_dialogue_cont_matcher, confidence=0.95)` → `<p class="dialogue-cont">`. It is accepted only while `state["in_dialogue"]` is set. The speaker matcher sets the flag, and a separator or heading clears it. Without that guard, 5-3 displayed text elsewhere would be mislabelled.
- The confidences must beat `create_list_detector`, which currently claims these blocks. Check them against the BANA values: 0.95, 0.94 and 0.9 for paragraphs.

**e. Reused from BANA without change:** 3-1 paragraph detector, `create_cell_heading(6,"h3")` and `(4,"h2")`, list, tables, `detect_pre`, the TN block and inline detectors, Nemeth, emphasis.

### 3.4 Links for URLs and email addresses (NFB only)

How they appear in the samples (ASCII braille):

| BRF | Target `href` |
|---|---|
| `HTTPS3_/_/NFB4ORG_/PUBLICA;NS4` (trailing `4` is a sentence period) | `https://nfb.org/publications` |
| `COMMUNICA;NS@ANFB4ORG` | `mailto:communications@nfb.org` |
| `CDANIELS5@ANFB4ORG` | `mailto:cdanielsen@nfb.org` |
| `HTTPS3_/_/CR1TIVECOMMONS4ORG_/LIC5SES_/"`⏎`BY-NC-ND_/#D4J_/DEED4EN4` (`"` at line end means the URL continues on the next line) | `https://creativecommons.org/licenses/by-nc-nd/4.0/deed.en` |
| `WWW4NFB4ORG4` (not linked in the target) | link it as `https://www.nfb.org` |

The URLs are **contracted** (`;N` = "tion", `5` = "en", `1` = "ea"), so `href` needs grade 2 back-translation.

**a. Back-translation support (cross-project, needed):**
- The vendored liblouis (`vendor/liblouis/src/louis/tables`) ships only `en-ueb-g1.ctb` and the tables it includes. Add `en-ueb-g2.ctb`, plus any tables it includes that are missing, copied from the liblouis **3.39.0** release so they match the DLL. Note the addition in `vendor/liblouis/README.md`.
- Add `back_translate_contracted(braille: str) -> str | None` to `brf2ebrl/utils/back_translation.py`, using the tables `unicode.dis` + `en-ueb-g2.ctb`. Cache it. Return `None` when liblouis leaves `\…/` escapes or private-use characters, which is the same check `back_translate_page_number` already does.
- Make sure Nuitka still bundles the new table: `--include-package-data=louis` should cover it, but check in the packaged exe.

**b. Detector:** `detect_links` is a `Parser` pass in `brf2ebrl_nfb/links.py`. It runs on the HTML after block detection, so URLs that wrap across lines are already inside one `<p>`/`<li>`.
- It only scans text outside tags and processing instructions.
- **URL start:** `⠓⠞⠞⠏⠎?⠒⠸⠌⠸⠌` (`http(s)://`) or `⠺⠺⠺⠲` (`www.`).
- **Email:** a run of non-space braille that contains `⠈⠁` (`@`, which is `@A`) followed by a domain with at least one `⠲` (`.`).
- **Extent:** the run continues up to a braille space (⠀) or a newline. The exception is a line ending in `⠐` (dots 5, the UEB continuation indicator), where the newline and the `⠐` are dropped and the run continues on the next line.
- **Trailing punctuation:** strip it from the end of the link (`⠲` period, `⠂` comma, `⠆` semicolon, `⠒` colon, `⠦`/`⠴` quotes, `⠐⠜` close paren). It stays outside the `</a>`, as in the target.
- **Skip a candidate** if a processing instruction falls inside it (for example a page break in the middle of a URL), or if it is already inside a `<a>`.
- **href:** back-translate, lowercase the scheme and host, and add `mailto:` for emails or `https://` for bare `www.`. Escape `&` and `"` for XHTML.
- **Link text** stays the original braille, without the continuation `⠐`.
- If back-translation returns `None`, or the result does not look like a URL or email (simple regex), leave the text unlinked and log a warning through `parser_context.notify`. The parser factory receives `parser_context` and passes it in.

### 3.5 Order of the "Detect blocks" list (NFB)
```
detect_and_pass_nemeth_block,
nfb_braille_page_tracker,          # new, passes PI through
nfb_toc_detector,                  # new (3.6a), replaces create_toc_detector
nfb_centered_detector,             # NFB copy in brf2ebrl_nfb/centered.py
create_cell_heading(6, "h3"), create_cell_heading(4, "h2"),
caption detector (6/4),            # new
speaker detector (0/2),            # new
dialogue-cont detector (4/2),      # new
BANA TN paragraph (6/4), 3-1 paragraph (2/0),
list, column_row, listed, table, detect_pre,
detect_and_pass_processing_instructions
```

### 3.6 TOC with links to articles

**Why it has to be done in two places:** `convert()` parses each BRF separately and writes it to the zip straight away. The TOC in vol 0 lists articles that are in vol 1, vol 2 and so on, and their heading ids (`h_N`, assigned by `xhtml_fixup_detector`) don't exist yet when vol 0 is parsed. So:
- the **parser** marks each TOC entry with a placeholder link;
- the **bundler**, which sees every volume before the zip is finished, works out the real targets.

The existing `bundler_factory` hook on `create_plugin` makes this possible with no library change.

**a. NFB TOC detector** (`brf2ebrl_nfb/toc.py`). It replaces BANA's `create_toc_detector` in the NFB list, because the NFB 3-1 run-over layout makes the shared detector nest every run-over line, and changing it would risk BANA.
- **Start:** a centered `⠠⠒⠞⠢⠞⠎` ("Contents"), or "Contents—Part N", gives `<h1 class="toc-title">`. Set `state["in_toc"]`.
- **Inside the TOC:**
  - A centered `⠠⠐⠏⠀⠼…` ("Part N") gives `<h2 class="toc-part">`.
  - An **entry** is a line at cell 1 plus the following lines at cell 3. It ends at the line that finishes with an optional run of guide dots `⠀⠐+` and then a braille page number (`⠼…` or roman letters).
  - Blank-line PIs and `<?braille-page?>` PIs inside the TOC are passed through.
- **End:** the first line that is neither an entry nor a Part heading, such as the first photo caption. Clear `state["in_toc"]`.
- **Output:**
  ```html
  <nav class="toc"><h1 …>…</h1>
    <ul class="toc">
      <li><a href="#nfb-toc-7">⠠⠋⠀⠮⠀⠠⠫⠊⠞⠕⠗⠀⠃⠽⠀⠠⠡⠗⠊⠎⠀⠠⠙⠁⠝⠊⠑⠇⠎⠢</a> <span class="toc-page">⠼⠁</span></li>
      …
  ```
  The entry text has its run-over lines joined with ⠀ and the guide dots removed. The braille page number is kept visible.
- **Placeholder links:** `#nfb-toc-<n>` uses a counter kept in detection state. It must be unique within the file, and the bundler adds the volume name to make it unique across files.
- **`<nav>` and `<h1>`:** check that `xhtml_fixup_detector` and the bundler's navigation builder accept a `<nav>` wrapping an `<h1>`. If it confuses the generated index, use `<div class="toc">` instead. The `<h1>` "Contents" still goes in the index navigation as it does today.

**b. `NfbZippedBundler(EBrlZippedBundler)`** (`brf2ebrl_nfb/bundler.py`):
- `write_volume(name, data)`: keep `(name, data)` in an in-memory list instead of writing it. One issue is under 1 MB of text.
- `close()`:
  1. **Collect articles.** Parse each buffered volume with `lxml.html` (read only). Walk the document in order and record each `h1.article-title` as `(volume, id, key, braille_page)`.
     - `key` is the heading text with all whitespace and ⠀ removed.
     - `braille_page` is not available: braille page numbers are dropped during conversion (BANA only turns *print* pages into `doc-pagebreak`, and NFB has none, which matches the target). So matching relies on the title prefix plus document order. A fuzzy fallback (difflib ratio ≥ 0.8 on the title part before the last "BY") replaces the page-number fallback.
  2. **Match each TOC entry, in document order.** Make the entry's `key` the same way, without the page number. Pick the **first article after the previously matched article** where:
     - the article key is a **prefix** of the entry key (the entry is "title BY author" and the heading is "title"); or, as a fallback,
     - (fallback) the fuzzy title match described above.
     The order rule keeps two articles that start on the same page apart. The prefix rule handles titles that themselves contain "BY" (for example "…Network by the Blind by Lia Soto").
  3. **Rewrite.** Each `href="#nfb-toc-<n>"` becomes `#h_12` when the article is in the same volume, or `vol1.html#h_12` otherwise. All volumes are in `ebraille/`, so relative links work. Use a regex on the serialized string, the same way the placeholder was written, so the volume is not re-serialized and its formatting is not changed.
  4. **Unmatched entries:** unwrap the `<a>`, keeping its text, and log a warning (`logging.warning`, because the bundler has no `parser_context`).
  5. Write each volume with `super().write_volume(name, data)` in the original order (the spine order depends on it), then call `super().close()`, which builds `index.html` and `package.opf` as today.
- If the parser fails part-way, `convert()` still writes `errors/…` through `write_str`, which is not buffered, so error handling is unchanged.

**c. Optional, nice to have (BRF-only path):** give `h1.article-title` a readable id, such as a slug of the back-translated title (the target uses `from-the-editor`). `xhtml_fixup_detector` keeps any id that is already set. This needs `back_translate_contracted` from 3.4 and has to deduplicate repeated slugs. Leave it out of the first pass; the `h_N` ids work. When print HTML is present, 3.7 provides these ids anyway.

### 3.7 Optional print HTML (used automatically when present)

**Rule:** if the print HTML exists, use it; if it does not, don't. The BRF-only result from 3.1–3.6 is always produced first. Print only **adjusts** that result, and only where a match is confident. A missing, unreadable or mismatched print file can never make the output worse than BRF-only.

**a. Finding it.** This is done inside the NFB plugin, so the CLI, the GUI, `convert()` and the parser options do not change.
- The NFB parser factory already receives `brf_path`. `find_print_html(brf_path)` in `brf2ebrl_nfb/print_source.py` looks in that BRF's folder for `*.htm` / `*.html`, ignoring `*_files/` folders.
- Exactly one match: use it. Several: prefer the one whose name starts with `Complete`. If it is still ambiguous, use none and send a WARN notification.
- No match: BRF-only, with no warning (that is the normal case).
- When a print file is used, send an INFO notification "Using print file <name> to refine links and headings" through `parser_context.notify`, so the GUI warnings dialog and the CLI log show it.
- **Reading it:** parse once and cache by path. Get the encoding from the `<meta charset>` / `http-equiv`, falling back to `cp1252` (the samples are Windows-1252, with `Pár` and curly quotes).
- **What is extracted** (`PrintIssue` dataclass):
  - the `<title>`;
  - the ordered list of headings `(level, text)`, skipping the masthead `<h1>` and the "Contents" `<h2>`;
  - the ordered list of external links (`http`, `https`, `mailto`), deduplicated.

  In the samples, print article titles are `<h2>` (12–18 per issue) and subheadings are `<h3>`.

**b. What print improves.** Each item is a small optional step inside a pass that already exists. When `print_issue` is `None`, the step is skipped.

| Item | Where | How it matches | If no confident match |
|---|---|---|---|
| **Link `href`** (3.4) | link pass | Back-translate the braille URL/email as usual, then compare it to the print link list after normalising (lowercase, strip scheme, `www.` and trailing `/`). Exact match: use the print `href`, which fixes contraction errors. Otherwise use the closest print link with `difflib` ratio ≥ 0.9. | Keep the back-translated `href` (BRF-only behaviour) |
| **Link whose back-translation failed** | link pass | The nearest print link by the same similarity check, run on the partial back-translation | Leave unlinked and warn (BRF-only behaviour) |
| **Article ids** | NFB centered detector (3.3b) | Back-translate the `h1.article-title` text (g2), then fuzzy-match it (ratio ≥ 0.85) against print `<h2>` titles not yet used in this volume. Set `id` to a slug of the print title (`from-the-editor`), deduplicated within the file. `xhtml_fixup_detector` keeps preset ids, and the TOC bundler (3.6b) reads whatever id is there, so cross-volume TOC links pick these up automatically. | Keep `h_N` |
| **Heading level for non-article centered headings** | NFB centered detector | Same fuzzy match against print `<h3>`/`<h4>`. Print `h3` → `h2`, print `h4` → `h3`. This gives the front-matter h2/h3 split that braille cannot show. | Keep the 3.3b rule (`h2`) |
| **Book title** | `NfbZippedBundler.close()` | If the user left the title metadata at its default, use the print `<title>` (for example "NFB Braille Monitor October 2026"). Pass it through `metadata_entries`, which the bundler already has. | Keep the current title detection |

Links that exist only in print (text links like "visit our website") are **not added**, because there is no braille text to attach them to.

**c. Matching is per item and fuzzy, never by position.** A caption dropped in braille, an extra link in print or a reordered article only loses that one match. It does not shift the rest. Every fallback is logged at DEBUG. A summary INFO notification reports, for example, "print: 8/9 links, 12/12 titles matched", so a bad print file is easy to spot.

**d. Not in scope:** the special classes (`attribution`, `salutation`, `plaque`, `steps`, `blocked`), joining paragraph lines, and anything else that would make print the source of the text. The braille text is always kept exactly as transcribed.

---

## 4. Tests

`plugins/brf2ebrl_nfb/tests/`, following `plugins/brf2ebrl_bana/tests/test_low_confidence_warnings.py`. Fixtures are short BRF excerpts cut from the samples:

1. Title page: each centered line becomes a `titlepage` paragraph, and the ISSN is kept.
2. Separator followed by a 2-line title and a 2-line byline gives `separator`, then `h1.article-title`, then `p.byline`.
3. Two consecutive captions followed by a title give two captions, then `h1`.
4. A transcript excerpt gives only `dialogue`/`dialogue-cont` paragraphs and no `<li>`.
5. A real 1-3 list inside an article is still a list.
6. A body paragraph that crosses a page break stays a single paragraph, and the braille page number is removed from its text (NFB output has no `doc-pagebreak`, as in the target).
7. The plugin is discoverable: `find_plugins()` contains ids `BANA` and `NFB`.
8. Links: each row of the 3.4 table gives the expected `href`. The trailing period stays outside `</a>`. A URL with a page break inside it is left unlinked.
9. TOC structure: the October vol 1 TOC excerpt gives two `toc-part` headings and 8 flat `<li>`, with no nested `<ol>`/`<ul>`. Each entry's run-over lines are joined, and every entry has a page span, including `,X'S ,\R ,TURN … #GA`.
10. TOC links (bundler unit test with two small fake volumes): an entry for an article in the same volume gets `#h_N`. An entry for an article in another volume gets `vol1.html#h_N`. An entry whose title contains "BY" still matches. Two articles on the same page are matched in order. An unmatched entry is unwrapped and logs a warning. The volumes are written in their original order.
11. `brf2ebrl/tests`: `back_translate_contracted` turns `⠉⠙⠁⠝⠊⠑⠇⠎⠢` into `cdanielsen`, and returns `None` for braille it cannot back-translate.
12. Print discovery: tests run in a temp folder.
    - No `.htm`: BRF-only, with no notification.
    - One `.htm`: it is used, with an INFO notification.
    - Two `.htm`: the one starting with `Complete` is used.
    - Two ambiguous files: neither is used, with a WARN.
    - `*_files/` folders are ignored.
13. Print refinement, on a small fixture `.htm` alongside a BRF excerpt:
    - a contracted URL whose back-translation is slightly wrong gets the exact print `href`;
    - a title gets the print slug id;
    - a centered subhead matching a print `<h3>` stays `h2`, and one matching `<h4>` becomes `h3`;
    - a braille link with no print match keeps its back-translated `href`;
    - the braille text is byte-identical with and without the print file.
14. Windows-1252 print file (`Pár`, curly quotes) is decoded correctly.

Also run the existing `brf2ebrl` and BANA tests (`uv run pytest`) after every step, and run the BANA baseline comparison in §7.

**Sample regression (manual):** add `work/nfb_loop.ps1`, adapted from `work/loop.ps1`. It runs `uv run --all-packages brf2ebrl --parser NFB --no-running-heads <issue>/*.brf -o <issue>.ebrl` for the three issues and unzips the results. Then compare the element counts with the target `.ebrl` (h1.article-title, separator, caption, byline, dialogue). The October target has 12 article titles, 9 separators, 14 captions and 7 bylines, and its 145 dialogue paragraphs are the `dialogue` + `dialogue-cont` counts. The October target also has 8 URL/email links in vol 0, and we should match those plus `WWW4NFB4ORG`. Every TOC entry in all three issues should link to the right article: open the `.ebrl`, follow each link, and check the heading. Run each issue **twice**: once with the `.htm` in the folder, and once with it moved away. Both runs must succeed. The braille text must be identical between them. The print run should match every target link `href` and article id that has braille text. That is the acceptance check.

---

## 5. Order of work

0. **Before any code change:** capture the BANA baseline (§7) from the current `main`.
1. Scaffold the NFB package as a straight copy of the BANA pipeline. Register it in the workspace, the GUI dependencies and Nuitka, and run `uv lock`.
2. Add the CLI default fix and the GUI combo box. At this point NFB converts exactly like BANA, which is a safe checkpoint.
3. Drop the print-page and running-head passes, and add the separator pass.
4. Add the NFB centered detector copy in `brf2ebrl_nfb/centered.py` (title page, title, byline).
5. Add the caption detector.
6. Add the dialogue detectors.
7. Add the grade 2 liblouis table and `back_translate_contracted` (with its test), then the NFB link pass.
8. Add the NFB TOC detector with placeholder links, then `NfbZippedBundler` to resolve them, and wire it in through `bundler_factory`.
9. Add optional print support (3.7): discovery and `PrintIssue` parsing first, then link `href` correction, then article ids and heading levels, then the book title.
10. Add the tests and run the sample loop against all three issues, with and without print. Tune the confidences and similarity thresholds.
11. Packaging smoke test of the Nuitka build: the combo box lists NFB, and links get an `href`, which shows the g2 table was bundled.

## 6. Risks to watch

- **Contracted back-translation of URLs can be wrong.** A contraction that UEB would not use inside a URL can come back as the wrong letters. Mitigation: the URL/email sanity check, and a warning instead of a bad link. Check every `href` in the three samples by hand.
- **The dialogue matcher could claim real 1-3 lists** whose first item ends with a colon. Mitigation: the speaker regex requires capitalised name words, and test 5 covers this.
- **Plugin discovery in the packaged exe** depends on entry-point metadata (see 3.1).
- **TOC matching can fail** when the TOC wording differs from the heading, for example a shortened title. Mitigation: the fuzzy fallback, plus a warning and an unlinked entry instead of a wrong link.
- **The wrong print file could be in the folder**, for example last month's issue or a draft. Mitigation: confident matches only, with the "N/M matched" summary in the notifications. A low match rate shows up straight away and costs nothing beyond falling back to BRF-only. Consider skipping print entirely when fewer than half the titles match.
- **The bundler holds all volumes in memory until `close()`.** This is fine at newsletter size, and it only affects the NFB plugin.

## 7. BANA safety: no change to BANA conversions

**Rule:** BANA output must be byte-for-byte the same before and after this work. If any step seems to need a change to shared conversion code, copy the code into `brf2ebrl_nfb` and change the copy instead.

**Files that must not change:**
- `brf2ebrl/src/brf2ebrl/common/*` (all detectors, including `block_detectors.py`)
- `brf2ebrl/src/brf2ebrl/parser.py`
- `brf2ebrl/src/brf2ebrl/plugin.py` (including `EBrlZippedBundler`)
- `brf2ebrl/src/brf2ebrl/__init__.py` (`convert()`)
- everything under `plugins/brf2ebrl_bana/`

**Shared files that do change, and why BANA is not affected:**

| File | Change | Why BANA output is the same |
|---|---|---|
| `brf2ebrl/scripts/brf2ebrl.py` | Default parser is explicitly `BANA` | Today's default (BANA) stays the default. Only CLI selection logic changes, not conversion. |
| `brf2ebrl/utils/back_translation.py` | New function `back_translate_contracted` | Additive. BANA never calls it. `back_translate_page_number` is unchanged. |
| `vendor/liblouis/src/louis/tables/` | Add `en-ueb-g2.ctb`, plus any **missing** includes | Add files only; never overwrite an existing table. BANA uses `en-ueb-g1.ctb` + `unicode.dis` for page numbers, and those stay untouched. |
| `gui/…/general_tab.py`, `brf_to_ebrf.py` | Plugin combo box | Defaults to BANA when no choice is saved. When BANA is selected, the same plugin object and options are passed as today. |
| Root and `gui` `pyproject.toml`, `uv.lock`, `Convert2EBRL.pyw` | Register `brf2ebrl_nfb` | Run `uv lock` **without** `--upgrade`. The lock diff must only add `brf2ebrl-nfb`, with no version bumps. |

**How to check it:**
1. **Before any code change** (step 0 in §5), on current `main`, run `issue-71043\run_issue71043.ps1 -BanaCheck Baseline`. This converts the `work/ebrl-test-files/books` set with `--parser BANA`, the same way `work/loop.ps1` does, and keeps every `ebraille/*.html` and `index.html`.
2. After each step in §5, run `issue-71043\run_issue71043.ps1 -BanaCheck Compare`. Every file must be identical; the script exits non-zero on any difference. `package.opf` is skipped because it contains a timestamp.
3. Run `uv run pytest` in `brf2ebrl` and in `plugins/brf2ebrl_bana`; these must pass unchanged.
4. Check `git diff --stat main` before committing. Nothing should appear under the "must not change" paths.

## 8. Command-line test script

`issue-71043/run_issue71043.ps1` runs the issue-71043 samples from the command line. See the help at the top of the script, or run `Get-Help .\issue-71043\run_issue71043.ps1 -Detailed`.

| Command | What it does |
|---|---|
| `.\issue-71043\run_issue71043.ps1` | Converts all three issues with the NFB plugin, with print HTML if it is present, and compares each against the target `.ebrl` |
| `… -Issue 10-26` | Converts only the October issue |
| `… -NoPrint` | Converts from a copy of the BRFs without the `.htm`, to test the BRF-only path |
| `… -Parser BANA` | Uses today's converter (works now, before the NFB plugin exists) |
| `… -BanaCheck Baseline` / `Compare` | The BANA safety check in §7 |

Output goes to `issue-71043/out/` (not committed). For each issue it writes:
- the converted `.ebrl` and its unzipped folder;
- the unzipped target;
- `compare.txt`, with element counts side by side (article titles, separators, captions, bylines, dialogue, links, TOC links, list items, page breaks);
- `links_ours.txt` / `links_target.txt`, to diff the `href`s;
- the converter log.

