#  Copyright (c) 2024. American Printing House for the Blind.
#
# This file is part of Convert2EBRF.
# Convert2EBRF is free software: you can redistribute it and/or modify it under the terms of the GNU General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# Convert2EBRF is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License for more details.
# You should have received a copy of the GNU General Public License along with Convert2EBRF. If not, see <https://www.gnu.org/licenses/>.

import os
from collections.abc import Iterable
from dataclasses import replace

from PySide6.QtCore import QObject, Slot, Signal, QThreadPool, QSettings
from PySide6.QtGui import QAction
from PySide6.QtWidgets import QWidget, QFormLayout, QCheckBox, QDialog, QDialogButtonBox, QVBoxLayout, \
    QProgressDialog, QMessageBox, QTabWidget, QSpinBox, QFileDialog, QComboBox, QHBoxLayout, QMenu, QPushButton, QLabel, \
    QInputDialog
# noinspection PyUnresolvedReferences
from __feature__ import snake_case, true_property
from brf2ebrf.common import PageLayout, PageNumberPosition

from convert2ebrf.convert_task import ConvertTask
from convert2ebrf.settings import SettingsProfile
from convert2ebrf.settings.defaults import CONVERSION_LAST_DIR as DEFAULT_LAST_DIR, DEFAULT_SETTINGS_PROFILES_LIST
from convert2ebrf.settings.keys import CONVERSION_LAST_DIR as LAST_DIR_SETTING_KEY
from convert2ebrf.utils import RunnableAdapter, load_settings_profiles, save_settings_profiles, load_settings_profile, \
    save_settings_profile
from convert2ebrf.widgets import FilePickerWidget


class ConversionGeneralSettingsWidget(QWidget):
    inputBrfChanged = Signal(str)
    imagesDirectoryChanged = Signal(str)
    outputEbrfChanged = Signal(str)

    def __init__(self, parent: QObject = None):
        super().__init__(parent)
        layout = QFormLayout(self)
        self._input_type_combo = QComboBox()
        self._input_type_combo.editable = False
        self._input_type_combo.add_items(["List of BRF", "Directory of BRF"])
        layout.add_row("Input type", self._input_type_combo)
        self._input_brf_edit = FilePickerWidget(self._get_input_brf_from_user)
        layout.add_row("Input BRF", self._input_brf_edit)
        self._include_images_checkbox = QCheckBox()
        layout.add_row("Include images", self._include_images_checkbox)

        def get_images_dir_from_user(x) -> list[str]:
            settings = QSettings()
            default_dir = str(settings.value(LAST_DIR_SETTING_KEY, DEFAULT_LAST_DIR))
            image_dir = QFileDialog.get_existing_directory(parent=x, dir=default_dir)
            if image_dir:
                settings.set_value(LAST_DIR_SETTING_KEY, image_dir)
            return [image_dir]

        self._image_dir_edit = FilePickerWidget(
            get_images_dir_from_user)
        layout.add_row("Image directory", self._image_dir_edit)

        def get_output_ebrf_file_from_user(x) -> list[str]:
            settings = QSettings()
            default_dir = str(settings.value(LAST_DIR_SETTING_KEY, DEFAULT_LAST_DIR))
            save_path = QFileDialog.get_save_file_name(
                parent=x, dir=default_dir, filter="eBraille Files (*.zip)",
                options=QFileDialog.Option.DontConfirmOverwrite
            )[0]
            if save_path:
                settings.set_value(LAST_DIR_SETTING_KEY, os.path.dirname(save_path))
            return [save_path]

        self._output_ebrf_edit = FilePickerWidget(get_output_ebrf_file_from_user)
        layout.add_row("Output EBRF", self._output_ebrf_edit)
        self._update_include_images_state(self._include_images_checkbox.checked)
        def restore_from_settings():
            settings = QSettings()
            self._input_type_combo.current_index = int(bool(settings.value("Conversion/input_type", defaultValue=False, type=bool)))
        restore_from_settings()
        def on_input_type_changed(index):
            settings = QSettings()
            settings.set_value("Conversion/input_type", bool(index))
        self._input_type_combo.currentIndexChanged.connect(on_input_type_changed)
        self._include_images_checkbox.toggled.connect(self._update_include_images_state)
        self._input_type_combo.currentIndexChanged.connect(self._clear_input_brf)
        self._input_brf_edit.fileChanged.connect(self.inputBrfChanged.emit)
        self._image_dir_edit.fileChanged.connect(self.imagesDirectoryChanged.emit)
        self._output_ebrf_edit.fileChanged.connect(self.outputEbrfChanged.emit)

    @Slot(bool)
    def _update_include_images_state(self, checked: bool):
        self._image_dir_edit.enabled = checked
        if not checked:
            self._image_dir_edit.file_name = ""

    def _get_input_brf_from_user(self, x) -> list[str]:
        settings = QSettings()
        default_dir = str(settings.value(LAST_DIR_SETTING_KEY, DEFAULT_LAST_DIR))
        if self._input_type_combo.current_index:
            input_dir = QFileDialog.get_existing_directory(
                parent=x, dir=default_dir
            )
            if input_dir:
                settings.set_value(LAST_DIR_SETTING_KEY, input_dir)
            return [input_dir]
        else:
            input_files = QFileDialog.get_open_file_names(
                parent=x, dir=default_dir, filter="Braille Ready Files (*.brf)"
            )[0]
            if input_files:
                settings.set_value(LAST_DIR_SETTING_KEY, os.path.dirname(input_files[0]))
            return input_files

    @property
    def input_brfs(self) -> list[str]:
        return self._input_brf_edit.files

    @input_brfs.setter
    def input_brfs(self, value: list[str]):
        self._input_type_combo.current_index = 1 if len(value) == 1 and os.path.isdir(value[0]) else 0
        self._input_brf_edit.files = value

    def _clear_input_brf(self):
        self._input_brf_edit.files = []

    @property
    def image_directory(self) -> str | None:
        return self._image_dir_edit.file_name if self._include_images_checkbox.checked else None

    @image_directory.setter
    def image_directory(self, value: str | None):
        if value is None:
            self._include_images_checkbox.checked = False
        else:
            self._include_images_checkbox.checked = True
            self._image_dir_edit.file_name = value

    @property
    def output_ebrf(self) -> str:
        return self._output_ebrf_edit.file_name

    @output_ebrf.setter
    def output_ebrf(self, value: str):
        self._output_ebrf_edit.text = value


