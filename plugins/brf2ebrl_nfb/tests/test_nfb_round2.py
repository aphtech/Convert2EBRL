#  Copyright (c) 2026. American Printing House for the Blind.
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.
"""Problems found in the second review (Round 2) of the June to October 2026 conversions."""
import re

from brf2ebrl.common.detectors import translate_ascii_to_unicode_braille
from brf2ebrl_nfb.groups import group_blocks

from test_nfb_blocks import TITLE_PAGE, centered, convert, brl, elements, with_page_number

# As in the real issues, the page after the title page starts with a blank line.
ARTICLE = [
    "",
    centered(",A ,T5T ,>TICLE"),
    "  ,! >TICLE 2G9S )A FIR/ P>AGRAPH",
    "T RUNS OV] TWO L9ES4",
]


def text(html: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"<[^>]*>", "", html)).strip()


def u(ascii_text: str) -> str:
    """ASCII braille as Unicode braille, U+2800 kept, as in the text block detection works on."""
    return translate_ascii_to_unicode_braille(ascii_text)


def test_quote_paragraph_at_the_top_of_an_unnumbered_page_is_one_block():
    first_page = ARTICLE + [
        "    ,LOVE IS ABLE TO GET >.D CAMPUS )\\T",
        "  ! AID ( A GUIDE DOG4",
    ]
    second_page = [
        "    8,I ?9K ! USE ( ! :ITE CANE IS",
        "  ABSOLUTELY CRUCIAL TO MOBIL;Y & TO 2+",
        "  ABLE TO GET >.D10 %E SD4",
    ]
    html, _ = convert([TITLE_PAGE, first_page, second_page])
    assert elements(html, "p", "closing") == []
    assert elements(html, "p", "quote")[-1] == \
        brl("8,I ?9K ! USE ( ! :ITE CANE IS ABSOLUTELY CRUCIAL TO MOBIL;Y & TO 2+ ABLE TO GET >.D10 %E SD4")


def test_quote_paragraph_sharing_its_first_line_with_the_page_number_is_one_block():
    # The first line is short only because the page number is on it.
    pages = [TITLE_PAGE, ARTICLE, [
        with_page_number("    8,X 0 V SURR1L TO HE> X1 B X 0", "#C"),
        "  AL V EXCIT+ TO \"K T ,OHIO _H BE5",
        "  REPRES5T$4",
    ]]
    html, _ = convert(pages)
    assert elements(html, "p", "closing") == []
    assert elements(html, "p", "quote") == [brl("8,X 0 V SURR1L TO HE> X1 B X 0 AL V EXCIT+ TO \"K T ,OHIO _H BE5 REPRES5T$4")]


def test_heading_after_a_blank_first_line_of_an_unnumbered_page():
    pages = [TITLE_PAGE, ARTICLE, ["", "    ,COPY\"R & ,REQUE/S", "  ^C#BJBF ,NA;NAL ,F$]A;N ( ! ,BL4"]]
    html, _ = convert(pages)
    assert elements(html, "h2") == [brl(",COPY\"R & ,REQUE/S")]
    assert elements(html, "p", "closing") == []


def test_closing_of_a_quoted_letter_in_cell_7_is_not_a_heading():
    body = ARTICLE + [
        "",
        "    ,I WD WELCOME YR ?\"\\S ON ? MATT] & ON",
        "  :AT WE %D D NEXT4",
        "      ,S9C]ELY1",
        "      ,M>K",
        "",
        "    ,! ,SUB/.E ( ! ,SUIT",
    ]
    html, _ = convert([TITLE_PAGE, body])
    assert elements(html, "p", "closing") == [brl(",S9C]ELY1"), brl(",M>K")]
    assert elements(html, "h3") == []
    assert elements(html, "h2") == [brl(",! ,SUB/.E ( ! ,SUIT")]


def test_centered_title_with_source_and_date_inside_an_article_is_a_quoted_article_title():
    body = ARTICLE + [
        "",
        centered(",MIAMI ,UNIV]S;Y ,/UD5T ,HONOR$"),
        centered(",MIAMI ,UNIV]S;Y ,NEWS"),
        centered(",MAY #F1 #BJBF"),
        "    ,MA,K5ZIE ,LOVE 0 HONOR$ BY ! ,OHIO",
        "  LEGISLATURE REC5TLY4",
    ]
    html, _ = convert([TITLE_PAGE, body])
    # Without the print the source and date cannot be told from the title, so they stay in it.
    assert elements(html, "h1", "article-title")[-1].startswith(brl(",MIAMI ,UNIV]S;Y ,/UD5T ,HONOR$"))
    assert elements(html, "h2") == []


