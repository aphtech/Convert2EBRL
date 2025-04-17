#  Copyright (c) 2024. American Printing House for the Blind.
#
# This file is part of Convert2EBRL.
# Convert2EBRL is free software: you can redistribute it and/or modify it under the terms of the GNU General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# Convert2EBRL is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License for more details.
# You should have received a copy of the GNU General Public License along with Convert2EBRL. If not, see <https://www.gnu.org/licenses/>.
import os.path
from collections.abc import Callable

from PySide6.QtCore import QObject, Signal, Slot
from PySide6.QtWidgets import QWidget, QLineEdit, QPushButton, QHBoxLayout


class FilePickerWidget(QWidget):
    fileChanged = Signal(str)

    def __init__(self, browse_func: Callable[[QWidget], list[str]], parent: QObject = None):
        super().__init__(parent)
        self._files = []
        self._browse_func = browse_func
        file_name_edit = QLineEdit()
        file_name_edit.setReadOnly(True)
        file_name_edit.setMinimumWidth(400)
        browse_button = QPushButton("Browse...")
        browse_button.setAutoDefault(False)
        browse_button.setDefault(False)
        layout = QHBoxLayout(self)
        layout.addWidget(file_name_edit)
        layout.addWidget(browse_button)
        browse_button.clicked.connect(self._browse_clicked)
        self._file_name_edit = file_name_edit

    @Slot()
    def _browse_clicked(self):
        directory = self._browse_func(self)
        if directory:
            self.files = directory

    @property
    def file_name(self) -> str:
        return os.path.pathsep.join(self.files)

    @file_name.setter
    def file_name(self, value: str):
        self.files = value.split(os.path.pathsep)

    @property
    def files(self) -> list[str]:
        return self._files

    @files.setter
    def files(self, value: list[str]):
        self._files = value
        self._file_name_edit.setText(os.path.pathsep.join(value))
        self.fileChanged.emit(self._file_name_edit.text())
