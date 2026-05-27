#  Copyright (c) 2024. American Printing House for the Blind.
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.
from brf2ebrl import ParserContext
from brf2ebrl.common.box_line_detectors import convert_box_lines, remove_box_lines_processing_instructions, tag_boxlines
from brf2ebrl.parser import DetectionResult, NotifyLevel


def test_convert_g_box():
    brf = """
⠶⠶⠶⠶⠶⠶⠶⠶⠶⠶⠶⠶⠶⠶⠶⠶⠶⠶⠶⠶⠶⠶⠶⠶⠶⠶⠶⠶⠶⠶⠶⠶⠶⠶⠶⠶⠶⠶⠶⠶
⠁⠃⠉⠀⠁⠃⠉⠀⠁⠃⠉⠀⠁⠃⠉⠀⠁⠃⠉⠀
⠛⠛⠛⠛⠛⠛⠛⠛⠛⠛⠛⠛⠛⠛⠛⠛⠛⠛⠛⠛⠛⠛⠛⠛⠛⠛⠛⠛⠛⠛⠛⠛⠛⠛⠛⠛⠛⠛⠛⠛

"""
    expected_brf = '''
<div type="<?box ⠶?>">
⠁⠃⠉⠀⠁⠃⠉⠀⠁⠃⠉⠀⠁⠃⠉⠀⠁⠃⠉⠀
</div>

'''
    actual = convert_box_lines(brf,0,{},"")
    expected = DetectionResult(len(brf ), {},1.0, expected_brf)
    assert actual == expected

def test_convert_g_color_box():
    brf = """
⠈⠨⠣⠃⠇⠥⠑⠈⠨⠜⠀⠶⠶⠶⠶⠶⠶⠶⠶⠶⠶⠶⠶⠶⠶⠶⠶⠶⠶⠶⠶⠶⠶⠶⠶⠶⠶⠶⠶⠶⠶
⠁⠃⠉⠀⠁⠃⠉⠀⠁⠃⠉⠀⠁⠃⠉⠀⠁⠃⠉⠀
⠛⠛⠛⠛⠛⠛⠛⠛⠛⠛⠛⠛⠛⠛⠛⠛⠛⠛⠛⠛⠛⠛⠛⠛⠛⠛⠛⠛⠛⠛⠛⠛⠛⠛⠛⠛⠛⠛⠛⠛

"""
    expected_brf = '''
<div screen_type="<?box ⠈⠨⠣⠃⠇⠥⠑⠈⠨⠜?>" type="<?box ⠶?>">
⠁⠃⠉⠀⠁⠃⠉⠀⠁⠃⠉⠀⠁⠃⠉⠀⠁⠃⠉⠀
</div>

'''
    actual = convert_box_lines(brf,0,{},"")
    expected = DetectionResult(len(brf ), {},1.0, expected_brf)
    assert actual == expected



def test_convert_enclosing_box():
    brf = """
⠿⠿⠿⠿⠿⠿⠿⠿⠿⠿⠿⠿⠿⠿⠿⠿⠿⠿⠿⠿⠿⠿⠿⠿⠿⠿⠿⠿⠿⠿⠿⠿⠿⠿⠿⠿⠿⠿⠿⠿
⠁⠃⠉⠀⠁⠃⠉⠀⠁⠃⠉⠀⠁⠃⠉⠀⠁⠃⠉⠀
⠿⠿⠿⠿⠿⠿⠿⠿⠿⠿⠿⠿⠿⠿⠿⠿⠿⠿⠿⠿⠿⠿⠿⠿⠿⠿⠿⠿⠿⠿⠿⠿⠿⠿⠿⠿⠿⠿⠿⠿

"""
    expected_brf = '''
<div type="<?box ⠿?>">
⠁⠃⠉⠀⠁⠃⠉⠀⠁⠃⠉⠀⠁⠃⠉⠀⠁⠃⠉⠀
</div>

'''
    actual = convert_box_lines(brf,0,{},"")
    expected = DetectionResult(len(brf ), {},1.0, expected_brf)
    assert actual == expected


def test_convert_enclosing_color_box():
    brf = """
⠈⠨⠣⠃⠇⠥⠑⠈⠨⠜⠀⠿⠿⠿⠿⠿⠿⠿⠿⠿⠿⠿⠿⠿⠿⠿⠿⠿⠿⠿⠿⠿⠿⠿⠿⠿⠿⠿⠿⠿⠿
⠁⠃⠉⠀⠁⠃⠉⠀⠁⠃⠉⠀⠁⠃⠉⠀⠁⠃⠉⠀
⠿⠿⠿⠿⠿⠿⠿⠿⠿⠿⠿⠿⠿⠿⠿⠿⠿⠿⠿⠿⠿⠿⠿⠿⠿⠿⠿⠿⠿⠿⠿⠿⠿⠿⠿⠿⠿⠿⠿⠿

"""
    expected_brf = '''
<div screen_type="<?box ⠈⠨⠣⠃⠇⠥⠑⠈⠨⠜?>" type="<?box ⠿?>">
⠁⠃⠉⠀⠁⠃⠉⠀⠁⠃⠉⠀⠁⠃⠉⠀⠁⠃⠉⠀
</div>

'''
    actual = convert_box_lines(brf,0,{},"")
    expected = DetectionResult(len(brf ), {},1.0, expected_brf)
    assert actual == expected



