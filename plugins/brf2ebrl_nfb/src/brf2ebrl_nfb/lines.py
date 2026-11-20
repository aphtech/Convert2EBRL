#  Copyright (c) 2026. American Printing House for the Blind.
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.
"""Joining the BRF lines of one block, and telling a wrapped line from a deliberate line break."""
from collections.abc import Sequence

_HYPHEN = "\u2824"
# Dot 5 at the end of a line is the continuation indicator of a long item such as a web address.
_CONTINUATION = "\u2810"


def join_lines(lines: Sequence[str], separator: str = "\n") -> str:
    """Join the lines of a block with separator, which becomes a space in the eBraille text.

    A line ending in a hyphen or dash joins the next line with no space, and a line ending in the
    continuation indicator (dot 5, but not guide dots) loses it and joins with no space. Processing
    instructions (items starting "<?") are kept in place but never separate words."""
    result = ""
    pending_pis = ""
    has_text = False
    for line in lines:
        if line.startswith("<?"):
            pending_pis += line
            continue
        if not has_text:
            result += pending_pis + line
        elif result.endswith(_HYPHEN):
            result += pending_pis + line
        elif ends_with_continuation(result):
            result = result[:-1] + pending_pis + line
        else:
            result += separator + pending_pis + line
        pending_pis = ""
        has_text = True
    return result + pending_pis


def ends_with_continuation(line: str) -> bool:
    """The line ends in the continuation indicator (dot 5), not in guide dots."""
    return line.endswith(_CONTINUATION) and not line.endswith(_CONTINUATION * 2)


def first_word(line: str) -> str:
    return line.lstrip("\u2800").split("\u2800", 1)[0]


def wraps(width: int, next_line: str, cells_per_line: int, slack: int = 0) -> bool:
    """A line of width cells was wrapped: the next line's first word would not have fitted on it.

    Transcribers do not always fill a line, so slack cells can be allowed for."""
    return width + 1 + len(first_word(next_line)) > cells_per_line - slack
