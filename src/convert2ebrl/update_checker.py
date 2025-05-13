#  Copyright (c) 2025. American Printing House for the Blind.
#
# This file is part of Convert2EBRL.
# Convert2EBRL is free software: you can redistribute it and/or modify it under the terms of the GNU General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# Convert2EBRL is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License for more details.
# You should have received a copy of the GNU General Public License along with Convert2EBRL. If not, see <https://www.gnu.org/licenses/>.
import re

from PySide6.QtCore import QObject, QUrl, Slot, Signal, QCoreApplication
from PySide6.QtNetwork import QNetworkAccessManager, QNetworkRequest, QNetworkReply
from packaging.version import Version

_APP_VERSION_RE = re.compile("^app.version[ \t]*[ \t:=][ \t]*(.*)(?:\n|$)", flags=re.MULTILINE)

class UpdateChecker(QObject):
    checkingForUpdates = Signal()
    updateAvailable = Signal(str)
    noUpdateAvailable = Signal()
    errorOccurred = Signal(str)
    def __init__(self, parent: QObject|None = None):
        super().__init__(parent)
        self.network_manager = QNetworkAccessManager(self)
        self.reply = None
    def check_for_update(self, update_url: QUrl):
        self.checkingForUpdates.emit()
        self.reply = self.network_manager.get(QNetworkRequest(update_url))
        self.reply.readyRead.connect(self.on_ready_read)
        self.reply.finished.connect(self.on_finished)
        self.reply.errorOccurred.connect(self.on_error)
    @Slot()
    def on_ready_read(self):
        if self.reply:
            if self.reply.error() == QNetworkReply.NetworkError.NoError:
                response_text = str(self.reply.readAll(), "utf-8")
                if m := _APP_VERSION_RE.search(response_text):
                    if Version(QCoreApplication.applicationVersion()) < Version(m.group(1)):
                        print(m.group(1))
                        self.updateAvailable.emit(m.group(1))
    @Slot()
    def on_finished(self):
        if self.reply:
            self.reply.deleteLater()
    @Slot(QNetworkReply.NetworkError)
    def on_error(self, _: QNetworkReply.NetworkError):
        if self.reply:
            self.errorOccurred.emit(self.reply.errorString())