_PAGE_NUMBER_POSITIONS_DICT = {
    PageNumberPosition.NONE: "None",
    PageNumberPosition.TOP_LEFT: "Top left",
    PageNumberPosition.TOP_RIGHT: "Top right",
    PageNumberPosition.BOTTOM_LEFT: "Bottom left",
    PageNumberPosition.BOTTOM_RIGHT: "Bottom right"
}


class ConversionPageSettingsWidget(QWidget):
    detectRunningHeadsChanged = Signal(bool)
    cellsPerLineChanged = Signal(int)
    linesPerPageChanged = Signal(int)
    oddBraillePageNumberChanged = Signal(PageNumberPosition)
    evenBraillePageNumberChanged = Signal(PageNumberPosition)
    oddPrintPageNumberChanged = Signal(PageNumberPosition)
    evenPrintPageNumberChanged = Signal(PageNumberPosition)
    isValidChanged = Signal(bool)

    def __init__(self, parent: QObject = None):
        super().__init__(parent=parent)
        self._is_valid = False
        layout = QFormLayout(self)
        self._detect_running_heads_checkbox = QCheckBox()
        self._detect_running_heads_checkbox.checked = True
        layout.add_row("Has running heads", self._detect_running_heads_checkbox)
        self._cells_per_line_spinbox = QSpinBox()
        self._cells_per_line_spinbox.set_range(10, 100)
        self._cells_per_line_spinbox.single_step = 1
        self._cells_per_line_spinbox.value = 40
        layout.add_row("Cells per line", self._cells_per_line_spinbox)
        self._lines_per_page_spinbox = QSpinBox()
        self._lines_per_page_spinbox.set_range(10, 100)
        self._lines_per_page_spinbox.value = 25
        self._lines_per_page_spinbox.single_step = 1
        layout.add_row("Lines per page", self._lines_per_page_spinbox)

        def create_page_number_position_combo(default_selection: PageNumberPosition = PageNumberPosition.NONE):
            combo = QComboBox()
            combo.editable = False
            for p, t in _PAGE_NUMBER_POSITIONS_DICT.items():
                combo.add_item(t, p)
            combo.current_text = _PAGE_NUMBER_POSITIONS_DICT[default_selection]
            return combo

        self._odd_bpn_position = create_page_number_position_combo(PageNumberPosition.BOTTOM_RIGHT)
        layout.add_row("Odd Braille page number", self._odd_bpn_position)
        self._even_bpn_position = create_page_number_position_combo()
        layout.add_row("Even Braille page number", self._even_bpn_position)
        self._odd_ppn_position = create_page_number_position_combo(PageNumberPosition.TOP_RIGHT)
        layout.add_row("Odd print page number", self._odd_ppn_position)
        self._even_ppn_position = create_page_number_position_combo()
        layout.add_row("Even print page number", self._even_ppn_position)
        self._update_validity()
        self._detect_running_heads_checkbox.toggled.connect(self.detectRunningHeadsChanged.emit)
        self._cells_per_line_spinbox.valueChanged.connect(self.cellsPerLineChanged.emit)
        self._lines_per_page_spinbox.valueChanged.connect(self.linesPerPageChanged.emit)
        def form_update(change_signal: Signal, value: PageNumberPosition):
            change_signal.emit(value)
            self._update_validity()
        self._odd_bpn_position.currentIndexChanged.connect(
            lambda x: form_update(self.oddBraillePageNumberChanged, self._odd_bpn_position.item_data(x)))
        self._even_bpn_position.currentIndexChanged.connect(
            lambda x: form_update(self.evenBraillePageNumberChanged, self._even_bpn_position.item_data(x)))
        self._odd_ppn_position.currentIndexChanged.connect(
            lambda x: form_update(self.oddPrintPageNumberChanged, self._odd_ppn_position.item_data(x)))
        self._even_ppn_position.currentIndexChanged.connect(
            lambda x: form_update(self.evenPrintPageNumberChanged, self._even_ppn_position.item_data(x)))

    def _update_validity(self):
        old_validity = self._is_valid
        new_validity = (self.odd_braille_page_number_position == PageNumberPosition.NONE or self.odd_braille_page_number_position != self.odd_print_page_number_position) and (self.even_braille_page_number_position == PageNumberPosition.NONE or self.even_braille_page_number_position != self.even_print_page_number_position)
        if old_validity != new_validity:
            self._is_valid = new_validity
            self.isValidChanged.emit(new_validity)

    @property
    def is_valid(self) -> bool:
        return self._is_valid

    @property
    def detect_running_heads(self) -> bool:
        return self._detect_running_heads_checkbox.checked

    @detect_running_heads.setter
    def detect_running_heads(self, value: bool):
        self._detect_running_heads_checkbox.checked = value

    @property
    def cells_per_line(self) -> int:
        return self._cells_per_line_spinbox.value

    @cells_per_line.setter
    def cells_per_line(self, value: int):
        self._cells_per_line_spinbox.value = value

    @property
    def lines_per_page(self) -> int:
        return self._lines_per_page_spinbox.value

    @lines_per_page.setter
    def lines_per_page(self, value: int):
        self._lines_per_page_spinbox.value = value

    @property
    def odd_braille_page_number_position(self) -> PageNumberPosition:
        return self._odd_bpn_position.current_data()

    @odd_braille_page_number_position.setter
    def odd_braille_page_number_position(self, value: PageNumberPosition):
        self._odd_bpn_position.current_index = self._odd_bpn_position.find_data(value)

    @property
    def even_braille_page_number_position(self) -> PageNumberPosition:
        return self._even_bpn_position.current_data()

    @even_braille_page_number_position.setter
    def even_braille_page_number_position(self, value: PageNumberPosition):
        self._even_bpn_position.current_index = self._even_bpn_position.find_data(value)

    @property
    def odd_print_page_number_position(self) -> PageNumberPosition:
        return self._odd_ppn_position.current_data()

    @odd_print_page_number_position.setter
    def odd_print_page_number_position(self, value: PageNumberPosition):
        self._odd_ppn_position.current_index = self._odd_ppn_position.find_data(value)

    @property
    def even_print_page_number_position(self) -> PageNumberPosition:
        return self._even_ppn_position.current_data()

    @even_print_page_number_position.setter
    def even_print_page_number_position(self, value: PageNumberPosition):
        self._even_ppn_position.current_index = self._even_ppn_position.find_data(value)


