#  Copyright (c) 2026. American Printing House for the Blind.
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.
"""The NFB Braille Monitor table of contents.

Layout: a centered "Contents" heading, optional centered "Part N" dividers, and entries of
"title by author" starting at the margin with run-over lines in cell 3, the last line ending in
optional guide dots and the braille page number. Blank lines and page breaks may fall between.

Each entry gets a placeholder link (#nfb-toc-N). The articles are in other volumes too, whose
heading ids do not exist yet, so NfbZippedBundler resolves the placeholders once every volume
has been converted."""
import re

from brf2ebrl.parser import DetectionResult, DetectionState
from brf2ebrl_nfb.lines import join_lines

TOC_PLACEHOLDER_PREFIX = "nfb-toc-"

# Centered ",3T5TS" (Contents), possibly followed by a part, eg. "Contents--Part 2".
_CONTENTS_RE = re.compile("\u2800{3,}(\u2820\u2812\u281e\u2822\u281e\u280e[\u2800-\u28ff]*?)\u2800*\n")
# Centered ","P #A" (Part 1).
_PART_RE = re.compile("\u2800{3,}(\u2820\u2810\u280f\u2800\u283c[\u2801\u2803\u2809\u2819\u2811\u280b\u281b\u2813\u280a\u281a]+)\u2800*\n")
_ENTRY_FIRST_LINE_RE = re.compile("([\u2801-\u28ff][\u2800-\u28ff]*)\n")
_ENTRY_RUN_OVER_RE = re.compile("\u2800\u2800([\u2801-\u28ff][\u2800-\u28ff]*)\n")
_SKIPPABLE_PI_RE = re.compile("<\\?(?:blank-line|braille-page [\u2800-\u28ff]*)\\?>\n")
_BRAILLE_PAGE_PI_RE = re.compile("<\\?braille-page [\u2800-\u28ff]*\\?>\n")
# Optional guide dots, then a braille page number (arabic, or roman for preliminary pages).
_ENTRY_PAGE_RE = re.compile(
    "(?:\u2800\u2810+)?\u2800(\u283c[\u2801\u2803\u2809\u2819\u2811\u280b\u281b\u2813\u280a\u281a]+"
    "|\u2830?[\u280a\u2827\u282d\u2807\u2809]+)$")


def _match_entry(text: str, pos: int) -> tuple[str, str, int] | None:
    """An entry starting at pos: (entry braille, page number, end position)."""
    first = _ENTRY_FIRST_LINE_RE.match(text, pos)
    if not first:
        return None
    lines = [first.group(1).rstrip("\u2800")]
    end = pos = first.end()
    pending_pis: list[str] = []
    while True:
        # An entry can run over onto the next braille page.
        if pi := _BRAILLE_PAGE_PI_RE.match(text, pos):
            pending_pis.append(pi.group().rstrip("\n"))
            pos = pi.end()
            continue
        run_over = _ENTRY_RUN_OVER_RE.match(text, pos)
        if not run_over:
            break
        lines.extend(pending_pis)
        pending_pis = []
        lines.append(run_over.group(1).rstrip("\u2800"))
        end = pos = run_over.end()
    page = _ENTRY_PAGE_RE.search(lines[-1])
    if not page:
        return None
    lines[-1] = lines[-1][:page.start()]
    return join_lines(lines, "\u2800"), page.group(1), end


def detect_toc(text: str, cursor: int, state: DetectionState, output_text: str) -> DetectionResult | None:
    """Detect the whole TOC from its "Contents" heading to the last entry."""
    contents = _CONTENTS_RE.match(text, cursor)
    if not contents:
        return None
    count = state.get("nfb_toc_count", 0)
    html = [f'<nav class="toc">\n<h1 class="toc-title">{contents.group(1)}</h1>']
    items: list[str] = []
    end = pos = contents.end()

    def close_list():
        if items:
            html.append('<ul class="toc">\n' + "\n".join(items) + "\n</ul>")
            items.clear()

    entries = 0
    while True:
        if pi := _SKIPPABLE_PI_RE.match(text, pos):
            pos = pi.end()
            continue
        if part := _PART_RE.match(text, pos):
            close_list()
            html.append(f'<h2 class="toc-part">{part.group(1)}</h2>')
            end = pos = part.end()
            continue
        if entry := _match_entry(text, pos):
            entry_brl, page, end = entry
            count += 1
            entries += 1
            items.append(f'<li><a href="#{TOC_PLACEHOLDER_PREFIX}{count}">{entry_brl}</a> '
                         f'<span class="toc-page">{page}</span></li>')
            pos = end
            continue
        break
    if not entries:
        return None
    close_list()
    html.append("</nav>\n")
    # Body matter starts after the TOC, so the next centered heading is an article title.
    new_state = dict(state, nfb_toc_count=count, article_start=True, in_dialogue=False, open_caption=False)
    return DetectionResult(end, new_state, 0.97, output_text + "\n".join(html))
