#  Copyright (c) 2024. American Printing House for the Blind.
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.
import re

from brf2ebrl import ParserContext
from brf2ebrl.common.nemeth_detectors import (
    NEMETH_OPEN,
    NEMETH_TERM,
    detect_and_pass_nemeth_block,
    detect_block_nemeth,
    find_nemeth_span,
    restore_nemeth_braille,
    tag_inline_nemeth,
)

MATH = "⠭⠬⠑"
DOT_LOCATOR = "⠨⠿"


def test_find_nemeth_span_none_without_opening_indicator():
    assert find_nemeth_span(f"plain text {MATH}\n", 0) is None


def test_find_nemeth_span_none_when_unterminated():
    brf = f"  {NEMETH_OPEN}{MATH}\n"
    assert find_nemeth_span(brf, brf.index(NEMETH_OPEN)) is None


def test_find_nemeth_span_none_for_dot_locator_mention():
    brf = f"{DOT_LOCATOR}{NEMETH_OPEN} description\n"
    assert find_nemeth_span(brf, brf.index(NEMETH_OPEN)) is None


def test_find_nemeth_span_inline_when_prose_on_both_sides():
    brf = f"find {NEMETH_OPEN}{MATH}{NEMETH_TERM} and solve it.\n"
    span = find_nemeth_span(brf, brf.index(NEMETH_OPEN))
    assert span is not None
    assert span.is_block is False
    assert span.is_clean is False


def test_find_nemeth_span_block_when_clean_single_line():
    """A displayed equation with nothing else on its line is block, even
    though it fits entirely on one braille line -- prose adjacency is the
    signal that matters, not whether it wraps."""
    brf = f"  {NEMETH_OPEN}{MATH}{NEMETH_TERM}\n"
    span = find_nemeth_span(brf, brf.index(NEMETH_OPEN))
    assert span is not None
    assert span.is_block is True
    assert span.is_clean is True


def test_find_nemeth_span_block_when_multiline():
    brf = f"  {NEMETH_OPEN}{MATH}\n    {MATH}\n    {MATH}{NEMETH_TERM}\n"
    span = find_nemeth_span(brf, brf.index(NEMETH_OPEN))
    assert span is not None
    assert span.is_block is True
    assert span.is_clean is True


def test_find_nemeth_span_block_when_surrounded_by_blank_lines():
    brf = (
        "solve the following equation.\n"
        "<?blank-line?>\n"
        f"    {NEMETH_OPEN}{MATH}{NEMETH_TERM}\n"
        "<?blank-line?>\n"
    )
    span = find_nemeth_span(brf, brf.index(NEMETH_OPEN))
    assert span is not None
    assert span.is_block is True
    # prose introduces it on the line above, not sharing the Nemeth's own line
    assert span.is_clean is True


def test_find_nemeth_span_dirty_when_prose_shares_opening_line():
    brf = f"solve the equation {NEMETH_OPEN}{MATH}\n  {MATH}{NEMETH_TERM}\n"
    span = find_nemeth_span(brf, brf.index(NEMETH_OPEN))
    assert span is not None
    assert span.is_clean is False


def test_find_nemeth_span_block_when_blank_line_between_open_and_close():
    """A blank line strictly between the open and close indicators is a
    decisive block signal, even with prose sharing both the opening and
    closing line -- an inline, same-line usage can never contain a full
    blank line."""
    brf = (
        f"problem 1. {NEMETH_OPEN} {MATH}\n"
        "<?blank-line?>\n"
        f"problem 2. {MATH}{NEMETH_TERM} answer key\n"
    )
    span = find_nemeth_span(brf, brf.index(NEMETH_OPEN))
    assert span is not None
    assert span.has_internal_blank_line is True
    assert span.is_block is True
    assert span.is_clean is False


def test_detect_block_nemeth_wraps_clean_block_in_shadow_encoded_div():
    brf = f"  {NEMETH_OPEN}{MATH}{NEMETH_TERM}\n"
    cursor = brf.index(NEMETH_OPEN)
    result = detect_block_nemeth(brf, cursor, {}, "prefix")
    assert result is not None
    assert result.cursor == len(brf)
    assert result.text.startswith('prefix<div class="nemeth">')
    assert result.text.endswith("</div>\n")
    # the braille content between the tags must not be real braille cells any more
    inner = result.text[len('prefix<div class="nemeth">'):-len("</div>\n")]
    assert not any("⠀" <= c <= "⣿" for c in inner)


