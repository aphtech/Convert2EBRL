#  Copyright (c) 2025. American Printing House for the Blind.
#
# This file is part of Convert2EBRL.
# Convert2EBRL is free software: you can redistribute it and/or modify it under the terms of the GNU General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# Convert2EBRL is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License for more details.
# You should have received a copy of the GNU General Public License along with Convert2EBRL. If not, see <https://www.gnu.org/licenses/>.

from PySide6.QtCore import QUrl
from PySide6.QtGui import QAction, QDesktopServices
from PySide6.QtWidgets import QMainWindow, QMessageBox, QApplication

from convert2ebrl.brf_to_ebrf import Brf2EbrfWidget
from convert2ebrl.log_viewer import LogViewerDialog
from convert2ebrl.update_checker import UpdateChecker
from convert2ebrl.utils import make_qurl


class MainWindow(QMainWindow):
    def __init__(self, download_site: str):
        super().__init__()
        self.setWindowTitle("Convert BRF to eBraille")
        self.setCentralWidget(Brf2EbrfWidget())

        self._log_viewer = None
        log_view_action = QAction("View log", self)
        log_view_action.triggered.connect(lambda _: self._open_log_viewer())

        update_checker = UpdateChecker(self)
        def on_update_available(v):
            if QMessageBox.question(self, "Update available",
                                 f"A new version {v} of the software is available. Would you like to go to the download site?") == QMessageBox.StandardButton.Yes:
                QDesktopServices.openUrl(QUrl(QApplication.instance().property("home_page")))
        update_checker.updateAvailable.connect(on_update_available)
        update_checker.noUpdateAvailable.connect(lambda: QMessageBox.information(self, "No updates", "You are running the latest version of the software."))
        update_checker.errorOccurred.connect(lambda x: QMessageBox.warning(self, "Unable to check for updates.", "There was a problem whilst checking for updates, please try again later."))
        update_check_action = QAction("Check for updates", self)
        download_url = make_qurl(download_site, "metadata.properties")
        update_check_action.triggered.connect(lambda _: update_checker.check_for_update(download_url))

        def show_about():
            QMessageBox.about(self, QApplication.applicationName(), f"{QApplication.applicationVersion()} built on {str(QApplication.instance().property('build_date'))}\nCopyright (C) 2026 {QApplication.organizationName()}")
        about_action = QAction("About", self)
        about_action.triggered.connect(lambda _: show_about())

        menu = self.menuBar()
        help_menu = menu.addMenu("&Help")
        help_menu.addAction(log_view_action)
        help_menu.addAction(update_check_action)
        help_menu.addAction(about_action)
    def _open_log_viewer(self):
        if not self._log_viewer:
            self._log_viewer = LogViewerDialog(self)
        self._log_viewer.show()
        self._log_viewer.raise_()
        self._log_viewer.activateWindow()
    def closeEvent(self, event, /):
        super().closeEvent(event)
        QApplication.quit()
