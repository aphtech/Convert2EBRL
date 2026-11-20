#  Copyright (c) 2026. American Printing House for the Blind.
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.
"""Block detectors specific to the NFB Braille Monitor.

The newsletter uses a compact layout with almost no blank lines, so consecutive centered
lines (title page lines, an article title and its byline) and consecutive photo captions
cannot be told apart by blank lines as the shared detectors expect. These detectors are
NFB only; the shared detectors are not changed.

Detection state keys used here:
    nfb_page       braille pages seen so far in this volume
    nfb_title_page on the title page (the first page, which has no braille page number)
    open_caption   a bracketed photo caption has not been closed yet
    article_start  the next centered heading starts an article (after a separator or the TOC)
    in_dialogue    inside a transcript, so 5-3 paragraphs are dialogue continuations

Lines are joined with join_lines, so a line ending in a hyphen, dash or continuation indicator
joins the next with no space, and the other line breaks become spaces.
"""
import difflib
import re
from collections.abc import Callable

from brf2ebrl.common import PageLayout
from brf2ebrl.common.block_detectors import _notify_low_confidence_match
from brf2ebrl.parser import Detector, DetectionResult, DetectionState, ParserContext
from brf2ebrl.utils.back_translation import back_translate_contracted
from brf2ebrl_nfb.lines import ends_with_continuation, join_lines, wraps
from brf2ebrl_nfb.print_source import PrintIssue, match_heading, normalise
from brf2ebrl_nfb.toc import detect_toc

_DEFAULT_CELLS_PER_LINE = 40

_SEPARATOR_LINE_RE = re.compile("^\u2800+(\u2810\u2812{6,})\u2800*$", re.MULTILINE)
_SEPARATOR_PI_RE = re.compile("<\\?nfb-separator ([\u2800-\u28ff]+)\\?>\n?")
_BRAILLE_PAGE_PI_RE = re.compile("<\\?braille-page ([\u2800-\u28ff]*)\\?>\n?")
_CENTERED_LINE_RE = re.compile("(\u2800{3,})([\u2801-\u28ff][\u2800-\u28ff]*)\n")
# "by" as a whole word.
_BY_WORD = "\u2803\u283d"
# ",,,SPECIAL SYMBOLS" heading of the special symbols page.
_SPECIAL_SYMBOLS = "\u2820\u2820\u2820\u280e\u280f\u2811\u2809\u280a\u2801\u2807"
# ".<" opens the bracketed photo captions.
_CAPTION_START = "\u2828\u2823"
_CLOSING_BRACKET = "\u2828\u281c"
# A capitalised word, perhaps after grade 1 (;), typeform or opening punctuation indicators.
_NAME_RE = re.compile("[\u2830\u2818\u2828\u2838\u2808\u2810\u2826]*\u2820")
# Photo captions start ",,PHOTO", usually inside the brackets.
_PHOTO_CAPTION_RE = re.compile("(?:\u2828\u2823)?\u2820\u2820\u280f\u2813\u2815\u281e\u2815")
# A TOC entry ends in a braille page number: after guide dots, or at the end of a one line entry.
# (A year at the end of a later line, such as "#BJBF", is not enough.)
_PAGE_NUMBER_AT_END_RE = re.compile(
    "\u2800\u283c[\u2801\u2803\u2809\u2819\u2811\u280b\u281b\u2813\u280a\u281a]+$", re.MULTILINE)
_GUIDE_DOTS_PAGE_NUMBER_RE = re.compile(
    "\u2810{2,}\u2800\u283c[\u2801\u2803\u2809\u2819\u2811\u280b\u281b\u2813\u280a\u281a]+$", re.MULTILINE)
# A speaker label: one to four words, the first capitalised, the last ending in a colon, then a space.
# For example ",LIA ,/"O3 " or ",J4,J4 ,M$DAU<3 ".
_SPEAKER_RE = re.compile("\u2820[^\u2800\n]*(?:\u2800[^\u2800\n]+){0,3}(?<=\u2812)\u2800")

