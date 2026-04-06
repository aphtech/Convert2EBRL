#  Copyright (c) 2024. American Printing House for the Blind.
#
# This file is part of Convert2EBRL.
# Convert2EBRL is free software: you can redistribute it and/or modify it under the terms of the GNU General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# Convert2EBRL is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License for more details.
# You should have received a copy of the GNU General Public License along with Convert2EBRL. If not, see <https://www.gnu.org/licenses/>.
import logging
import os
from collections.abc import Iterable
from dataclasses import replace
from pathlib import Path

from PySide6.QtCore import QObject, Slot, Signal, QThreadPool, QSettings, QCoreApplication
from PySide6.QtGui import QAction
from PySide6.QtWidgets import QWidget, QDialogButtonBox, QVBoxLayout, \
    QProgressDialog, QMessageBox, QTabWidget, QFileDialog, QComboBox, QHBoxLayout, QMenu, QPushButton, QLabel, \
    QInputDialog
from brf2ebrl.common import PageLayout
from brf2ebrl.parser import EBrailleParserOptions
from brf2ebrl.plugin import find_plugins

from convert2ebrl.convert_task import ConvertTask, Notification
from convert2ebrl.settings import SettingsProfile
from convert2ebrl.settings.defaults import DEFAULT_SETTINGS_PROFILES_LIST
from convert2ebrl.tabs.general_tab import ConversionGeneralSettingsWidget, expand_input_brfs
from convert2ebrl.tabs.metadata_tab import MetadataWidget
from convert2ebrl.tabs.page_settings_tab import ConversionPageSettingsWidget
from convert2ebrl.utils import RunnableAdapter, load_settings_profiles, save_settings_profiles, load_settings_profile, \
    save_settings_profile

DISCOVERED_PARSER_PLUGINS = find_plugins()

class SettingsProfilesWidget(QWidget):
    currentSettingsProfileChanged = Signal(SettingsProfile)

    def __init__(self, parent: QObject = None):
        super().__init__(parent)
        self._custom_profile = SettingsProfile(name="")
        orig_profiles = load_settings_profiles()
        layout = QHBoxLayout(self)
        tool_label = QLabel("Conversion profile")
        layout.addWidget(tool_label)
        self._profile_combo = QComboBox()
        self._profile_combo.setEditable(False)
        self._profile_combo.setPlaceholderText("Custom")
        layout.addWidget(self._profile_combo)
        tool_label.setBuddy(self._profile_combo)

        def update_profiles(profiles: Iterable[SettingsProfile], sync_settings: bool = False):
            if sync_settings:
                save_settings_profiles(profiles, clear_existing=True)
            self._profile_combo.clear()
            for profile in profiles:
                self._profile_combo.addItem(profile.name, profile)
            self._profile_combo.setCurrentIndex(-1 if self._profile_combo.count() < 0 else 0)

        update_profiles(orig_profiles)
        profile_menu = QMenu(parent=self)

        def save_profile():
            while True:
                text, ok = QInputDialog.getText(self, "Name the profile", "Profile name:")
                if not ok:
                    return
                if not text:
                    QMessageBox.warning(self, "Name empty",
                                        "A profile name cannot be empty, please provide a profile name.")
                    continue
                profiles = list(self.settings_profiles)
                profile = replace(self.current_settings_profile, name=text)
                if text in [p.name for p in profiles]:
                    result = QMessageBox.question(self, "Overwrite profile",
                                                  f"A profile named {text} already exists, are you sure you want to overwrite it?")
                    if result != QMessageBox.StandardButton.Yes:
                        continue
                    profiles = [p for p in profiles if p.name != text]
                profiles.insert(0, profile)
                update_profiles(profiles, sync_settings=True)
                return

        profile_menu.addAction("Save profile...", save_profile)

        def delete_profile(profile: SettingsProfile):
            result = QMessageBox.question(self, "Delete profile",
                                          f"Are you sure you want to delete profile {profile.name}")
            if result == QMessageBox.StandardButton.Yes:
                profiles = list(self.settings_profiles)
                profiles.remove(profile)
                update_profiles(profiles, sync_settings=True)

        delete_action = QAction("Delete profile...", self)
        self._profile_combo.currentIndexChanged.connect(lambda x: delete_action.setDisabled(x < 0))
        delete_action.triggered.connect(lambda: delete_profile(self._profile_combo.currentData()))
        profile_menu.addAction(delete_action)

        def reset_profiles():
            result = QMessageBox.question(self, "Reset profiles",
                                          "Are you sure you want to reset profiles to defaults?")
            if result == QMessageBox.StandardButton.Yes:
                update_profiles(DEFAULT_SETTINGS_PROFILES_LIST, sync_settings=True)

        profile_menu.addAction("Reset profiles...", reset_profiles)
        profile_menu_button = QPushButton("...")
        profile_menu_button.setAccessibleName("Profiles menu")
        profile_menu_button.setMenu(profile_menu)
        layout.addWidget(profile_menu_button)
        # Notify of saved profile changes, custom profiles are notified in setter.
        self._profile_combo.currentIndexChanged.connect(
            lambda x: self.currentSettingsProfileChanged.emit(self._profile_combo.itemData(x)) if x >= 0 else None)

    @property
    def settings_profiles(self) -> Iterable[SettingsProfile]:
        return [self._profile_combo.itemData(i) for i in range(0, self._profile_combo.count())]

    @property
    def current_settings_profile(self) -> SettingsProfile:
        return self._custom_profile if self._profile_combo.currentIndex() < 0 else self._profile_combo.currentData()

    @current_settings_profile.setter
    def current_settings_profile(self, value: SettingsProfile):
        new_index = self._profile_combo.findText(value.name)
        if new_index < 0:
            self._custom_profile = value
        self._profile_combo.setCurrentIndex(new_index)
        if new_index < 0:
            self.currentSettingsProfileChanged.emit(value)