def test_press_release_title_then_a_dateline_that_happens_to_be_centered():
    dateline = "^.,,BALTIMORE1 ,,MD \"<,APRIL #BJ1"
    # 33 cells: centered in cell 4 or 5, and as the first line of a 5-3 paragraph in cell 5.
    assert len(dateline) == 33
    body = ARTICLE + [
        "",
        centered(",NA;NAL ,F$]A;N ( ! ,BL ,3D5MS"),
        centered(",DELAY ( ,DIGITAL ,A3ESSIBIL;Y"),
        "    " + dateline,
        "  #BJBF\">,- ,! ,NA;NAL ,F$]A;N ( ! ,BL",
        "  3D5MS ! RULE4",
    ]
    html, _ = convert([TITLE_PAGE, body])
    assert elements(html, "h1", "article-title")[-1] == brl(",NA;NAL ,F$]A;N ( ! ,BL ,3D5MS ,DELAY ( ,DIGITAL ,A3ESSIBIL;Y")
    quotes = elements(html, "p", "quote")
    assert len(quotes) == 1 and text(brl(",,BALTIMORE1 ,,MD")) in text(quotes[0])


def test_heading_followed_by_a_3_1_paragraph_is_not_a_5_3_paragraph():
    body = ARTICLE + [
        "",
        "    ,US+ ! ,*AIR & ,CANE AT ! ,SAME ,TIME",
        "  ,& N[ WE MOVE ONTO ! R1L M1T ( ! \"Q3",
        ",H[ D Y USE A :ITE CANE & A WHEEL*AIR",
        "AT ! SAME \"T8",
    ]
    html, _ = convert([TITLE_PAGE, body])
    assert elements(html, "h2") == [brl(",US+ ! ,*AIR & ,CANE AT ! ,SAME ,TIME")]
    assert elements(html, "p", "quote") == []
    assert elements(html, "p")[-1].startswith(brl(",& N[ WE MOVE ONTO"))


def test_long_blocked_quotation_after_a_blank_line_is_not_a_heading():
    body = ARTICLE + [
        "",
        "    ,JACOBUS T5,BROEK ,AW>D PRES5T$ TO",
        "    ,S&Y & ,JOHN ,HALV]SON = YR D$ICA;N1",
        "    SACRIFICE1 & COMMIT;T ON 2HALF ( !",
        "    BL ( ? NA;N4",
        "",
        "    ,,RESOLU;N #BJBF-#JB ,REG>D+",
        "    ,SUPPORT+ ,MOD]NIZA;N ( !",
        "    ,ABILITY,\"O ,PROGRAM & ,RE=M ( !",
        "    ,DIRECT ,LABOR ,RATIO",
        "  ,,\":AS1 ! ,ABILITY,\"O ,PROGRAM1",
    ]
    html, _ = convert([TITLE_PAGE, body])
    assert len(elements(html, "p", "quote-block")) == 1
    assert elements(html, "h2") == [brl(",,RESOLU;N #BJBF-#JB ,REG>D+ ,SUPPORT+ ,MOD]NIZA;N ( ! "
                                        ",ABILITY,\"O ,PROGRAM & ,RE=M ( ! ,DIRECT ,LABOR ,RATIO")]


def test_consecutive_photo_captions_are_separate():
    body = ARTICLE + [
        centered("\"333333333333"),
        "      ,,PHOTO ,,CAP;N3 ,CAYTE ,M5DEZ",
        "      ,,PHOTO ,,CAP;N3 #BJBF ,S*OL>%IP",
        "    ,CLASS3 ,FRONT ,R[1 LEFT TO \"R3",
        "    ,ALICESON ,MC,K5ZIE ,B>G]4",
    ]
    html, _ = convert([TITLE_PAGE, body])
    assert elements(html, "p", "caption") == [
        brl(",,PHOTO ,,CAP;N3 ,CAYTE ,M5DEZ"),
        brl(",,PHOTO ,,CAP;N3 #BJBF ,S*OL>%IP ,CLASS3 ,FRONT ,R[1 LEFT TO \"R3 ,ALICESON ,MC,K5ZIE ,B>G]4"),
    ]
    assert elements(html, "p", "quote-block") == []


def test_special_symbols_are_a_list():
    symbols_page = [
        "",
        centered(",,,SPECIAL SYMBOLS"),
        centered("US$ 9 ? VOLUME,'"),
        "",
        ".= ,DOT LOCATOR = 8M5;N0",
        ".=^/ ,ACUTE A35T ABV FOLL[+ LR",
        "",
    ]
    html, _ = convert([TITLE_PAGE, symbols_page, ARTICLE])
    assert re.search(r"</h2>\s*<ul>", html)
    assert [text(item) for item in re.findall(r"<li>(.*?)</li>", html, re.S)] == [
        text(brl(".= ,DOT LOCATOR = 8M5;N0")), text(brl(".=^/ ,ACUTE A35T ABV FOLL[+ LR"))]
    assert elements(html, "p", "left-justified") == []


