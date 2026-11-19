#  Copyright (c) 2026. American Printing House for the Blind.
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.
"""The NFB TOC: one flat entry per article, linked to the article heading, across volumes."""
import re
import zipfile

from brf2ebrl import convert
from brf2ebrl.common import PageLayout
from brf2ebrl.parser import ParserContext, EBrailleParserOptions
from brf2ebrl_nfb import PLUGIN
from brf2ebrl_nfb.bundler import resolve_toc_links

from test_nfb_blocks import TITLE_PAGE, centered, convert as convert_pages, brl, elements

TOC_PAGE = [
    centered(",3T5TS"),
    "",
    centered(',"P #A'),
    ',F ! ,$ITOR BY ,*RIS ,DANIELS5 """""" #A',
    ",KEEP ,BUILD+ ,3NEC;NS3 ,! ,F$]A;N",
    '  ,EMPLOY;T ,NET"W BY ! ,BL BY',
    '  ,LIA ,/"O """"""""""""""""""""""""" #C',
    "",
    centered(',"P #B'),
    ",X'S ,\\R ,TURN ,N[ BY ,JONA?AN ,MOS5 #GA",
]

ARTICLES_VOLUME_1 = [
    '      .<,,PHOTO ,,CAP;N3 ,*RIS ,DANIELS5.>',
    centered(",F ! ,$ITOR"),
    centered("BY ,*RIS ,DANIELS5"),
    "  ,P>AGRAPH4",
    centered('"333333333333'),
    centered(",KEEP ,BUILD+ ,3NEC;NS3 ,! ,F$]A;N"),
    centered(',EMPLOY;T ,NET"W BY ! ,BL'),
    centered('BY ,LIA ,/"O'),
    "  ,P>AGRAPH4",
    centered('"333333333333'),
]

ARTICLES_VOLUME_2 = [
    # As in the real issues, the page after the title page starts with a blank line.
    "",
    centered(",X'S ,\\R ,TURN ,N["),
    centered("BY ,JONA?AN ,MOS5"),
    "  ,P>AGRAPH4",
    centered('"333333333333'),
]


def test_toc_entries_are_flat_with_parts_and_page_numbers():
    html, _ = convert_pages([TITLE_PAGE, TOC_PAGE, ARTICLES_VOLUME_1])
    assert elements(html, "h1", "toc-title") == [brl(",3T5TS")]
    assert elements(html, "h2", "toc-part") == [brl(',"P #A'), brl(',"P #B')]
    entries = re.findall(r'<li>\s*<a href="#nfb-toc-\d+">(.*?)</a>\s*<span class="toc-page">(.*?)</span>\s*</li>',
                         html, re.S)
    assert [(re.sub(r"\s+", " ", e), p) for e, p in entries] == [
        (brl(",F ! ,$ITOR BY ,*RIS ,DANIELS5"), brl("#A")),
        (brl(',KEEP ,BUILD+ ,3NEC;NS3 ,! ,F$]A;N ,EMPLOY;T ,NET"W BY ! ,BL BY ,LIA ,/"O'), brl("#C")),
        (brl(",X'S ,\\R ,TURN ,N[ BY ,JONA?AN ,MOS5"), brl("#GA")),
    ]
    assert "<ol" not in html
    # The first heading after the TOC starts an article.
    assert elements(html, "h1", "article-title")[0] == brl(",F ! ,$ITOR")


def _write_brf(path, pages):
    path.write_text("\f".join("\n".join(lines) + "\n" for lines in pages), encoding="utf-8")
    return str(path)


def test_toc_links_to_articles_in_the_same_and_later_volumes(tmp_path):
    volume_1 = _write_brf(tmp_path / "bm01.brf", [TITLE_PAGE, TOC_PAGE, ARTICLES_VOLUME_1])
    volume_2 = _write_brf(tmp_path / "bm02.brf", [TITLE_PAGE, ARTICLES_VOLUME_2])
    output = tmp_path / "out.ebrl"
    convert(PLUGIN, [volume_1, volume_2], str(output),
            parser_context=ParserContext(options={EBrailleParserOptions.page_layout: PageLayout()}))
    with zipfile.ZipFile(output) as z:
        vol0 = z.read("ebraille/vol0.html").decode("utf-8")
        vol1 = z.read("ebraille/vol1.html").decode("utf-8")
        names = z.namelist()
    assert names.index("ebraille/vol0.html") < names.index("ebraille/vol1.html")
    links = re.findall('<a href="([^"]*)">', vol0)
    ids_0 = dict(re.findall('<h1 class="article-title" id="([^"]+)">(.*?)</h1>', vol0))
    ids_1 = dict(re.findall('<h1 class="article-title" id="([^"]+)">(.*?)</h1>', vol1))
    assert len(links) == 3
    assert ids_0[links[0].lstrip("#")] == brl(",F ! ,$ITOR")
    # Title containing "by" ("...Network by the Blind by Lia Soto") still links to its article.
    assert ids_0[links[1].lstrip("#")] == brl(',KEEP ,BUILD+ ,3NEC;NS3 ,! ,F$]A;N ,EMPLOY;T ,NET"W BY ! ,BL')
    assert links[2].startswith("vol1.html#")
    assert ids_1[links[2].split("#")[1]] == brl(",X'S ,\\R ,TURN ,N[")
    assert "nfb-toc-" not in vol0


def test_unmatched_entry_is_unlinked_and_warned(caplog):
    volume = ('<html><body><nav class="toc"><ul class="toc">'
              '<li><a href="#nfb-toc-1">\u2820\u2801 BY X</a> <span class="toc-page">1</span></li>'
              '</ul></nav><h1 class="article-title" id="h_1">\u2820\u2803</h1></body></html>')
    [(_, resolved)] = resolve_toc_links([("vol0.html", volume)])
    assert "<a " not in resolved
    assert "\u2820\u2801 BY X" in resolved
    assert "No article found for TOC entry" in caplog.text


def test_two_articles_with_the_same_title_are_matched_in_order():
    volume = ('<html><body><ul class="toc">'
              '<li><a href="#nfb-toc-1">\u2820\u2801 \u2803\u283d \u2820\u282d</a></li>'
              '<li><a href="#nfb-toc-2">\u2820\u2801 \u2803\u283d \u2820\u283d</a></li></ul>'
              '<h1 class="article-title" id="h_1">\u2820\u2801</h1>'
              '<h1 class="article-title" id="h_2">\u2820\u2801</h1></body></html>')
    [(_, resolved)] = resolve_toc_links([("vol0.html", volume)])
    assert re.findall('<a href="([^"]*)">', resolved) == ["#h_1", "#h_2"]
