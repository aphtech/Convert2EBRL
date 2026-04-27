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