def test_detect_block_nemeth_drops_trailing_line_padding():
    """BRF lines are often padded with blank braille cells out to the cell
    width. That padding must not survive as a whitespace-only chunk after
    the closing div -- otherwise a later pass like detect_pre picks it up
    and emits a bogus empty <pre></pre> block for every Nemeth region."""
    padding = "⠀⠀⠀⠀"
    brf = f"  {NEMETH_OPEN}{MATH}{NEMETH_TERM}{padding}\n"
    result = detect_block_nemeth(brf, brf.index(NEMETH_OPEN), {}, "")
    assert result is not None
    assert result.cursor == len(brf)
    assert result.text.endswith("</div>\n")
    assert padding not in result.text


def test_detect_block_nemeth_drops_leading_indent():
    """A clean block Nemeth region is commonly indented (e.g. 2 or 4 cells)
    to set it off from surrounding prose. That indent is copied verbatim
    into output_text by earlier, unmatched single-character advances before
    this detector ever sees the opening indicator -- it must be trimmed back
    out, otherwise a later pass like detect_pre picks it up and emits a
    bogus whitespace-only <pre>  </pre> block right before the div for
    every indented Nemeth region."""
    indent = "⠀⠀⠀⠀"
    brf = f"{indent}{NEMETH_OPEN}{MATH}{NEMETH_TERM}\n"
    cursor = brf.index(NEMETH_OPEN)
    # output_text already ends with the indent, as if earlier unmatched
    # single-character advances had copied it there verbatim.
    result = detect_block_nemeth(brf, cursor, {}, f"prefix{indent}")
    assert result is not None
    assert result.text.startswith('prefix<div class="nemeth">')
    assert indent not in result.text


def test_detect_block_nemeth_returns_none_for_inline_match():
    brf = f"find {NEMETH_OPEN}{MATH}{NEMETH_TERM} and solve it.\n"
    assert detect_block_nemeth(brf, brf.index(NEMETH_OPEN), {}, "") is None


def test_detect_block_nemeth_wraps_multiline_region_sharing_only_opening_line():
    """A label like "Student Answers" commonly introduces a multi-line
    displayed expression on the same braille line. Block detection would
    otherwise split the region at its interior blank lines before the inline
    pass gets a chance to see it as one contiguous match, so it has to be
    wrapped here even though the opening line is not clean -- with the label
    left in place, on its own line, ahead of the div."""
    brf = f"  student answers {NEMETH_OPEN}\n    {MATH}\n    {MATH}{NEMETH_TERM}\n"
    cursor = brf.index(NEMETH_OPEN)
    result = detect_block_nemeth(brf, cursor, {}, brf[:cursor])
    assert result is not None
    assert result.cursor == len(brf)
    assert result.text.startswith("  student answers \n" + '<div class="nemeth">')
    assert result.text.endswith("</div>\n")


def test_detect_block_nemeth_returns_none_when_opening_line_and_closing_line_both_dirty():
    """A short, single-line region with prose on both sides scores as inline
    even though both ends are dirty -- there is no block signal here (no
    internal blank line, no multi-line span) to override that."""
    brf = f"solve {NEMETH_OPEN}{MATH}{NEMETH_TERM} and simplify.\n"
    assert detect_block_nemeth(brf, brf.index(NEMETH_OPEN), {}, "") is None


def test_detect_block_nemeth_wraps_dirty_both_ends_when_multiline_with_blank_inside():
    """Prose sharing the opening line, prose sharing the closing line, and a
    blank line in between: the blank line makes this decisively a block, and a
    found terminator is trusted to close it even though neither end is clean --
    the trailing prose is preserved outside the div rather than dropped."""
    brf = (
        f"solve {NEMETH_OPEN}\n"
        f"  {MATH}\n"
        "<?blank-line?>\n"
        f"  {MATH}{NEMETH_TERM} and simplify.\n"
    )
    result = detect_block_nemeth(brf, brf.index(NEMETH_OPEN), {}, brf[:brf.index(NEMETH_OPEN)])
    assert result is not None
    assert result.cursor == len(brf)
    assert result.text.startswith("solve \n" + '<div class="nemeth">')
    assert result.text.endswith("</div>\n and simplify.\n")


def test_detect_block_nemeth_wraps_despite_nested_opening_indicator():
    """A second, unescaped opening indicator before the terminator does not
    make the match untrustworthy: Nemeth open/close indicators are a single
    on/off toggle, not a stack, so the nearest terminator always validly
    closes whatever is open, regardless of any redundant opens re-emitted in
    between (a common pattern across a run of several exercises)."""
    brf = (
        f"label {NEMETH_OPEN}\n"
        f"  {MATH}\n"
        f"  more label {NEMETH_OPEN}\n"
        f"  {MATH}{NEMETH_TERM}\n"
    )
    result = detect_block_nemeth(brf, brf.index(NEMETH_OPEN), {}, "")
    assert result is not None
    assert result.cursor == len(brf)
    assert result.text.endswith("</div>\n")


