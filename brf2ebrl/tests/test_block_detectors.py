#  Copyright (c) 2024. American Printing House for the Blind.
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from brf2ebrl.common.block_detectors import create_centered_detector
from brf2ebrl.common.detectors import translate_ascii_to_unicode_braille


def test_create_centered_detector_detects_multi_word_guide_words_without_dash():
    # Regression: guide words are any centered text on the last line of a page
    # (see BANA Formats 2016, section 21), not only hyphenated pairs. A page
    # with a single new main entry has guide words with no dash and can
    # contain spaces, e.g. "ADJAC5T ANGLES".
    cells_per_line = 40
    content = "ADJAC5T ANGLES"
    indent = (cells_per_line - len(content)) // 2
    brl_content = translate_ascii_to_unicode_braille(content)
    text = "⠀" * indent + brl_content + "\n<?braille-page ?>\n"

    detector = create_centered_detector(cells_per_line, 3, "h1")
    result = detector(text, 0, {}, "")

    assert result is not None
    assert result.text == f"<!-- guide words {brl_content} -->\n"
