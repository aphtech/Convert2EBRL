#  Copyright (c) 2024. American Printing House for the Blind.
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from brf2ebrl.common.detectors import translate_ascii_to_unicode_braille
from brf2ebrl.common.volume_markers import remove_volume_markers


def _brl(ascii_text: str) -> str:
    return translate_ascii_to_unicode_braille(ascii_text.upper())


def test_remove_volume_marker():
    text = _brl("            @.<,VOLUME #C@.>\n")
    assert remove_volume_markers(text) == ""


def test_remove_volume_marker_with_surrounding_text():
    text = _brl("HEADING\n\n            @.<,VOLUME #C@.>\n  ,LESSON #I\n")
    expected = _brl("HEADING\n\n  ,LESSON #I\n")
    assert remove_volume_markers(text) == expected


def test_remove_multiple_volume_markers():
    text = "".join(
        _brl(f"            @.<,VOLUME {n}@.>\ncontent {n}\n")
        for n in ("#A", "#B", "#C", "#D")
    )
    expected = "".join(_brl(f"content {n}\n") for n in ("#A", "#B", "#C", "#D"))
    assert remove_volume_markers(text) == expected


def test_volume_number_matches_any_legal_braille():
    # Multi-cell volume numbers (eg. "#AJ" for 10) should also be matched,
    # since the volume number can be any legal Braille.
    text = _brl("            @.<,VOLUME #AJ@.>\n")
    assert remove_volume_markers(text) == ""


def test_does_not_remove_volume_list_entry():
    # Front matter, eg. ",VOLUME #A", is not bracketed by the "@.<" / "@.>"
    # indicator and must be left alone.
    text = _brl(",VOLUME #A\n")
    assert remove_volume_markers(text) == text
