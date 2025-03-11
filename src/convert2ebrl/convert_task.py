#  Copyright (c) 2024. American Printing House for the Blind.
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from PySide6.QtCore import QObject, Signal
# noinspection PyUnresolvedReferences
from __feature__ import snake_case, true_property
from brf2ebrl import convert
from brf2ebrl.common import PageLayout, PageNumberPosition
from brf2ebrl.parser import NotifyLevel, ParsingCancelledException, ParserContext, EBrailleParserOptions
from brf2ebrl.plugin import find_plugins

DISCOVERED_PARSER_PLUGINS = find_plugins()
_DEFAULT_PAGE_LAYOUT = PageLayout(
    odd_braille_page_number=PageNumberPosition.BOTTOM_RIGHT,
    odd_print_page_number=PageNumberPosition.TOP_RIGHT,
    cells_per_line=40,
    lines_per_page=25
)


@dataclass(frozen=True)
class Notification:
    level: NotifyLevel
    message: str


class ConvertTask(QObject):
    started = Signal()
    progress = Signal(int, float)
    finished = Signal()
    cancelled = Signal()
    notify = Signal(Notification)
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
            logging.exception("Conversion failed because of an exception.")
            Path(output_ebrf).unlink(missing_ok=True)
            self.errorRaised.emit(e)

    def _convert(self, input_brf_list: Iterable[str], input_images: str, output_ebrf: str, detect_running_heads: bool,
                 page_layout: PageLayout):
        selected_plugin = [plugin for plugin in DISCOVERED_PARSER_PLUGINS.values()][0]

        parser_options = {EBrailleParserOptions.detect_running_heads: detect_running_heads, EBrailleParserOptions.page_layout: page_layout, EBrailleParserOptions.images_path: input_images}
        parser_context = ParserContext(is_cancelled=lambda: self._cancel_requested,
                                notify=lambda l, m: self.notify.emit(Notification(l, m())), options=parser_options)
        convert(selected_plugin, input_brf_list, input_images, output_ebrf, detect_running_heads, page_layout,
                self.progress.emit, parser_context=parser_context)

    def cancel(self):
        self._cancel_requested = True
