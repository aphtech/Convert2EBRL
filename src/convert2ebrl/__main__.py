#  Copyright (c) 2024. American Printing House for the Blind.
#
# This file is part of Convert2EBRL.
# Convert2EBRL is free software: you can redistribute it and/or modify it under the terms of the GNU General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# Convert2EBRL is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License for more details.
# You should have received a copy of the GNU General Public License along with Convert2EBRL. If not, see <https://www.gnu.org/licenses/>.

import logging
import os.path
import sys
from collections.abc import Sequence
from pathlib import Path

from PySide6.QtCore import QSettings, QTimer
from PySide6.QtWidgets import QApplication, QMessageBox
# noinspection PyUnresolvedReferences
from __feature__ import snake_case, true_property

from convert2ebrl.brf_to_ebrf import Brf2EbrfDialog
from convert2ebrl.hash_utils import get_file_hash
from convert2ebrl.settings import PROFILES_FILE_NAME
from convert2ebrl.settings.defaults import DEFAULT_SETTINGS_PROFILES_LIST
from convert2ebrl.utils import save_settings_profiles, get_app_config_path

def check_release(exe_file_name: str) -> bool:
    exe_hash = get_file_hash(exe_file_name).strip()
    app_dir = os.path.dirname(exe_file_name)
    hash_path = Path(os.path.join(app_dir, "release.hash"))
    return hash_path.exists() and Path(hash_path).read_text(encoding="UTF-8").strip() == exe_hash

def run_app(args: Sequence[str]):
    logging.basicConfig(
        level=logging.INFO, format="%(levelname)s:%(asctime)s:%(module)s:%(message)s"
    )
    logging.debug(f"Executable hash: {get_file_hash(sys.argv[0])}")
    release_build = check_release(sys.argv[0])
    logging.info(f"Release build: {release_build}")
    app = QApplication(args)
    app.organization_name = "American Printing House for the Blind"
    app.organization_domain = "aph.org"
    app.application_name = "Convert2EBRL"
    QSettings.set_default_format(QSettings.Format.IniFormat)
    profiles_path = get_app_config_path().joinpath(PROFILES_FILE_NAME)
    if not profiles_path.exists():
        save_settings_profiles(DEFAULT_SETTINGS_PROFILES_LIST)
    def starting_app():
        if not release_build:
            QMessageBox.warning(None, "Not for production use!", "This is not a production ready build and is only for testing purposes. No other use is recommended and is at the user's own risk.")
        w = Brf2EbrfDialog()
        w.show()

    QTimer.single_shot(0, starting_app)
    app.exec()


def main():
    run_app(sys.argv)


if __name__ == "__main__":
    main()
