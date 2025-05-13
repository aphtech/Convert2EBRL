#  Copyright (c) 2025. American Printing House for the Blind.
#
# This file is part of Convert2EBRL.
# Convert2EBRL is free software: you can redistribute it and/or modify it under the terms of the GNU General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# Convert2EBRL is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License for more details.
# You should have received a copy of the GNU General Public License along with Convert2EBRL. If not, see <https://www.gnu.org/licenses/>.

from PySide6.QtCore import QObject, QUrl, Slot
from PySide6.QtNetwork import QNetworkAccessManager, QNetworkRequest, QNetworkReply


class UpdateChecker(QObject):
    def __init__(self, parent: QObject|None = None):
        super().__init__(parent)
        self.network_manager = QNetworkAccessManager(self)
        self.reply = None
    def check_for_update(self, update_url: QUrl):
        self.reply = self.network_manager.get(QNetworkRequest(update_url))
    @Slot()
    def on_ready_read(self):
        if self.reply:
            if self.reply.error() == QNetworkReply.NetworkError.NoError:
                response_text = self.reply.readAll()
                print(response_text)
    @Slot()
    def on_finished(self):
        if self.reply:
            self.reply.deleteLater()
