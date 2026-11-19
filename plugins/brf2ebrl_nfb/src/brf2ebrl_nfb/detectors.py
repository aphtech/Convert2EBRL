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
"""
import re
from collections.abc import Callable

from brf2ebrl.common import PageLayout
from brf2ebrl.common.block_detectors import _notify_low_confidence_match
from brf2ebrl.parser import Detector, DetectionResult, DetectionState, ParserContext
from brf2ebrl.utils.back_translation import back_translate_contracted
from brf2ebrl_nfb.print_source import PrintIssue, match_heading
from brf2ebrl_nfb.toc import detect_toc

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


def _print_text(braille: str) -> str:
    return back_translate_contracted(braille) or ""


def _unique_id(base: str, used: frozenset[str]) -> str:
    heading_id, n = base, 2
    while heading_id in used:
        heading_id, n = f"{base}-{n}", n + 1
    return heading_id


def create_centered_detector(cells_per_line: int, parser_context: ParserContext = ParserContext(),
                             print_issue: PrintIssue | None = None) -> Detector:
    """Centered lines: title page lines, article title plus byline, or a section heading.

    Based on the shared centered detector, with the same one cell tolerance, but it keeps the
    lines separate, does not require a blank line after the heading and never makes guide words.
    With the print HTML, article titles get the print title as a readable id and section
    headings get the print level."""

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
                pass
            elif actual_indent - 1 in indents or actual_indent + 1 in indents:
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
        if state.get("nfb_title_page", False):
            html = "".join(f'<p class="titlepage">{line}</p>\n' for line in lines)
        else:
            by_index = next((i for i, line in enumerate(lines)
                             if _is_byline_start(line, lines[i + 1] if i + 1 < len(lines) else "")), len(lines))
            heading = "\u2800".join(lines[:by_index])
            byline = "\u2800".join(lines[by_index:])
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
                else:
                    # Braille cannot show the print level of a section heading; the print can.
                    tag = "h2"
                    if print_issue and (match := match_heading(print_issue, _print_text(heading), (3, 4))):
                        tag = "h3" if match.level == 4 else "h2"
                    html += f"<{tag}>{heading}</{tag}>\n"
            if byline:
                html += f'<p class="byline">{byline}</p>\n'
        return DetectionResult(new_cursor, new_state, confidence, output_text + html,
                               on_selected=notify_pending if pending_notifications else None)

    return detect_centered


def create_shape_paragraph_detector(
        first_line_indent: int,
        run_over: int,
        matcher: Callable[[str, DetectionState], tuple[str | None, DetectionState]],
        confidence: float,
        stop_before: Callable[[str, str], bool] = lambda previous_line, line: False,
) -> Detector:
    """A paragraph is a first line at first_line_indent followed by run-over lines at run_over.

    The newsletter has no blank lines between blocks, so the indents alone mark where a block
    ends. Unlike the shared paragraph finder there is no line wrapping check, which wrongly
    rejects paragraphs that start on the line holding the top right page number. Braille page
    processing instructions may fall inside a paragraph, as in the shared finder."""
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
        html, new_state = matcher("\n".join(lines), state)
        if html is None:
            return None
        return DetectionResult(new_cursor, new_state, confidence, f"{output_text}{html}\n")

    return detect_shape_paragraph


def _after_closing_bracket(previous_line: str, line: str) -> bool:
    """A bracketed caption ends with ".>"; the next line starts something else."""
    return previous_line.endswith(_CLOSING_BRACKET)


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
    return bool(_SPEAKER_RE.match(line))


def _looks_like_toc_entry(brl: str) -> bool:
    return bool(_GUIDE_DOTS_PAGE_NUMBER_RE.search(brl) or _PAGE_NUMBER_AT_END_RE.search(brl.split("\n", 1)[0]))


def _starts_transcript(previous_line: str, line: str) -> bool:
    """A margin line after a finished sentence that opens with a speaker label starts a transcript."""
    return bool(_SENTENCE_END_RE.search(previous_line)) and _is_speaker_line(line)


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


def create_nfb_block_detectors(page_layout: PageLayout, parser_context: ParserContext,
                               print_issue: PrintIssue | None = None) -> list[Detector]:
    """The NFB specific detectors for the "Detect blocks" pass, ahead of the shared ones."""
    return [
        detect_separator,
        track_braille_pages,
        create_centered_detector(page_layout.cells_per_line, parser_context, print_issue),
        # Photo captions in 7-5, starting with ".<".
        create_shape_paragraph_detector(6, 4, _caption_matcher, 0.96, stop_before=_after_closing_bracket),
        # The same one cell late (cell 8), a common transcriber slip.
        create_shape_paragraph_detector(7, 4, _caption_matcher, 0.94, stop_before=_after_closing_bracket),
        # Transcripts: speaker paragraphs in 1-3, continuation paragraphs in 5-3.
        create_shape_paragraph_detector(0, 2, _speaker_matcher, 0.95),
        create_shape_paragraph_detector(4, 2, _dialogue_continuation_matcher, 0.95),
        # Body paragraphs in 3-1. A speaker line at the margin starts a transcript, not a run-over.
        create_shape_paragraph_detector(2, 0, _paragraph_matcher, 0.93, stop_before=_starts_transcript),
        detect_toc,
    ]
