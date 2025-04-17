#  Copyright (c) 2025. American Printing House for the Blind.
#
# This file is part of Convert2EBRL.
# Convert2EBRL is free software: you can redistribute it and/or modify it under the terms of the GNU General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# Convert2EBRL is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License for more details.
# You should have received a copy of the GNU General Public License along with Convert2EBRL. If not, see <https://www.gnu.org/licenses/>.

import os

from PySide6.QtCore import Signal, QObject, QSettings, Slot
from PySide6.QtWidgets import QWidget, QFormLayout, QComboBox, QCheckBox, QFileDialog

from convert2ebrl.settings.defaults import CONVERSION_LAST_DIR as DEFAULT_LAST_DIR
from convert2ebrl.settings.keys import CONVERSION_LAST_DIR as LAST_DIR_SETTING_KEY
from convert2ebrl.widgets import FilePickerWidget

class ConversionGeneralSettingsWidget(QWidget):
    inputBrfChanged = Signal(str)
    imagesDirectoryChanged = Signal(str)
    outputEbrfChanged = Signal(str)

    def __init__(self, parent: QObject | None = None):
        super().__init__(parent)
        layout = QFormLayout(self)
        self._input_type_combo = QComboBox()
        self._input_type_combo.setEditable(False)
        self._input_type_combo.addItems(["List of BRF", "Directory of BRF"])
        layout.addRow("Input type", self._input_type_combo)
        self._input_brf_edit = FilePickerWidget(self._get_input_brf_from_user)
        layout.addRow("Input BRF", self._input_brf_edit)
        self._include_images_checkbox = QCheckBox()
        layout.addRow("Include images", self._include_images_checkbox)

        def get_images_dir_from_user(x) -> list[str]:
            settings = QSettings()
            default_dir = str(settings.value(LAST_DIR_SETTING_KEY, DEFAULT_LAST_DIR))
            image_dir = QFileDialog.getExistingDirectory(parent=x, dir=default_dir)
            if image_dir:
                settings.setValue(LAST_DIR_SETTING_KEY, image_dir)
            return [image_dir]

        self._image_dir_edit = FilePickerWidget(
            get_images_dir_from_user)
        layout.addRow("Image directory", self._image_dir_edit)

        def get_output_ebrf_file_from_user(x) -> list[str]:
            settings = QSettings()
            default_dir = str(settings.value(LAST_DIR_SETTING_KEY, DEFAULT_LAST_DIR))
            save_path = QFileDialog.getSaveFileName(
                parent=x, dir=default_dir, filter="eBraille Files (*.zip)",
                options=QFileDialog.Option.DontConfirmOverwrite
            )[0]
            if save_path:
                settings.setValue(LAST_DIR_SETTING_KEY, os.path.dirname(save_path))
            return [save_path]

        self._output_ebrf_edit = FilePickerWidget(get_output_ebrf_file_from_user)
        layout.addRow("Output eBraille", self._output_ebrf_edit)
        self._update_include_images_state(self._include_images_checkbox.isChecked())
        def restore_from_settings():
            settings = QSettings()
            self._input_type_combo.setCurrentIndex(int(bool(settings.value("Conversion/input_type", defaultValue=False, type=bool))))
        restore_from_settings()
        def on_input_type_changed(index):
            settings = QSettings()
            settings.setValue("Conversion/input_type", bool(index))
        self._input_type_combo.currentIndexChanged.connect(on_input_type_changed)
        self._include_images_checkbox.toggled.connect(self._update_include_images_state)
        self._input_type_combo.currentIndexChanged.connect(self._clear_input_brf)
        self._input_brf_edit.fileChanged.connect(self.inputBrfChanged.emit)
        self._image_dir_edit.fileChanged.connect(self.imagesDirectoryChanged.emit)
        self._output_ebrf_edit.fileChanged.connect(self.outputEbrfChanged.emit)

    @Slot(bool)
    def _update_include_images_state(self, checked: bool):
        self._image_dir_edit.setEnabled(checked)
        if not checked:
            self._image_dir_edit.file_name = ""

    def _get_input_brf_from_user(self, x) -> list[str]:
        settings = QSettings()
        default_dir = str(settings.value(LAST_DIR_SETTING_KEY, DEFAULT_LAST_DIR))
        if self._input_type_combo.currentIndex():
            input_dir = QFileDialog.getExistingDirectory(
                parent=x, dir=default_dir
            )
            if input_dir:
                settings.setValue(LAST_DIR_SETTING_KEY, input_dir)
            return [input_dir]
        else:
            input_files = QFileDialog.getOpenFileNames(
                parent=x, dir=default_dir, filter="Braille Ready Files (*.brf)"
            )[0]
            if input_files:
                settings.setValue(LAST_DIR_SETTING_KEY, os.path.dirname(input_files[0]))
            return input_files

    @property
    def input_brfs(self) -> list[str]:
        return self._input_brf_edit.files

    @input_brfs.setter
    def input_brfs(self, value: list[str]):
        self._input_type_combo.setCurrentIndex(1 if len(value) == 1 and os.path.isdir(value[0]) else 0)
        self._input_brf_edit.files = value

    def _clear_input_brf(self):
        self._input_brf_edit.files = []

    @property
    def image_directory(self) -> str | None:
        return self._image_dir_edit.file_name if self._include_images_checkbox.isChecked() else None

    @image_directory.setter
    def image_directory(self, value: str | None):
        if value is None:
            self._include_images_checkbox.setChecked(False)
        else:
            self._include_images_checkbox.setChecked(True)
            self._image_dir_edit.file_name = value

    @property
    def output_ebrf(self) -> str:
        return self._output_ebrf_edit.file_name

    @output_ebrf.setter
    def output_ebrf(self, value: str):
        self._output_ebrf_edit.file_name = value
