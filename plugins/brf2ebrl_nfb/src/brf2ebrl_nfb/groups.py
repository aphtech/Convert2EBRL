#  Copyright (c) 2026. American Printing House for the Blind.
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.
"""Wrap sets of blocks that the BRF sets off with blank lines in an element saying what the set is.

The markup says what each set is; the stylesheet gives each kind of set its spacing, so another
set of formatting rules only needs a different stylesheet. Runs after block detection, while the
blank line and braille page processing instructions are still in the text.

Sets, in the order they are found (a block belongs to one set at most):
    div.fm-group       a group of title page or masthead lines, before the contents or first article
    div.transcript     speaker turns (p.dialogue) and their continuations
    div.letter         a letter, from its date line to its closing or cc lines
    blockquote         quoted material: 5-3, 5-5 and 7-5 blocks set off by blank lines or page
                       breaks, perhaps starting with a centered title; also a sample conversation
                       set off inside the text
    div.event-details  short margin lines straight after an article title and byline
    div.roster         short margin lines set off by blank lines elsewhere in an article
"""
import re
from dataclasses import dataclass, field

from brf2ebrl.parser import ParserContext

_BLANK_LINE = "<?blank-line?>"
_BRAILLE_PAGE = "<?braille-page "
_START_TAG_RE = re.compile(r"<([a-zA-Z][a-zA-Z0-9]*)\b[^>]*>")
_CLASS_RE = re.compile(r'\bclass="([^"]*)"')
# ",,,SPECIAL SYMBOLS" heading of the special symbols page.
_SPECIAL_SYMBOLS = "\u2820\u2820\u2820\u280e\u280f\u2811\u2809\u280a\u2801\u2807"
# A date on its own: a capitalised month, the day and the year, eg. ",AUGU/ #AG1 #BJBF".
_DATE_RE = re.compile("^\u2820[\u2801-\u28ff]+\u2800\u283c[\u2801\u2803\u2809\u2819\u2811\u280b\u281b\u2813\u280a\u281a]+\u2802\u2800\u283c[\u2801\u2803\u2809\u2819\u2811\u280b\u281b\u2813\u280a\u281a]+$")
# "CC:" (,,CC3) opening a letter's copy lines.
_CC_RE = re.compile("(?:<li>)?\u2820\u2820\u2809\u2809\u2812")

_TRANSCRIPT_KINDS = {"dialogue", "dialogue-cont", "quote-indent", "direction", "caption"}
_QUOTE_KINDS = {"quote", "quote-block", "quote-indent", "closing", "salutation", "centered", "quoted-title"}
_HEADING_KINDS = {"heading", "title", "quoted-title"}
# Blocks of the article text, after which a centered title starts quoted material.
_BODY_KINDS = {"", "quote", "quote-block", "quote-indent", "dialogue", "dialogue-cont", "left-justified", "list"}


@dataclass
class _Block:
    start: int
    end: int
    kind: str
    html: str
    # Processing instructions between the previous block and this one.
    blank_before: bool = False
    page_before: bool = False
    group: str | None = field(default=None)


def _end_of_element(text: str, start: int, tag: str) -> int:
    """The index after the element starting at start, allowing for nested elements of the same tag."""
    depth = 0
    for m in re.finditer(f"<(/?){tag}\\b[^>]*?(/?)>", text[start:]):
        if m.group(1):
            depth -= 1
        elif not m.group(2):
            depth += 1
        if depth == 0:
            return start + m.end()
    return -1


def _kind(tag: str, start_tag: str) -> str:
    classes = (m.group(1) if (m := _CLASS_RE.search(start_tag)) else "").split()
    if tag == "p":
        return classes[0] if classes else ""
    if tag == "h1":
        return "title" if "article-title" in classes else "heading"
    if re.fullmatch("h[2-6]", tag):
        return "heading"
    if tag in ("ul", "ol"):
        return "list"
    return tag


