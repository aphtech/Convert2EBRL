#  Copyright (c) 2026. American Printing House for the Blind.
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

import lxml.html
import pytest

from brf2ebrl.utils.back_translation import back_translate_page_number
from brf2ebrl.utils.ebrl import create_navigation_html, PageRef


@pytest.mark.parametrize("page_num_braille,expected", [
    ("⠼⠁", "1"),
    ("⠼⠁⠚⠚", "100"),
    ("⠊", "i"),
    ("⠭⠊⠧", "xiv"),
    ("⠭", "x"),
    ("⠇", "l"),
    ("⠠⠺⠼⠁", "W1"),
    ("⠁⠼⠃", "a2"),
    ("⠼⠁⠤⠼⠃", "1-2"),
    (" ⠼⠉ ", "3"),
])
def test_back_translate_page_number(page_num_braille: str, expected: str):
    assert back_translate_page_number(page_num_braille) == expected


def test_navigation_page_list_has_print_page_title():
    nav = create_navigation_html(page_refs=[
        PageRef(href="ebraille/vol0.html#page_1", title="i", page_num_braille="⠊"),
        PageRef(href="ebraille/vol0.html#page_2", title="1", page_num_braille="⠼⠁"),
    ])
    root = lxml.html.fromstring(nav.encode("utf-8"), parser=lxml.html.xhtml_parser)
    links = root.xpath("//*[@role='doc-pagelist']//*[local-name()='a']")
    assert [(a.get("href"), a.get("title"), a.text) for a in links] == [
        ("ebraille/vol0.html#page_1", "i", "⠊"),
        ("ebraille/vol0.html#page_2", "1", "⠼⠁"),
    ]
