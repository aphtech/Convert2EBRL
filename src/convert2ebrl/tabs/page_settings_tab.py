#  Copyright (c) 2025. American Printing House for the Blind.
#
# This file is part of Convert2EBRL.
# Convert2EBRL is free software: you can redistribute it and/or modify it under the terms of the GNU General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# Convert2EBRL is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License for more details.
# You should have received a copy of the GNU General Public License along with Convert2EBRL. If not, see <https://www.gnu.org/licenses/>.

from PySide6.QtCore import Signal, QObject, SignalInstance
from PySide6.QtWidgets import QWidget, QFormLayout, QCheckBox, QSpinBox, QComboBox
from brf2ebrl.common import PageNumberPosition

# noinspection PyUnresolvedReferences
from __feature__ import snake_case, true_property
_PAGE_NUMBER_POSITIONS_DICT = {
    PageNumberPosition.NONE: "None",
    PageNumberPosition.TOP_LEFT: "Top left",
    PageNumberPosition.TOP_RIGHT: "Top right",
    PageNumberPosition.BOTTOM_LEFT: "Bottom left",
    PageNumberPosition.BOTTOM_RIGHT: "Bottom right"
}


class ConversionPageSettingsWidget(QWidget):
    detectRunningHeadsChanged = Signal(bool)
    cellsPerLineChanged = Signal(int)
    linesPerPageChanged = Signal(int)
    oddBraillePageNumberChanged = Signal(PageNumberPosition)
    evenBraillePageNumberChanged = Signal(PageNumberPosition)
    oddPrintPageNumberChanged = Signal(PageNumberPosition)
    evenPrintPageNumberChanged = Signal(PageNumberPosition)
    isValidChanged = Signal(bool)

    def __init__(self, parent: QObject = None):
        super().__init__(parent=parent)
        self._is_valid = False
        layout = QFormLayout(self)
        self._detect_running_heads_checkbox = QCheckBox()
        self._detect_running_heads_checkbox.checked = True
        layout.add_row("Has running heads", self._detect_running_heads_checkbox)
        self._cells_per_line_spinbox = QSpinBox()
        self._cells_per_line_spinbox.set_range(10, 100)
        self._cells_per_line_spinbox.single_step = 1
        self._cells_per_line_spinbox.value = 40
        layout.add_row("Cells per line", self._cells_per_line_spinbox)
        self._lines_per_page_spinbox = QSpinBox()
        self._lines_per_page_spinbox.set_range(10, 100)
        self._lines_per_page_spinbox.value = 25
        self._lines_per_page_spinbox.single_step = 1
        layout.add_row("Lines per page", self._lines_per_page_spinbox)

        def create_page_number_position_combo(default_selection: PageNumberPosition = PageNumberPosition.NONE):
            combo = QComboBox()
            combo.editable = False
            for p, t in _PAGE_NUMBER_POSITIONS_DICT.items():
                combo.add_item(t, p)
            combo.current_text = _PAGE_NUMBER_POSITIONS_DICT[default_selection]
            return combo

        self._odd_bpn_position = create_page_number_position_combo(PageNumberPosition.BOTTOM_RIGHT)
        layout.add_row("Odd Braille page number", self._odd_bpn_position)
        self._even_bpn_position = create_page_number_position_combo()
        layout.add_row("Even Braille page number", self._even_bpn_position)
        self._odd_ppn_position = create_page_number_position_combo(PageNumberPosition.TOP_RIGHT)
        layout.add_row("Odd print page number", self._odd_ppn_position)
        self._even_ppn_position = create_page_number_position_combo()
        layout.add_row("Even print page number", self._even_ppn_position)
        self._update_validity()
        self._detect_running_heads_checkbox.toggled.connect(self.detectRunningHeadsChanged.emit)
        self._cells_per_line_spinbox.valueChanged.connect(self.cellsPerLineChanged.emit)
        self._lines_per_page_spinbox.valueChanged.connect(self.linesPerPageChanged.emit)
        def form_update(change_signal: SignalInstance, value: PageNumberPosition):
            change_signal.emit(value)
            self._update_validity()
        self._odd_bpn_position.currentIndexChanged.connect(
            lambda x: form_update(self.oddBraillePageNumberChanged, self._odd_bpn_position.item_data(x)))
        self._even_bpn_position.currentIndexChanged.connect(
            lambda x: form_update(self.evenBraillePageNumberChanged, self._even_bpn_position.item_data(x)))
        self._odd_ppn_position.currentIndexChanged.connect(
            lambda x: form_update(self.oddPrintPageNumberChanged, self._odd_ppn_position.item_data(x)))
        self._even_ppn_position.currentIndexChanged.connect(
            lambda x: form_update(self.evenPrintPageNumberChanged, self._even_ppn_position.item_data(x)))

    def _update_validity(self):
        old_validity = self._is_valid
        new_validity = (self.odd_braille_page_number_position == PageNumberPosition.NONE or self.odd_braille_page_number_position != self.odd_print_page_number_position) and (self.even_braille_page_number_position == PageNumberPosition.NONE or self.even_braille_page_number_position != self.even_print_page_number_position)
        if old_validity != new_validity:
            self._is_valid = new_validity
            self.isValidChanged.emit(new_validity)

    @property
    def is_valid(self) -> bool:
        return self._is_valid

    @property
    def detect_running_heads(self) -> bool:
        return self._detect_running_heads_checkbox.checked

    @detect_running_heads.setter
    def detect_running_heads(self, value: bool):
        self._detect_running_heads_checkbox.checked = value

    @property
    def cells_per_line(self) -> int:
        return self._cells_per_line_spinbox.value

    @cells_per_line.setter
    def cells_per_line(self, value: int):
        self._cells_per_line_spinbox.value = value

    @property
    def lines_per_page(self) -> int:
        return self._lines_per_page_spinbox.value

    @lines_per_page.setter
    def lines_per_page(self, value: int):
        self._lines_per_page_spinbox.value = value

    @property
    def odd_braille_page_number_position(self) -> PageNumberPosition:
        return self._odd_bpn_position.current_data()

    @odd_braille_page_number_position.setter
    def odd_braille_page_number_position(self, value: PageNumberPosition):
        self._odd_bpn_position.current_index = self._odd_bpn_position.find_data(value)

    @property
    def even_braille_page_number_position(self) -> PageNumberPosition:
        return self._even_bpn_position.current_data()

    @even_braille_page_number_position.setter
    def even_braille_page_number_position(self, value: PageNumberPosition):
        self._even_bpn_position.current_index = self._even_bpn_position.find_data(value)

    @property
    def odd_print_page_number_position(self) -> PageNumberPosition:
        return self._odd_ppn_position.current_data()

    @odd_print_page_number_position.setter
    def odd_print_page_number_position(self, value: PageNumberPosition):
        self._odd_ppn_position.current_index = self._odd_ppn_position.find_data(value)

    @property
    def even_print_page_number_position(self) -> PageNumberPosition:
        return self._even_ppn_position.current_data()

    @even_print_page_number_position.setter
    def even_print_page_number_position(self, value: PageNumberPosition):
        self._even_ppn_position.current_index = self._even_ppn_position.find_data(value)