def _parse(text: str) -> list[_Block] | None:
    """The blocks of the text, or None when there is text outside a block (then nothing is wrapped)."""
    blocks: list[_Block] = []
    pos = 0
    blank = page = False
    while pos < len(text):
        if text[pos].isspace():
            pos += 1
        elif text.startswith("<?", pos):
            end = text.find("?>", pos)
            if end < 0:
                return None
            blank = blank or text.startswith(_BLANK_LINE, pos)
            page = page or text.startswith(_BRAILLE_PAGE, pos)
            pos = end + 2
        elif m := _START_TAG_RE.match(text, pos):
            end = _end_of_element(text, pos, m.group(1))
            if end < 0:
                return None
            blocks.append(_Block(pos, end, _kind(m.group(1), m.group()), text[pos:end], blank, page))
            blank = page = False
            pos = end
        else:
            return None
    return blocks


def _inner(html: str) -> str:
    return re.sub("<[^>]*>", "", html)


def _mark_quoted_titles(blocks: list[_Block]) -> None:
    """A centered title inside an article's text is the title of quoted material."""
    for i, block in enumerate(blocks):
        if block.kind == "title" and i:
            previous = next((b for b in reversed(blocks[:i]) if b.kind != "caption"), None)
            # The first article after the masthead is not quoted.
            if previous is not None and previous.kind in _BODY_KINDS and previous.group != "fm-group":
                block.kind = "quoted-title"




# A set: (first block, last block, name).
_Set = tuple[int, int, str]


def _wrap(blocks: list[_Block], sets: list[_Set], first: int, last: int, name: str) -> None:
    for b in blocks[first:last + 1]:
        b.group = name
    sets.append((first, last, name))


def _free(blocks: list[_Block], first: int, last: int, within: tuple[str | None, ...] = (None,)) -> bool:
    return all(b.group in within for b in blocks[first:last + 1])


def _front_matter(blocks: list[_Block], sets: list[_Set]) -> None:
    """Title page and masthead lines up to the special symbols, contents or first article."""
    if not blocks or blocks[0].kind != "titlepage":
        return
    group: list[int] = []

    def close() -> None:
        if group:
            _wrap(blocks, sets, group[0], group[-1], "fm-group")
        group.clear()

    for i, block in enumerate(blocks):
        if block.kind in ("nav", "title", "separator") or _inner(block.html).startswith(_SPECIAL_SYMBOLS):
            break
        if block.kind in _HEADING_KINDS:
            close()
            continue
        # The blank line before a list (such as an address after "sent to:") is the list's own, so it
        # does not end a group. A page break between title page lines and the masthead does.
        previous = blocks[group[-1]] if group else None
        if previous and ((block.blank_before and block.kind != "list")
                         or (block.page_before and (block.kind == "titlepage") != (previous.kind == "titlepage"))):
            close()
        group.append(i)
    close()


def _transcripts(blocks: list[_Block], sets: list[_Set]) -> None:
    """Speaker turns and their continuations. Set off by a blank line inside the text, such as a
    sample conversation, they are quoted material instead."""
    i = 0
    while i < len(blocks):
        if blocks[i].kind != "dialogue" or blocks[i].group is not None:
            i += 1
            continue
        last = j = i
        while j < len(blocks) and blocks[j].kind in _TRANSCRIPT_KINDS and blocks[j].group is None:
            if blocks[j].kind != "caption":
                last = j
            j += 1
        quoted = blocks[i].blank_before and i and blocks[i - 1].kind in ("", "quote")
        _wrap(blocks, sets, i, last, "blockquote" if quoted else "transcript")
        i = last + 1


