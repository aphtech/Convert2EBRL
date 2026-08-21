#  Copyright (c) 2024. American Printing House for the Blind.
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from brf2ebrl.common.block_detectors import (
    create_cell_heading,
    create_centered_detector,
    create_toc_detector,
)
from brf2ebrl.common.detectors import translate_ascii_to_unicode_braille


def test_create_cell_heading_detects_correctly_indented_heading_with_high_confidence():
    content = translate_ascii_to_unicode_braille(",REMEMB]")
    text = "⠀" * 4 + content + "\n"

    detector = create_cell_heading(4, "h2")
    result = detector(text, 0, {}, "")

    assert result is not None
    assert result.confidence == 0.9
    assert result.text == f"<h2>{content}</h2>\n"


def test_create_cell_heading_detects_off_by_one_indent_with_lower_confidence():
    # Regression: a transcriber sometimes mistakes the cell number for a
    # count of blanks to insert before the text, e.g. work/cell_5_bad.brf
    # line 653's ",,REMEMB]" starting in cell 6 (5 leading blanks) instead
    # of the correct cell 5 (4 leading blanks). Still recognized as a
    # heading, but with lower confidence so a correctly indented heading
    # (or another detector) wins when both are possible.
    content = translate_ascii_to_unicode_braille(",REMEMB]")
    text = "⠀" * 5 + content + "\n"

    detector = create_cell_heading(4, "h2")
    result = detector(text, 0, {}, "")

    assert result is not None
    assert result.confidence == 0.6
    assert result.text == f"<h2>{content}</h2>\n"


def test_create_cell_heading_does_not_match_indent_further_than_off_by_one():
    content = translate_ascii_to_unicode_braille(",REMEMB]")
    text = "⠀" * 6 + content + "\n"

    detector = create_cell_heading(4, "h2")
    result = detector(text, 0, {}, "")

    assert result is None


def test_create_centered_detector_detects_off_by_one_indent_with_lower_confidence():
    # Regression: work/center_bad.brf line 359's ",,FAMILY ,,MA?" starts one
    # cell later than the centered formula (floor((page_width-text_width)/2)+1)
    # requires -- the transcriber mistake of treating the cell number as a
    # blank-count. Still recognized as centered text, but with lower
    # confidence.
    cells_per_line = 40
    brl_content = translate_ascii_to_unicode_braille(",,FAMILY ,,MA?")
    correct_indent = (cells_per_line - len(brl_content)) // 2
    text = "⠀" * (correct_indent + 1) + brl_content + "\n<?blank-line?>\n"

    detector = create_centered_detector(cells_per_line, 3, "h1")
    result = detector(text, 0, {}, "")

    assert result is not None
    assert result.confidence == 0.6
    assert result.text == f"<h1>{brl_content}</h1>\n"


def test_create_centered_detector_detects_correctly_indented_text_with_high_confidence():
    cells_per_line = 40
    brl_content = translate_ascii_to_unicode_braille(",,FAMILY ,,MA?")
    correct_indent = (cells_per_line - len(brl_content)) // 2
    text = "⠀" * correct_indent + brl_content + "\n<?blank-line?>\n"

    detector = create_centered_detector(cells_per_line, 3, "h1")
    result = detector(text, 0, {}, "")

    assert result is not None
    assert result.confidence == 0.9
    assert result.text == f"<h1>{brl_content}</h1>\n"


def test_create_centered_detector_detects_multi_word_guide_words_without_dash():
    # Regression: guide words are any centered text on the last line of a page
    # (see BANA Formats 2016, section 21), not only hyphenated pairs. A page
    # with a single new main entry has guide words with no dash and can
    # contain spaces, e.g. "ADJAC5T ANGLES".
    cells_per_line = 40
    content = "ADJAC5T ANGLES"
    indent = (cells_per_line - len(content)) // 2
    brl_content = translate_ascii_to_unicode_braille(content)
    text = "⠀" * indent + brl_content + "\n<?braille-page ?>\n"

    detector = create_centered_detector(cells_per_line, 3, "h1")
    result = detector(text, 0, {}, "")

    assert result is not None
    assert result.text == f"<!-- guide words {brl_content} -->\n"