class Brf2EbrfWidget(QWidget):
    def __init__(self, parent: QObject = None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        self._profiles_tool = SettingsProfilesWidget()
        layout.addWidget(self._profiles_tool)
        tab_widget = QTabWidget()
        self._brf2ebrf_form = ConversionGeneralSettingsWidget()
        tab_widget.addTab(self._brf2ebrf_form, "General")
        self._page_settings_form = ConversionPageSettingsWidget()
        tab_widget.addTab(self._page_settings_form, "Page settings")
        self._metadata_form = MetadataWidget()
        tab_widget.addTab(self._metadata_form, "Metadata")
        layout.addWidget(tab_widget)
        self.button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        b = self.button_box.button(QDialogButtonBox.StandardButton.Close)
        b.setDefault(False)
        b.setAutoDefault(False)
        self._convert_button = self.button_box.addButton("Convert", QDialogButtonBox.ButtonRole.ApplyRole)
        self._convert_button.setDefault(True)
        layout.addWidget(self.button_box)

        def restore_from_settings():
            settings = QSettings()
            if "ConverterLastProfile" in settings.childGroups():
                settings.beginGroup("ConverterLastProfile")
                self._profiles_tool.current_settings_profile = load_settings_profile(settings)
                settings.endGroup()
            self._on_settings_profile_changed(self._profiles_tool.current_settings_profile)
            self._update_validity()

        restore_from_settings()
        self._profiles_tool.currentSettingsProfileChanged.connect(self._on_settings_profile_changed)
        self.button_box.rejected.connect(QCoreApplication.quit)
        self._convert_button.clicked.connect(self.on_apply)
        self._brf2ebrf_form.inputBrfChanged.connect(lambda x: self._update_validity())
        self._brf2ebrf_form.imagesDirectoryChanged.connect(lambda x: self._update_validity())
        self._brf2ebrf_form.outputEbrfChanged.connect(lambda x: self._update_validity())
        self._page_settings_form.isValidChanged.connect(lambda x: self._update_validity())
        self._page_settings_form.detectRunningHeadsChanged.connect(
            lambda x: self._on_settings_changed(detect_runningheads=x))
        self._page_settings_form.cellsPerLineChanged.connect(lambda x: self._on_settings_changed(cells_per_line=x))
        self._page_settings_form.linesPerPageChanged.connect(lambda x: self._on_settings_changed(lines_per_page=x))
        self._page_settings_form.oddBraillePageNumberChanged.connect(
            lambda x: self._on_settings_changed(odd_bpn_position=x))
        self._page_settings_form.evenBraillePageNumberChanged.connect(
            lambda x: self._on_settings_changed(even_bpn_position=x))
        self._page_settings_form.oddPrintPageNumberChanged.connect(
            lambda x: self._on_settings_changed(odd_ppn_position=x))
        self._page_settings_form.evenPrintPageNumberChanged.connect(
            lambda x: self._on_settings_changed(even_ppn_position=x))

    def _on_settings_changed(self, **kwargs):
        current_profile = self._profiles_tool.current_settings_profile
        new_profile = replace(current_profile, **kwargs)
        if new_profile != current_profile:
            self._profiles_tool.current_settings_profile = replace(new_profile, name="")

    @Slot(SettingsProfile)
    def _on_settings_profile_changed(self, profile: SettingsProfile):
        settings = QSettings()
        settings.beginGroup("ConverterLastProfile")
        save_settings_profile(settings, profile)
        settings.endGroup()
        self._page_settings_form.detect_running_heads = profile.detect_runningheads
        self._page_settings_form.cells_per_line = profile.cells_per_line
        self._page_settings_form.lines_per_page = profile.lines_per_page
        self._page_settings_form.odd_braille_page_number_position = profile.odd_bpn_position
        self._page_settings_form.even_braille_page_number_position = profile.even_bpn_position
        self._page_settings_form.odd_print_page_number_position = profile.odd_ppn_position
        self._page_settings_form.even_print_page_number_position = profile.even_ppn_position

    @Slot()
    def _update_validity(self):
        general_settings = self._brf2ebrf_form
        is_valid = self._page_settings_form.is_valid and all(
            [general_settings.input_brfs != [], general_settings.image_directory != "",
             general_settings.output_ebrf != ""])
        self._convert_button.setEnabled(is_valid)

    @Slot()
    def on_apply(self):
        number_of_steps = 1000
        brf_list = expand_input_brfs(self._brf2ebrf_form.input_brfs)
        num_of_inputs = len(brf_list)
        output_ebrf = self._brf2ebrf_form.output_ebrf
        if os.path.exists(output_ebrf):
            overwrite_result = QMessageBox.question(
                self, "Overwrite existing file?",
                f"The output file {output_ebrf} already exists, do you want to overwrite it?"
            )
            if overwrite_result == QMessageBox.StandardButton.No:
                return
        page_layout = PageLayout(
            odd_braille_page_number=self._page_settings_form.odd_braille_page_number_position,
            even_braille_page_number=self._page_settings_form.even_braille_page_number_position,
            odd_print_page_number=self._page_settings_form.odd_print_page_number_position,
            even_print_page_number=self._page_settings_form.even_print_page_number_position,
            cells_per_line=self._page_settings_form.cells_per_line,
            lines_per_page=self._page_settings_form.lines_per_page
        )
        parser_options = {EBrailleParserOptions.images_path: self._brf2ebrf_form.image_directory,
                          EBrailleParserOptions.page_layout: page_layout,
                          EBrailleParserOptions.detect_running_heads: self._page_settings_form.detect_running_heads,
                          EBrailleParserOptions.metadata_entries: self._metadata_form.metadata_entries}
        pd = QProgressDialog("Conversion in progress", "Cancel", 0, number_of_steps)
        notifications = []

        def on_notification(notification: Notification):
            notifications.append(notification)

        def update_progress(value: float):
            if not pd.wasCanceled():
                pd.setValue(int(value * number_of_steps))

        def finished_converting():
            update_progress(1)
            if notifications:
                dlg = QMessageBox(QMessageBox.Icon.Warning, "Conversion complete but warnings issued",
                                  f"Your file has been converted and {output_ebrf} has been created.",
                                  buttons=QMessageBox.StandardButton.Ok)
                dlg.setDetailedText(notifications_as_text(notifications))
                btn = dlg.addButton("Save warnings to file", QMessageBox.ButtonRole.ActionRole)
                btn.clicked.disconnect()
                btn.clicked.connect(lambda x: save_notifications(dlg, notifications, os.path.dirname(output_ebrf)))
                dlg.exec()
            else:
                QMessageBox.information(None, "Conversion complete",
                                        f"Your file has been converted and {output_ebrf} has been created.")

        def error_raised(error: Exception):
            pd.cancel()
            QMessageBox.critical(None, "Error encountered", f"Encountered an error\n{error}")

        t = ConvertTask(self)
        pd.canceled.connect(t.cancel)
        t.started.connect(lambda: update_progress(0))
        t.progress.connect(lambda i, p: update_progress((i + p) / num_of_inputs))
        t.finished.connect(finished_converting)
        t.notify.connect(on_notification)
        t.errorRaised.connect(error_raised)
        QThreadPool.globalInstance().start(
            RunnableAdapter(t, list(DISCOVERED_PARSER_PLUGINS.values())[0], brf_list, output_ebrf, parser_options=parser_options))


def save_notifications(parent: QWidget | None, notifications: Iterable[Notification], default_dir: str):
    save_path = QFileDialog.getSaveFileName(parent, dir=default_dir, filter="Text file (*.txt)")[0]
    if save_path:
        try:
            Path(save_path).write_text(notifications_as_text(notifications), encoding="UTF-8")
        except Exception as e:
            print(e)
            QMessageBox.critical(parent, "Problem saving", f"Could not save to file {save_path}")


def notifications_as_text(notifications):
    return "\n".join(f"{logging.getLevelName(n.level)}: {n.message}" for n in notifications)
