#  Copyright (c) 2026. American Printing House for the Blind.
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.
"""Web and email addresses become links with back-translated hrefs (examples from issue-71043)."""
import re

import pytest

from brf2ebrl.common.detectors import translate_ascii_to_unicode_braille
from brf2ebrl.parser import ParserContext
from brf2ebrl_nfb.links import address_href, create_link_pass

from test_nfb_blocks import TITLE_PAGE, convert, brl


def u(ascii_brf: str) -> str:
    return translate_ascii_to_unicode_braille(ascii_brf)


@pytest.mark.parametrize("braille,is_email,expected", [
    ("HTTPS3_/_/NFB4ORG_/PUBLICA;NS", False, "https://nfb.org/publications"),
    ("HTTPS3_/_/NFB4ORG_/PRESS-ROOM", False, "https://nfb.org/press-room"),
    ("HTTPS3_/_/CR1TIVECOMMONS4ORG_/LIC5SES_/BY-NC-ND_/#D4J_/DEED4EN", False,
     "https://creativecommons.org/licenses/by-nc-nd/4.0/deed.en"),
    ("WWW4NFB4ORG", False, "https://www.nfb.org"),
    ("COMMUNICA;NS@ANFB4ORG", True, "mailto:communications@nfb.org"),
    ("CDANIELS5@ANFB4ORG", True, "mailto:cdanielsen@nfb.org"),
])
def test_address_href(braille: str, is_email: bool, expected: str):
    assert address_href(u(braille), is_email) == expected


def _links(html: str) -> list[tuple[str, str]]:
    return [(href, re.sub(r"\s+", " ", text)) for href, text in re.findall('<a href="([^"]*)">(.*?)</a>', html, re.S)]


def test_links_in_paragraph_keep_braille_text_and_trailing_period_outside():
    html, notes = convert([TITLE_PAGE, [
        "  ,VISIT HTTPS3_/_/NFB4ORG_/PUBLICA;NS4 ,OR",
        "EMAIL CDANIELS5@ANFB4ORG4",
    ]])
    assert _links(html) == [
        ("https://nfb.org/publications", brl("HTTPS3_/_/NFB4ORG_/PUBLICA;NS")),
        ("mailto:cdanielsen@nfb.org", brl("CDANIELS5@ANFB4ORG")),
    ]
    # The sentence's period (4) follows the link instead of being inside it.
    assert brl("PUBLICA;NS") + "</a>" + brl("4") in html
    assert not [n for n in notes if "address" in n]


def test_address_continued_on_next_line():
    html, _ = convert([TITLE_PAGE, [
        "  ,? \"W IS LIC5S$ \"U ,,CC ,,BY-,,NC-,,ND3",
        'HTTPS3_/_/CR1TIVECOMMONS4ORG_/LIC5SES_/"',
        "BY-NC-ND_/#D4J_/DEED4EN4",
    ]])
    assert [href for href, _ in _links(html)] == ["https://creativecommons.org/licenses/by-nc-nd/4.0/deed.en"]


def test_social_media_handle_is_not_an_email():
    html, notes = convert([TITLE_PAGE, ["  ,FOLL[ U3 @ANA;NSBL9D@ANFB4SOCIAL4"]])
    assert _links(html) == []
    assert not [n for n in notes if "address" in n]


def test_address_split_by_processing_instruction_is_not_linked():
    text = u("    ,SEE HTTPS3_/_/NFB4ORG_/") + "<?braille-page " + u("#C") + "?>" + u("PUBLICA;NS4")
    assert "<a " not in create_link_pass()(text, ParserContext())


def test_existing_links_are_left_alone():
    text = '<a href="#h_1">' + u("WWW4NFB4ORG") + "</a>"
    assert create_link_pass()(text, ParserContext()) == text


def test_untranslatable_address_is_left_with_a_warning():
    notes = []
    text = "<p>" + u("  ,SEE WWW4NFB4ORG4") + "</p>"
    result = create_link_pass(lambda braille: None)(text, ParserContext(notify=lambda l, m: notes.append(m())))
    assert "<a " not in result
    assert notes and "not a link" in notes[0]
