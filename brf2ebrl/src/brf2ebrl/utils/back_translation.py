#  Copyright (c) 2026. American Printing House for the Blind.
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.
"""Back-translation of braille to print using liblouis."""
import logging
from functools import cache

import louis
from louis.bundled import table_path

# Page numbers are uncontracted, and grade 2 would back-translate roman numerals such as ⠭ and ⠇ as "it" and "like".
_PAGE_NUMBER_TABLES = [table_path("unicode.dis"), table_path("en-ueb-g1.ctb")]


_CONTRACTED_TABLES = [table_path("unicode.dis"), table_path("en-ueb-g2.ctb")]


def _has_untranslated(print_text: str) -> bool:
    # liblouis marks braille it cannot back-translate as \dots/ or with private use characters.
    return "\\" in print_text or any("" <= c <= "" for c in print_text)


@cache
def back_translate_contracted(braille: str) -> str | None:
    """Back-translate contracted (grade 2) UEB Unicode braille, or None if part of it cannot be."""
    print_text = louis.backTranslateString(_CONTRACTED_TABLES, braille.strip("⠀")).strip()
    return None if not print_text or _has_untranslated(print_text) else print_text


@cache
def back_translate_page_number(page_num_braille: str) -> str:
    """Back-translate a Unicode braille page number to its print equivalent."""
    print_page_num = louis.backTranslateString(_PAGE_NUMBER_TABLES, page_num_braille.strip()).strip()
    # liblouis marks braille it cannot back-translate as \dots/ or with private use characters.
    if "\\" in print_page_num or any("" <= c <= "" for c in print_page_num):
        logging.warning(f"Page number {page_num_braille} could not be fully back-translated, got {print_page_num!r}")
    return print_page_num
