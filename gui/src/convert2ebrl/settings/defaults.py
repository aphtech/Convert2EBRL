#  Copyright (c) 2024. American Printing House for the Blind.
#
# This file is part of Convert2EBRL.
# Convert2EBRL is free software: you can redistribute it and/or modify it under the terms of the GNU General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# Convert2EBRL is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License for more details.
# You should have received a copy of the GNU General Public License along with Convert2EBRL. If not, see <https://www.gnu.org/licenses/>.
from pathlib import Path
from brf2ebrl.common import PageNumberPosition
from convert2ebrl.settings import SettingsProfile

CONVERSION_LAST_DIR = str(Path.home())
DEFAULT_SETTINGS_PROFILE = SettingsProfile(name="")
DEFAULT_SETTINGS_PROFILES_LIST = (
    SettingsProfile(name="APH Interpoint",
                    odd_bpn_position=PageNumberPosition.BOTTOM_RIGHT, even_bpn_position=PageNumberPosition.NONE,
                    odd_ppn_position=PageNumberPosition.TOP_RIGHT, even_ppn_position=PageNumberPosition.TOP_RIGHT),
    SettingsProfile(name="APH Single Sided",
                    odd_bpn_position=PageNumberPosition.BOTTOM_RIGHT, even_bpn_position=PageNumberPosition.BOTTOM_RIGHT,
                    odd_ppn_position=PageNumberPosition.TOP_RIGHT, even_ppn_position=PageNumberPosition.TOP_RIGHT))