# End of a sentence: period, question or exclamation mark, possibly followed by closing quotes or brackets.
_SENTENCE_END_RE = re.compile("[\u2832\u2826\u2816][\u2834\u2820\u281c\u2810]*$")
# Any non blank line: (indent, text).
_ANY_LINE_RE = re.compile("(\u2800*)([\u2801-\u28ff][\u2800-\u28ff]*)\n")
# The title page goes on over the next page when that page starts straight after a title page line,
# with no blank line (otherwise the next page starts the body, eg. with ",WELCOME TO ! ,MOVE;T").
_AFTER_TITLE_PAGE_RE = re.compile('<p class="titlepage">[^<]*</p>\n+<\\?braille-page \\?>\n?$')
# A numbered braille page break just before a line.
_PAGE_PI_BEFORE_RE = re.compile("<\\?braille-page ([\u2800-\u28ff]+)\\?>\n$")
# Any braille page break just before a line.
_AT_PAGE_TOP_RE = re.compile("<\\?braille-page [\u2800-\u28ff]*\\?>\n$")
# Trailing processing instructions and white space, skipped to find the previous block.
_TRAILING_PI_RE = re.compile("(?:<\\?braille-page [\u2800-\u28ff]*\\?>|\\s)+$")
# Blank lines straight after a numbered braille page break: the first one only held the page number.
_PAGE_TOP_BLANK_RE = re.compile("(<\\?braille-page [\u2800-\u28ff]+\\?>)(?:\\s*<\\?blank-line\\?>)+$")
# Blocks after which a blocked line starts a heading, as after a blank line.
_HEADING_CONTEXT_RE = re.compile('(?:<\\?blank-line\\?>|</h[1-6]>|<p class="(?:byline|separator)">[^<]*</p>|</nav>)$')
# "Dear ...:" opening a letter.
_DEAR = "\u2820\u2819\u2811\u281c\u2800"
_COLON = "\u2812"
# A list item marker: a bullet (_4) or a number and period (#A4).
_LIST_MARKER_RE = re.compile("\u2838\u2832|\u283c[\u2801\u2803\u2809\u2819\u2811\u280b\u281b\u2813\u280a\u281a]+\u2832")
# A numbered list item: a number and period (#A4).
_NUMBER_MARKER_RE = re.compile("\u283c[\u2801\u2803\u2809\u2819\u2811\u280b\u281b\u2813\u280a\u281a]+\u2832")
# Indent pairs (first line, next line) where an off centre line is a paragraph's first line.
_PARAGRAPH_STARTS = {(4, 2), (2, 0), (6, 4)}
# A CC line of a letter looks like a speaker label.
_CC = "\u2820\u2820\u2809\u2809\u2812"
# So does a letter's "Re:" line, which may be in capitals (,RE3 / ,,,RE3).
_RE_LINE_RE = re.compile("\u2820+\u2817\u2811\u2812\u2800")
# The "Special Symbols Used in This Volume" heading, which the list of symbols follows.
_AFTER_SPECIAL_SYMBOLS_RE = re.compile(
    f"<h2[^>]*>{_SPECIAL_SYMBOLS}[^<]*</h2>\\s*(?:<\\?blank-line\\?>\\s*)*$")
# A letter's address follows its date, a one line 1-1 paragraph.
_AFTER_DATE_LINE_RE = re.compile('<p class="left-justified">[^<\n]*</p>\\s*(?:<\\?blank-line\\?>\\s*)+$')


def mark_article_separators(text: str, _: ParserContext) -> str:
    """Replace each centered article separator line with a processing instruction.

    Done before block detection so no other detector sees the line."""
    return _SEPARATOR_LINE_RE.sub(lambda m: f"<?nfb-separator {m.group(1)}?>", text)


def detect_separator(text: str, cursor: int, state: DetectionState, output_text: str) -> DetectionResult | None:
    if m := _SEPARATOR_PI_RE.match(text, cursor):
        return DetectionResult(m.end(), dict(state, article_start=True, in_dialogue=False, open_caption=False), 0.95,
                               f'{output_text}<p class="separator">{m.group(1)}</p>\n')
    return None


def track_braille_pages(text: str, cursor: int, state: DetectionState, output_text: str) -> DetectionResult | None:
    """Track braille pages so the title page can be recognised. The PI is passed through.

    The title page is the first page of a volume and has no braille page number. Some volumes
    start straight into an article on a numbered page, and have no title page."""
    if m := _BRAILLE_PAGE_PI_RE.match(text, cursor):
        page = state.get("nfb_page", 0) + 1
        is_title_page = page == 1 and not m.group(1)
        return DetectionResult(m.end(), dict(state, nfb_page=page, nfb_title_page=is_title_page), 0.91,
                               output_text + m.group())
    return None


def _is_name(word: str) -> bool:
    """A capitalised word, allowing leading grade 1, typeform or punctuation indicators."""
    return bool(_NAME_RE.match(word))


def _is_byline_start(line: str, next_line: str = "") -> bool:
    """A centered line starting a byline: "by Chris Danielsen", "Presented by Pam Allen", or
    "An Address Delivered by" with the names on the next line. "by" must be within the first
    four words, followed by a capitalised name with at least half the remaining words names,
    so a title line such as "Network by the Blind" is not a byline."""
    words = [w for w in line.split("\u2800") if w]
    for i, word in enumerate(words[:4]):
        if word == _BY_WORD:
            names = words[i + 1:] or [w for w in next_line.split("\u2800") if w]
            return bool(names) and _is_name(names[0]) and 2 * sum(map(_is_name, names)) >= len(names)
    return False


def _is_centered(indent: int, line: str, cells_per_line: int) -> bool:
    """The line is centered, give or take a cell."""
    return abs(indent - (cells_per_line - len(line)) / 2) <= 1


def _print_text(braille: str) -> str:
    return back_translate_contracted(braille) or ""


def _unique_id(base: str, used: frozenset[str]) -> str:
    heading_id, n = base, 2
    while heading_id in used:
        heading_id, n = f"{base}-{n}", n + 1
    return heading_id


def _join_continued(lines: list[str]) -> list[str]:
    """Join a line ending in the continuation indicator, such as a long web address, to the next."""
    joined: list[str] = []
    for line in lines:
        if joined and ends_with_continuation(joined[-1]):
            joined[-1] = join_lines([joined[-1], line])
        else:
            joined.append(line)
    return joined


