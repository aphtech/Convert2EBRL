#  Copyright (c) 2026. American Printing House for the Blind.
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.
"""NFB Braille Monitor specific components for processing BRF.

The pipeline is the BANA one with the passes the newsletter does not need removed
(print page numbers, running heads) and NFB specific block detectors added. Nothing
here changes the shared detectors, so BANA conversions are unaffected."""
import string
from dataclasses import replace
from typing import Sequence

from brf2ebrl.common import PageLayout, PageNumberPosition
from brf2ebrl.common.block_detectors import create_cell_heading, create_paragraph_detector, \
    detect_pre, create_list_detector
from brf2ebrl.common.box_line_detectors import remove_box_lines_processing_instructions, tag_boxlines
from brf2ebrl.common.detectors import detect_and_pass_processing_instructions, \
    xhtml_fixup_detector, translate_ascii_to_unicode_braille, convert_blank_lines_to_processing_instructions
from brf2ebrl.common.emphasis_detectors import tag_emphasis
from brf2ebrl.common.graphic_detectors import create_pdf_graphic_detector
from brf2ebrl.common.nemeth_detectors import detect_block_nemeth, detect_and_pass_nemeth_block, \
    tag_inline_nemeth, restore_nemeth_braille
from brf2ebrl.common.page_numbers import create_ebrf_print_page_tags
from brf2ebrl.common.selectors import most_confident_detector
from brf2ebrl.common.table_detectors import create_listed_detector, create_table_detector, create_column_row_detector
from brf2ebrl.common.volume_markers import remove_volume_markers
from brf2ebrl.parser import detector_parser, Parser, ParserContext
from brf2ebrl.plugin import create_plugin
from brf2ebrl_bana.tn_detectors import tn_indicators_block_matcher, tag_inline_tn, tag_symbols_list_tn

from brf2ebrl_nfb.bundler import NfbZippedBundler
from brf2ebrl_nfb.detectors import create_nfb_block_detectors, mark_article_separators
from brf2ebrl_nfb.pages import create_nfb_braille_page_detector

PLUGIN_ID = "NFB"


def nfb_page_layout(page_layout: PageLayout) -> PageLayout:
    """The Braille Monitor always numbers odd braille pages top right and has no print page numbers.

    Force those positions so a GUI profile or CLI layout meant for books cannot break page detection.
    The page size still comes from the caller."""
    return replace(page_layout,
                   odd_braille_page_number=PageNumberPosition.TOP_RIGHT,
                   even_braille_page_number=PageNumberPosition.NONE,
                   odd_print_page_number=PageNumberPosition.NONE,
                   even_print_page_number=PageNumberPosition.NONE)


def create_brf2ebrl_parser(
        page_layout: PageLayout = PageLayout(),
        brf_path: str = "",
        output_path: str = "",
        images_path: str = "",
        detect_running_heads: bool = True,
        parser_context: ParserContext = ParserContext(),
        *args,
        **kwargs
) -> Sequence[Parser]:
    # The newsletter has no running heads, so detect_running_heads is ignored.
    page_layout = nfb_page_layout(page_layout)
    return [
        x
        for x in [
            Parser(
                "Ensure only valid BRF ASCII, eg. control characters",
                lambda x, _: "".join(c for c in x if c in string.printable)
            ),
            Parser(
                "Transform to uppercase ASCII",
                lambda x, _: x.upper()
            ),
            Parser(
                "Convert to unicode Braille",
                translate_ascii_to_unicode_braille
            ),
            Parser(
                "Remove volume markers",
                remove_volume_markers
            ),
            detector_parser(
                "Detect Braille pages",
                {"start_braille_page": True, "page_count": 1},
                [
                    create_nfb_braille_page_detector(page_layout),
                    detect_and_pass_processing_instructions,
                ],
                most_confident_detector,
            ),
            Parser(
                "Remove form feeds",
                lambda text, _: text.replace("\f", "")
            ),
            Parser(
                "Detect blank lines",
                convert_blank_lines_to_processing_instructions
            ),
            Parser(
                "Convert box lines to div tags",
                tag_boxlines
            ),
            Parser(
                "Mark NFB article separators",
                mark_article_separators
            ),
            detector_parser(
                "Detect Nemeth",
                {},
                [
                    detect_block_nemeth,
                    detect_and_pass_processing_instructions,
                ],
                most_confident_detector,
            ),
            detector_parser(
                "Detect blocks",
                {},
                [
                    detect_and_pass_nemeth_block,
                    *create_nfb_block_detectors(page_layout, parser_context),
                    create_cell_heading(6, "h3", parser_context),
                    create_cell_heading(4, "h2", parser_context),
                    create_paragraph_detector(
                        first_line_indent=6,
                        run_over=4,
                        layout=page_layout,
                        indicator_matcher=tn_indicators_block_matcher,
                        confidence=0.95,
                    ),
                    create_paragraph_detector(
                        first_line_indent=2,
                        run_over=0,
                        layout=page_layout,
                        confidence=0.9,
                    ),
                    create_list_detector(
                        layout=page_layout,
                        paragraph_indent=2,
                        block_paragraph_indent=0,
                        run_over=0
                    ),
                    create_column_row_detector(),
                    create_listed_detector(),
                    create_table_detector(),
                    detect_pre,
                    detect_and_pass_processing_instructions,
                ],
                most_confident_detector,
            ),
            Parser(
                "Remove  box lines processing instructions",
                remove_box_lines_processing_instructions
            ),
            Parser(
                "Detecting inline TNs",
                tag_inline_tn
            ),
            Parser(
                "Detecting inline Nemeth",
                tag_inline_nemeth
            ),
            Parser(
                "Detect TN symbols lists",
                tag_symbols_list_tn
            ),
            Parser(
                "Convert Emphasis",
                tag_emphasis
            ),
            Parser(
                "Restore Nemeth braille",
                restore_nemeth_braille
            ),
            _create_image_detection_parser_pass(brf_path, images_path, output_path, page_layout),
            detector_parser(
                "Print page numbers to ebrf",
                {},
                [create_ebrf_print_page_tags()],
                most_confident_detector,
            ),
            Parser(
                "Remove processing instructions.",
                lambda x, _: "".join(part.split("?>", 1)[1] if "?>" in part else part for part in x.split("<?"))
            ),
            Parser(
                "Make complete XML",
                xhtml_fixup_detector
            ),
            Parser(
                "Convert u+2800 to regular space as per ebraille standard",
                lambda x, _: x.replace("\u2800", " ")
            )
        ]
        if x is not None
    ]


def _create_image_detection_parser_pass(brf_path, images_path, output_path, page_layout: PageLayout) -> Parser | None:
    if images_path and (image_detector := create_pdf_graphic_detector(brf_path, output_path, images_path, page_layout)):
        return Parser(
            "Convert PDF to single files and links",
            image_detector
        )
    return None


PLUGIN = create_plugin(plugin_id=PLUGIN_ID, name="Convert NFB Braille Monitor BRF to eBraille",
                       brf_parser_factory=create_brf2ebrl_parser,
                       file_mapper=lambda input_file, index: f"vol{index}.html",
                       bundler_factory=NfbZippedBundler)
