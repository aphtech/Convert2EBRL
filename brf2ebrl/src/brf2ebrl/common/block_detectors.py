#  Copyright (c) 2024. American Printing House for the Blind.
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""Detectors for blocks."""

import re
from dataclasses import dataclass
from collections.abc import Iterable, Callable

from brf2ebrl.parser import DetectionState, DetectionResult, Detector
from brf2ebrl.common import PageLayout, PageNumberPosition

# constants for list and paragraph.
_PRINT_PAGE_RE = "(?:<\\?print-page[ \u2800-\u28ff]*?\\?>)"
_RUNNING_HEAD_RE = "(?:<\\?running-head[ \u2800-\u28ff]*\\?>)"
_BRAILLE_PAGE_RE = "(?:<\\?braille-page[ \u2800-\u28ff]*\\?>)"
_BRAILLE_PPN_RE = "(?:<\\?braille-ppn [ \u2800-\u28ff]*\\?>)"
_BLANK_LINE_RE = "(?:<\\?blank-line\\?>)"
_PROCESSING_INSTRUCTION_RE = (
    f"(?:(?:{_BRAILLE_PAGE_RE}\n)?"
    f"(?:{_BRAILLE_PPN_RE}\n)?"
    f"(?:{_PRINT_PAGE_RE}\n)?"
    f"(?:{_RUNNING_HEAD_RE}\n)?)"
)


@dataclass
class ParsedLine:
    """holds parsed lines information"""
    depth: int
    pi: str
    line_text: str
    end: int = 0

    def copy(self) -> "ParsedLine":
        """copy helper function"""
        return ParsedLine(self.depth, self.pi, self.line_text, self.end)


def detect_pre(
    text: str, cursor: int, state: DetectionState, output_text: str
) -> DetectionResult | None:
    """Detects preformatted Braille"""
    brl = ""
    for c in text[cursor:]:
        if ord(c) in range(0x2800, 0x2900):
            brl += c
        else:
            break
    return (
        DetectionResult(cursor + len(brl), state, 0.4, f"{output_text}<pre>{brl}</pre>")
        if brl
        else None
    )


def create_cell_heading(indent: int, tag_name: str) -> Detector:
    """Creates a detector for a heading indented by the specified amount."""
    heading_re = re.compile(f"\u2800{{{indent}}}([\u2801-\u28ff][\u2800-\u28ff]*)\n+")

    def detect_cell_heading(
        text: str, cursor: int, state: DetectionState, output_text: str
    ) -> DetectionResult | None:
        lines = []
        new_cursor = cursor
        while line := heading_re.match(
            text[new_cursor:],
        ):
            lines.append(line.group(1))
            new_cursor += line.end()
        brl = "\u2800".join(lines)
        return (
            DetectionResult(
                new_cursor, state, 0.9, f"{output_text}<{tag_name}>{brl}</{tag_name}>\n"
            )
            if brl
            else None
        )

    return detect_cell_heading


def create_centered_detector(
    cells_per_line: int, min_indent: int, tag_name: str
) -> Detector:
    """Creates a detector for detecting centered text."""
    heading_re = re.compile(
        f"(\u2800{{{min_indent},}})([\u2801-\u28ff][\u2800-\u28ff]*)\n+",
    )

    _next_line_re = re.compile(
        rf"{_BLANK_LINE_RE}\n|<div type=.*\n|\u283f{{{cells_per_line / 2},{cells_per_line}}}\n|"
        "^[\u2801-\u28ff][\u2800-\u28ff]*\n"
    )

    def detect_centered(
        text: str, cursor: int, state: DetectionState, output_text: str
    ) -> DetectionResult | None:
        lines = []
        brl = ""
        new_cursor = cursor
        while line := heading_re.match(
            text[new_cursor:],
        ):
            line_brl = line.group(2).rstrip("\u2800")
            indent, indent_mod = divmod(cells_per_line - len(line_brl), 2)
            indents = [indent] if indent_mod == 0 else [indent, indent + indent_mod]
            if len(line.group(1)) in indents:
                lines.append(line_brl)
                new_cursor += line.end()
            else:
                break
        if _next_line_re.match(text[new_cursor:]):
            brl = "\u2800".join(lines)
        return (
            DetectionResult(
                new_cursor, state, 0.9, f"{output_text}<{tag_name}>{brl}</{tag_name}>\n"
            )
            if brl
            else None
        )

    return detect_centered


def create_table_detector() -> Detector:
    """Creates a detector for finding simple tables more can be added"""
    seperator_re = re.compile(
        "((?:[\u2800-\u28ff]+?\n){1,2})(\u2810\u2812+?(?:\u2800\u2800\u2810\u2812+?)+?)\n"
    )

    def row_column_check(widths: list[int], line: str) -> bool:
        """compares each row to make sure it has the right seperator to see if it is a row"""
        i = 0
        for width in widths[:-1]:
            end_of_cell = i + width
            start_of_next_cell = end_of_cell + 2
            if line[end_of_cell:start_of_next_cell] != "\u2800\u2800":
                return False
            i = start_of_next_cell
        return True

    def get_line(brf_text: str, pos: int, widths: list[int]) -> int | None:
        """Gets each line after table header that matches table columns"""
        pos2 = brf_text[pos:].find("\n") + 1

        return pos2 if row_column_check(widths, brf_text[pos : pos + pos2]) else None

    def wrap_and_join(fmt: str, items: Iterable[str]) -> str:
        """Wraps each element and joins into a single string."""
        return "".join([fmt.format(s) for s in items])

    def detect_table(
        text: str, cursor: int, state: DetectionState, output_text: str
    ) -> DetectionResult | None:
        match = seperator_re.match(text[cursor:])
        if not match:
            return None

        # code
        col_widths = [len(col) for col in match.group(2).split("\u2800\u2800")]

        # create header
        header_lines = match.group(1).split("\n")
        table = ["<tr>"]
        if len(header_lines) > 1:
            pos = 0
            for index, width in enumerate(col_widths):
                cell_text = header_lines[0][pos : pos + width + 2].strip("\u2800")
                if cell_text and header_lines[1].strip("\u2800"):
                    cell_text += "\u2800"
                cell_text = (
                    "<th>"
                    + cell_text
                    + ""
                    + header_lines[1][pos : pos + width + 2].strip("\u2800")
                    + "</th>"
                )
                pos += width + 2
                table[0] += cell_text
        else:
            table[0] += wrap_and_join(
                "<th>{}</th>",
                [
                    cell.strip("\u2800")
                    for cell in header_lines[0].split("\u2800\u2800")
                ],
            )
        table[0] += "</tr>"
        # header done

        cursor += match.end(2) + 1
        # cells
        row = 0
        while end_cursor := get_line(text, cursor, col_widths):
            line = text[cursor : cursor + end_cursor]
            if line.startswith("\u2800\u2800"):
                sep = "\u2800"
            else:
                sep = ""
                table.append([""] * len(col_widths))
                row += 1

            for index, cell in enumerate(line.split("\u2800\u2800")):
                if index < len(col_widths):
                    # need this temp var because of backslashes.
                    cell_strip = cell.strip("\u2800\u2810\n")
                    table[row] += f"{sep}{cell_strip}"
            cursor += end_cursor

        complete_table = table[0] + "\n"
        complete_table += wrap_and_join(
            "<tr>{}</tr>\n", [wrap_and_join("<td>{}</td>", row) for row in table[1:]]
        )
        complete_table = f"<table>\n{complete_table}\n</table>"
        return DetectionResult(cursor, state, 0.9, f"{output_text}{complete_table}\n")

    return detect_table


# used a data class for best type checking and protection
@dataclass(frozen=True)
class RightPageNumberLengths:
    top: int
    bottom: int


running_head_re = re.compile("^<\\?running-head([ \u2800-\u28ff]*)\\?>$")
print_page_re = re.compile("^<\\?print-page([ \u2800-\u28ff]*)\\?>$")
braille_page_ppn_re = re.compile(
    "^<\\?(braille-page|braille-ppn)([ \u2800-\u28ff]*)\\?>$"
)


def is_toc_or_table_line(lines: list[ParsedLine]) -> bool:
    """return if the line is a toc or table line by looking for dividers or long runs of dots
    """

    # fail if any has 1 set of guide dots rows or a table divider. and return
    dots_re = re.compile("\u2810{2,}")
    for line in lines:
        if re.findall("\u2810\u2812{2,}", line.line_text):
            return  True
        if dots_re.findall(line.line_text):
            return True
        
    return False

            


def build_lines_pi(text: str, cursor: int) -> dict[str, str]:
    """Scan backward from cursor through all content to find the current page's
    braille-page and braille-ppn processing instructions."""
    page_dict: dict[str, str] = {}

    scan_pos = cursor
    while scan_pos > 0:
        line_end = scan_pos
        if text[line_end - 1] == "\n":
            line_end -= 1

        line_start = text.rfind("\n", 0, line_end) + 1
        line = text[line_start:line_end]
        scan_pos = line_start

        # Skip running-heads — they don't affect page numbering
        if running_head_re.fullmatch(line):
            continue

        page_match = braille_page_ppn_re.fullmatch(line)
        if page_match:
            key = page_match.group(1)
            if key not in page_dict:
                page_dict[key] = page_match.group(2)
            # braille-page marks the start of the current page — stop here
            if key == "braille-page":
                break
        # All other lines (content, blank-line PI, print-page PI, etc.) are skipped

    return page_dict


def get_top_and_bottom_page_length(
    page_dict: dict[str, str], layout: PageLayout
) -> RightPageNumberLengths:
    """Return a Data class containing the lengths of the top and bottom right page numbers."""
    top = 0
    bottom = 0
    page_dict["braille-page"] = page_dict.get("braille-page", "")
    page_dict["braille-ppn"] = page_dict.get("braille-ppn", "")

    if PageNumberPosition.TOP_RIGHT in [
        layout.odd_braille_page_number,
        layout.even_braille_page_number,
    ]:
        top = len(page_dict["braille-page"].strip())
    elif PageNumberPosition.TOP_RIGHT in [
        layout.odd_print_page_number,
        layout.even_print_page_number,
    ]:
        top = len(page_dict["braille-ppn"].strip())

    if PageNumberPosition.BOTTOM_RIGHT in [
        layout.even_braille_page_number,
        layout.odd_braille_page_number,
    ]:
        bottom = len(page_dict["braille-page"].strip())
    elif PageNumberPosition.BOTTOM_RIGHT in [
        layout.odd_print_page_number,
        layout.even_print_page_number,
    ]:
        bottom = len(page_dict["braille-ppn"].strip())

    return RightPageNumberLengths(top=top, bottom=bottom)


def _create_indented_block_finder(
    first_line_indent: int, run_over: int, layout: PageLayout
) -> Callable[[str, int], tuple[list[ParsedLine], int]]:

    cells_per_line = layout.cells_per_line
    _first_line_re = re.compile(
        f"(\u2800{{{first_line_indent}}})([\u2801-\u28ff][\u2800-\u28ff]*)\n"
    )

    _run_over_re = re.compile(
        f"(\u2800{{{run_over}}})([\u2801-\u28ff][\u2800-\u28ff]*)\n"
    )

    paragraph_processing_instruction_re = re.compile(
        f"((?:{_BLANK_LINE_RE}\n)|(?:{_BRAILLE_PAGE_RE}\n)"
        f"|(?:{_BRAILLE_PPN_RE}\n)|(?:{_PRINT_PAGE_RE}\n)"
        f"|(?:{_RUNNING_HEAD_RE}\n))"
    )

    def get_paragraph_lines(
        text: str,
        cursor_offset: int,
        line: re.Match[str],
    ) -> tuple[list[ParsedLine], int]:
        """
        collect all lines of a paragraph.
        Returns (lines, new_cursor).
        """
        new_lines: list[ParsedLine] = []
        _block: list[ParsedLine] = []
        new_cursor = cursor_offset

        # Compute top padding context by scanning backward from start of first line
        initial_page_dict = build_lines_pi(text, cursor_offset)
        initial_right_page_lengths = get_top_and_bottom_page_length(
            initial_page_dict, layout
        )

        current_match: re.Match[str] | None = line
        current_is_pi = False  # first line is a content line
        is_first = True

        while current_match is not None:
            current_pi_str = current_match.group(1) if current_is_pi else ""

            # if current_line is blank line: break
            if current_is_pi and current_pi_str == "<?blank-line?>\n":
                break

            # Determine if previous line is a PI
            prev_is_pi = (new_lines[-1].depth == -1) if new_lines else False
            prev_pi_str = new_lines[-1].pi if (new_lines and prev_is_pi) else ""

            # if current is a page PI and previous is not PI: add bottom padding to previous
            if (
                current_is_pi
                and new_lines
                and not prev_is_pi
                and current_pi_str.startswith(
                    (
                        "<?braille-page",
                        "<?braille-ppn",
                        "<?running-head",
                        "<?print-page",
                    )
                )
            ):
                page_dict = build_lines_pi(text, new_cursor)
                right_page_lengths = get_top_and_bottom_page_length(page_dict, layout)
                if right_page_lengths.bottom:
                    new_lines[-1].line_text += " " * (right_page_lengths.bottom + 3)

            # Build ParsedLine for current_match
            if current_is_pi:
                parsed = ParsedLine(-1, current_pi_str, "", current_match.end())
            else:
                indent_len = len(current_match.group(1))
                if is_first:
                    line_text = " " * indent_len + current_match.group(2)
                    indent_len = 0
                    if initial_right_page_lengths.top > 0:
                        line_text += " " * (initial_right_page_lengths.top + 3)
                else:
                    line_text = current_match.group(2)
                    # if current is not PI and previous is PI: add top padding
                    if prev_is_pi and not prev_pi_str.startswith(
                        ("<?running-head", "<?print-page")
                    ):
                        page_dict = build_lines_pi(text, new_cursor)
                        right_page_lengths = get_top_and_bottom_page_length(
                            page_dict, layout
                        )
                        if right_page_lengths.top:
                            line_text += " " * (right_page_lengths.top + 3)
                parsed = ParsedLine(indent_len, "", line_text, current_match.end())
                is_first = False
            if parsed.depth != -1:
                _block.append(parsed)
                if not detect_paragraph_wrapping(_block, cells_per_line, parsed.depth):
                    break
            new_lines.append(parsed)
            new_cursor += parsed.end

            # Get next legal line: PI or run-over content
            if pi_match := paragraph_processing_instruction_re.match(text[new_cursor:]):
                current_match = pi_match
                current_is_pi = True
            elif runover := _run_over_re.match(text[new_cursor:]):
                current_match = runover
                current_is_pi = False
            else:
                current_match = None

        _block = [line for line in new_lines if line.depth != -1]
        if not _block:
            return ([], cursor_offset)

        if is_toc_or_table_line(new_lines):
            return ([], cursor_offset)  
        return (new_lines, new_cursor)

    def find_paragraph_braille(text: str, cursor: int) -> tuple[list[ParsedLine], int]:
        new_cursor = cursor

        if line := _first_line_re.match(text[cursor:]):
            lines, new_cursor = get_paragraph_lines(text, cursor, line)

            if lines and is_block_paragraph(lines, cells_per_line=cells_per_line):
                return (lines, new_cursor)
        return ([], new_cursor)

    return find_paragraph_braille


def _no_indicators_block_matcher(
    brl: str, state: DetectionState, tags: tuple[str, str] = ("<p>", "</p>")
) -> tuple[str | None, DetectionState]:
    """if not a TN then return no indecators"""
    return f"{tags[0]}{brl}{tags[1]}", state



def create_paragraph_detector(
    first_line_indent: int,
    run_over: int,
    layout: PageLayout,
    indicator_matcher: Callable[
        [str, DetectionState], tuple[str | None, DetectionState]
    ] = _no_indicators_block_matcher,
    confidence: float = 0.9,
) -> Detector:
    """Creates a detector for finding paragraphs with the
    specified first line indent and run over."""
    find_paragraph_braille = _create_indented_block_finder(
        first_line_indent=first_line_indent,
        run_over=run_over,
        layout=layout,
    )

    def make_paragraph(lines: list[ParsedLine]) -> str:
        """Make a paragraph or block paragraph"""
        brl_lines = []
        for line in lines:
            brl_lines.append(
                f"{line.pi.strip()}{line.line_text}".strip(" ").lstrip("\u2800")
            )
        return "\n".join(brl_lines)

    def detect_paragraph(
        text: str, cursor: int, state: DetectionState, output_text: str
    ) -> DetectionResult | None:
        new_lines, new_cursor = find_paragraph_braille(text, cursor)
        brl = make_paragraph(new_lines)
        if brl:
            tag, new_state = indicator_matcher(brl, state)
            if tag:
                return DetectionResult(
                    new_cursor, new_state, confidence, f"{output_text}{tag}\n"
                )
        return None

    return detect_paragraph


def has_toc(lines: list[ParsedLine]) -> bool:
    """return if one of the tiems is a toc entry"""
    for line in lines:
        if re.search(r".*?\u2810{2,}.*", line.line_text):
            return True
    return False


def detect_paragraph_wrapping(
    lines: list[ParsedLine], cells_per_line: int, depth: int = 0
) -> bool:
    """Detect if paragraph is wrapped or not."""

    if cells_per_line <= 0:
        raise ValueError("cells_per_line must be greater than 0 for is_block_paragraph")

    # Willo idea.
    #  if any of the lines start with a word that could fit on the previous line not a paragraph
    for i in range(1, len(lines)):
        prev_line_len = len(lines[i - 1].line_text.strip("\u2800")) + depth
        if prev_line_len < cells_per_line:
            word = lines[i].line_text.strip("\u2800").split("\u2800", maxsplit=1)[0]
            available_space = cells_per_line - prev_line_len
            word_plus_space = len(word) + 1
            if word_plus_space <= available_space:
                return False

    return True


_BRAILLE_PAGE_LENGTH_RE = re.compile("(?:<\\?braille-page([ \u2800-\u28ff]*)\\?>)")


def is_block_paragraph(
    lines: list[ParsedLine], depth: int = 0, cells_per_line: int = 0
) -> bool:
    """Check if this is a list or block paragraph."""

    _roman_re = re.compile(
        "^\u280d{0,3}"
        "(\u2809\u280d|\u2809\u2819|\u2819?\u2809{0,3})"
        "(\u282d\u2809|\u282d\u2807|\u2807?\u282d{0,3})"
        "(\u280a\u282d|\u280a\u2827|\u2827?\u280a{0,3})"
        "\u2800[2800-28ff]+$"
    )
    _lower_alpha_with_period_re = re.compile(
        "[\u2801\u2803\u2805\u2807\u2809\u280a\u280b\u280d\u280e\u280f"
        "\u2811\u2813\u2815\u2817\u2819\u281a\u281b\u281d\u281e\u281f"
        "\u2825\u2827\u282d\u2835\u283a\u283d]+\u2832\u2800[2800-28ff]+"
    )
    _lower_alpha_with_paran_re = re.compile(
        "[\u2801\u2803\u2805\u2807\u2809\u280a\u280b\u280d\u280e\u280f"
        "\u2811\u2813\u2815\u2817\u2819\u281a\u281b\u281d\u281e\u281f"
        "\u2825\u2827\u282d\u2835\u283a\u283d]+\u2802\u28c1\u2800[\u2800-\u28ff]+"
    )
    _cells_per_line = cells_per_line
    _end_punctuation_equal_re = re.compile(".*[\u2832\u2826\u2816][\u2804\u2834]*$")

    # copy and remove just PI
    _lines = [line for line in lines if line.depth != -1]

    block_len = len(_lines)
    block = [line.line_text for line in _lines if line.depth == depth]
    # if not all lines have depth  indent
    if len(block) != block_len:
        return False

        # return False
    if not detect_paragraph_wrapping(_lines, _cells_per_line, depth):
        return False

    # if it is length one it is a block because who makes a 1 line list in braille
    if len(_lines) == 1:
        return True

    # if all lines start with roman with out punctuation
    if not [line for line in block if not _roman_re.match(line)]:
        return False

    # if all lines start with letter  period  assume list with small letters or small roman
    if not [line for line in block if not _lower_alpha_with_period_re.match(line)]:
        return False

    # if all lines start with letter  right paran   assume list with small letters or small roman
    if not [line for line in block if not _lower_alpha_with_paran_re.match(line)]:
        return False

        # if all lines start with the same symbole then not block
    if len(block) > 2 and all(line[0] == block[0][0] for line in block):
        return False

    # if all lines end in punctuation assume list
    # if not [line for line in block if not _end_punctuation_equal_re.match(line)]:
    # return False

    # do not know so default
    return True


def get_run_over_depth(lines: list[ParsedLine], cells_per_line: int) -> int:
    """Get the lists of the deepest groupings."""
    max_depth = 0
    current_depth = 0
    current_start = 0
    groupings = []

    for index, line in enumerate(lines):
        if line.depth > current_depth:
            current_depth = line.depth
            current_start = index
        elif line.depth < current_depth:
            if current_depth > max_depth:
                max_depth = current_depth
                groupings = [lines[current_start:index]]
            elif current_depth == max_depth:
                groupings.append(lines[current_start:index])
            current_depth = line.depth

    if current_depth == max_depth:
        groupings.append(lines[current_start:])
    elif current_depth > max_depth:
        groupings = [lines[current_start:]]

    for group in groupings:
        if is_block_paragraph(group, group[0].depth, cells_per_line):
            return group[0].depth

    return 0


# detect TOC
def create_toc_detector(cells_per_line: int) -> Detector:
    """Creates a detector for finding TOC"""
    first_line_re = re.compile("([\u2801-\u28ff][\u2800-\u28ff]*)\n")
    run_over_re = re.compile("(\u2800+)([\u2801-\u28ff][\u2800-\u28ff]*)\n")

    toc_processing_instruction_re = re.compile(
        f"((?:{_BLANK_LINE_RE}\n)|(?:{_BRAILLE_PAGE_RE}\n)"
        f"|(?:{_BRAILLE_PPN_RE}\n)|(?:{_PRINT_PAGE_RE}\n)"
        f"|(?:{_RUNNING_HEAD_RE}\n))"
    )

    min_indent = 3
    heading_re = re.compile(
        f"(\u2800{{{min_indent},}})([\u2801-\u28ff][\u2800-\u28ff]*)\n+",
    )

    toc_entry_re = re.compile(
        r"([\u2800-\u28FF]+?)"  # Group 1: Section title (non-greedy)
        r"(?:\u2800\u2810{2,}\u2800|\u2800\u2800)"  # Divider: 2+ ⠐ or exactly two ⠀
        r"([\u2801-\u28FF]+)"  # Group 2: Page number (must not include ⠀)
        r"(<.*)?"  # Group 3: Optional <...>, only after ⠀
    )

    def parse_and_create_toc_entry(line: str) -> str:
        """use re because there were problems."""
        toc_lines = line.split("\n")
        match = toc_entry_re.fullmatch(toc_lines[0])
        if not match:
            return line

        if match.group(3):
            toc_lines[0] = (
                f"<span>{match.group(1)}</span> <span>{match.group(2)}</span>{match.group(3)}"
            )
        else:
            toc_lines[0] = (
                f"<span>{match.group(1)}</span> <span>{match.group(2)}</span>"
            )
        return "\n".join(toc_lines)

    def join_toc(lines: list[ParsedLine]) -> str:
        """
        check for dot five split if there take last item if not for anchor
        """
        for index, line in enumerate(lines):
            if line.line_text:
                lines[index].line_text = parse_and_create_toc_entry(
                    lines[index].line_text
                )

        list_head = '<ol class="toc" style="list-style-type: none">'
        list_tail = "</ol>"

        list_str = f"{list_head}\n"
        for line in lines:
            if line.pi:
                list_str += f"{line.pi}\n"
            if line.line_text:
                list_str += f"<li>{line.line_text}</li>\n"
        list_str += f"{list_tail}\n"
        return list_str

    def build_toc(
        lines: list[ParsedLine],
        index: int,
        length: int,
        levels: list[int],
        current_level: int,
    ) -> list:
        """Recursive list builder, preserving processing instructions and supporting nested toc's"""
        list_level = []
        original_index = index

        while index < length:
            current = lines[index]
            next_line = lines[index + 1] if (index + 1) < length else None

            # Always include processing instructions
            if current.depth == -1:
                list_level.append(current)
                index += 1
                continue

            # Check for deeper nested structure
            if next_line and next_line.depth > current_level:
                list_level.append(current.copy())
                nested_index_diff, nested_html = build_toc(
                    lines, index + 1, length, levels, next_line.depth
                )
                if re.search(
                    "\u2800\u2810{2,}\u2800", current.line_text
                ) and not nested_html.startswith("<ol"):
                    list_level.append(next_line.copy())
                    list_level[-1].line_text = nested_html
                else:
                    list_level[-1].line_text += nested_html
                index += nested_index_diff + 1
                continue

            # Check for return to a shallower level
            if next_line and next_line.depth < current_level and next_line.depth != -1:
                list_level.append(current.copy())
                if not re.search(
                    "\u2800\u2810{2,}\u2800", current.line_text
                ) and not re.search("\u2800\u2810{2,}\u2800", next_line.line_text):
                    list_level[-1].line_text += f"\n{next_line.line_text}"
                    index += 2
                    continue
                index += 1
                break

            # Normal list entry
            list_level.append(current)
            index += 1

        # At deepest level, check if it's a block paragraph
        if current_level == levels[-1] and is_block_paragraph(
            list_level, current_level, cells_per_line
        ):
            joined = "".join(
                f"{line.pi}\u2800{line.line_text}" if line.pi else line.line_text
                for line in list_level
            )
            return [index - original_index, joined]

        # Otherwise, render HTML list, preserving PI lines
        return [index - original_index, join_toc(list_level)]

    def make_toc(lines: list[ParsedLine]) -> str:
        """Make a list or nested list"""
        if not has_toc(lines):
            return ""

        # create clean set of levels acending
        levels = list({level.depth for level in lines if level.depth != -1})

        # one level list
        if len(levels) == 1:
            return join_toc(lines)

        #  nested list or over run list
        _, brl_str = build_toc(lines, 0, len(lines), levels, 0)
        return str(brl_str)

    def match_toc_line(current_line: str) -> ParsedLine | None:
        """Match lines if they are possibly part of a list"""
        if line := first_line_re.match(current_line):
            return ParsedLine(0, "", line.group(1), line.end())

        if line := run_over_re.match(current_line):
            return ParsedLine(len(line.group(1)), "", line.group(2), line.end())

        return None

    def get_toc_pages(
        text: str, cursor_offset: int, debug: int = 0
    ) -> tuple[list[ParsedLine], int]:
        """
        get toc pages
        return lines and cursor to add to text
        """
        new_cursor = cursor_offset
        new_lines: list[ParsedLine] = []

        # consume PI's if consicutive blanks stop and return [[],0]
        while line := toc_processing_instruction_re.match(text[new_cursor:]):
            if (
                new_lines
                and line.group(1) == "<?blank-line?>\n"
                and new_lines[-1].pi == line.group(1)
            ):
                return ([], cursor_offset)
            new_lines.append(ParsedLine(-1, line.group(1), "", line.end()))
            new_cursor += line.end()

        # if centered heading stop and return [[], 0]
        center_line = heading_re.match(text[new_cursor:])
        if center_line:
            line_brl = center_line.group(2).rstrip("\u2800")
            indent, indent_mod = divmod(cells_per_line - len(line_brl), 2)
            indents = [indent] if indent_mod == 0 else [indent, indent + indent_mod]
            if len(center_line.group(1)) in indents and not re.findall(
                "\u2808\u2828\u2823[\u2800-\u28ff]*\n", text[new_cursor:]
            ):
                return ([], cursor_offset)

        # consume all legal toc lines until does not match.
        while line := match_toc_line(text[new_cursor:]):
            new_lines.append(line)
            new_cursor += line.end

        if not [line for line in new_lines if line.depth != -1]:
            return ([], cursor_offset)

        # test if it has at least one with a single set of guide dots or two spaces has
        # fail if any has two rows or a table divider. and return [[],0]
        guide_dots = False
        dots_re = re.compile("\u2810{2,}")
        for line in new_lines:
            # fail if a line has two sets of "\u2800\u2800"  non consecutive
            if len(re.findall("\u2800\u2800", line.line_text)) > 1:
                return ([], cursor_offset)
            if re.findall("\u2810\u2812{2,}", line.line_text):
                return ([], cursor_offset)
            if dots := dots_re.findall(line.line_text):
                if len(dots) > 1:
                    return ([], cursor_offset)
                guide_dots = True

        # not a toc probably a list
        if not guide_dots:
            return ([], cursor_offset)

        temp_list = get_toc_pages(text, new_cursor, debug + 1)
        new_lines.extend(temp_list[0])
        return (new_lines, temp_list[1])

    def detect_toc(
        text: str, cursor: int, state: DetectionState, output_text: str
    ) -> DetectionResult | None:
        brl = ""
        lines: list[ParsedLine] = []
        new_cursor = cursor
        if (cursor == 0 or text[cursor - 1] == "\n") and first_line_re.match(
            text[cursor:]
        ):
            lines, new_cursor = get_toc_pages(text, cursor)
        if lines:
            brl = make_toc(lines)
            # do not suck in table
            if re.findall("\u2810\u2812+\u2800+\u2810+\u2812+", brl):
                brl = ""
            # if re.search(r"\u2810{3,}", brl):
            # brl = ""
        return (
            DetectionResult(new_cursor, state, 0.91, f"{output_text}{brl}\n")
            if brl
            else None
        )

    return detect_toc