def create_centered_detector(cells_per_line: int, parser_context: ParserContext = ParserContext(),
                             print_issue: PrintIssue | None = None) -> Detector:
    """Centered lines: title page lines, article title plus byline, or a section heading.

    Based on the shared centered detector, with the same one cell tolerance, but it keeps the
    lines separate, does not require a blank line after the heading and never makes guide words.
    With the print HTML, article titles get the print title as a readable id and section
    headings get the print level."""

    def _split_print_heading(lines: list[str]) -> tuple[list[str], list[str]]:
        """With the print, the first lines that make up a print heading, and the centered lines after it.

        Without the print, or when the whole run or no part of it is a print heading, all lines are the heading."""
        if not print_issue or len(lines) < 2:
            return lines, []
        levels = (2, 3, 4)
        # The number of lines whose text is most like a print heading, preferring all of them.
        best_k, best_ratio = len(lines), 0.0
        for k in range(len(lines), 0, -1):
            text = normalise(_print_text(join_lines(lines[:k], "\u2800")))
            if match := match_heading(print_issue, text, levels):
                ratio = difflib.SequenceMatcher(None, text, match.key).ratio()
                if ratio > best_ratio:
                    best_k, best_ratio = k, ratio
        return lines[:best_k], lines[best_k:]

    def detect_centered(text: str, cursor: int, state: DetectionState, output_text: str) -> DetectionResult | None:
        lines: list[str] = []
        new_cursor = cursor
        confidence = 0.92
        pending_notifications: list[tuple[int, str, int]] = []
        while m := _CENTERED_LINE_RE.match(text, new_cursor):
            brl = m.group(2).rstrip("\u2800")
            if brl.startswith(_CAPTION_START) or _PHOTO_CAPTION_RE.match(brl):
                break
            indent, indent_mod = divmod(cells_per_line - len(brl), 2)
            indents = [indent] if indent_mod == 0 else [indent, indent + indent_mod]
            actual_indent = len(m.group(1))
            if actual_indent in indents:
                # A 5-3 or 7-5 paragraph whose short first line, such as a bold dateline, happens to be
                # centered. Two run-over lines are required, as a title can be followed by a 3-1 paragraph.
                if _starts_indented_paragraph(text, m.end(), actual_indent, brl, cells_per_line, run_overs=2):
                    break
            elif actual_indent - 1 in indents or actual_indent + 1 in indents:
                # A 5-3 or 7-5 paragraph's first line can be a cell off centre; it wraps onto the next line.
                next_line = _ANY_LINE_RE.match(text, m.end())
                if next_line and (actual_indent, len(next_line.group(1))) in _PARAGRAPH_STARTS \
                        and wraps(actual_indent + len(brl), next_line.group(2), cells_per_line):
                    break
                pending_notifications.append((1 if actual_indent - 1 in indents else -1, brl, new_cursor))
                confidence = min(confidence, 0.6)
            else:
                break
            lines.append(brl)
            new_cursor = m.end()
        if not lines:
            return None

        def notify_pending() -> None:
            for direction, line_brl, pos in pending_notifications:
                _notify_low_confidence_match(parser_context, "Center", "centered position", direction, line_brl,
                                             text, pos)

        new_state = dict(state, in_dialogue=False, open_caption=False)
        # The title page can go on at the top of the second page, which has no page number either.
        if state.get("nfb_title_page", False) or _AFTER_TITLE_PAGE_RE.search(output_text[-1000:]):
            html = "".join(f'<p class="titlepage">{line}</p>\n' for line in _join_continued(lines))
        else:
            by_index = next((i for i, line in enumerate(lines)
                             if _is_byline_start(line, lines[i + 1] if i + 1 < len(lines) else "")), len(lines))
            heading_lines, other_lines = _split_print_heading(lines[:by_index])
            heading = join_lines(heading_lines, "\u2800")
            byline = join_lines(lines[by_index:], "\u2800")
            html = ""
            if heading:
                if heading.startswith(_SPECIAL_SYMBOLS):
                    html += f"<h2>{heading}</h2>\n"
                elif state.get("article_start", True) or byline:
                    id_attr = ""
                    if print_issue and (match := match_heading(print_issue, _print_text(heading), (2,))):
                        used_ids = state.get("nfb_ids", frozenset())
                        heading_id = _unique_id(match.slug, used_ids)
                        new_state["nfb_ids"] = used_ids | {heading_id}
                        id_attr = f' id="{heading_id}"'
                    html += f'<h1 class="article-title"{id_attr}>{heading}</h1>\n'
                    new_state["article_start"] = False
                    if byline and len(pending_notifications) <= 1:
                        # A title with its byline is an article heading even when one line is a
                        # cell off centre, so prefer it to the cell 5 heading detector.
                        confidence = max(confidence, 0.93)
                elif other_lines or _starts_indented_paragraph(text, new_cursor):
                    # A centered title inside an article followed by a source and date, or by a 5-3
                    # paragraph, is the title of quoted material such as a news article or press release.
                    html += f'<h1 class="article-title">{heading}</h1>\n'
                    new_state["article_start"] = False
                else:
                    # Braille cannot show the print level of a section heading; the print can.
                    tag = "h2"
                    if print_issue and (match := match_heading(print_issue, _print_text(heading), (3, 4))):
                        tag = "h3" if match.level == 4 else "h2"
                    html += f"<{tag}>{heading}</{tag}>\n"
            # Centered lines under a heading that are not part of the print heading, such as a source and date.
            html += "".join(f'<p class="centered">{line}</p>\n' for line in other_lines)
            if byline:
                html += f'<p class="byline">{byline}</p>\n'
        return DetectionResult(new_cursor, new_state, confidence, output_text + html,
                               on_selected=notify_pending if pending_notifications else None)

    return detect_centered


