#  Copyright (c) 2026. American Printing House for the Blind.
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.
"""Block and spacing problems found by reviewing the June to October 2026 conversions."""
import re
import zipfile
from importlib import resources

from brf2ebrl import convert as convert_files
from brf2ebrl.common import PageLayout
from brf2ebrl.parser import ParserContext, EBrailleParserOptions
from brf2ebrl_nfb import PLUGIN
from brf2ebrl_nfb.lines import join_lines

from test_nfb_blocks import TITLE_PAGE, centered, convert, brl, elements, with_page_number


def text(html: str) -> str:
    """The text a reader gets: tags and processing instructions removed, line breaks as spaces."""
    return re.sub(r"\s+", " ", re.sub(r"<[^>]*>", "", html)).strip()


def test_join_lines_hyphen_dash_and_continuation():
    hyphen, dash, dot5 = brl("CROSS-"), brl("UP,-"), brl("NFB4ORG_/GET\"")
    assert join_lines([hyphen, brl("SECTION")]) == brl("CROSS-SECTION")
    assert join_lines([dash, brl("OVENS")]) == brl("UP,-OVENS")
    assert join_lines([dot5, brl("WAYS")]) == brl("NFB4ORG_/GETWAYS")
    assert join_lines([brl("A"), "<?braille-page x?>", brl("B")]) == brl("A") + "\n<?braille-page x?>" + brl("B")
    # Guide dots are not a continuation indicator.
    assert join_lines([brl('TITLE """"'), brl("MORE")]) == brl('TITLE """"') + "\n" + brl("MORE")


def test_paragraph_and_list_lines_join_with_one_space():
    body = [
        "",
        "  ,! WORD CROSS-",
        "SECTION & ,R&OLPH,-",
        ",%EPP>D4",
        "",
        "_4 ,DEVELOP PROJECTS TO %[ BL Y\\? T MA?",
        "  C>E]S >E )9 _! R1*4",
        "_4 ,ANO!R ITEM4",
        "",
    ]
    html, _ = convert([TITLE_PAGE, body])
    assert brl(",! WORD CROSS-SECTION & ,R&OLPH,-,%EPP>D4") in text(html)
    assert brl("_4 ,DEVELOP PROJECTS TO %[ BL Y\\? T MA? C>E]S >E )9 _! R1*4") in elements(html, "li")


def test_cell_5_heading_over_two_lines_is_one_heading():
    body = [
        "  ,P>AGRAPH4",
        "",
        "    ,3FIGUR+ ,ADOBE ,ACROBAT ,R1D] =",
        "    ,A3ESSIBIL;Y",
        "  ,AF ,ADOBE ,ACROBAT HAS BE5 9/ALL$4",
    ]
    html, _ = convert([TITLE_PAGE, body])
    assert elements(html, "h2") == [brl(",3FIGUR+ ,ADOBE ,ACROBAT ,R1D] = ,A3ESSIBIL;Y")]
    assert brl(",AF ,ADOBE ,ACROBAT HAS BE5 9/ALL$4") in elements(html, "p")


def test_letter_date_address_salutation_and_closing():
    body = [
        "  ,LA/ P>AGRAPH4",
        "",
        ",AUGU/ #F1 #BJBF",
        "",
        ",! ,HONORABLE ,JOHN ,?UNE",
        ",MAJOR;Y ,L1D]",
        "#EAA ,DIRKS5 ,S5ATE ,(FICE ,BUILD+",
        ",WA%+TON1 ,,DC #BJEAJ",
        "",
        "    ,DE> ,MAJOR;Y ,L1D] ,?UNE3",
        "  ,! ,NA;NAL ,F$]A;N ( ! ,BL IS ! LARGE/",
        "ORGANIZA;N4",
        "    ,S9C]ELY1",
        "    ,M>K ,A4 ,RI3OBONO1 ,PRESID5T",
        "    ,NA;NAL ,F$]A;N ( ! ,BL",
    ]
    html, _ = convert([TITLE_PAGE, body])
    assert not re.search("<li[ >]", html) and "<h2" not in html
    assert elements(html, "p", "left-justified") == [
        brl(",AUGU/ #F1 #BJBF"),
        "<br/>".join(brl(line) for line in [",! ,HONORABLE ,JOHN ,?UNE", ",MAJOR;Y ,L1D]",
                                            "#EAA ,DIRKS5 ,S5ATE ,(FICE ,BUILD+", ",WA%+TON1 ,,DC #BJEAJ"])]
    assert elements(html, "p", "salutation") == [brl(",DE> ,MAJOR;Y ,L1D] ,?UNE3")]
    assert elements(html, "p", "closing") == [brl(",S9C]ELY1"), brl(",M>K ,A4 ,RI3OBONO1 ,PRESID5T"),
                                              brl(",NA;NAL ,F$]A;N ( ! ,BL")]


