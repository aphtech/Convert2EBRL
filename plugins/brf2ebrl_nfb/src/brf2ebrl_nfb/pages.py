#  Copyright (c) 2026. American Printing House for the Blind.
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.
"""Braille page numbers for the NFB Braille Monitor.

Like the BANA detector, but preliminary pages use roman numerals (iii, v, vii), sometimes
with a grade 1 indicator (;v), and these must be recognised too or they stay in the text."""
import re

from brf2ebrl.common import PageLayout
from brf2ebrl.parser import Detector, DetectionState, DetectionResult
from brf2ebrl_bana.pages import _find_page_number

# Arabic: optional p/t prefix then number sign and digits a-j. Roman: optional grade 1
# indicator then i, v, x, l, c.
_PAGE_NUMBER_RE = re.compile(
    "[\u280f\u281e]?\u283c[\u2801\u2803\u2809\u2819\u2811\u280b\u281b\u2813\u280a\u281a]+"
    "|\u2830?[\u280a\u2827\u282d\u2807\u2809]+"
)


def create_nfb_braille_page_detector(page_layout: PageLayout, separator: str = "\u2800" * 3) -> Detector:
    """Detect braille pages (split on form feeds) and their page numbers."""

    def detect_braille_page_number(text: str, cursor: int, state: DetectionState,
                                   output_text: str) -> DetectionResult | None:
        page_count = state.get("page_count", 1)
        if state.get("start_braille_page", False):
            page_content = text[cursor:].split("\f")[0]
            new_cursor = cursor + len(page_content)
            page_content, page_num = _find_page_number(
                page_content,
                page_layout.odd_braille_page_number if page_count % 2 else page_layout.even_braille_page_number,
                page_layout.cells_per_line,
                page_layout.lines_per_page,
                separator,
                lambda n: bool(_PAGE_NUMBER_RE.fullmatch(n)),
            )
            return DetectionResult(new_cursor, dict(state, start_braille_page=False), 1.0,
                                   f"{output_text}<?braille-page {page_num}?>\n{page_content}")
        if text.startswith("\f", cursor):
            return DetectionResult(cursor + 1, dict(state, start_braille_page=True, page_count=page_count + 1),
                                   1.0, output_text + text[cursor])
        return None

    return detect_braille_page_number