def _letters(blocks: list[_Block], sets: list[_Set]) -> None:
    """From a date line, through the address and "Dear ...:", to the closing and any cc lines."""
    for i, block in enumerate(blocks):
        if block.kind != "salutation" or block.group is not None:
            continue
        # The date, then the address and perhaps a "Re:" line.
        first = next((k for k in range(i - 1, max(-1, i - 5), -1)
                      if blocks[k].kind == "left-justified" and _DATE_RE.match(_inner(blocks[k].html))), None)
        if first is None:
            continue
        last = None
        for k in range(i + 1, len(blocks)):
            kind = blocks[k].kind
            if kind == "closing":
                last = k
            elif last is not None or kind in _HEADING_KINDS or kind in ("separator", "dialogue", "nav"):
                break
        if last is None:
            continue
        if last + 1 < len(blocks) and _CC_RE.match(_inner(blocks[last + 1].html).lstrip()):
            last += 1
        if _free(blocks, first, last):
            _wrap(blocks, sets, first, last, "letter")


def _bounded_before(blocks: list[_Block], i: int) -> bool:
    return i == 0 or blocks[i].blank_before or blocks[i].page_before or blocks[i - 1].kind in _HEADING_KINDS


def _bounded_after(blocks: list[_Block], i: int) -> bool:
    return i + 1 == len(blocks) or blocks[i + 1].blank_before or blocks[i + 1].page_before \
        or blocks[i + 1].kind in _HEADING_KINDS or blocks[i + 1].kind == "separator"


def _quoted_material(blocks: list[_Block], sets: list[_Set]) -> None:
    """Runs of quoted blocks set off by blank lines (or a page break) before and after, also inside
    a letter.

    A blank line ends a run; two quoted runs next to each other get one blank line between them,
    as the stylesheet's margins collapse."""
    i = 0
    while i < len(blocks):
        if blocks[i].kind not in _QUOTE_KINDS or blocks[i].group not in (None, "letter"):
            i += 1
            continue
        j = i
        while j + 1 < len(blocks) and blocks[j + 1].kind in _QUOTE_KINDS - {"quoted-title"} \
                and blocks[j + 1].group == blocks[i].group and not blocks[j + 1].blank_before:
            j += 1
        if _bounded_before(blocks, i) and _bounded_after(blocks, j) \
                and any(b.kind in ("quote", "quote-block", "quote-indent") for b in blocks[i:j + 1]):
            _wrap(blocks, sets, i, j, "blockquote")
        i = j + 1


def _short_line_sets(blocks: list[_Block], sets: list[_Set]) -> None:
    """Short margin lines kept on their own lines (a 1-1 block with line breaks)."""
    for i, block in enumerate(blocks):
        if block.kind != "left-justified" or "<br/>" not in block.html or block.group is not None:
            continue
        if i and blocks[i - 1].kind in ("title", "byline"):
            _wrap(blocks, sets, i, i, "event-details")
        elif block.blank_before and _bounded_after(blocks, i):
            _wrap(blocks, sets, i, i, "roster")


def _open_tag(name: str) -> str:
    return "<blockquote>" if name == "blockquote" else f'<div class="{name}">'


def _close_tag(name: str) -> str:
    return "</blockquote>" if name == "blockquote" else "</div>"


def group_blocks(text: str, _: ParserContext = ParserContext()) -> str:
    blocks = _parse(text)
    if not blocks:
        return text
    sets: list[_Set] = []
    _front_matter(blocks, sets)
    _mark_quoted_titles(blocks)
    _transcripts(blocks, sets)
    _letters(blocks, sets)
    _quoted_material(blocks, sets)
    _short_line_sets(blocks, sets)
    # Sets nest (a quotation inside a letter): open the outer set first and close the inner one first.
    opens: dict[int, list[_Set]] = {}
    closes: dict[int, list[_Set]] = {}
    for s in sorted(sets, key=lambda s: (s[0], -s[1])):
        opens.setdefault(s[0], []).append(s)
        closes.setdefault(s[1], []).insert(0, s)
    result = ""
    pos = 0
    for i, block in enumerate(blocks):
        if i in opens:
            result += text[pos:block.start] + "".join(_open_tag(s[2]) + "\n" for s in opens[i])
            pos = block.start
        if i in closes:
            result += text[pos:block.end] + "".join("\n" + _close_tag(s[2]) for s in closes[i])
            pos = block.end
    return result + text[pos:]
