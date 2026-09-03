#  Copyright (c) 2025. American Printing House for the Blind.
#
# This file is part of Convert2EBRL.
# Convert2EBRL is free software: you can redistribute it and/or modify it under the terms of the GNU General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# Convert2EBRL is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License for more details.
# You should have received a copy of the GNU General Public License along with Convert2EBRL. If not, see <https://www.gnu.org/licenses/>.
import logging
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
        self._network_manager = QNetworkAccessManager(self)
        self._reply = None
    def check_for_update(self, update_url: QUrl):
        self.checkingForUpdates.emit()
        logging.info("Checking for update at %s", update_url.toDisplayString())
        self._reply = self._network_manager.get(QNetworkRequest(update_url))
        self._reply.readyRead.connect(self.on_ready_read)
        self._reply.finished.connect(self.on_finished)
        self._reply.errorOccurred.connect(self.on_error)
    @Slot()
    def on_ready_read(self):
        if self._reply:
            if self._reply.error() == QNetworkReply.NetworkError.NoError and self._reply.attribute(QNetworkRequest.Attribute.HttpStatusCodeAttribute) == 200:
                response_text = self._reply.readAll().toStdString()
                if m := _APP_VERSION_RE.search(response_text):
                    if Version(QCoreApplication.applicationVersion()) < Version(m.group(1)):
                        self.updateAvailable.emit(m.group(1))
                    else:
                        self.noUpdateAvailable.emit()
                else:
                    self.errorOccurred.emit("Unable to find latest version")
    @Slot()
    def on_finished(self):
        if self._reply:
            self._reply.deleteLater()
    @Slot(QNetworkReply.NetworkError)
    def on_error(self, _: QNetworkReply.NetworkError):
        if self._reply:
            self.errorOccurred.emit(self._reply.errorString())
        else:
            self.errorOccurred.emit("Unknown error")
