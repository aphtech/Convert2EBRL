#  Copyright (c) 2024. American Printing House for the Blind.
#
# This file is part of Convert2EBRL.
# Convert2EBRL is free software: you can redistribute it and/or modify it under the terms of the GNU General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# Convert2EBRL is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License for more details.
# You should have received a copy of the GNU General Public License along with Convert2EBRL. If not, see <https://www.gnu.org/licenses/>.
import posixpath
from collections.abc import Iterable
from pathlib import Path

from PySide6.QtCore import QRunnable, Slot, QSettings, QStandardPaths, QUrl
from brf2ebrl.common import PageNumberPosition

from convert2ebrl.settings import SettingsProfile, PROFILES_FILE_NAME
from convert2ebrl.settings.defaults import DEFAULT_SETTINGS_PROFILE
from convert2ebrl.settings.keys import PROFILE_NAME, PROFILE_CELLS_PER_LINE, PROFILE_LINES_PER_PAGE, \
    PROFILE_ODD_BPN_POSITION, PROFILE_EVEN_BPN_POSITION, PROFILE_ODD_PPN_POSITION, \
    PROFILE_EVEN_PPN_POSITION, PROFILE_DETECT_RUNNINGHEADS


def get_app_config_path(create: bool = True) -> Path:
    config_path = Path(QStandardPaths.writableLocation(QStandardPaths.StandardLocation.AppDataLocation))
    if create:
        config_path.mkdir(parents=True, exist_ok=True)
    return config_path

class RunnableAdapter(QRunnable):
    def __init__(self, fn, *args, **kwargs):
        super().__init__()
        self.fn = fn
        self.args = args
        self.kwargs = kwargs

    @Slot()
    def run(self):
        self.fn(*self.args, **self.kwargs)


def save_settings_profiles(profiles: Iterable[SettingsProfile], clear_existing: bool = False):
    settings = QSettings(str(get_app_config_path().joinpath(PROFILES_FILE_NAME)), QSettings.Format.IniFormat)
    if clear_existing:
        settings.clear()
    for profile in profiles:
        settings.beginGroup(str(profile.id))
        save_settings_profile(settings, profile)
        settings.endGroup()
    settings.sync()


def save_settings_profile(settings, profile):
    settings.setValue(PROFILE_NAME, profile.name)
    settings.setValue(PROFILE_DETECT_RUNNINGHEADS, profile.detect_runningheads)
    settings.setValue(PROFILE_CELLS_PER_LINE, profile.cells_per_line)
    settings.setValue(PROFILE_LINES_PER_PAGE, profile.lines_per_page)
    settings.setValue(PROFILE_ODD_BPN_POSITION, profile.odd_bpn_position.name)
    settings.setValue(PROFILE_EVEN_BPN_POSITION, profile.even_bpn_position.name)
    settings.setValue(PROFILE_ODD_PPN_POSITION, profile.odd_ppn_position.name)
    settings.setValue(PROFILE_EVEN_PPN_POSITION, profile.even_ppn_position.name)


def load_settings_profiles() -> Iterable[SettingsProfile]:
    profiles = []
    settings = QSettings(str(get_app_config_path().joinpath(PROFILES_FILE_NAME)), QSettings.Format.IniFormat)
    profile_ids = settings.childGroups()
    for profile_id in profile_ids:
        settings.beginGroup(profile_id)
        profile = load_settings_profile(settings)
        if profile.name != DEFAULT_SETTINGS_PROFILE.name:
            profiles.append(profile)
        settings.endGroup()
    return profiles


def load_settings_profile(settings):
    name = settings.value(PROFILE_NAME, DEFAULT_SETTINGS_PROFILE.name)
    detect_runningheads = settings.value(PROFILE_DETECT_RUNNINGHEADS, DEFAULT_SETTINGS_PROFILE.detect_runningheads,
                                         type=bool)
    cpl = settings.value(PROFILE_CELLS_PER_LINE, DEFAULT_SETTINGS_PROFILE.cells_per_line, type=int)
    lpp = settings.value(PROFILE_LINES_PER_PAGE, DEFAULT_SETTINGS_PROFILE.lines_per_page, type=int)
    odd_bpn = PageNumberPosition[settings.value(PROFILE_ODD_BPN_POSITION, DEFAULT_SETTINGS_PROFILE.odd_bpn_position)]
    even_bpn = PageNumberPosition[settings.value(PROFILE_EVEN_BPN_POSITION, DEFAULT_SETTINGS_PROFILE.even_bpn_position)]
    odd_ppn = PageNumberPosition[settings.value(PROFILE_ODD_PPN_POSITION, DEFAULT_SETTINGS_PROFILE.even_ppn_position)]
    even_ppn = PageNumberPosition[settings.value(PROFILE_EVEN_PPN_POSITION, DEFAULT_SETTINGS_PROFILE.even_ppn_position)]
    return SettingsProfile(name=name, detect_runningheads=detect_runningheads, cells_per_line=cpl,
                           lines_per_page=lpp, odd_bpn_position=odd_bpn, even_bpn_position=even_bpn,
                           odd_ppn_position=odd_ppn, even_ppn_position=even_ppn)

def make_qurl(base: str, extra: str) -> QUrl:
    url = QUrl(base)
    url.setPath(posixpath.join(url.path(), extra))
    return url