def test_create_toc_detector_continues_after_multiple_blank_lines_before_page_break():
    # Regression: a TOC entry landing right after a page turn preceded by more
    # than one blank line of page-bottom spacing (e.g. three "<?blank-line?>"
    # PIs before "<?braille-page?>") was being dropped from the TOC and left
    # as unparsed preformatted text (see BANA Formats 2016, section 2.10, on
    # continuing TOCs across a page break).
    cells_per_line = 40
    heading = translate_ascii_to_unicode_braille(",TOPIC\n")
    entry1 = translate_ascii_to_unicode_braille(
        '  ,LESSON #A """""""""""""""""""" #AA\n'
    )
    entry2 = translate_ascii_to_unicode_braille(
        '  ,LESSON #B """""""""""""""""""" #AB\n'
    )
    page_break = (
        "<?blank-line?>\n<?blank-line?>\n<?blank-line?>\n"
        "<?braille-page ?>\n<?braille-ppn ⠃⠼⠁?>\n"
        "<?running-head ⠭?>\n<?blank-line?>\n"
    )
    text = heading + entry1 + page_break + entry2

    detector = create_toc_detector(cells_per_line)
    result = detector(text, 0, {}, "")

    assert result is not None
    assert result.cursor == len(text)
    entry2_title, entry2_page = translate_ascii_to_unicode_braille(
        "LESSON #B"
    ), translate_ascii_to_unicode_braille("#AB")
    assert entry2_title in result.text
    assert entry2_page in result.text


def test_create_toc_detector_continues_past_trailing_print_page_number_line():
    # Regression: a print page can end mid-braille-page, leaving its number
    # alone, pushed to the right margin, on its own line right before the
    # page turn (see BANA Formats 2016, section 2.10, on continuing TOCs
    # across a page break, and work/tn.brf line 275's "P#E" before LESSON
    # #E). That lone remnant line has no guide dots, so it was failing the
    # TOC's guide-dots check and dropping the rest of the TOC after it.
    cells_per_line = 40
    heading = translate_ascii_to_unicode_braille(",TOPIC\n")
    entry1 = translate_ascii_to_unicode_braille(
        '  ,LESSON #A """""""""""""""""""" #AA\n'
    )
    entry2 = translate_ascii_to_unicode_braille(
        '  ,LESSON #B """""""""""""""""""" #AB\n'
    )
    furniture = translate_ascii_to_unicode_braille("P#E")
    furniture_line = "⠀" * (cells_per_line - len(furniture)) + furniture + "\n"
    page_break = (
        "<?blank-line?>\n"
        + furniture_line
        + "<?braille-page ?>\n<?braille-ppn ⠃⠼⠁?>\n"
        "<?running-head ⠭?>\n<?blank-line?>\n"
    )
    text = heading + entry1 + page_break + entry2

    detector = create_toc_detector(cells_per_line)
    result = detector(text, 0, {}, "")

    assert result is not None
    assert result.cursor == len(text)
    entry2_title, entry2_page = translate_ascii_to_unicode_braille(
        "LESSON #B"
    ), translate_ascii_to_unicode_braille("#AB")
    assert entry2_title in result.text
    assert entry2_page in result.text
    assert furniture not in result.text


