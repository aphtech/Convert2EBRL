#  Copyright (c) 2024. American Printing House for the Blind.
#
# This file is part of Convert2EBRF.
# Convert2EBRF is free software: you can redistribute it and/or modify it under the terms of the GNU General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# Convert2EBRF is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License for more details.
# You should have received a copy of the GNU General Public License along with Convert2EBRF. If not, see <https://www.gnu.org/licenses/>.

"""
Convert2EBRF application
"""
import logging
import sys

try:
    from importlib import metadata as importlib_metadata
except ImportError:
    # Backwards compatibility - importlib.metadata was added in Python 3.8
    import importlib_metadata

from collections.abc import Sequence

from PySide6.QtWidgets import QApplication
# noinspection PyUnresolvedReferences
from __feature__ import snake_case, true_property

from convert2ebrf.brf_to_ebrf import Brf2EbrfDialog

def main():
    logging.basicConfig(
        level=logging.INFO, format="%(levelname)s:%(asctime)s:%(module)s:%(message)s"
    )
    # Linux desktop environments use app's .desktop file to integrate the app
    # to their application menus. The .desktop file of this app will include
    # StartupWMClass key, set to app's formal name, which helps associate
    # app's windows to its menu item.
    #
    # For association to work any windows of the app must have WMCLASS
    # property set to match the value set in app's desktop file. For PySide2
    # this is set with setApplicationName().

    # Find the name of the module that was used to start the app
    app_module = sys.modules['__main__'].__package__
    # Retrieve the app's metadata
    metadata = importlib_metadata.metadata(app_module)

    app = QApplication(sys.argv)
    app.organization_name = "American Printing House for the Blind"
    app.organization_domain = "aph.org"
    app.application_name = metadata['Formal-Name']
    w = Brf2EbrfDialog()
    w.show()
    sys.exit(app.exec())