def _starts_indented_paragraph(text: str, pos: int, indent: int = 4, first_line: str = "",
                               cells_per_line: int = _DEFAULT_CELLS_PER_LINE, run_overs: int = 1) -> bool:
    """A 5-3 (or 7-5) paragraph starts at pos, or, given its first_line, goes on at pos.

    Without first_line the paragraph's first line at indent must be at pos, followed by run_overs
    lines two cells to the left. With it, the run_overs lines must be at pos and first_line must
    have been wrapped onto them."""
    if not first_line:
        if not (m := _ANY_LINE_RE.match(text, pos)) or len(m.group(1)) != indent:
            return False
        first_line, pos = m.group(2).rstrip("\u2800"), m.end()
    next_line = None
    for _ in range(run_overs):
        m = _ANY_LINE_RE.match(text, pos)
        if not m or len(m.group(1)) != indent - 2:
            return False
        next_line = next_line or m
        pos = m.end()
    return (indent, indent - 2) in _PARAGRAPH_STARTS and wraps(indent + len(first_line), next_line.group(2),
                                                                cells_per_line)


def _runs_over_to(text: str, pos: int, width: int, indent: int, cells_per_line: int) -> bool:
    """The line at pos is at indent and carries on a line of width cells before it, ie. its first
    word would not have fitted on that line."""
    m = _ANY_LINE_RE.match(text, pos)
    return bool(m) and len(m.group(1)) == indent and wraps(width, m.group(2), cells_per_line)


def create_shape_paragraph_detector(
        first_line_indent: int,
        run_over: int,
        matcher: Callable[[str, DetectionState], tuple[str | None, DetectionState]],
        confidence: float,
        stop_before: Callable[[str, str], bool] = lambda previous_line, line: False,
        min_lines: int = 1,
        first_line_must_wrap: bool = False,
        cells_per_line: int = _DEFAULT_CELLS_PER_LINE,
) -> Detector:
    """A paragraph is a first line at first_line_indent followed by run-over lines at run_over.

    The newsletter has no blank lines between blocks, so the indents alone mark where a block
    ends. Unlike the shared paragraph finder there is no line wrapping check, which wrongly
    rejects paragraphs that start on the line holding the top right page number. Braille page
    processing instructions may fall inside a paragraph, as in the shared finder.

    min_lines rejects shorter blocks. first_line_must_wrap rejects a block whose first line is not
    full, ie. the second line's first word would have fitted on it, so it is a line on its own."""
    first_re = re.compile(f"\u2800{{{first_line_indent}}}([\u2801-\u28ff][\u2800-\u28ff]*)\n")
    run_over_re = re.compile(f"\u2800{{{run_over}}}([\u2801-\u28ff][\u2800-\u28ff]*)\n")

    def detect_shape_paragraph(text: str, cursor: int, state: DetectionState,
                               output_text: str) -> DetectionResult | None:
        if cursor and text[cursor - 1] != "\n":
            return None
        m = first_re.match(text, cursor)
        if not m:
            return None
        lines = [m.group(1).rstrip("\u2800")]
        new_cursor = pos = m.end()
        pending_pis: list[str] = []
        while True:
            if pi := _BRAILLE_PAGE_PI_RE.match(text, pos):
                pending_pis.append(pi.group().rstrip("\n"))
                pos = pi.end()
                continue
            line = run_over_re.match(text, pos)
            if not line or stop_before(lines[-1], line.group(1)):
                break
            lines.extend(pending_pis)
            pending_pis = []
            lines.append(line.group(1).rstrip("\u2800"))
            new_cursor = pos = line.end()
        text_lines = [line for line in lines if not line.startswith("<?")]
        if len(text_lines) < min_lines:
            return None
        if first_line_must_wrap:
            first_cells = _line_cells(text, cursor, cells_per_line)
            if len(text_lines) < 2 or not wraps(first_line_indent + len(text_lines[0]), text_lines[1], first_cells):
                return None
            # Centered lines, such as a title, can fall in the same cells.
            indents = [first_line_indent] + [run_over] * (len(text_lines) - 1)
            if all(_is_centered(indent, line, cells_per_line) for indent, line in zip(indents, text_lines)):
                return None
            # A heading followed by a 3-1 paragraph has the same first two lines; there the second
            # line runs over to the margin.
            if len(text_lines) == 2 and run_over >= 2 \
                    and _runs_over_to(text, new_cursor, run_over + len(text_lines[1]), run_over - 2, cells_per_line):
                return None
        html, new_state = matcher(join_lines(lines), state)
        if html is None:
            return None
        return DetectionResult(new_cursor, new_state, confidence, f"{output_text}{html}\n")

    return detect_shape_paragraph