def test_create_toc_detector_continues_a_runover_split_by_a_page_turn():
    # Regression: an entry's own multi-line runover (its title/guide dots
    # already matched, but its description not yet finished) can be split
    # by a real braille-page turn (BANA Formats 2016, 2.10.6 allows a TOC to
    # continue across a page break). The runover lines right after the turn
    # have no guide dots of their own -- they're a continuation of the
    # entry above, not a new one -- but the TOC's guide-dots validation
    # checked each page-turn segment in isolation and required every
    # segment to have its own guide dots, so it dropped the runover's
    # second half and every entry after it from the TOC (see
    # work/toc2.brf line 306's "LESSON #AG").
    cells_per_line = 40
    heading = translate_ascii_to_unicode_braille(",TOPIC\n")
    entry1_start = translate_ascii_to_unicode_braille(
        '  ,LESSON #AF """""""""""""""""""""" #GG\n'
        "      ,USE 3CRETE MODELS TO\n"
    )
    page_break = "<?braille-page ?>\n<?running-head ⠠?>\n"
    entry1_cont = translate_ascii_to_unicode_braille(
        "    SUBTRACT & RELATE !M TO WRITT5\n    RECORD+S4\n"
    )
    entry2 = translate_ascii_to_unicode_braille(
        '  ,LESSON #AG """""""""""""""""""""" #HA\n'
    )
    text = heading + entry1_start + page_break + entry1_cont + "<?blank-line?>\n" + entry2

    detector = create_toc_detector(cells_per_line)
    result = detector(text, 0, {}, "")

    assert result is not None
    assert result.cursor == len(text)
    entry1_cont_text = translate_ascii_to_unicode_braille("RECORD+S4")
    entry2_title, entry2_page = translate_ascii_to_unicode_braille(
        "LESSON #AG"
    ), translate_ascii_to_unicode_braille("#HA")
    assert entry1_cont_text in result.text
    assert entry2_title in result.text
    assert entry2_page in result.text


def test_create_toc_detector_nests_subentries_under_a_wrapped_main_entry():
    # Regression: a main entry (chapter) whose title is too long for one
    # line wraps onto a run-over line that carries its guide dots and page
    # number (BANA Formats 2016, 2.10.6: runovers share one margin two
    # cells past the deepest subentry actually used, which can land deeper
    # than the entry's own subentries). That run-over was being mistaken
    # for a one-off nested subentry: the chapter's own real subentries
    # (its lessons) ended up as top-level siblings of the chapter instead
    # of nested under it, and a lesson's own multi-line description could
    # even swallow the next lesson into the wrong sub-list.
    cells_per_line = 40
    chapter_a = translate_ascii_to_unicode_braille(
        ',A ,ATTRIBUTES """""""""""""""""""" #C\n'
    )
    lesson_1 = translate_ascii_to_unicode_braille(
        '  ,LESSON #A """""""""""""""""""" #E\n'
    )
    chapter_b = translate_ascii_to_unicode_braille(";,B ,COMPOSITE ,%APES\n")
    concepts = translate_ascii_to_unicode_braille(
        '    ,3CEPTS """""""""""""""""""""""" #CC\n'
    )
    lesson_f = translate_ascii_to_unicode_braille(
        '  ,LESSON #F """"""""""""""""""""""" #CE\n'
    )
    lesson_f_cont1 = translate_ascii_to_unicode_braille(
        "      ,RECOGNIZE T A ;OLE POLYGON1\n"
    )
    lesson_f_cont2 = translate_ascii_to_unicode_braille(
        '    C 2 DECOMPOS$ 9TO SMALL] "PS4\n'
    )
    lesson_g = translate_ascii_to_unicode_braille(
        '  ,LESSON #G """"""""""""""""""""""" #DA\n'
    )
    text = (
        chapter_a
        + lesson_1
        + chapter_b
        + concepts
        + lesson_f
        + lesson_f_cont1
        + lesson_f_cont2
        + lesson_g
    )

    detector = create_toc_detector(cells_per_line)
    result = detector(text, 0, {}, "")

    assert result is not None
    assert result.cursor == len(text)
    # Chapter B's title and its run-over ("Concepts") merge into one entry...
    chapter_b_title = translate_ascii_to_unicode_braille(",COMPOSITE ,%APES")
    concepts_title = translate_ascii_to_unicode_braille(",3CEPTS")
    assert chapter_b_title in result.text
    assert concepts_title in result.text
    assert result.text.index(chapter_b_title) < result.text.index(concepts_title)
    # ...and LESSON G stays nested under chapter B (one <ol> for the
    # top-level chapters, one for chapter A's lesson, one for chapter B's
    # lessons) instead of under LESSON F or as a top-level sibling of the
    # chapters.
    assert result.text.count("<ol") == 3
    chapter_b_sublist_open = result.text.rindex("<ol")
    lesson_g_title = translate_ascii_to_unicode_braille("LESSON #G")
    assert result.text.index(lesson_g_title) > chapter_b_sublist_open
