#  Copyright (c) 2024. American Printing House for the Blind.
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from brf2ebrl.common.detectors import translate_ascii_to_unicode_braille
from brf2ebrl.common.table_detectors import create_table_detector


def test_create_table_detector_keeps_second_column_with_extra_inter_column_spaces():
    # Regression for a simple-table row where extra spaces appear between columns.
    ascii_table = (
        ',AC;N          ,KEY ,COMB9A;N\n'
        '"333333333333  "33333333333333333333333\n'
        ',PLUS """""""  ,DOTS #C-#D-#F\n'
        ',M9US """""""  ,DOTS #C-#F\n'
        ',MULTIPLY """  ,DOTS #A-#F\n'
        ',DIVIDE """""  ,DOTS #C-#D\n'
        ',EQUALS """""  ,5T]\n'
        ',CLE> """""""  ,SPACE "6 ,DOTS #C-#E-#F\n'
        ',DECIMAL PO9T  ,DOTS #D-#F\n'
        ',P]C5T """"""  ,DOTS #A-#D-#F\n'
        ',SQU>E ROOT    ,SPACE "6 ,DOTS #C-#D-#E\n'
        ',PI """""""""  ,SPACE "6 ;,Y\n\n'
    )
    text = translate_ascii_to_unicode_braille(ascii_table)

    detector = create_table_detector()
    result = detector(text, 0, {}, "")

    assert result is not None

    expected_row_heading = translate_ascii_to_unicode_braille(',SQU>E ROOT')
    expected_col_2 = translate_ascii_to_unicode_braille(',SPACE "6 ,DOTS #C-#D-#E')
    assert f"<td>{expected_row_heading}</td><td>{expected_col_2}</td>" in result.text


def test_create_table_detector_detects_headerless_simple_table():
    # A simple table with no heading/rule line: just rows of columns
    # separated by 2+ spaces, with a consistent column count.
    ascii_table = (
        ',CATS  #C  #F   #I  #AB  #AE\n'
        ',DOGS  #G  #AD  ""  """  """\n'
    )
    text = translate_ascii_to_unicode_braille(ascii_table)

    detector = create_table_detector()
    result = detector(text, 0, {}, "")

    assert result is not None
    assert result.cursor == len(text)

    expected_row1 = [
        translate_ascii_to_unicode_braille(cell)
        for cell in (',CATS', '#C', '#F', '#I', '#AB', '#AE')
    ]
    expected_row2 = [
        translate_ascii_to_unicode_braille(cell)
        for cell in (',DOGS', '#G', '#AD', '""', '"""', '"""')
    ]
    expected_row1_html = "<tr>" + "".join(f"<td>{c}</td>" for c in expected_row1) + "</tr>"
    expected_row2_html = "<tr>" + "".join(f"<td>{c}</td>" for c in expected_row2) + "</tr>"
    assert expected_row1_html in result.text
    assert expected_row2_html in result.text


def test_create_table_detector_ignores_single_line_with_double_spaces():
    # A lone line with a double space should not be treated as a table.
    ascii_table = ',CATS  #C  #F   #I  #AB  #AE\n'
    text = translate_ascii_to_unicode_braille(ascii_table)

    detector = create_table_detector()
    result = detector(text, 0, {}, "")

    assert result is None


def test_create_table_detector_ignores_rows_with_mismatched_column_counts():
    # If the rows do not have a consistent column count, it is not a table.
    ascii_table = (
        ',CATS  #C  #F\n'
        ',DOGS  #G  #AD  ""\n'
    )
    text = translate_ascii_to_unicode_braille(ascii_table)

    detector = create_table_detector()
    result = detector(text, 0, {}, "")

    assert result is None


def test_create_table_detector_detects_headerless_table_with_row_label_overrun():
    # Regression: a headerless table whose first row's label is too long to
    # fit alongside its data overruns onto an indented continuation line that
    # also carries that row's data cells (see the boxed table in the issue).
    ascii_table = (
        ',CO/\n'
        '  _% (@S) _:  ""  #FJ  """  #AHJ  #BDJ\n'
        ',TICKETS """  #D  """  #AF  """"  #CB\n'
    )
    text = translate_ascii_to_unicode_braille(ascii_table)

    detector = create_table_detector()
    result = detector(text, 0, {}, "")

    assert result is not None
    assert result.cursor == len(text)
    assert result.text.count("<tr>") == 2
    expected_label = translate_ascii_to_unicode_braille(',CO/ _% (@S) _:')
    assert f"<td>{expected_label}</td>" in result.text


def test_create_table_detector_ignores_row_label_overrun_without_data_columns():
    # A line with no column separator followed by an indented line that also
    # has no column separator is ordinary wrapped text, not a table row.
    ascii_table = (
        ',CO/\n'
        '  ISN0 A TABLE ROW AT ALL4\n'
        ',TICKETS """  #D  """  #AF  """"  #CB\n'
    )
    text = translate_ascii_to_unicode_braille(ascii_table)

    detector = create_table_detector()
    result = detector(text, 0, {}, "")

    assert result is None