def test_convert_enclosing_and_g_box():
    brf = """
⠿⠿⠿⠿⠿⠿⠿⠿⠿⠿⠿⠿⠿⠿⠿⠿⠿⠿⠿⠿⠿⠿⠿⠿⠿⠿⠿⠿⠿⠿⠿⠿⠿⠿⠿⠿⠿⠿⠿⠿
⠁⠃⠉⠀⠁⠃⠉⠀⠁⠃⠉⠀⠁⠃⠉⠀⠁⠃⠉⠀
⠶⠶⠶⠶⠶⠶⠶⠶⠶⠶⠶⠶⠶⠶⠶⠶⠶⠶⠶⠶⠶⠶⠶⠶⠶⠶⠶⠶⠶⠶⠶⠶⠶⠶⠶⠶⠶⠶⠶⠶
⠁⠃⠉⠀⠁⠃⠉⠀⠁⠃⠉⠀⠁⠃⠉⠀⠁⠃⠉⠀
⠛⠛⠛⠛⠛⠛⠛⠛⠛⠛⠛⠛⠛⠛⠛⠛⠛⠛⠛⠛⠛⠛⠛⠛⠛⠛⠛⠛⠛⠛⠛⠛⠛⠛⠛⠛⠛⠛⠛⠛

⠿⠿⠿⠿⠿⠿⠿⠿⠿⠿⠿⠿⠿⠿⠿⠿⠿⠿⠿⠿⠿⠿⠿⠿⠿⠿⠿⠿⠿⠿⠿⠿⠿⠿⠿⠿⠿⠿⠿⠿

"""
    expected_brf = '''
<div type="<?box ⠿?>">
⠁⠃⠉⠀⠁⠃⠉⠀⠁⠃⠉⠀⠁⠃⠉⠀⠁⠃⠉⠀
<div type="<?box ⠶?>">
⠁⠃⠉⠀⠁⠃⠉⠀⠁⠃⠉⠀⠁⠃⠉⠀⠁⠃⠉⠀
</div>

</div>

'''
    actual = convert_box_lines(brf,0,{},"")
    expected = DetectionResult(len(brf ), {},1.0, expected_brf)
    assert actual == expected


def test_convert_enclosing_and_g_color_box():
    brf = """
⠈⠨⠣⠃⠇⠥⠑⠈⠨⠜⠀⠿⠿⠿⠿⠿⠿⠿⠿⠿⠿⠿⠿⠿⠿⠿⠿⠿⠿⠿⠿⠿⠿⠿⠿⠿⠿⠿⠿⠿⠿
⠁⠃⠉⠀⠁⠃⠉⠀⠁⠃⠉⠀⠁⠃⠉⠀⠁⠃⠉⠀
⠈⠨⠣⠃⠇⠥⠑⠈⠨⠜⠀⠶⠶⠶⠶⠶⠶⠶⠶⠶⠶⠶⠶⠶⠶⠶⠶⠶⠶⠶⠶⠶⠶⠶⠶⠶⠶⠶⠶⠶⠶
⠁⠃⠉⠀⠁⠃⠉⠀⠁⠃⠉⠀⠁⠃⠉⠀⠁⠃⠉⠀
⠛⠛⠛⠛⠛⠛⠛⠛⠛⠛⠛⠛⠛⠛⠛⠛⠛⠛⠛⠛⠛⠛⠛⠛⠛⠛⠛⠛⠛⠛⠛⠛⠛⠛⠛⠛⠛⠛⠛⠛

⠿⠿⠿⠿⠿⠿⠿⠿⠿⠿⠿⠿⠿⠿⠿⠿⠿⠿⠿⠿⠿⠿⠿⠿⠿⠿⠿⠿⠿⠿⠿⠿⠿⠿⠿⠿⠿⠿⠿⠿

"""
    expected_brf = '''
<div screen_type="<?box ⠈⠨⠣⠃⠇⠥⠑⠈⠨⠜?>" type="<?box ⠿?>">
⠁⠃⠉⠀⠁⠃⠉⠀⠁⠃⠉⠀⠁⠃⠉⠀⠁⠃⠉⠀
<div screen_type="<?box ⠈⠨⠣⠃⠇⠥⠑⠈⠨⠜?>" type="<?box ⠶?>">
⠁⠃⠉⠀⠁⠃⠉⠀⠁⠃⠉⠀⠁⠃⠉⠀⠁⠃⠉⠀
</div>

</div>

'''
    actual = convert_box_lines(brf,0,{},"")
    expected = DetectionResult(len(brf ), {},1.0, expected_brf)
    assert actual == expected