def test_detect_block_nemeth_returns_none_without_opening_indicator():
    assert detect_block_nemeth("plain text\n", 0, {}, "") is None


def test_detect_and_pass_nemeth_block_consumes_whole_div():
    brf = f"  {NEMETH_OPEN}{MATH}{NEMETH_TERM}\n"
    wrapped = detect_block_nemeth(brf, brf.index(NEMETH_OPEN), {}, "").text
    div_start = wrapped.index("<div")
    result = detect_and_pass_nemeth_block(wrapped, div_start, {}, wrapped[:div_start])
    assert result is not None
    consumed_end = wrapped.index("</div>") + len("</div>")
    assert result.text == wrapped[:consumed_end]
    assert result.cursor == consumed_end


def test_detect_and_pass_nemeth_block_returns_none_elsewhere():
    assert detect_and_pass_nemeth_block("<p>text</p>", 0, {}, "") is None


def test_tag_inline_nemeth_wraps_inline_occurrence_in_span():
    brf = f"find {NEMETH_OPEN}{MATH}{NEMETH_TERM} and solve it.\n"
    result = tag_inline_nemeth(brf, ParserContext())
    assert f'<span class="nemeth">' in result
    assert result.startswith("find <span")
    assert result.rstrip("\n").endswith("</span> and solve it.")


def test_tag_inline_nemeth_wraps_each_of_two_expressions_on_one_line_separately():
    """A greedy match here would run from the first opening indicator to the
    *last* terminator it can reach, swallowing the plain-language text between
    two separate expressions -- "long and" below -- into a single, wrongly
    merged span."""
    other_math = "⠼⠆⠎"
    brf = f"is {NEMETH_OPEN}{MATH}{NEMETH_TERM} long and {NEMETH_OPEN}{other_math}{NEMETH_TERM} wide.\n"
    result = tag_inline_nemeth(brf, ParserContext())
    assert result.count('<span class="nemeth">') == 2
    assert "</span> long and <span" in result
    assert restore_nemeth_braille(result) == (
        f'is <span class="nemeth">{NEMETH_OPEN}{MATH}{NEMETH_TERM}</span> long and '
        f'<span class="nemeth">{NEMETH_OPEN}{other_math}{NEMETH_TERM}</span> wide.\n'
    )


def test_tag_inline_nemeth_leaves_dot_locator_mentions_untouched():
    brf = (
        f"{DOT_LOCATOR}{NEMETH_OPEN} open nemeth code indicator\n"
        f"{DOT_LOCATOR}{NEMETH_TERM} nemeth code terminator\n"
    )
    result = tag_inline_nemeth(brf, ParserContext())
    assert result == brf


def test_tag_inline_nemeth_does_not_cross_html_tag_boundaries():
    """A dirty match whose terminator ends up in a different block element
    (e.g. because block detection already split the surrounding text) must
    not be wrapped -- that would require an invalid overlapping tag."""
    brf = f"<p>intro {NEMETH_OPEN}{MATH}</p>\n<p>{MATH}{NEMETH_TERM} tail</p>\n"
    result = tag_inline_nemeth(brf, ParserContext())
    assert result == brf


def test_restore_nemeth_braille_round_trips_shadowed_content():
    brf = f"  {NEMETH_OPEN}{MATH}{NEMETH_TERM}\n"
    wrapped = detect_block_nemeth(brf, brf.index(NEMETH_OPEN), {}, "").text
    assert restore_nemeth_braille(wrapped) == f'<div class="nemeth">{NEMETH_OPEN}{MATH}{NEMETH_TERM}</div>\n'


def test_shadow_encoded_content_is_immune_to_braille_pattern_regexes():
    """The whole point of shadow-encoding: a regex that would otherwise match
    braille dot patterns anywhere in the text (like the emphasis detector)
    must not be able to match inside a tagged Nemeth region."""
    brf = f"  {NEMETH_OPEN}{MATH}{NEMETH_TERM}\n"
    wrapped = detect_block_nemeth(brf, brf.index(NEMETH_OPEN), {}, "").text
    corrupted = re.sub("[⠀-⣿]+", "CORRUPTED", wrapped)
    assert "CORRUPTED" not in corrupted
    assert restore_nemeth_braille(corrupted) == restore_nemeth_braille(wrapped)
