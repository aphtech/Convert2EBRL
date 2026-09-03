#  Copyright (c) 2026. American Printing House for the Blind.
#
# This file is part of Convert2EBRL.
# Convert2EBRL is free software: you can redistribute it and/or modify it under the terms of the GNU General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# Convert2EBRL is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License for more details.
# You should have received a copy of the GNU General Public License along with Convert2EBRL. If not, see <https://www.gnu.org/licenses/>.
import json

from PySide6.QtCore import QObject, QUrl, QUrlQuery, Slot, Signal
from PySide6.QtNetwork import QNetworkAccessManager, QNetworkRequest, QNetworkReply


class OpenLibrary(QObject):
    errorOccurred = Signal(str)
    def __init__(self, /, parent: QObject|None = None):
        super().__init__(parent)
        self._network_manager = QNetworkAccessManager(self)
        self._reply = None

    def search(self, isbn: str):
        query = QUrlQuery()
        query.addQueryItem("isbn", isbn)
        query.addQueryItem("fields", "*,editions")
        query_url = QUrl("https://openlibrary.org/search.json")
        query_url.setQuery(query)
        self._reply = self._network_manager.get(QNetworkRequest(query_url))
        self._reply.readyRead.connect(self.on_ready_read)
        self._reply.finished.connect(self.on_finished)
        self._reply.errorOccurred.connect(self.on_error_occurred)
    @Slot()
    def on_ready_read(self):
        if reply := self._reply:
            if reply.error() == QNetworkReply.NetworkError.NoError and reply.attribute(QNetworkRequest.Attribute.HttpStatusCodeAttribute) == 200:
                json_doc = json.loads(reply.readAll().toStdString())
                print(json.dumps(json_doc, indent=4))
    @Slot()
    def on_finished(self):
        if reply := self._reply:
            reply.deleteLater()
    @Slot(QNetworkReply.NetworkError)
    def on_error_occurred(self, _: QNetworkReply.NetworkError):
        if reply := self._reply:
            self.errorOccurred.emit(reply.errorString())
        else:
            self.errorOccurred.emit("Unknown error")