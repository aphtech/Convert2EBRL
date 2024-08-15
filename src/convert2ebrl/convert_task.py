#  Copyright (c) 2024. American Printing House for the Blind.

import os
import shutil
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Iterable, Callable

from PySide6.QtCore import QObject, Signal
# noinspection PyUnresolvedReferences
from __feature__ import snake_case, true_property
from brf2ebrl.common import PageLayout, PageNumberPosition
from brf2ebrl.parser import ParsingCancelledException
from brf2ebrl.plugin import Brf2EbrlPlugin, find_plugins
from brf2ebrl.scripts.brf2ebrl import convert_brf2ebrf

DISCOVERED_PARSER_PLUGINS = find_plugins()
_DEFAULT_PAGE_LAYOUT = PageLayout(
    odd_braille_page_number=PageNumberPosition.BOTTOM_RIGHT,
    odd_print_page_number=PageNumberPosition.TOP_RIGHT,
    cells_per_line=40,
    lines_per_page=25
)


def convert(selected_plugin: Brf2EbrlPlugin, input_brf_list: Iterable[str], input_images: str, output_ebrf: str,
            detect_running_heads: bool, page_layout: PageLayout, is_cancelled: Callable[[], bool],
            progress_callback: Callable[[int, float], None]):
    with open(output_ebrf, "wb") as out_file:
        with TemporaryDirectory() as temp_dir:
            os.makedirs(os.path.join(temp_dir, "images"), exist_ok=True)
            for index, brf in enumerate(input_brf_list):
                temp_file = os.path.join(temp_dir, f"vol{index}.html")
                parser = selected_plugin.create_brf2ebrl_parser(
                    page_layout=page_layout,
                    detect_running_heads=detect_running_heads,
                    brf_path=brf,
                    output_path=temp_file,
                    images_path=input_images
                )
                parser_steps = len(parser)
                convert_brf2ebrf(brf, temp_file, parser,
                                 progress_callback=lambda x: progress_callback(index, x / parser_steps),
                                 is_cancelled=is_cancelled)
            bundle_as_zip(temp_dir, out_file)


def bundle_as_zip(input_dir, out_file):
    with TemporaryDirectory() as out_temp_dir:
        temp_ebrf = shutil.make_archive(os.path.join(out_temp_dir, "output_ebrf"), "zip", input_dir)
        with open(temp_ebrf, "rb") as temp_ebrf_file:
            shutil.copyfileobj(temp_ebrf_file, out_file)


class ConvertTask(QObject):
    started = Signal()
    progress = Signal(int, float)
    finished = Signal()
    cancelled = Signal()
    errorRaised = Signal(Exception)

    def __init__(self, parent: QObject = None):
        super().__init__(parent=parent)
        self._cancel_requested = False

    def __call__(self, input_brf_list: Iterable[str], output_ebrf: str, input_images: str | None,
                 detect_running_heads: bool = True,
                 page_layout: PageLayout = _DEFAULT_PAGE_LAYOUT):
        self.started.emit()
        try:
            self._convert(input_brf_list, input_images, output_ebrf, detect_running_heads, page_layout)
            self.finished.emit()
        except ParsingCancelledException:
            Path(output_ebrf).unlink(missing_ok=True)
            self.cancelled.emit()
        except Exception as e:
            Path(output_ebrf).unlink(missing_ok=True)
            self.errorRaised.emit(e)

    def _convert(self, input_brf_list: Iterable[str], input_images: str, output_ebrf: str, detect_running_heads: bool,
                 page_layout: PageLayout):
        selected_plugin = [plugin for plugin in DISCOVERED_PARSER_PLUGINS.values()][0]
        progress_callback = self.progress.emit
        is_cancelled = lambda: self._cancel_requested
        convert(selected_plugin, input_brf_list, input_images, output_ebrf, detect_running_heads, page_layout,
                is_cancelled, progress_callback)

    def cancel(self):
        self._cancel_requested = True