class SettingsProfilesWidget(QWidget):
    currentSettingsProfileChanged = Signal(SettingsProfile)

    def __init__(self, parent: QObject = None):
        self._custom_profile = SettingsProfile(name="")
        super().__init__(parent)
        orig_profiles = load_settings_profiles()
        layout = QHBoxLayout(self)
        tool_label = QLabel("Conversion profile")
        layout.add_widget(tool_label)
        self._profile_combo = QComboBox()
        self._profile_combo.editable = False
        self._profile_combo.placeholder_text = "Custom"
        layout.add_widget(self._profile_combo)
        tool_label.set_buddy(self._profile_combo)
        def update_profiles(profiles: Iterable[SettingsProfile], sync_settings: bool = False):
            if sync_settings:
                save_settings_profiles(profiles, clear_existing=True)
            self._profile_combo.clear()
            for profile in profiles:
                self._profile_combo.add_item(profile.name, profile)
            self._profile_combo.current_index = -1 if self._profile_combo.count < 0 else 0
        update_profiles(orig_profiles)
        profile_menu = QMenu(parent=self)
        def save_profile():
            while True:
                text, ok = QInputDialog.get_text(self, "Name the profile", "Profile name:")
                if not ok:
                    return
                if not text:
                    QMessageBox.warning(self, "Name empty", "A profile name cannot be empty, please provide a profile name.")
                    continue
                profiles = list(self.settings_profiles)
                profile = replace(self.current_settings_profile, name=text)
                if text in [p.name for p in profiles]:
                    result = QMessageBox.question(self, "Overwrite profile", f"A profile named {text} already exists, are you sure you want to overwrite it?")
                    if result != QMessageBox.StandardButton.Yes:
                        continue
                    profiles = [p for p in profiles if p.name != text]
                profiles.insert(0, profile)
                update_profiles(profiles, sync_settings=True)
                return
        profile_menu.add_action("Save profile...", save_profile)
        def delete_profile(profile: SettingsProfile):
            result = QMessageBox.question(self, "Delete profile", f"Are you sure you want to delete profile {profile.name}")
            if result == QMessageBox.StandardButton.Yes:
                profiles = list(self.settings_profiles)
                profiles.remove(profile)
                update_profiles(profiles, sync_settings=True)
        delete_action = QAction("Delete profile...", self)
        self._profile_combo.currentIndexChanged.connect(lambda x: delete_action.set_disabled(x < 0))
        delete_action.triggered.connect(lambda: delete_profile(self._profile_combo.current_data()))
        profile_menu.add_action(delete_action)
        def reset_profiles():
            result = QMessageBox.question(self, "Reset profiles", "Are you sure you want to reset profiles to defaults?")
            if result == QMessageBox.StandardButton.Yes:
                update_profiles(DEFAULT_SETTINGS_PROFILES_LIST, sync_settings=True)
        profile_menu.add_action("Reset profiles...", reset_profiles)
        profile_menu_button = QPushButton("...")
        profile_menu_button.accessible_name = "Profiles menu"
        profile_menu_button.set_menu(profile_menu)
        layout.add_widget(profile_menu_button)
        # Notify of saved profile changes, custom profiles are notified in setter.
        self._profile_combo.currentIndexChanged.connect(lambda x: self.currentSettingsProfileChanged.emit(self._profile_combo.item_data(x)) if x >= 0 else None)

    @property
    def settings_profiles(self) -> Iterable[SettingsProfile]:
        return [self._profile_combo.item_data(i) for i in range(0,self._profile_combo.count)]

    @property
    def current_settings_profile(self) -> SettingsProfile:
        return self._custom_profile if self._profile_combo.current_index < 0 else self._profile_combo.current_data()

    @current_settings_profile.setter
    def current_settings_profile(self, value: SettingsProfile):
        new_index = self._profile_combo.find_text(value.name)
        if new_index < 0:
            self._custom_profile = value
        self._profile_combo.current_index = new_index
        if new_index < 0:
            self.currentSettingsProfileChanged.emit(value)


