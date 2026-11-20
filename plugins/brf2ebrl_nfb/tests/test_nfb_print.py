#  Copyright (c) 2026. American Printing House for the Blind.
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.
"""The optional print HTML: used when it is next to the BRF, ignored when it is not."""
import re

from brf2ebrl.common import PageLayout
from brf2ebrl.parser import ParserContext, parse
from brf2ebrl_nfb import create_brf2ebrl_parser
from brf2ebrl_nfb.print_source import find_print_html, load_print_issue

from test_nfb_blocks import TITLE_PAGE, centered

PRINT_HTML = """<html><head><meta charset="windows-1252"><title>NFB Braille Monitor October 2026</title></head>
<body><h1>Braille Monitor</h1><h2>Contents</h2>
<h2>It\x92s Our Turn Now</h2><p>by Jonathan Mos\xe9n</p>
<h3>Ways to Access the Monitor</h3><h4>Submission Guidelines</h4>
<p><a href="https://www.nfb.org/newsline/">NEWSLINE</a>
<a href="mailto:cdanielsen@nfb.org">email</a></p></body></html>"""

BODY = [
    centered('"333333333333'),
    centered(",X'S ,\\R ,TURN ,N["),
    centered("BY ,JONA?AN ,MOS5"),
    "  ,EMAIL CDANIELS5@ANFB4ORG4",
    centered(",WAYS TO ,A3ESS ! ,MONITOR"),
    "  ,P>AGRAPH4",
    centered(",SUBMIS.N ,GUIDEL9ES"),
    "  ,VISIT WWW4NFB4ORG_/NEWSL9E4",
]


def _write_issue(folder, print_files: dict[str, bytes]):
    brf = folder / "bm2610v01.brf"
    brf.write_text("\f".join("\n".join(lines) + "\n" for lines in [TITLE_PAGE, BODY]), encoding="utf-8")
    for name, content in print_files.items():
        (folder / name).write_bytes(content)
    return str(brf)


def _convert(brf_path: str) -> str:
    with open(brf_path, encoding="utf-8") as f:
        brf = f.read()
    context = ParserContext()
    load_print_issue.cache_clear()
    return parse(brf, create_brf2ebrl_parser(page_layout=PageLayout(), brf_path=brf_path, parser_context=context),
                 parser_context=context)


def test_find_print_html(tmp_path):
    assert find_print_html(str(tmp_path / "a.brf")) is None
    (tmp_path / "Complete Braille Monitor.htm").write_text("<html></html>")
    assert find_print_html(str(tmp_path / "a.brf")).endswith("Complete Braille Monitor.htm")
    (tmp_path / "notes.html").write_text("<html></html>")
    assert find_print_html(str(tmp_path / "a.brf")).endswith("Complete Braille Monitor.htm")
    (tmp_path / "Complete draft.html").write_text("<html></html>")
    assert find_print_html(str(tmp_path / "a.brf")) is None
    files = tmp_path / "files"
    files.mkdir()
    (files / "Complete inner.htm").write_text("<html></html>")
    assert find_print_html(str(files / "a.brf")) is not None  # a folder's own file, not its parent's


def test_print_issue_reads_windows_1252(tmp_path):
    path = tmp_path / "Complete.htm"
    path.write_bytes(PRINT_HTML.encode("latin-1"))
    load_print_issue.cache_clear()
    issue = load_print_issue(str(path))
    assert issue.title == "NFB Braille Monitor October 2026"
    assert [h.text for h in issue.headings][0] == "It’s Our Turn Now"
    assert "Contents" not in [h.text for h in issue.headings]
    assert issue.links == ["https://www.nfb.org/newsline/", "mailto:cdanielsen@nfb.org"]


def test_print_refines_ids_levels_and_links_but_not_text(tmp_path):
    with_print = tmp_path / "with"
    without_print = tmp_path / "without"
    with_print.mkdir()
    without_print.mkdir()
    html_with = _convert(_write_issue(with_print, {"Complete Braille Monitor.htm": PRINT_HTML.encode("latin-1")}))
    html_without = _convert(_write_issue(without_print, {}))

    assert '<h1 class="article-title" id="its-our-turn-now">' in html_with
    assert re.search('<h1 class="article-title" id="h_\\d+">', html_without)
    # Print h3 stays h2, print h4 becomes h3.
    assert re.search("<h2[^>]*>[^<]*</h2>", html_with) and re.search("<h3[^>]*>[^<]*</h3>", html_with)
    assert not re.search("<h3", html_without)
    # The print address (here with its final slash) replaces the back-translated one.
    assert 'href="https://www.nfb.org/newsline/"' in html_with
    assert 'href="https://www.nfb.org/newsline"' in html_without
    strip_tags = lambda html: re.sub("<[^>]+>", "", html)
    assert strip_tags(html_with) == strip_tags(html_without)
