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
        table: list[str | list[str]] = ["<tr>"]
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
        while end_cursor := get_line(text, cursor):
            line = text[cursor : cursor + end_cursor].rstrip("\n")
            if line.startswith("\u2800\u2800"):
                # Runover: split gives an empty first element before the leading separator
                cells = line.split("\u2800\u2800")
                for col_idx, cell in enumerate(cells[1:]):
                    if col_idx < len(col_widths):
                        cell_strip = cell.strip("\u2800\u2810")
                        if cell_strip:
                            if table[row][col_idx]:
                                table[row][col_idx] += "\u2800" + cell_strip
                            else:
                                table[row][col_idx] = cell_strip
            else:
                table.append([""] * len(col_widths))
                row += 1
                cells = line.split("\u2800\u2800")
                for col_idx, cell in enumerate(cells):
                    if col_idx < len(col_widths):
                        table[row][col_idx] = cell.strip("\u2800\u2810")
            cursor += end_cursor

        complete_table = table[0] + "\n"
        complete_table += wrap_and_join(
            "<tr>{}</tr>\n", [wrap_and_join("<td>{}</td>", row) for row in table[1:]]
        )
        complete_table = f"<table>\n{complete_table}\n</table>"
        return DetectionResult(cursor, state, 0.91, f"{output_text}{complete_table}\n")

    return detect_table