def _after_closing_bracket(previous_line: str, line: str) -> bool:
    """A bracketed caption ends with ".>"; the next line starts something else. A line starting
    "Photo caption:" starts the next caption, even when the one before has no brackets."""
    return previous_line.endswith(_CLOSING_BRACKET) or bool(_PHOTO_CAPTION_RE.match(line))


def _caption_matcher(brl: str, state: DetectionState) -> tuple[str | None, DetectionState]:
    """Photo captions, and other bracketed 7-5 text such as "[Video begins]" as stage directions.

    A caption can run to a second 7-5 paragraph (eg. "Left to right: ..."); while a caption's
    opening bracket is not closed, the next 7-5 paragraph is part of the caption."""
    if _PHOTO_CAPTION_RE.match(brl) or state.get("open_caption", False):
        is_open = (brl.startswith(_CAPTION_START) or state.get("open_caption", False)) \
            and not brl.endswith(_CLOSING_BRACKET)
        return f'<p class="caption">{brl}</p>', dict(state, open_caption=is_open)
    if brl.startswith(_CAPTION_START):
        return f'<p class="direction">{brl}</p>', state
    return None, state


def _is_speaker_line(line: str) -> bool:
    return bool(_SPEAKER_RE.match(line)) and not line.startswith(_CC) and not _RE_LINE_RE.match(line)


def _looks_like_toc_entry(brl: str) -> bool:
    return bool(_GUIDE_DOTS_PAGE_NUMBER_RE.search(brl) or _PAGE_NUMBER_AT_END_RE.search(brl.split("\n", 1)[0]))


def _starts_transcript(previous_line: str, line: str) -> bool:
    """A margin line after a finished sentence that opens with a speaker label starts a transcript.

    Inside a paragraph every word of the label must be capitalised, so a sentence such as
    "Immediately the car speaks: ..." carries on the paragraph."""
    if not (_SENTENCE_END_RE.search(previous_line) and _is_speaker_line(line)):
        return False
    label = _SPEAKER_RE.match(line).group()
    return all(_is_name(word) for word in label.split("\u2800") if word)


def _speaker_matcher(brl: str, state: DetectionState) -> tuple[str | None, DetectionState]:
    # TOC entries share the 1-3 layout and can end a title with a colon; they end in a page number.
    if _is_speaker_line(brl) and not _looks_like_toc_entry(brl):
        return f'<p class="dialogue">{brl}</p>', dict(state, in_dialogue=True)
    return None, state


def _dialogue_continuation_matcher(brl: str, state: DetectionState) -> tuple[str | None, DetectionState]:
    if state.get("in_dialogue", False):
        return f'<p class="dialogue-cont">{brl}</p>', state
    return None, state


def _paragraph_matcher(brl: str, state: DetectionState) -> tuple[str | None, DetectionState]:
    return f"<p>{brl}</p>", dict(state, open_caption=False)


def _quote_matcher(brl: str, state: DetectionState) -> tuple[str | None, DetectionState]:
    """A 5-3 paragraph outside a transcript, such as a quoted news item."""
    if state.get("in_dialogue", False):
        return None, state
    return f'<p class="quote">{brl}</p>', dict(state, open_caption=False)


def _indented_quote_matcher(brl: str, state: DetectionState) -> tuple[str | None, DetectionState]:
    """A 7-5 paragraph that is not a caption, such as text read out in a transcript."""
    return f'<p class="quote-indent">{brl}</p>', dict(state, open_caption=False)


# The most lines a cell 5 or cell 7 heading runs to.
_MAX_HEADING_LINES = 3
# Slack for deciding whether consecutive lines of a block were wrapped or broken on purpose.
_WRAP_SLACK = 3


def _follows_break(output_text: str) -> bool:
    """The block before ended with a blank line, or was a heading, byline, separator or the TOC.

    A blank first line of a numbered page is not counted: it only holds the page number, and a
    heading at the top of a page has no blank line before it. On a page without a number, a blank
    first line is a real blank line."""
    tail = _TRAILING_PI_RE.sub("", output_text[-2000:])
    tail = _TRAILING_PI_RE.sub("", _PAGE_TOP_BLANK_RE.sub("", tail))
    return bool(_HEADING_CONTEXT_RE.search(tail))


def _line_cells(text: str, cursor: int, cells_per_line: int) -> int:
    """The cells the line at cursor could fill: fewer on the first line of a numbered page, which
    also holds the page number and the three blank cells before it."""
    if m := _PAGE_PI_BEFORE_RE.search(text, max(0, cursor - 40), cursor):
        return cells_per_line - len(m.group(1)) - 3
    return cells_per_line


def _pi_line(pi: str) -> bool:
    return pi.startswith("<?")


