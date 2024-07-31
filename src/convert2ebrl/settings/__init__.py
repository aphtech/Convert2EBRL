#  Copyright (c) 2024. American Printing House for the Blind.
#
# This file is part of Convert2EBRL.
# Convert2EBRL is free software: you can redistribute it and/or modify it under the terms of the GNU General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# Convert2EBRL is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License for more details.
# You should have received a copy of the GNU General Public License along with Convert2EBRL. If not, see <https://www.gnu.org/licenses/>.
from dataclasses import dataclass, field
from uuid import UUID, uuid5
from brf2ebrl.common import PageNumberPosition

PROFILES_FILE_NAME = "profiles.ini"
SETTINGS_PROFILE_NAMESPACE = UUID("8c4d55b1-98c0-484c-8677-4a019353c3aa")


@dataclass(frozen=True)
class SettingsProfile:
    id: UUID = field(init=False)
    name: str
    detect_runningheads: bool = True
    cells_per_line: int = 40
    lines_per_page: int = 25
    odd_bpn_position: PageNumberPosition = PageNumberPosition.BOTTOM_RIGHT
    even_bpn_position: PageNumberPosition = PageNumberPosition.NONE
    odd_ppn_position: PageNumberPosition = PageNumberPosition.TOP_RIGHT
    even_ppn_position: PageNumberPosition = PageNumberPosition.NONE
    def __post_init__(self):
        object.__setattr__(self, "id", uuid5(SETTINGS_PROFILE_NAMESPACE, self.name))
