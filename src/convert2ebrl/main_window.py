#  Copyright (c) 2025. American Printing House for the Blind.
#
# This file is part of Convert2EBRL.
# Convert2EBRL is free software: you can redistribute it and/or modify it under the terms of the GNU General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# Convert2EBRL is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License for more details.
# You should have received a copy of the GNU General Public License along with Convert2EBRL. If not, see <https://www.gnu.org/licenses/>.

from PySide6.QtCore import QUrl
from PySide6.QtGui import QAction
from PySide6.QtWidgets import QMainWindow

from convert2ebrl.brf_to_ebrf import Brf2EbrfWidget
from convert2ebrl.update_checker import UpdateChecker


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Convert BRF to eBraille")
        self.setCentralWidget(Brf2EbrfWidget())
        update_checker = UpdateChecker(self)
        update_check_action = QAction("Check for updates", self)
        update_check_action.triggered.connect(lambda _: update_checker.check_for_update(QUrl("https://download.brailleblaster-ng.app/metadata.properties")))
        menu = self.menuBar()
        help_menu = menu.addMenu("Help")
        help_menu.addAction(update_check_action)