def test_numbered_steps_with_sub_steps_and_note_are_one_nested_list():
    body = [
        "  ,P>AGRAPH4",
        "",
        "#A4 ,BY DEFAULT1 ,ADOBE ,ACROBAT ,R1D] W",
        "    2 US+ ! ,NEW M5U4",
        "      ,TO BR+ BACK ! TRADI;NAL M5U B> 9",
        "    ,ADOBE ,ACROBAT ,R1D]1 PRESS ,ALT4",
        "#B4 ,N[ 3FIGURE ,ADOBE ,ACROBAT ,R1D]4",
        "  ,A4 ,F/ SET ! DEFAULT PROGRAM TO OP5",
        "    ,,PDF FILES4",
        "  ;,B4 ,3FIGURE ! R1D+ ORD]4",
        "",
    ]
    html, _ = convert([TITLE_PAGE, body])
    assert html.count("<ul class=\"steps\">") == 1 and html.count("<ul>") == 1
    assert "<h2" not in html and "<h3" not in html
    assert elements(html, "p", "note") == [brl(",TO BR+ BACK ! TRADI;NAL M5U B> 9 ,ADOBE ,ACROBAT ,R1D]1 PRESS ,ALT4")]
    items = re.findall(r"<li>(.*?)(?=<p|<ul|</li>)", html, re.S)
    assert [re.sub(r"\s+", " ", item).strip() for item in items] == [
        brl("#A4 ,BY DEFAULT1 ,ADOBE ,ACROBAT ,R1D] W 2 US+ ! ,NEW M5U4"),
        brl("#B4 ,N[ 3FIGURE ,ADOBE ,ACROBAT ,R1D]4"),
        brl(",A4 ,F/ SET ! DEFAULT PROGRAM TO OP5 ,,PDF FILES4"),
        brl(";,B4 ,3FIGURE ! R1D+ ORD]4"),
    ]


def test_bracketed_direction_in_7_7_is_one_block():
    body = [
        ",JONA?AN ,MOS53 ,HELLO4",
        "      .<,APPLAUSE & MUSIC1 EXC]PT (",
        "      8,VIDEO ,KILL$ ! ,RADIO ,/>0 BY ,!",
        "      ,BU7LES.>",
        ",JONA?AN ,MOS53 ,HOPE;LLY4",
    ]
    html, _ = convert([TITLE_PAGE, body])
    assert elements(html, "p", "direction") == [
        brl('.<,APPLAUSE & MUSIC1 EXC]PT ( 8,VIDEO ,KILL$ ! ,RADIO ,/>0 BY ,! ,BU7LES.>')]
    assert "<h3" not in html


def test_quoted_plaque_in_a_transcript_is_two_paragraphs_not_headings():
    body = [
        ",PAM ,ALL53 ,X SAYS3",
        "    ,JACOBUS T5,BROEK ,AW>D PRES5T$ TO",
        "    ,S&Y & ,JOHN ,HALV]SON = YR D$ICA;N1",
        "    SACRIFICE1 & COMMIT;T ON 2HALF ( !",
        "    BL ( ? NA;N4",
        "      ,:5\"E WE H ASK$1 Y H ANSW]$4 ,WE",
        "    CALL Y \\R COLL1GUES ) RESPECT4",
    ]
    html, _ = convert([TITLE_PAGE, body])
    assert "<h2" not in html and "<h3" not in html
    assert len(elements(html, "p", "quote-block")) == 1
    assert len(elements(html, "p", "quote-indent")) == 1


def test_sentence_with_a_colon_does_not_start_a_transcript():
    body = [
        "  ,I GET 9 & CLOSE ! DOOR4",
        ",IMMLY ! C> SP1KS3 8,GD MORN+40",
        ",MY WIFE CALLS ! VOICE ,W&A4",
    ]
    html, _ = convert([TITLE_PAGE, body])
    assert 'class="dialogue"' not in html and not re.search("<li[ >]", html)
    assert len(elements(html, "p")) == 1


def test_toc_entry_running_over_a_page_break_stays_in_the_toc():
    page_2 = [
        "",
        centered(",3T5TS"),
        "",
        ",NA;NAL ,F$]A;N ( ! ,BL ,ANN\\NCES",
        "  ,/AFF ,L1D]%IP ,TRANSI;N",
    ]
    page_3 = [
        with_page_number("  ,EXECUTIVE ,ROLE \"\"\"\"\"\"\" #BGD", "#C"),
        ',3V5;N ,M9IATURES """"""""""""""""" #BGG',
        "",
    ]
    html, _ = convert([TITLE_PAGE, page_2, page_3])
    nav = html[html.index("<nav"):html.index("</nav>")]
    assert brl(",3V5;N ,M9IATURES") in nav
    assert len(re.findall("<li>", nav)) == 2


def test_title_page_continued_on_the_second_page():
    page_2 = [
        centered(",WAT* & %>E \\R VIDEOS3"),
        centered(",Y\\,TUBE4COM_/,NA;NS,BL9D"),
        "",
        "  ,LRS TO ! ,PRESID5T4",
    ]
    html, _ = convert([TITLE_PAGE, page_2])
    assert brl(",WAT* & %>E \\R VIDEOS3") in elements(html, "p", "titlepage")
    assert 'class="article-title"' not in html


def test_bundle_uses_the_nfb_stylesheet(tmp_path):
    brf = tmp_path / "bm01.brf"
    brf.write_text("\f".join("\n".join(lines) + "\n" for lines in [TITLE_PAGE, ["  ,TEXT4"]]), encoding="ascii")
    output = tmp_path / "out.ebrl"
    convert_files(PLUGIN, [str(brf)], str(output),
                  parser_context=ParserContext(options={EBrailleParserOptions.page_layout: PageLayout()}))
    with zipfile.ZipFile(output) as z:
        css = z.read("ebraille/css/default.css")
        assert z.namelist().count("ebraille/css/default.css") == 1
    assert css == resources.files("brf2ebrl_nfb").joinpath("css", "default.css").read_bytes()
