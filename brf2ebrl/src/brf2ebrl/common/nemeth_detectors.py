#  Copyright (c) 2024. American Printing House for the Blind.
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""Detectors for Nemeth mathematics code embedded in literary braille.

The Nemeth start/end indicators (dot patterns dots-456,146 and dots-456,156,
Unicode ``⠸⠩`` / ``⠸⠱``) only mark where Nemeth code begins
and ends -- they do not say whether the enclosed math is meant to be read
inline with surrounding prose or displayed as its own block.  That has to be
inferred from layout: whether prose shares the same braille line, whether
blank lines surround the expression, and whether it spans multiple lines.

Because block detection (paragraphs, lists, headings, tables, ...) works by
matching whole braille lines, a region classified as block is always wrapped
in a ``<div>`` *before* block detection runs, even when prose shares its
opening and/or closing line (e.g. a "Student Answers" label right before a
displayed expression, or trailing commentary right after one) -- otherwise
block detection would split a multi-line region at every blank line it
contains, and the inline pass that runs afterwards could never find the
pieces again as one contiguous match to wrap in a ``<span>``. Any such prose
is preserved outside the div, moved onto its own line rather than dropped.
Regions classified as inline are left alone here and picked up afterwards,
once blocks already exist, by that second, inline-only pass -- the same
two-stage approach already used for transcriber's notes.

A region containing a blank line between its open and close indicators is
always classified as block, regardless of what the rest of the scoring says:
an inline, same-line usage can never contain a full blank line, so the signal
is decisive rather than just another point of evidence.

A found terminator is trusted to close its region even when a second,
unescaped opening indicator appears before it: the Nemeth open/close
indicators are a single on/off toggle, not a stack, so the nearest terminator
always validly closes whatever is currently open. In practice, transcriptions
of a run of several exercises commonly re-emit the open indicator before each
one without an intervening close, since Nemeth was never actually switched
back off -- rejecting those would leave large, legitimate stretches of a
document (spatial answer keys, tables of contents that use Nemeth numerals)
unwrapped instead.