def test_remove_box_processing_instructions():
    brf = '''
<div screen_type="<?box ⠈⠨⠣⠃⠇⠥⠑⠈⠨⠜?>" type="<?box ⠿?>">
⠁⠃⠉⠀⠁⠃⠉⠀⠁⠃⠉⠀⠁⠃⠉⠀⠁⠃⠉⠀
<div screen_type="<?box ⠈⠨⠣⠃⠇⠥⠑⠈⠨⠜?>" type="<?box ⠶?>">
⠁⠃⠉⠀⠁⠃⠉⠀⠁⠃⠉⠀⠁⠃⠉⠀⠁⠃⠉⠀
</div>

</div>

'''
    expected_brf = '''
<div screen_type="⠈⠨⠣⠃⠇⠥⠑⠈⠨⠜" type="⠿">
⠁⠃⠉⠀⠁⠃⠉⠀⠁⠃⠉⠀⠁⠃⠉⠀⠁⠃⠉⠀
<div screen_type="⠈⠨⠣⠃⠇⠥⠑⠈⠨⠜" type="⠶">
⠁⠃⠉⠀⠁⠃⠉⠀⠁⠃⠉⠀⠁⠃⠉⠀⠁⠃⠉⠀
</div>

</div>

'''
    actual = remove_box_lines_processing_instructions(brf, ParserContext())
    assert actual == expected_brf


def test_orphan_top_box_line_warns(caplog):
    import logging
    brf = "\n⠶⠶⠶⠶⠶⠶⠶⠶⠶⠶⠶⠶⠶⠶⠶⠶⠶⠶⠶⠶⠶⠶⠶⠶⠶⠶⠶⠶⠶⠶⠶⠶⠶⠶⠶⠶⠶⠶⠶⠶\n⠁⠃⠉⠀⠁⠃⠉⠀\n"
    with caplog.at_level(logging.WARNING):
        result = tag_boxlines(brf, ParserContext())
    assert result == brf
    assert len(caplog.records) == 1
    assert caplog.records[0].levelno == logging.WARNING
    assert "top (7)" in caplog.records[0].message
    assert "line 2" in caplog.records[0].message


def test_orphan_bottom_box_line_warns(caplog):
    import logging
    brf = "\n⠁⠃⠉⠀⠁⠃⠉⠀\n⠛⠛⠛⠛⠛⠛⠛⠛⠛⠛⠛⠛⠛⠛⠛⠛⠛⠛⠛⠛⠛⠛⠛⠛⠛⠛⠛⠛⠛⠛⠛⠛⠛⠛⠛⠛⠛⠛⠛⠛\n"
    with caplog.at_level(logging.WARNING):
        result = tag_boxlines(brf, ParserContext())
    assert result == brf
    assert len(caplog.records) == 1
    assert caplog.records[0].levelno == logging.WARNING
    assert "bottom (g)" in caplog.records[0].message
    assert "line 3" in caplog.records[0].message


def test_orphan_exterior_box_line_warns(caplog):
    import logging
    brf = "\n⠿⠿⠿⠿⠿⠿⠿⠿⠿⠿\n⠁⠃⠉⠀⠁⠃⠉⠀\n"
    with caplog.at_level(logging.WARNING):
        result = tag_boxlines(brf, ParserContext())
    assert result == brf
    assert len(caplog.records) == 1
    assert caplog.records[0].levelno == logging.WARNING
    assert "exterior border (=)" in caplog.records[0].message
    assert "line 2" in caplog.records[0].message


def test_no_warnings_for_matched_box():
    brf = "\n⠶⠶⠶⠶⠶⠶⠶⠶⠶⠶⠶⠶⠶⠶⠶⠶⠶⠶⠶⠶⠶⠶⠶⠶⠶⠶⠶⠶⠶⠶⠶⠶⠶⠶⠶⠶⠶⠶⠶⠶\n⠁⠃⠉⠀⠁⠃⠉⠀\n⠛⠛⠛⠛⠛⠛⠛⠛⠛⠛⠛⠛⠛⠛⠛⠛⠛⠛⠛⠛⠛⠛⠛⠛⠛⠛⠛⠛⠛⠛⠛⠛⠛⠛⠛⠛⠛⠛⠛⠛\n"
    warnings = []
    ctx = ParserContext(notify=lambda level, msg: warnings.append((level, msg())))
    tag_boxlines(brf, ctx)
    assert warnings == []