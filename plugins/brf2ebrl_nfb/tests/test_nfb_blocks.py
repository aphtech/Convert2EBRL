#  Copyright (c) 2026. American Printing House for the Blind.
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.
"""Block structure of the NFB Braille Monitor conversion.

Fixtures are built from short ASCII BRF lines modelled on the issue-71043 samples: 40 cells,
form feeds between pages, odd braille page numbers top right, and no blank lines."""
import re

from brf2ebrl.common import PageLayout
from brf2ebrl.common.detectors import translate_ascii_to_unicode_braille
from brf2ebrl.parser import ParserContext, parse
from brf2ebrl.plugin import find_plugins
from brf2ebrl_nfb import create_brf2ebrl_parser

CELLS = 40


def centered(text: str) -> str:
    return " " * ((CELLS - len(text)) // 2) + text


def with_page_number(text: str, number: str) -> str:
    return text + " " * (CELLS - len(text) - len(number)) + number


def brl(ascii_text: str) -> str:
    """ASCII BRF as it appears in the output: Unicode braille with U+2800 turned into spaces."""
    return translate_ascii_to_unicode_braille(ascii_text).replace("\u2800", " ")


def convert(pages: list[list[str]]) -> tuple[str, list[str]]:
    brf = "\f".join("\n".join(lines) + "\n" for lines in pages)
    notifications = []
    context = ParserContext(notify=lambda level, msg: notifications.append(msg()))
    result = parse(brf, create_brf2ebrl_parser(page_layout=PageLayout(), parser_context=context),
                   parser_context=context)
    return result, notifications


def elements(html: str, tag: str, css_class: str | None = None) -> list[str]:
    class_attr = f' class="{css_class}"' if css_class else ""
    pattern = f"<{tag}{class_attr}(?: id=\"[^\"]*\")?>(.*?)</{tag}>"
    return [re.sub(r"\s+", " ", m).strip() for m in re.findall(pattern, html, re.S)]


def has_list_items(html: str) -> bool:
    return re.search("<li[ >]", html) is not None


TITLE_PAGE = [
    centered(",,BRL ,,MONITOR"),
    centered(",! ,FLAG%IP ,MAGAZ9E ( !"),
    centered(",OCTOB] #BJBF"),
    centered(",,ISSN #JJJF-#HHBI"),
]


def test_plugin_is_discoverable():
    plugin_ids = {plugin.id for plugin in find_plugins().values()}
    assert {"BANA", "NFB"} <= plugin_ids


def test_title_page_lines_are_separate_and_issn_is_kept():
    html, _ = convert([TITLE_PAGE, ["  ,TEXT4"]])
    lines = elements(html, "p", "titlepage")
    assert lines == [brl(",,BRL ,,MONITOR"), brl(",! ,FLAG%IP ,MAGAZ9E ( !"), brl(",OCTOB] #BJBF"),
                     brl(",,ISSN #JJJF-#HHBI")]
    assert "guide words" not in html


def test_separator_then_title_and_byline():
    body = [
        "  ,LA/ P>AGRAPH ( ! O!R >TICLE4",
        centered('"333333333333'),
        centered(",KEEP ,BUILD+ ,3NEC;NS3 ,! ,F$]A;N"),
        centered(',EMPLOY;T ,NET"W BY ! ,BL'),
        centered('BY ,LIA ,/"O1 ,*AIR1 ,,NFB'),
        centered(",EMPLOY;T ,COMMITTEE1 ,MOD]ATOR"),
        "  ,F/ P>AGRAPH4",
    ]
    html, _ = convert([TITLE_PAGE, body])
    assert elements(html, "p", "separator") == [brl('"333333333333')]
    assert elements(html, "h1", "article-title") == [
        brl(',KEEP ,BUILD+ ,3NEC;NS3 ,! ,F$]A;N ,EMPLOY;T ,NET"W BY ! ,BL')]
    assert elements(html, "p", "byline") == [brl('BY ,LIA ,/"O1 ,*AIR1 ,,NFB ,EMPLOY;T ,COMMITTEE1 ,MOD]ATOR')]
    assert html.index('class="separator"') < html.index('class="article-title"') < html.index('class="byline"')


def test_centered_heading_inside_article_is_h2():
    # As in the real issues, the page after the title page starts with a blank line.
    body = [
        "",
        centered(",WELCOME TO ! ,MOVE;T"),
        "  ,P>AGRAPH4",
        centered(",WAYS TO ,A3ESS ! ,MONITOR"),
        "  ,ANO!R P>AGRAPH4",
    ]
    html, _ = convert([TITLE_PAGE, body])
    assert elements(html, "h1", "article-title") == [brl(",WELCOME TO ! ,MOVE;T")]
    assert elements(html, "h2") == [brl(",WAYS TO ,A3ESS ! ,MONITOR")]


def test_consecutive_captions_then_title():
    body = [
        centered('"333333333333'),
        '      .<,,PHOTO ,,CAP;N3 ,LIA ,/"O.>',
        "      .<,,PHOTO ,,CAP;N3 ,AUDREY ,F>NUM1",
        "    ,J5N ,HAN1 & ,J4,J4 ,M$DAU<.>",
        centered(",! ,TITLE"),
        centered("BY ,AN ,AU?OR"),
        "  ,P>AGRAPH4",
    ]
    html, _ = convert([TITLE_PAGE, body])
    assert elements(html, "p", "caption") == [
        brl('.<,,PHOTO ,,CAP;N3 ,LIA ,/"O.>'),
        brl(".<,,PHOTO ,,CAP;N3 ,AUDREY ,F>NUM1 ,J5N ,HAN1 & ,J4,J4 ,M$DAU<.>"),
    ]
    assert "<figure" not in html
    assert elements(html, "h1", "article-title") == [brl(",! ,TITLE")]


def test_transcript_is_dialogue_not_lists():
    body = [
        centered('"333333333333'),
        centered(",! ,PANEL"),
        centered("BY ,LIA ,/\"O"),
        ",M>K ,RI3OBONO3 ,? NEXT PANEL IS ABOUT",
        "  EMPLOY;T4 ,I W 9TRODUCE \\R MOD]ATOR4",
        "    ,I'D L Y TO GIVE A W>M WELCOME TO",
        "  ,LIA4",
        ',LIA ,/"O3 ,OH1 GD MORN+1 MY ,F$]A;N',
        "  FAMILY4",
        ",J4,J4 ,M$DAU<3 ,3GRATULA;NS4",
    ]
    html, _ = convert([TITLE_PAGE, body])
    assert len(elements(html, "p", "dialogue")) == 3
    assert elements(html, "p", "dialogue-cont") == [brl(",I'D L Y TO GIVE A W>M WELCOME TO ,LIA4")]
    assert not has_list_items(html)


def test_real_list_in_article_is_not_dialogue():
    body = [
        "  ,P>AGRAPH 2=E ! LI/4",
        ",GIVE ! GIFT ( LIT]ACY4",
        ',M5TOR "Y P4',
    ]
    html, _ = convert([TITLE_PAGE, body])
    assert 'class="dialogue"' not in html


def test_paragraph_starting_beside_page_number_stays_a_paragraph():
    page2 = ["  ,F/ P>AGRAPH 9 ! ,MIDDLE ( ! PAGE4"] * 2
    page3 = [
        with_page_number("  ,? P>AGRAPH />TS ON ! LINE", "#C"),
        ") ! PAGE NUMB] & RUNS ON4",
    ]
    html, _ = convert([TITLE_PAGE, page2, page3])
    paragraphs = elements(html, "p")
    assert brl(",? P>AGRAPH />TS ON ! LINE ) ! PAGE NUMB] & RUNS ON4") in paragraphs
    assert brl("#C") not in html
    assert not has_list_items(html) and "<h2" not in html


def test_roman_preliminary_page_numbers_are_removed():
    page3 = [with_page_number("  ,A P>AGRAPH ON A PRELIM PAGE", "III"), "C9UES HERE4"]
    page5 = [with_page_number("  ,ANO!R P>AGRAPH", ";V"), "C9UES4"]
    html, _ = convert([TITLE_PAGE, ["  ,PAGE TWO4"], page3, ["  ,PAGE FOUR4"], page5])
    assert brl("III") not in html
    assert brl(";V") not in html


def test_presented_by_is_a_byline_but_title_with_by_is_not():
    body = [
        centered('"333333333333'),
        centered(",! ,AW>D ,PRES5TA;N"),
        centered(",PRES5T$ BY ,PAM ,ALL5"),
        "  ,P>AGRAPH4",
        centered('"333333333333'),
        centered(',NET"W BY ! ,BL'),
        "  ,ANO!R P>AGRAPH4",
    ]
    html, _ = convert([TITLE_PAGE, body])
    assert elements(html, "p", "byline") == [brl(",PRES5T$ BY ,PAM ,ALL5")]
    assert elements(html, "h1", "article-title") == [brl(",! ,AW>D ,PRES5TA;N"), brl(',NET"W BY ! ,BL')]


def test_unbracketed_caption_and_stage_direction():
    body = [
        centered('"333333333333'),
        "      ,,PHOTO ,,CAP;N3 ,LAUR5 ,B1LL",
        centered(",! ,TITLE"),
        "  ,P>AGRAPH4",
        "      .<,VIDEO 2G9S.>",
        "  ,MORE TEXT4",
    ]
    html, _ = convert([TITLE_PAGE, body])
    assert elements(html, "p", "caption") == [brl(",,PHOTO ,,CAP;N3 ,LAUR5 ,B1LL")]
    assert elements(html, "p", "direction") == [brl(".<,VIDEO 2G9S.>")]


def test_speaker_paragraph_ending_a_line_with_a_year_is_still_dialogue():
    body = [
        centered('"333333333333'),
        centered(",! ,PANEL"),
        ",N>RATOR3 ,! W9N]S RCV A TROPHY & A",
        "  PRIZE ) _! #BJBF",
        "  ,AW>DS4",
    ]
    html, _ = convert([TITLE_PAGE, body])
    assert len(elements(html, "p", "dialogue")) == 1