def create_blocked_detector(indent: int, cells_per_line: int = _DEFAULT_CELLS_PER_LINE) -> Detector:
    """Lines blocked at cell 5 (indent 4) or cell 7 (indent 6).

    After a blank line (or a heading) they are one heading, h2 at cell 5 and h3 at cell 7, joined
    however many lines it takes; "Dear ...:" at cell 5 is a letter's salutation. A single line
    that wraps onto a run-over two cells to the left is the first line of a paragraph instead.

    Elsewhere, at cell 5: lines that wrap from one to the next are a blocked quotation, and short
    lines, such as a letter's closing, are separate paragraphs."""
    line_re = re.compile(f"\u2800{{{indent}}}([\u2801-\u28ff][\u2800-\u28ff]*)\n")
    tag = "h2" if indent == 4 else "h3"

    def detect_blocked(text: str, cursor: int, state: DetectionState, output_text: str) -> DetectionResult | None:
        # A page break before the first line is left to track_braille_pages, so that at the top of a
        # page the paragraph detectors, which start at a line, are tried on the same footing.
        if (cursor and text[cursor - 1] != "\n") or _BRAILLE_PAGE_PI_RE.match(text, cursor):
            return None
        lines: list[str] = []
        pending_pis: list[str] = []
        pos = end = cursor
        while True:
            if pi := _BRAILLE_PAGE_PI_RE.match(text, pos):
                pending_pis.append(pi.group().rstrip("\n"))
                pos = pi.end()
                continue
            m = line_re.match(text, pos)
            if not m:
                break
            lines.extend(pending_pis)
            pending_pis = []
            lines.append(m.group(1).rstrip("\u2800"))
            end = pos = m.end()
        text_lines = [line for line in lines if not _pi_line(line)]
        if not text_lines or text_lines[0].startswith(_CAPTION_START) or _PHOTO_CAPTION_RE.match(text_lines[0]):
            return None
        next_line = _ANY_LINE_RE.match(text, end)
        starts_paragraph = (len(text_lines) == 1 and next_line is not None
                            and len(next_line.group(1)) == indent - 2
                            and wraps(indent + len(text_lines[0]), next_line.group(2),
                                      _line_cells(text, cursor, cells_per_line))
                            # Unless the next line runs over two cells further left still: then this
                            # line is a heading and the next starts a paragraph, eg. a 3-1 one.
                            and not _runs_over_to(text, next_line.end(), len(next_line.group().rstrip("\n\u2800")),
                                                  indent - 4, cells_per_line))
        pairs = list(zip(text_lines, text_lines[1:]))
        # Most lines wrapped: a blocked quotation; else short lines such as a letter's closing.
        wrapped = sum(wraps(indent + len(a), b, cells_per_line) for a, b in pairs)
        is_quote = 2 * wrapped > len(pairs)
        # A heading is a few lines at most; more lines that wrap and end a sentence are a blocked
        # quotation, such as the text of a plaque, even after a blank line. (A long resolution title
        # does not end in a period.)
        is_long_quote = is_quote and len(text_lines) > _MAX_HEADING_LINES \
            and bool(_SENTENCE_END_RE.search(text_lines[-1]))
        if _follows_break(output_text) and not is_long_quote:
            if starts_paragraph:
                return None
            # A long article title after a separator is centered, which can put it in cell 5 or 7.
            if state.get("article_start", False) and _is_centered(indent, text_lines[0], cells_per_line):
                return None
            # So can the title of quoted material: then the lines after it are centered too.
            if all(_is_centered(indent, line, cells_per_line) for line in text_lines) and next_line \
                    and len(next_line.group(1)) > indent \
                    and _is_centered(len(next_line.group(1)), next_line.group(2).rstrip("\u2800"), cells_per_line):
                return None
            brl = join_lines(lines, "\u2800")
            new_state = dict(state, in_dialogue=False, open_caption=False)
            if indent == 4 and brl.startswith(_DEAR) and brl.endswith(_COLON):
                return DetectionResult(end, new_state, 0.96, f'{output_text}<p class="salutation">{brl}</p>\n')
            return DetectionResult(end, new_state, 0.96, f"{output_text}<{tag}>{brl}</{tag}>\n")
        if indent != 4:
            # Short lines in cell 7 inside the text, such as the closing of a quoted 5-3 letter. A
            # heading at the top of a page has no blank line before it, so it is left to the shared
            # cell heading detector.
            if is_quote or _AT_PAGE_TOP_RE.search(text, max(0, cursor - 40), cursor):
                return None
            html = "".join(f"{line}\n" if _pi_line(line) else f'<p class="closing">{line}</p>\n' for line in lines)
            return DetectionResult(end, state, 0.92, output_text + html)
        if is_quote:
            return DetectionResult(end, state, 0.96, f'{output_text}<p class="quote-block">{join_lines(lines)}</p>\n')
        html = "".join(f"{line}\n" if _pi_line(line) else f'<p class="closing">{line}</p>\n' for line in lines)
        return DetectionResult(end, state, 0.92, output_text + html)

    return detect_blocked


