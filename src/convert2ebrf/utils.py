#  Copyright (c) 2024. American Printing House for the Blind.
#
# This file is part of Convert2EBRF.
# Convert2EBRF is free software: you can redistribute it and/or modify it under the terms of the GNU General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# Convert2EBRF is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License for more details.
# You should have received a copy of the GNU General Public License along with Convert2EBRF. If not, see <https://www.gnu.org/licenses/>.
from dataclasses import dataclass

from PySide6.QtCore import QRunnable, Slot

from brf2ebrf.common import PageNumberPosition


@dataclass(frozen=True)
class SettingsProfile:
    id: str
    name: str
    detect_runningheads: bool
    cells_per_line: int
    lines_per_page: int
    odd_bpn_position: PageNumberPosition
    even_bpn_position: PageNumberPosition
    odd_ppn_position: PageNumberPosition
    even_ppn_position: PageNumberPosition


class RunnableAdapter(QRunnable):
    def __init__(self, fn, *args, **kwargs):
        super().__init__()
        self.fn = fn
        self.args = args
        self.kwargs = kwargs

    @Slot()
    def run(self):
        self.fn(*self.args, **self.kwargs)
