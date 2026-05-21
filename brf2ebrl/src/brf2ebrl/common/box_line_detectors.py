#  Copyright (c) 2024. American Printing House for the Blind.
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""Detectors for Box lines"""
import re
import logging

from brf2ebrl import ParserContext
from brf2ebrl.parser import DetectionState, DetectionResult, NotifyLevel

# Define the regular expression patterns
_ENCLOSING_RE = re.compile(
    r"(?:([\u2801-\u28ff]+?)\u2800)*?(\u283f{10,})(.+?)(\u283f{10,})", re.DOTALL
)
_BOX_RE = re.compile(
    r"(?:([\u2801-\u28ff]+?)\u2800)*?(\u2836{10,})(.+?)(\u281b{10,})", re.DOTALL
)
_BOX_LINES_PROCESSING_INSTRUCTION_RE = re.compile(R"<\?box ([\u2800-\u28ff]+)\?>")
_ORPHAN_TOP_RE = re.compile(r"^\u2836{10,}$", re.MULTILINE)
_ORPHAN_BOTTOM_RE = re.compile(r"^\u281b{10,}$", re.MULTILINE)
_ORPHAN_EXT_RE = re.compile(r"^\u283f{10,}$", re.MULTILINE)


def _report_orphans(text: str, pattern: re.Pattern, label: str, ctx: ParserContext):
    for m in pattern.finditer(text):
        line_num = text.count("\n", 0, m.start()) + 1
        #ctx.notify_str(NotifyLevel.WARN, f"Unmatched {label} box line at line {line_num}")
        logging.warning(f"Unmatched {label} box line at line {line_num}")


def _convert_groups(match):
    """regular expression group substitution function"""
    if match.group(1):
        return (
                f'<div screen_type="<?box {match.group(1)}?>" type="<?box '
                + f'{match.group(2)[0]}?>">{match.group(3)}</div>'
        )
    return f'<div type="<?box {match.group(2)[0]}?>">{match.group(3)}</div>'


def convert_box_lines(
        text: str, _: int, state: DetectionState, output_text: str
) -> DetectionResult | None:
    """
    converts all box and screen material to their div equivlant or returns None if not a box line

    Arguments:
    - text of the file

    Returns:
    - The changed file worth of text in a detection result

    """
    return DetectionResult(
        len(text),
        state,
        1.0,
        output_text
        + tag_boxlines(text)
    )


def tag_boxlines(text: str, parser_context: ParserContext = ParserContext()) -> str:
    result = _ENCLOSING_RE.sub(_convert_groups, _BOX_RE.sub(_convert_groups, text))
    _report_orphans(result, _ORPHAN_TOP_RE, "top (7)", parser_context)
    _report_orphans(result, _ORPHAN_BOTTOM_RE, "bottom (g)", parser_context)
    _report_orphans(result, _ORPHAN_EXT_RE, "exterior border (=)", parser_context)
    return result


def remove_box_lines_processing_instructions(text: str, _: ParserContext = ParserContext()):
    return _BOX_LINES_PROCESSING_INSTRUCTION_RE.sub(lambda m: m.group(1), text)