class _ListItem:
    def __init__(self, line: str):
        self.lines = [line]
        self.notes: list[list[str]] = []
        self.sub_items: list[_ListItem] = []

    def html(self) -> str:
        html = f"<li>{join_lines(self.lines)}"
        html += "".join(f'\n<p class="note">{join_lines(note)}</p>' for note in self.notes)
        if self.sub_items:
            html += "\n<ul>\n" + "\n".join(item.html() for item in self.sub_items) + "\n</ul>\n"
        return html + "</li>"


def create_margin_block_detector(cells_per_line: int = _DEFAULT_CELLS_PER_LINE) -> Detector:
    """Blocks starting at the margin, up to a blank line.

    - 1-3 lists: items at the margin, run-overs in cell 3.
    - 1-5 lists: items at the margin, run-overs in cell 5, sub-items in 3-5 and notes in 7-5.
    - Lines all at the margin are one 1-1 paragraph (p.left-justified), such as an editor's note,
      a letter's date or its address. Lines that wrap are joined; a line that would have had room
      for the next line's first word ends with a line break, as in an address.
    A run of single lines starting with bullets or numbers is a list.

    Transcript speaker paragraphs are also 1-3, so a block starting with a speaker label is left to
    the speaker detector, unless it is a list of short items ended by a blank line outside a transcript
    (eg. "First Place: ..., Second Place: ...")."""

    def detect_margin_block(text: str, cursor: int, state: DetectionState,
                            output_text: str) -> DetectionResult | None:
        if cursor and text[cursor - 1] != "\n":
            return None
        first = _ANY_LINE_RE.match(text, cursor)
        if not first or first.group(1):
            return None
        # (indent, text, cells the text could fill) for lines; (-1, pi, 0) for braille page PIs.
        # The first line of a numbered page has less room, as the page number is on it.
        lines: list[tuple[int, str, int]] = []
        pending_pis: list[tuple[int, str, int]] = []
        run_over: int | None = None
        line_cells = cells_per_line
        pos = end = cursor
        while True:
            if pi := _BRAILLE_PAGE_PI_RE.match(text, pos):
                pending_pis.append((-1, pi.group().rstrip("\n"), 0))
                line_cells = cells_per_line - len(pi.group(1)) - 3 if pi.group(1) else cells_per_line
                pos = pi.end()
                continue
            m = _ANY_LINE_RE.match(text, pos)
            if not m:
                break
            indent = len(m.group(1))
            if run_over is None and indent:
                if indent not in (2, 4):
                    break
                run_over = indent
            allowed = (0,) if run_over is None else (0, 2) if run_over == 2 else (0, 2, 4, 6)
            if indent not in allowed:
                break
            lines.extend(pending_pis)
            pending_pis = []
            lines.append((indent, m.group(2).rstrip("\u2800"), line_cells))
            line_cells = cells_per_line
            end = pos = m.end()
        text_lines = [line for line in lines if line[0] >= 0]
        if not text_lines:
            return None
        if _AFTER_SPECIAL_SYMBOLS_RE.search(output_text[-1000:]):
            # Each line at the margin, with any run-over, defines one symbol.
            return DetectionResult(end, dict(state, open_caption=False), 0.96, output_text + _list_html(lines))
        if _is_speaker_line(text_lines[0][1]) and not _is_short_list_after_all(text, end, text_lines, run_over, state):
            return None
        has_markers = any(_LIST_MARKER_RE.match(line[1]) for line in text_lines)
        # Run-overs of a 3-1 paragraph are at the margin and could pass for 1-3 items.
        if run_over == 2 and not has_markers and _looks_like_prose(text_lines):
            return None
        if run_over is None and not has_markers:
            html = f'<p class="left-justified">{_join_margin_lines(lines)}</p>\n'
        elif run_over == 2 and not has_markers and _AFTER_DATE_LINE_RE.search(output_text[-1000:]):
            # An address with a long line run over in 1-3: a line break before each margin line.
            html = f'<p class="left-justified">{_join_address_lines(lines)}</p>\n'
        else:
            html = _list_html(lines)
        return DetectionResult(end, dict(state, open_caption=False), 0.96, output_text + html)

    return detect_margin_block


def _is_short_list_after_all(text: str, end: int, text_lines: list[tuple[int, str, int]],
                             run_over: int | None, state: DetectionState) -> bool:
    """A 1-3 block starting with a "Label:" is a list, not dialogue, when it is two or more items
    of at most two lines each, outside a transcript and followed by a blank line."""
    if state.get("in_dialogue", False) or run_over not in (None, 2):
        return False
    item_sizes: list[int] = []
    for indent, _, _ in text_lines:
        if indent == 0:
            item_sizes.append(1)
        else:
            item_sizes[-1] += 1
    return len(item_sizes) >= 2 and max(item_sizes) <= 2 and text.startswith("<?blank-line?>", end)


def _looks_like_prose(text_lines: list[tuple[int, str, int]]) -> bool:
    """Most margin lines after the first carry on a full line before them, as run-overs of a
    3-1 paragraph do, rather than starting new list items."""
    starts = [(previous, line) for previous, line in zip(text_lines, text_lines[1:]) if line[0] == 0]
    carried_on = sum(wraps(previous[0] + len(previous[1]), line[1], previous[2]) for previous, line in starts)
    return 2 * carried_on > len(starts)