def test_title_page_web_address_over_two_lines_is_one_line():
    title_page = TITLE_PAGE + [centered(",FACEBOOK4COM_/\""), centered("NA;NALF$]A;N(!BL9D")]
    html, _ = convert([title_page, ARTICLE])
    assert brl(",FACEBOOK4COM_/NA;NALF$]A;N(!BL9D") in elements(html, "p", "titlepage")


# The grouping pass, on the text as block detection leaves it.

def blocks(*parts: str) -> str:
    return "".join(f"{part}\n" for part in parts)


BLANK = "<?blank-line?>"
PAGE = "<?braille-page ?>"


def test_front_matter_groups_split_at_blank_lines_but_not_before_a_list():
    text_in = blocks('<p class="titlepage">a</p>', '<p class="titlepage">b</p>', BLANK, '<p class="titlepage">c</p>',
                     PAGE, "<p>d</p>", BLANK, "<ul>\n<li>e</li>\n</ul>", BLANK, "<p>f</p>",
                     '<h1 class="article-title">g</h1>', "<p>h</p>")
    html = group_blocks(text_in)
    groups = re.findall(r'<div class="fm-group">\n(.*?)\n</div>', html, re.S)
    assert [re.sub(r"<[^>]*>|\s|<\?[^>]*>", "", g) for g in groups] == ["ab", "c", "de", "f"]
    assert html.rstrip().endswith('<h1 class="article-title">g</h1>\n<p>h</p>')


def test_quoted_material_set_off_by_blank_lines_is_a_blockquote():
    text_in = blocks('<h1 class="article-title">t</h1>', "<p>a</p>", BLANK, '<p class="quote">q1</p>',
                     '<p class="quote">q2</p>', '<p class="closing">c</p>', BLANK, "<p>b</p>",
                     '<p class="quote">inline</p>', "<p>e</p>")
    html = group_blocks(text_in)
    assert re.findall(r"<blockquote>\n(.*?)\n</blockquote>", html, re.S) == [
        '<p class="quote">q1</p>\n<p class="quote">q2</p>\n<p class="closing">c</p>']


def test_quoted_article_title_starts_the_blockquote():
    text_in = blocks('<h1 class="article-title">t</h1>', "<p>a</p>", BLANK, '<h1 class="article-title">q</h1>',
                     '<p class="centered">source</p>', '<p class="quote">q1</p>', BLANK, "<p>b</p>")
    assert "<blockquote>\n<h1 class=\"article-title\">q</h1>" in group_blocks(text_in)


def test_letter_from_date_to_cc_with_a_quotation_inside():
    date = u(",AUGU/ #AG1 #BJBF")
    text_in = blocks('<h1 class="article-title">t</h1>', "<p>a</p>", f'<p class="left-justified">{date}</p>',
                     '<p class="left-justified">x<br/>y</p>', '<p class="salutation">dear</p>', "<p>body</p>",
                     BLANK, '<p class="quote">story</p>', BLANK, "<p>more</p>", '<p class="closing">s</p>',
                     '<p class="closing">m</p>', f"<ul>\n<li>{u(',,CC3 ,JACK')}</li>\n</ul>",
                     '<p class="separator">sep</p>')
    html = group_blocks(text_in)
    letter = re.search(r'<div class="letter">\n(.*?)\n</div>', html, re.S).group(1)
    assert letter.startswith(f'<p class="left-justified">{date}</p>') and letter.endswith("</ul>")
    assert '<blockquote>\n<p class="quote">story</p>\n</blockquote>' in letter
    assert "roster" not in html


def test_transcript_and_sample_conversation():
    transcript = blocks('<h1 class="article-title">t</h1>', '<p class="left-justified">org<br/>place</p>', BLANK,
                        '<p class="dialogue">a</p>', '<p class="dialogue-cont">b</p>',
                        '<p class="dialogue">c</p>', '<p class="separator">sep</p>')
    html = group_blocks(transcript)
    assert '<div class="event-details">\n<p class="left-justified">org<br/>place</p>\n</div>' in html
    assert re.search(r'<div class="transcript">\n<p class="dialogue">a</p>.*<p class="dialogue">c</p>\n</div>',
                     html, re.S)
    conversation = blocks('<h1 class="article-title">t</h1>', "<p>a</p>", BLANK,
                          '<p class="dialogue">x</p>', '<p class="dialogue">y</p>', BLANK, "<p>b</p>")
    html = group_blocks(conversation)
    assert "<blockquote>\n<p class=\"dialogue\">x</p>" in html and "transcript" not in html


def test_roster_of_short_lines_set_off_by_blank_lines():
    text_in = blocks('<h1 class="article-title">t</h1>', "<p>a</p>", BLANK,
                     '<p class="left-justified">n1<br/>n2</p>', BLANK, '<p class="caption">c</p>')
    assert '<div class="roster">\n<p class="left-justified">n1<br/>n2</p>\n</div>' in group_blocks(text_in)