Once a Nemeth region is tagged, its braille content is shadow-encoded into a
disjoint Private Use Area range so that later passes which scan for other
braille dot patterns (emphasis indicators, transcriber's note indicators,
...) cannot match inside it.  ``restore_nemeth_braille`` converts the shadow
codepoints back to real braille once those passes have run.
"""
import re

from brf2ebrl import ParserContext
from brf2ebrl.parser import DetectionState, DetectionResult

NEMETH_OPEN = "⠸⠩"  # ⠸⠩ aka _%: opening Nemeth code indicator
NEMETH_TERM = "⠸⠱"  # ⠸⠱ aka _: Nemeth code terminator

# The dot locator (⠨⠿ aka .=) precedes a symbol shown for definition
# or mention -- e.g. a "special symbols used in this volume" glossary entry --
# rather than a live use of that symbol, so a Nemeth indicator directly after
# it is not a real Nemeth region.
_DOT_LOCATOR = "⠨⠿"

_BLANK_CHARS = " \t⠀"
_STANDARD_INDENTS = frozenset({0, 2, 4, 6})

_SKIP_PI_RE = re.compile(
    r"^<\?(?:braille-page|braille-ppn|print-page|running-head)[ ⠀-⣿]*\?>$"
)
_BLANK_LINE_PI = "<?blank-line?>"
_DISALLOWED_TAG_RE = re.compile(r"<(?!\?)")

_SHADOW_OFFSET = 0xE000 - 0x2800
_BRAILLE_TO_SHADOW = str.maketrans({cp: cp + _SHADOW_OFFSET for cp in range(0x2800, 0x2900)})
_SHADOW_TO_BRAILLE = str.maketrans({cp + _SHADOW_OFFSET: cp for cp in range(0x2800, 0x2900)})


def _shadow_encode(text: str) -> str:
    """Move braille cells into a Private Use Area range so later braille-pattern
    detectors cannot match inside protected Nemeth content."""
    return text.translate(_BRAILLE_TO_SHADOW)


def restore_nemeth_braille(text: str, _: ParserContext = ParserContext()) -> str:
    """Restore braille cells that were shadow-encoded to protect Nemeth content."""
    return text.translate(_SHADOW_TO_BRAILLE)


def _line_start(text: str, pos: int) -> int:
    return text.rfind("\n", 0, pos) + 1


def _line_end(text: str, pos: int) -> int:
    idx = text.find("\n", pos)
    return idx if idx >= 0 else len(text)


def _prev_line(text: str, line_start: int) -> str | None:
    """Return the nearest preceding line, skipping page/running-head processing
    instructions so a page break does not hide a blank line before it."""
    pos = line_start
    while pos > 0:
        prev_end = pos - 1
        prev_start = _line_start(text, prev_end)
        prev_line = text[prev_start:prev_end]
        if _SKIP_PI_RE.match(prev_line):
            pos = prev_start
            continue
        return prev_line
    return None


def _next_line(text: str, line_end: int) -> str | None:
    """Return the nearest following line, skipping page/running-head processing
    instructions so a page break does not hide a blank line after it."""
    pos = line_end
    length = len(text)
    while pos < length:
        next_start = pos + 1
        next_end = text.find("\n", next_start)
        if next_end < 0:
            next_end = length
        next_line = text[next_start:next_end]
        if _SKIP_PI_RE.match(next_line):
            pos = next_end
            continue
        return next_line
    return None


class NemethSpan:
    """The result of matching a Nemeth region starting at some cursor."""

    __slots__ = ("end", "is_block", "is_clean", "ends_clean", "spans_multiple_lines", "has_internal_blank_line")

    def __init__(self, end: int, is_block: bool, is_clean: bool, ends_clean: bool, spans_multiple_lines: bool,
                 has_internal_blank_line: bool):
        self.end = end
        self.is_block = is_block
        self.is_clean = is_clean
        self.ends_clean = ends_clean
        self.spans_multiple_lines = spans_multiple_lines
        self.has_internal_blank_line = has_internal_blank_line


def find_nemeth_span(text: str, cursor: int) -> NemethSpan | None:
    """Match a Nemeth region starting at cursor and classify it as block or inline.

    Returns None if there is no Nemeth region starting at cursor (no opening
    indicator, no matching terminator, or the indicator is only being shown
    for definition/mention rather than used live).
    """
    if not text.startswith(NEMETH_OPEN, cursor):
        return None
    if text[cursor - len(_DOT_LOCATOR):cursor] == _DOT_LOCATOR:
        return None
    term_idx = text.find(NEMETH_TERM, cursor + len(NEMETH_OPEN))
    if term_idx < 0:
        return None
    end = term_idx + len(NEMETH_TERM)

    line_start = _line_start(text, cursor)
    close_line_end = _line_end(text, end)
    before = text[line_start:cursor]
    after = text[end:close_line_end]

    prose_before = bool(before.strip(_BLANK_CHARS))
    prose_after = bool(after.strip(_BLANK_CHARS))
    begins_line = not prose_before
    ends_line = not prose_after
    spans_multiple_lines = "\n" in text[cursor:end]
    blank_before = _prev_line(text, line_start) == _BLANK_LINE_PI
    blank_after = _next_line(text, close_line_end) == _BLANK_LINE_PI
    indent = len(before) - len(before.lstrip(_BLANK_CHARS)) if begins_line else 0
    unusual_indent = begins_line and indent > 0 and indent not in _STANDARD_INDENTS

    score = 0
    score += 3 if prose_before else 0
    score += 3 if prose_after else 0
    score -= 2 if begins_line else 0
    score -= 2 if ends_line else 0
    score -= 3 if blank_before else 0
    score -= 3 if blank_after else 0
    score -= 3 if spans_multiple_lines else 0
    score -= 1 if unusual_indent else 0

    # A blank line strictly between the open and close indicators means the
    # region spans a paragraph break -- something an inline, same-line usage can
    # never do -- so it overrides the score outright rather than just nudging it.
    has_internal_blank_line = _BLANK_LINE_PI in text[cursor:end]

    return NemethSpan(
        end=end,
        is_block=has_internal_blank_line or score <= 0,
        is_clean=begins_line and ends_line,
        ends_clean=ends_line,
        spans_multiple_lines=spans_multiple_lines,
        has_internal_blank_line=has_internal_blank_line,
    )


def detect_block_nemeth(text: str, cursor: int, state: DetectionState, output_text: str) -> DetectionResult | None:
    """Detects a Nemeth region classified as block (see ``find_nemeth_span``) and
    wraps it in a div, before block detection runs, so multi-line expressions
    are not mistaken for separate paragraphs/lists/headings.

    ``span.is_block`` is trusted outright, however dirty the opening/closing
    lines are: the Nemeth open/closing indicators are a single on/off toggle,
    not a stack, so the nearest terminator found by ``find_nemeth_span``
    always validly closes the region regardless of how many redundant open
    indicators appear in between it (transcriptions of a run of exercises
    commonly re-emit the open indicator before each one without an
    intervening close, since Nemeth was never actually switched off). Any
    prose sharing the opening or closing line is preserved outside the div
    rather than dropped.
    """
    span = find_nemeth_span(text, cursor)
    if span is None or not span.is_block:
        return None
    content = text[cursor:span.end]
    if _DISALLOWED_TAG_RE.search(content):
        return None
    line_start = _line_start(text, cursor)
    before = text[line_start:cursor]
    if before.strip(_BLANK_CHARS):
        # Real prose (e.g. a heading or label) shares the opening line -- leave
        # it as output_text already has it, just make sure the div starts on
        # its own line so it doesn't get glued onto the end of that prose.
        prefix = "" if output_text.endswith("\n") else "\n"
    else:
        # Leading indent before a clean block was already copied verbatim into
        # output_text by earlier, unmatched single-character advances in this
        # pass -- trim it back out so it doesn't survive as a whitespace-only
        # chunk that a later block detector (e.g. detect_pre) mistakes for its
        # own standalone content.
        prefix = ""
        if before and output_text.endswith(before):
            output_text = output_text[:-len(before)]
    close_line_end = _line_end(text, span.end)
    trailing = text[span.end:close_line_end]
    new_cursor = min(close_line_end + 1, len(text))
    line_ending = text[close_line_end:new_cursor]
    if trailing.strip(_BLANK_CHARS):
        # Real prose follows the terminator on its line -- keep it, moved onto
        # its own line after the div rather than glued to its closing tag, so
        # a later block detector still sees it as ordinary standalone text.
        suffix = f"\n{trailing}"
    else:
        # Blank padding out to the cell width -- drop it, keeping only the line
        # terminator itself, so it doesn't survive as a whitespace-only chunk
        # that later block detectors (e.g. detect_pre) mistake for content.
        suffix = ""
    return DetectionResult(
        new_cursor, state, 0.97,
        f'{output_text}{prefix}<div class="nemeth">{_shadow_encode(content)}</div>{suffix}{line_ending}'
    )


_NEMETH_DIV_OPEN = '<div class="nemeth">'
_NEMETH_DIV_CLOSE = "</div>"


def detect_and_pass_nemeth_block(text: str, cursor: int, state: DetectionState, output_text: str) -> DetectionResult | None:
    """Passes an already-tagged Nemeth div through block detection untouched."""
    if not text.startswith(_NEMETH_DIV_OPEN, cursor):
        return None
    close_idx = text.find(_NEMETH_DIV_CLOSE, cursor + len(_NEMETH_DIV_OPEN))
    if close_idx < 0:
        return None
    end = close_idx + len(_NEMETH_DIV_CLOSE)
    return DetectionResult(end, state, 1.0, output_text + text[cursor:end])


# Lazy quantifier: when two short Nemeth expressions share a line (e.g. "... is
# _%12x14 in._: long, 18 in. wide, and _%12.6x14.5 in._: tall."), a greedy match
# would swallow the plain-language text between them by running from the first
# opening indicator to the *last* terminator it can reach instead of the nearest.
_INLINE_NEMETH_RE = re.compile(f"{NEMETH_OPEN}[⠀-⣿\\s]+?{NEMETH_TERM}")


def tag_inline_nemeth(text: str, parser_context: ParserContext = ParserContext(), *, start: int = 0) -> str:
    """Wraps remaining (inline) Nemeth regions in a span, once block detection
    has already run. Regions already tagged as a div by detect_block_nemeth are
    shadow-encoded and so will not be matched here."""
    new_text = ""
    while m := _INLINE_NEMETH_RE.search(text, pos=start):
        prev_cursor = start
        start = m.start()
        new_text += text[prev_cursor:start]
        if start >= len(_DOT_LOCATOR) and text[start - len(_DOT_LOCATOR):start] == _DOT_LOCATOR:
            new_text += m.group()
        else:
            new_text += f'<span class="nemeth">{_shadow_encode(m.group())}</span>'
        start = m.end()
        parser_context.check_cancelled()
    return new_text + text[start:]