def _join_margin_lines(lines: list[tuple[int, str, int]]) -> str:
    """Join 1-1 lines: as one paragraph when most lines were wrapped (eg. an editor's note), else
    with a line break after every line (eg. an address, where a long line can still be followed
    by a word that would not have fitted)."""
    text_lines = [line for line in lines if line[0] >= 0]
    pairs = list(zip(text_lines, text_lines[1:]))
    wrapped = sum(wraps(len(a[1]), b[1], a[2], _WRAP_SLACK) for a, b in pairs)
    if 2 * wrapped > len(pairs):
        return join_lines([line[1] for line in lines])
    groups: list[list[str]] = [[]]
    for line in lines:
        groups[-1].append(line[1])
        if line[0] >= 0:
            groups.append([])
    groups[-2].extend(groups.pop())
    return "<br/>".join(join_lines(group) for group in groups)


def _join_address_lines(lines: list[tuple[int, str, int]]) -> str:
    groups: list[list[str]] = []
    pending_pis: list[str] = []
    for indent, line, _ in lines:
        if indent < 0:
            pending_pis.append(line)
            continue
        if indent == 0 or not groups:
            groups.append([])
        groups[-1].extend(pending_pis + [line])
        pending_pis = []
    groups[-1].extend(pending_pis)
    return "<br/>".join(join_lines(group) for group in groups)


def _list_html(lines: list[tuple[int, str, int]]) -> str:
    """Items at the margin; in a 1-5 list, sub-items at cell 3 and notes at cell 7 of the latest item."""
    nested = next((indent for indent, _, _ in lines if indent > 0), None) == 4
    items: list[_ListItem] = []
    owner: _ListItem | None = None
    target: list[str] = []
    pending_pis: list[str] = []
    for indent, line, _ in lines:
        if indent < 0:
            pending_pis.append(line)
            continue
        if indent == 0 or owner is None:
            owner = _ListItem(line)
            items.append(owner)
            target = owner.lines
        elif indent == 2 and nested:
            owner = _ListItem(line)
            items[-1].sub_items.append(owner)
            target = owner.lines
        elif indent == 6:
            owner.notes.append([line])
            target = owner.notes[-1]
        else:
            target.append(line)
        if pending_pis:
            # A page break goes just before the line after it.
            target.insert(len(target) - 1, "".join(pending_pis))
            pending_pis = []
    target.extend(pending_pis)
    # Numbered items running over in cell 5 (1-5) are steps, formatted unlike an ordinary 1-3 list.
    steps = nested and bool(_NUMBER_MARKER_RE.match(next(line for indent, line, _ in lines if indent >= 0)))
    return ('<ul class="steps">\n' if steps else "<ul>\n") + "\n".join(item.html() for item in items) + "\n</ul>\n"


def create_nfb_block_detectors(page_layout: PageLayout, parser_context: ParserContext,
                               print_issue: PrintIssue | None = None) -> list[Detector]:
    """The NFB specific detectors for the "Detect blocks" pass, ahead of the shared ones."""
    cells = page_layout.cells_per_line
    return [
        detect_separator,
        track_braille_pages,
        create_centered_detector(cells, parser_context, print_issue),
        # Bracketed directions in 7-7, eg. "(Applause and music, excerpt of ...)" over several lines.
        create_shape_paragraph_detector(6, 6, _caption_matcher, 0.97, stop_before=_after_closing_bracket,
                                        min_lines=2),
        # Photo captions in 7-5, starting with ".<".
        create_shape_paragraph_detector(6, 4, _caption_matcher, 0.96, stop_before=_after_closing_bracket),
        # The same one cell late (cell 8), a common transcriber slip.
        create_shape_paragraph_detector(7, 4, _caption_matcher, 0.94, stop_before=_after_closing_bracket),
        # Other 7-5 paragraphs, eg. a plaque read out in a transcript.
        create_shape_paragraph_detector(6, 4, _indented_quote_matcher, 0.94, min_lines=2, first_line_must_wrap=True,
                                        cells_per_line=cells),
        # Transcripts: speaker paragraphs in 1-3, continuation paragraphs in 5-3.
        create_shape_paragraph_detector(0, 2, _speaker_matcher, 0.95),
        create_shape_paragraph_detector(4, 2, _dialogue_continuation_matcher, 0.95),
        # 5-3 paragraphs outside transcripts, eg. a quoted news item.
        create_shape_paragraph_detector(4, 2, _quote_matcher, 0.94, first_line_must_wrap=True, cells_per_line=cells),
        # Headings, salutations, closings and blocked quotations at cell 5 or 7.
        create_blocked_detector(4, cells),
        create_blocked_detector(6, cells),
        # Lists and 1-1 paragraphs starting at the margin.
        create_margin_block_detector(cells),
        # Body paragraphs in 3-1. A speaker line at the margin starts a transcript, not a run-over.
        create_shape_paragraph_detector(2, 0, _paragraph_matcher, 0.93, stop_before=_starts_transcript),
        detect_toc,
    ]