class Brf2EbrfDialog(QDialog):
    def __init__(self, parent: QObject = None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        self._profiles_tool = SettingsProfilesWidget()
        layout.add_widget(self._profiles_tool)
        self.window_title = "Convert BRF to eBraille"
        tab_widget = QTabWidget()
        self._brf2ebrf_form = ConversionGeneralSettingsWidget()
        tab_widget.add_tab(self._brf2ebrf_form, "General")
        self._page_settings_form = ConversionPageSettingsWidget()
        tab_widget.add_tab(self._page_settings_form, "Page settings")
        layout.add_widget(tab_widget)
        self.button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        b = self.button_box.button(QDialogButtonBox.StandardButton.Close)
        b.default = False
        b.auto_default = False
        self._convert_button = self.button_box.add_button("Convert", QDialogButtonBox.ButtonRole.ApplyRole)
        self._convert_button.default = True
        layout.add_widget(self.button_box)
        def restore_from_settings():
            settings = QSettings()
            if "ConverterLastProfile" in settings.child_groups():
                settings.begin_group("ConverterLastProfile")
                self._profiles_tool.current_settings_profile = load_settings_profile(settings)
                settings.end_group()
            self._on_settings_profile_changed(self._profiles_tool.current_settings_profile)
            self._update_validity()
        restore_from_settings()
        self._profiles_tool.currentSettingsProfileChanged.connect(self._on_settings_profile_changed)
        self.button_box.rejected.connect(self.reject)
        self._convert_button.clicked.connect(self.on_apply)
        self._brf2ebrf_form.inputBrfChanged.connect(lambda x: self._update_validity())
        self._brf2ebrf_form.imagesDirectoryChanged.connect(lambda x: self._update_validity())
        self._brf2ebrf_form.outputEbrfChanged.connect(lambda x: self._update_validity())
        self._page_settings_form.isValidChanged.connect(lambda x: self._update_validity())
        self._page_settings_form.detectRunningHeadsChanged.connect(lambda x: self._on_settings_changed(detect_runningheads=x))
        self._page_settings_form.cellsPerLineChanged.connect(lambda x: self._on_settings_changed(cells_per_line=x))
        self._page_settings_form.linesPerPageChanged.connect(lambda x: self._on_settings_changed(lines_per_page=x))
        self._page_settings_form.oddBraillePageNumberChanged.connect(lambda x: self._on_settings_changed(odd_bpn_position=x))
        self._page_settings_form.evenBraillePageNumberChanged.connect(lambda x: self._on_settings_changed(even_bpn_position=x))
        self._page_settings_form.oddPrintPageNumberChanged.connect(lambda x: self._on_settings_changed(odd_ppn_position=x))
        self._page_settings_form.evenPrintPageNumberChanged.connect(lambda x: self._on_settings_changed(even_ppn_position=x))

    def _on_settings_changed(self, **kwargs):
        current_profile = self._profiles_tool.current_settings_profile
        new_profile = replace(current_profile, **kwargs)
        if new_profile != current_profile:
            self._profiles_tool.current_settings_profile = replace(new_profile, name="")

    @Slot(SettingsProfile)
    def _on_settings_profile_changed(self, profile: SettingsProfile):
        settings = QSettings()
        settings.begin_group("ConverterLastProfile")
        save_settings_profile(settings, profile)
        settings.end_group()
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
        is_valid = self._page_settings_form.is_valid and all([general_settings.input_brfs != [], general_settings.image_directory != "",
                              general_settings.output_ebrf != ""])
        self._convert_button.enabled = is_valid

    @Slot()
    def on_apply(self):
        number_of_steps = 1000
        brf_list = [brf for f in self._brf2ebrf_form.input_brfs for brf in
                    ([os.path.join(f, b) for b in os.listdir(f)] if os.path.isdir(f) else [f])]
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
        pd = QProgressDialog("Conversion in progress", "Cancel", 0, number_of_steps)

        def update_progress(value: float):
            if not pd.was_canceled:
                pd.value = int(value * number_of_steps)

        def finished_converting():
            update_progress(1)
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
        t.errorRaised.connect(error_raised)
        QThreadPool.global_instance().start(
            RunnableAdapter(t, brf_list, output_ebrf, self._brf2ebrf_form.image_directory,
                            detect_running_heads=self._page_settings_form.detect_running_heads,
                            page_layout=page_layout))
