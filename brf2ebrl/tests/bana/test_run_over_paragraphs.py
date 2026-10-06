#  Copyright (c) 2024. American Printing House for the Blind.
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""BANA pipeline tests for 7-5 paragraphs and their neighbouring headings."""

import re

from brf2ebrl.common import PageLayout
from brf2ebrl.common.detectors import translate_ascii_to_unicode_braille
from brf2ebrl.parser import parse
from brf2ebrl_bana import create_brf2ebrl_parser

_HEADING_RE = re.compile(r"<h[1-6][ >]")


def _convert(brf: str) -> str:
    return parse(brf, create_brf2ebrl_parser(page_layout=PageLayout()))


def _braille(text: str) -> str:
    """Only the non-blank braille cells, so markup and line breaks are ignored."""
    return "".join(c for c in text if "⠁" <= c <= "⣿")


def _element_containing(html: str, tag: str, brl: str) -> str:
    """The text of the first given element whose braille contains brl."""
    for m in re.finditer(rf"<{tag}\b[^>]*>(.*?)</{tag}>", html, flags=re.S):
        if brl in _braille(m.group(1)):
            return m.group(1)
    raise AssertionError(f"no <{tag}> contains {brl}")


# work/A-B2522-V01.BRF lines 1777-1792 with the original indentation: the end
# of a paragraph, a figure caption in 7-5 then a transcriber's note in 7-5.
_FIGURE_THEN_TN = r"""G5ES1 : >E COMPOS$ ( @#7DEOXYRIBONUCLEIC
ACID "<,,DNA">4@#' ,)9 A CELL'S NUCLEUS1
G5ES >E BUNDL$ 9 PACKAGES CALL$
.1*ROMO"SS "<,FIGURE #A4D">4 ,HUMANS
9H]IT HALF ( _! *ROMO"SS F EA*
BIOLOGICAL P>5T4 ,! UNIQUE COMB9A;N (
G5ES F YR P>5TS DET]M9ES _M ( YR
"*I/ICS4
      ^1,FIGURE ^1#A4D ,CELLS 3TA9 ?\S&S
    ( *ROMO"SS1 : 3TA9 HUNDR$S TO ?\S&S
    ( G5ES4 ,^! G5ES 3TA9 ,,DNA & =M !
    BLUEPR9T = YR P]SONAL;Y & H1L?4
      @.<,! FOLL[+ DIAGRAM %[S ! BASIC
    /RUCTURE ( A CELL & AL TWO EXP&$
    VIEWS ( MAT]IAL 9SIDE A CELL4@.>

"""
_CAPTION = _FIGURE_THEN_TN.splitlines()[8:12]
_TN = _FIGURE_THEN_TN.splitlines()[12:15]


def test_7_5_caption_and_transcribers_note_are_two_paragraphs_not_headings():
    html = _convert(_FIGURE_THEN_TN)

    assert not _HEADING_RE.search(html)
    caption_brl = _braille(translate_ascii_to_unicode_braille("".join(_CAPTION)))
    tn_brl = _braille(translate_ascii_to_unicode_braille("".join(_TN)))
    # the caption is one paragraph with all its run-over lines and keeps its bold
    caption = _element_containing(html, "p", _braille(translate_ascii_to_unicode_braille(",CELLS 3TA9")))
    assert _braille(caption) == caption_brl
    assert caption.count("<strong>") == 2
    # the transcriber's note is a separate TN block, from its opening to its closing indicator
    tn = _element_containing(html, "div", _braille(translate_ascii_to_unicode_braille("DIAGRAM")))
    assert _braille(tn) == tn_brl
    assert tn_brl.startswith("⠈⠨⠣") and tn_brl.endswith("⠈⠨⠜")
    assert '<div class="tn">' + tn in html
    # no braille is lost or reordered
    assert caption_brl + tn_brl in _braille(html)


def test_cell_7_heading_on_its_own_stays_a_heading():
    html = _convert("      ,R1D+ & ,WRIT+ ,PRACTICE\n\n")

    assert re.search(r"<h3[^>]*>⠠⠗⠂⠙⠬ ⠯ ⠠⠺⠗⠊⠞⠬ ⠠⠏⠗⠁⠉⠞⠊⠉⠑</h3>", html)
    assert "<p>" not in html


def test_cell_7_heading_followed_by_cell_5_lines_stays_a_heading():
    # work/A-B2522-V01.BRF lines 3383-3386: the cell 5 line's first word would
    # have fit on the heading line, so it is not a run-over of a 7-5 paragraph.
    html = _convert(
        "    ,/&>DIZ$ ,TE/ ,PREP\n"
        "      ,R1D+ & ,WRIT+ ,PRACTICE\n"
        "    ,R1D ! PASSAGE 2L & !N ANSW] !\n"
        "    FOLL[+ \"QS4\n\n"
    )

    assert re.search(r"<h3[^>]*>⠠⠗⠂⠙⠬ ⠯ ⠠⠺⠗⠊⠞⠬ ⠠⠏⠗⠁⠉⠞⠊⠉⠑</h3>", html)


def test_centered_heading_followed_by_7_5_caption():
    html = _convert("            ,CELL ,/RUCTURE\n\n" + "\n".join(_CAPTION) + "\n\n")

    assert re.search(r"<h1[^>]*>⠠⠉⠑⠇⠇ ⠠⠌⠗⠥⠉⠞⠥⠗⠑</h1>", html)
    assert len(_HEADING_RE.findall(html)) == 1
    caption = _element_containing(html, "p", _braille(translate_ascii_to_unicode_braille(",CELLS 3TA9")))
    assert _braille(caption) == _braille(translate_ascii_to_unicode_braille("".join(_CAPTION)))


def test_cell_5_heading_followed_by_7_5_caption():
    html = _convert("    ,CELL ,/RUCTURE\n" + "\n".join(_CAPTION) + "\n\n")

    assert re.search(r"<h2[^>]*>⠠⠉⠑⠇⠇ ⠠⠌⠗⠥⠉⠞⠥⠗⠑</h2>", html)
    assert len(_HEADING_RE.findall(html)) == 1
    caption = _element_containing(html, "p", _braille(translate_ascii_to_unicode_braille(",CELLS 3TA9")))
    assert _braille(caption) == _braille(translate_ascii_to_unicode_braille("".join(_CAPTION)))


def test_7_5_transcribers_note_introducing_a_listed_table_stays_with_the_table():
    # work/chem.brf lines 1604-1613: the transcriber's note describes the
    # listed table which follows it, so the table detector keeps both.
    html = _convert(
        "      @.<,PR9T =MAT IS *ANG$4 ,R[ H1D+S\n"
        "    >E BLOCK$ 9 CELL #E2 COLUMN H1D+S\n"
        "    2G9 9 CELL #A4 ,ALL H1D+S >E REP1T$\n"
        "    = CL>;Y4 ,A COLON SEP>ATES H1D+S F\n"
        "    TABLE 5TRIES4@.>\n"
        "\n"
        "    ,SETT+3 ,AIRPLANE MODE\n"
        ",OP;N_/,RESULT3 ,ON OR (F2 :5 ON1 ALL\n"
        "  WIRE.S FUNC;NALITIES >E 4ABL$\n"
        "\n"
        "    ,SETT+3 ,=MAT M>K]S\n"
        ",OP;N_/,RESULT3 ,ON OR (F2 :5 (F1 =MAT\n"
        "  M>K]S >E HIDD5\n"
        "\n"
    )

    assert '<table class="listed">' in html
    assert '<div class="tn">' not in html
    assert not _HEADING_RE.search(html)
