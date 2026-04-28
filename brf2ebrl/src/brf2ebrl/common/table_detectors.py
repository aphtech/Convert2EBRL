#  Copyright (c) 2024. American Printing House for the Blind.
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""Detectors for tables."""

import re
from collections.abc import Iterable

from brf2ebrl.parser import DetectionState, DetectionResult, Detector


def create_table_detector() -> Detector:
    """Creates a detector for finding simple tables more can be added"""
    seperator_re = re.compile(
        "((?:[\u2800-\u28ff]+?\n){1,2})(\u2810\u2812+?(?:\u2800\u2800\u2810\u2812+?)+?)\n"
    )

    def get_line(brf_text: str, pos: int) -> int | None:
        """Gets each line after table header that matches table rows"""
        nl_pos = brf_text[pos:].find("\n")
        if nl_pos < 0:
            return None
        line = brf_text[pos : pos + nl_pos + 1]
        if re.match(r"^[\u2801-\u28ff]", line) or line.startswith("\u2800\u2800"):
            return nl_pos + 1
        return None

    def wrap_and_join(fmt: str, items: Iterable[str]) -> str:
        """Wraps each element and joins into a single string."""
        return "".join(fmt.format(s) for s in items)

    def split_row_by_width(line: str, widths: list[int]) -> list[str]:
        """Split row text using measured column boundaries."""
        cells: list[str] = []
        start = 0
        for index, width in enumerate(widths):
            next_start = start + width + 2
            if index < len(widths) - 1:
                cell = line[start:next_start]
            else:
                cell = line[start:]
            cells.append(cell.strip("\u2800\u2810"))
            start = next_start
        return cells

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
        header_row = "<tr>"
        table_rows: list[list[str]] = []
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
                header_row += cell_text
        else:
            header_row += wrap_and_join(
                "<th>{}</th>",
                [
                    cell.strip("\u2800")
                    for cell in header_lines[0].split("\u2800\u2800")
                ],
            )
        header_row += "</tr>"
        # header done

        cursor += match.end(2) + 1
        # cells
        row = 0
        while end_cursor := get_line(text, cursor):
            line = text[cursor : cursor + end_cursor].rstrip("\n")
            if line.startswith("\u2800\u2800"):
                cells = split_row_by_width(line, col_widths)
                for col_idx, cell in enumerate(cells):
                    if cell and row > 0:
                        if table_rows[row - 1][col_idx]:
                            table_rows[row - 1][col_idx] += "\u2800" + cell
                        else:
                            table_rows[row - 1][col_idx] = cell
            else:
                table_rows.append([""] * len(col_widths))
                row += 1
                cells = split_row_by_width(line, col_widths)
                for col_idx, cell in enumerate(cells):
                    table_rows[row - 1][col_idx] = cell
            cursor += end_cursor

        complete_table = header_row + "\n"
        complete_table += wrap_and_join(
            "<tr>{}</tr>\n",
            [wrap_and_join("<td>{}</td>", row_cells) for row_cells in table_rows],
        )
        complete_table = f"<table>\n{complete_table}\n</table>"
        return DetectionResult(cursor, state, 0.91, f"{output_text}{complete_table}\n")

    return detect_table

def create_listed_detector() -> Detector:
    """Creates a detector for listed table format tables (BANA 11.16)."""

    # Matches a row-heading line: 4+ leading blank cells, then header text, separator (3, :, or full-cell), spaces, and value text
    row_heading_re = re.compile(
        rf"^[\u2800]{{4,}}(?P<header>[^\u2800\n].*?)(?P<sep>[3:\u2812])[\u2800]+(?P<value>[^\u2800\n].*)\n?$"
    )
    # Matches a column line: header text starting at left margin, separator, spaces, and value text
    column_re = re.compile(
        rf"^(?P<header>[^\u2800\n].*?)(?P<sep>[3:\u2812])[\u2800]+(?P<value>[^\u2800\n].*)\n?$"
    )
    # Matches a runover continuation line: 2+ leading blank cells followed by non-blank text
    runover_re = re.compile(rf"^[\u2800]{{2,}}(?P<value>[^\u2800\n].*)\n?$")

    def get_line(brf_text: str, pos: int) -> tuple[str, int] | None:
        """Gets the next line of text starting at pos, or None if at end of text."""
        if pos >= len(brf_text):
            return None
        nl_pos = brf_text.find("\n", pos)
        if nl_pos < 0:
            return brf_text[pos:], len(brf_text)
        return brf_text[pos : nl_pos + 1], nl_pos + 1

    def is_inter_row_line(line: str) -> bool:
        """Lines that can appear between table rows without ending the table (blank lines and page number PIs)."""
        return line in {
            "<?blank-line?>\n",
            "<?blank-line?>",
        } or line.startswith("<?braille-page") or line.startswith(
            "<?braille-ppn"
        ) or line.startswith("<?print-page")

    def is_boundary_line(line: str) -> bool:
        """A div tag marks the boundary of a container element, signalling the table has ended."""
        stripped = line.strip(" \u2800\n")
        return stripped.startswith("<div") or stripped.startswith("</div")

    def is_rule_line(line: str) -> bool:
        """A separator rule is a long line composed entirely of one repeated character (e.g. full-cell dots)."""
        stripped = line.strip(" \u2800\n")
        return len(stripped) >= 8 and len(set(stripped)) == 1

    def parse_row(
        brf_text: str,
        pos: int,
        expected_headers: list[str] | None,
        separator: str | None,
        join_space: str,
    ) -> tuple[list[str], list[str], str, int] | None:
        """Parses a row starting at pos, returning headers, values, separator, and new position if successful, or None if not a valid row."""
        first_line = get_line(brf_text, pos)
        if not first_line:
            return None
        line, pos = first_line
        # The first line of a row must match the indented row-heading pattern
        row_match = row_heading_re.match(line)
        if not row_match:
            return None
        # All rows in the same table must use the same separator character
        if separator and row_match.group("sep") != separator:
            return None

        headers = [row_match.group("header").strip("\u2800")]
        values = [row_match.group("value").strip("\u2800")]
        separator = row_match.group("sep") or ""

        # Read subsequent lines belonging to this row
        while next_line := get_line(brf_text, pos):
            line, next_pos = next_line
            # Stop collecting lines when a row/table boundary is encountered
            if (
                is_inter_row_line(line)
                or is_boundary_line(line)
                or is_rule_line(line)
                or row_heading_re.match(line)
            ):
                break

            # A column line adds another header/value pair to the current row
            if col_match := column_re.match(line):
                if col_match.group("sep") != separator:
                    return None
                headers.append(col_match.group("header").strip("\u2800"))
                values.append(col_match.group("value").strip("\u2800"))
                pos = next_pos
                continue

            # A runover line appends continuation text to the last cell value
            if runover_match := runover_re.match(line):
                if not values:
                    return None
                runover = runover_match.group("value").strip("\u2800")
                if runover:
                    values[-1] = f"{values[-1]}{join_space}{runover}" if values[-1] else runover
                    pos = next_pos
                    continue
            # Any unrecognised line means this is not a valid listed-table row
            return None

        # A valid row must have at least two fields
        if len(headers) < 2:
            return None
        # Subsequent rows must share the exact same column headers as the first row
        if expected_headers and headers != expected_headers:
            return None
        return headers, values, separator, pos

    def wrap_and_join(fmt: str, items: Iterable[str]) -> str:
        return "".join(fmt.format(item) for item in items)

    def consume_inter_row_lines(brf_text: str, pos: int) -> tuple[int, str]:
        consumed: list[str] = []
        while current := get_line(brf_text, pos):
            line, next_pos = current
            if is_inter_row_line(line):
                consumed.append(line)
                pos = next_pos
                continue
            break
        return pos, "".join(consumed)

    def detect_listed_table(
        text: str, cursor: int, state: DetectionState, output_text: str
    ) -> DetectionResult | None:
        # Use braille blank cell as the join space when the source text is braille, otherwise plain space
        join_space = "\u2800" if "\u2800" in text else " "
        pos = cursor

        # Skip any leading blank/page-number lines before the first row
        pos, leading_pi = consume_inter_row_lines(text, pos)

        # The first row establishes the column headers and separator character for the table
        first_row = parse_row(text, pos, None, None, join_space)
        if not first_row:
            return None

        headers, values, separator, pos = first_row
        rows = [values]
        inter_row_pis: list[str] = []  # PI strings that appear between rows (preserved in output)
        trailing_pi = ""

        # Collect additional rows, stopping at any boundary or unrecognised content
        while True:
            pos, gap_pi = consume_inter_row_lines(text, pos)

            current = get_line(text, pos)
            if not current:
                # End of text: any gap PIs become trailing content after the table
                trailing_pi += gap_pi
                break
            line, _ = current
            if is_boundary_line(line) or is_rule_line(line):
                # A div boundary or separator rule marks the end of the table
                trailing_pi += gap_pi
                break

            next_row = parse_row(text, pos, headers, separator, join_space)
            if not next_row:
                # Row doesn't match the established structure — table ends here
                trailing_pi += gap_pi
                break

            _, row_values, _, pos = next_row
            inter_row_pis.append(gap_pi)
            rows.append(row_values)

        # Require at least two data rows to emit a table (single-row match is likely a false positive)
        if len(rows) < 2:
            return None

        # Assemble the HTML table, interleaving preserved PI strings between rows
        complete_table = f'{leading_pi}<table class="listed">\n'
        complete_table += f"<tr>{wrap_and_join('<th>{}</th>', headers)}</tr>\n"
        complete_table += f"<tr>{wrap_and_join('<td>{}</td>', rows[0])}</tr>\n"
        for idx, row in enumerate(rows[1:], start=1):
            complete_table += inter_row_pis[idx - 1]
            complete_table += f"<tr>{wrap_and_join('<td>{}</td>', row)}</tr>\n"
        complete_table += "</table>"
        complete_table += trailing_pi
        return DetectionResult(pos, state, 0.90, f"{output_text}{complete_table}\n")

    return detect_listed_table

