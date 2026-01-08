#  Copyright (c) 2025. American Printing House for the Blind.
#
# This file is part of Convert2EBRL.
# Convert2EBRL is free software: you can redistribute it and/or modify it under the terms of the GNU General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# Convert2EBRL is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License for more details.
# You should have received a copy of the GNU General Public License along with Convert2EBRL. If not, see <https://www.gnu.org/licenses/>.
import logging

from PySide6.QtCore import Qt
from PySide6.QtGui import QTextCursor, QGuiApplication
from PySide6.QtWidgets import QDialog, QWidget, QDialogButtonBox, QVBoxLayout, QPlainTextEdit, QApplication, QMessageBox


class LogViewerDialog(QDialog):
    def __init__(self, /, parent: QWidget | None = None):
        super().__init__(parent)
        self.setWindowTitle("Log viewer")

        self._log_text = QPlainTextEdit()
        self._log_text.setReadOnly(True)
        self._log_text.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByKeyboard)
        self._refresh()

        self.button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        refresh_button = self.button_box.addButton("Refresh", QDialogButtonBox.ButtonRole.ActionRole)
        refresh_button.clicked.connect(lambda _: self._refresh())
        copy_button = self.button_box.addButton("Copy log", QDialogButtonBox.ButtonRole.ActionRole)
        copy_button.clicked.connect(lambda _: self._copy_log())
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)

        layout = QVBoxLayout()
        layout.addWidget(self._log_text)
        layout.addWidget(self.button_box)
        self.setLayout(layout)

    def _refresh(self):
        log_filename = QApplication.instance().property("log_filename")
        try:
            with open(log_filename, mode='r', encoding="UTF-8") as f:
                self._log_text.setPlainText(f.read())
                self._log_text.moveCursor(QTextCursor.MoveOperation.End)
                self._log_text.ensureCursorVisible()
        except:
            logging.exception("Problem loading log")
            QMessageBox.critical(self, "Problem loading log", f"Could not load the log file. The log should be available to view in {log_filename}", QMessageBox.StandardButton.Ok)

    def _copy_log(self):
        clipboard = QGuiApplication.clipboard()
        clipboard.setText(self._log_text.toPlainText())