# detect lists
def create_list_detector(
    layout:PageLayout,
    paragraph_indent:int=2,
    block_paragraph_indent=0,
    run_over:int=0,
    ) -> Detector:
    """Creates a detector for finding lists"""
    first_line_re = re.compile("([\u2801-\u28ff][\u2800-\u28ff]*)\n")
    run_over_re = re.compile(
        "(\u2800{2}|\u2800{4}|\u2800{6}|\u2800{8}"
        "|\u2800{10}|\u2800{12}|\u2800{14})"
        "([\u2801-\u28ff][\u2800-\u28ff]*)\n"
    )

    list_processing_instruction_re = re.compile(
        f"((?:{_BLANK_LINE_RE}\n)|(?:{_BRAILLE_PAGE_RE}\n)"
        f"|(?:{_BRAILLE_PPN_RE}\n)|(?:{_PRINT_PAGE_RE}\n)"
        f"|(?:{_RUNNING_HEAD_RE}\n))"
    )

    min_indent = 3
    heading_re = re.compile(
        f"(\u2800{{{min_indent},}})([\u2801-\u28ff][\u2800-\u28ff]*)\n+",
    )

    def join_list(lines: list[ParsedLine]) -> str:
        """
        join lists
        """
        list_head = '\n<ul style="list-style-type: none">'
        list_tail = "</ul>"
        list_str = f"{list_head}\n"
        for line in lines:
            if line.pi:
                list_str += f"{line.pi.strip()}\n"
            if line.line_text:
                list_str += f"<li>{line.line_text}</li>\n"
        list_str += f"{list_tail}\n"
        return list_str

    def build_list(
        lines: list[ParsedLine],
        index: int,
        length: int,
        levels: list[int],
        current_level: int,
    ) -> list:
        """Recursive list builder, preserving processing instructions and supporting nested lists"""
        list_level = [lines[index].copy()]
        original_index = index
        index += 1

        while index < length:
            if lines[index].depth == -1:  # Always include processing instructions
                list_level[-1].line_text += lines[index].pi
                index += 1
            elif (
                lines[index] and lines[index].depth > current_level
            ):  # Check for deeper nested structure
                nested_index_diff, nested_html = build_list(
                    lines, index, length, levels, lines[index].depth
                )
                sp = ""
                if not nested_html.startswith("</ul"):
                    sp = "\u2800"
                list_level[-1].line_text += sp + nested_html
                index += nested_index_diff
            elif (
                lines[index].depth < current_level and lines[index].depth != -1
            ):  # Check for return to a shallower
                break
            else:
                list_level.append(lines[index].copy())  # Normal list entry
                index += 1

        # At deepest level, check if it's a block paragraph
        if current_level >= levels[-1] and is_block_paragraph(
            list_level, current_level, layout.cells_per_line
        ):
            joined = "".join(
                f"{line.pi}\u2800{line.line_text}" if line.pi else line.line_text
                for line in list_level
            )
            return [index - original_index, re.sub(r"[\u2800]{2,}", "\u2800", joined)]

        # Otherwise, render HTML list, preserving PI lines
        joined = join_list(list_level)
        return [index - original_index, re.sub(r"[\u2800]{2,}", "\u2800", joined)]

    def make_list(lines: list[ParsedLine]) -> str:
        """Make a list or nested list"""

        # create clean set of levels acending
        levels = list({level.depth for level in lines if level.depth != -1})

        # one level list
        if len(levels) == 1:
            return join_list(lines)

        #  nested list or over run list
        _, brl_str = build_list(lines, 0, len(lines), levels, 0)
        return brl_str

    def match_list_line(current_line: str) -> ParsedLine | None:
        """Match lines if they are possibly part of a list"""
        if line := first_line_re.match(current_line):
            return ParsedLine(0, "", line.group(1), line.end())

        if line := run_over_re.match(current_line):
            return ParsedLine(len(line.group(1)), "", line.group(2), line.end())

        return None
    
    def check_block_paragraph_before_indent(
        lines: list[ParsedLine],
        paragraph_indent: int,
        cells_per_line: int,
    ) -> tuple[list[ParsedLine], int]:
        """Check if lines before the first paragraph_indent-depth line form a block paragraph.

        If a line with depth == paragraph_indent is found, checks whether the lines before
        that point form a block paragraph.

        Returns (block_lines, cursor_offset) where block_lines are the lines up to (not
        including) the first paragraph_indent line and cursor_offset is the sum of their
        .end values (to be added to the caller's cursor).  Returns ([], 0) if no block
        is found or the condition is not met.
        """
        if not lines:
            return ([], 0)

        _lines = [line for line in lines if line.depth != -1]
        if _lines[0].depth >= paragraph_indent:
            return ([], 0)
        first_indent_index = next(
            (index for index, level in enumerate(_lines) if level.depth >= paragraph_indent),
            len(_lines),
        )
        indent_found = first_indent_index < len(_lines)

        candidate_lines = _lines[:first_indent_index]
        if is_block_paragraph(
            candidate_lines, depth=0, cells_per_line=cells_per_line
        ):
            if indent_found:
                first_indent_index_full = next(
                    (index for index, level in enumerate(lines) if level.depth >= paragraph_indent),
                    len(lines),
                )
            else:
                first_indent_index_full = len(lines)
            block_lines = lines[:first_indent_index_full]
            cursor_offset = sum(line.end for line in block_lines)
            return (block_lines, cursor_offset)

        return ([], 0)



    _braille_page_capture_re = re.compile("(?:<\\?braille-page([ \u2800-\u28ff]*)\\?>)")
    _braille_ppn_capture_re = re.compile("(?:<\\?braille-ppn([ \u2800-\u28ff]*)\\?>)")

    def get_list_pages(
        text: str, cursor_offset: int, debug: int = 0
    ) -> tuple[list[ParsedLine], int]:
        """
        get list pages
        return lines and cursor to add to text
        """
        new_cursor = cursor_offset
        new_lines: list[ParsedLine] = []

        # consume PI
        #set is_first if braille-page or braille-ppn to know if need to add spaces to first line
        _blank_lines : int = 0
        is_first=False
        has_running_head = False
        page_dict: dict[str, str] = {}
        while line := list_processing_instruction_re.match(text[new_cursor:]):
            if line.group(1) == "<?blank-line?>\n":
                _blank_lines += 1
            if line.group(1).startswith("<?braille-page")  or line.group(1).startswith("<?braille-ppn"):
                is_first = True
            elif line.group(1).startswith("<?running-head"):    
                has_running_head = True
            # more than one blank line this is a hard stop
            if _blank_lines > 1:
                return ([], cursor_offset)
            new_lines.append(ParsedLine(-1, line.group(1), "", line.end()))
            new_cursor += line.end()

        # last item is a blank line stop
        if new_lines and new_lines[-1].pi == "<?blank-line?>\n":
            return ([], cursor_offset)

        page_dict = build_lines_pi(text, new_cursor)
        right_page_lengths = get_top_and_bottom_page_length(page_dict, layout)
        line_match : ParsedLine|None =None

        # if a blank line and either the page length bottom is 0 or the last line is a print page this is a hard stop because blank line should only be used for spacing and if there is no bottom page length or a print page then it is not doing spacing
        if _blank_lines ==  1 and (
            right_page_lengths.bottom==0 
            or  new_lines[-1].pi == "<?print-page?>\n"
            ):
            return ([], cursor_offset)
        
        line_match = match_list_line(text[new_cursor:])
        if line_match and is_first and not has_running_head:
            line_match.line_text= " " *line_match.depth +line_match.line_text+ " " * (right_page_lengths.top + 3) if right_page_lengths.top else ""
            if _blank_lines ==  1 and len(line_match.line_text) <=  layout.cells_per_line:
                return ([], cursor_offset)



        # if centered heading stop and return [[], 0]
        center_line = heading_re.match(text[new_cursor:])
        # test with out center just any heading
        if center_line:
            return ([], cursor_offset)

        if line_match:
            new_lines.append(line_match)
            new_cursor += line_match.end

        # consume all legal list items until does not match.
        # if first line and has page_length then add spaces
        while line := match_list_line(text[new_cursor:]):
            new_lines.append(line)
            new_cursor += line.end

        _block = [line for line in new_lines if line.depth != -1]
        if not _block:
            return ([], cursor_offset)

        # fail if any has 1 set of guide dots rows or a table divider. and return
        if is_toc_or_table_line(new_lines):
            return ([], cursor_offset)  
        
        # if first line depth is paragraph_indent or block_paragraph_indent and
        _block[0] = _block[0].copy()
        if _block[0].depth == paragraph_indent:
            _block[0].depth=run_over
            
        # if last line length is less than cells per line and page number then add remaining spaces
        line = list_processing_instruction_re.match(text[new_cursor:])
        if line and right_page_lengths.bottom and line.group(1) not in ["<?blank-line?>\n", "<?print-page?>\n"]:
            new_lines[-1].line_text += " " * (right_page_lengths.bottom + 3)+ " " *new_lines[-1].depth

        first_check = is_block_paragraph(_block, depth=run_over, cells_per_line=layout.cells_per_line   )
        temp_list = get_list_pages(text, new_cursor, debug + 1)
        if not temp_list[0]:
            return (new_lines,new_cursor)
        elif first_check:# and not is_block_paragraph(temp_list[0], depth=run_over, cells_per_line=layout.cells_per_line):
            _block_list  =check_block_paragraph_before_indent(temp_list[0], paragraph_indent, layout.cells_per_line)
            if _block_list[0]:
                new_lines.extend(_block_list[0])
                new_cursor += _block_list[1]
            return (new_lines, new_cursor)  
        elif first_check==is_block_paragraph(temp_list[0], depth=run_over, cells_per_line=layout.cells_per_line): 
            new_lines.extend(temp_list[0])
            return (new_lines, temp_list[1])

        return (new_lines, temp_list[1])

    def detect_list(
        text: str, cursor: int, state: DetectionState, output_text: str
    ) -> DetectionResult | None:
        brl = ""
        lines: list[ParsedLine] = []
        new_cursor = cursor
        if (cursor == 0 or text[cursor - 1] == "\n") and first_line_re.match(
            text[cursor:]
        ):
            lines, new_cursor = get_list_pages(text, cursor)

        confidence = 0.9
        levels = list({level.depth for level in lines if level.depth != -1})
        while not all(level == index * 2 for index, level in enumerate(levels)):
            new_cursor -= lines[-1].end
            lines = lines[:-1]
            levels = list({level.depth for level in lines if level.depth != -1})
        if lines:
            # must be a paragraph if wraps
            _lines = [line for line in lines if line.depth != -1]
            # if all lines before the first level 2 is wrapped like a paragraph ignore -1 depth
            first_level_2_index = next(
                (index for index, level in enumerate(_lines) if level.depth == 2),
                len(_lines),
            )
            if len(_lines[:first_level_2_index]) > 1 and is_block_paragraph(
                _lines[:first_level_2_index], depth=0, cells_per_line=layout.cells_per_line
            ):
                # if len(_lines[:first_level_2_index]) > 1 and
                # detect_paragraph_wrapping(_lines[:first_level_2_index], cells_per_line, depth=0):
                # if not detect_paragraph_wrapping(
                #     _lines[first_level_2_index-1:first_level_2_index+1],
                #     cells_per_line, depth=0) and
                #     detect_paragraph_wrapping(
                #     _lines[:first_level_2_index], cells_per_line, depth=0):

                #  probably block paragraph
                first_level_2_index = next(
                    (index for index, level in enumerate(lines) if level.depth == 2),
                    len(lines),
                )
                new_cursor = cursor + sum(
                    line.end for line in lines[:first_level_2_index]
                )
                brl = (
                    "<p  class='left-justified'>"
                    + "\n".join(
                        [
                            f"{line.pi}{line.line_text}".strip(" ").lstrip("\u2800")
                            for line in lines[:first_level_2_index]
                        ]
                    )
                    + "</p>"
                )

            if not brl:
                brl = make_list(lines)

        return (
            DetectionResult(new_cursor, state, confidence, f"{output_text}{brl}\n")
            if brl
            else None
        )

    return detect_list
