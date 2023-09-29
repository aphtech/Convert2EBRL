from PySide6.QtCore import QObject
from PySide6.QtWidgets import QWidget, QFormLayout, QLineEdit, QCheckBox, QDialog, QDialogButtonBox, QVBoxLayout, \
    QMessageBox
# noinspection PyUnresolvedReferences
from __feature__ import snake_case, true_property


class Brf2EbrfWidget(QWidget):
    def __init__(self, parent: QObject = None):
        super().__init__(parent)
        layout = QFormLayout()
        layout.add_row("Input BRF", QLineEdit(self))
        self.include_images_checkbox = QCheckBox(self)
        layout.add_row("Include images", self.include_images_checkbox)
        self.image_dir_edit = QLineEdit(self)
        layout.add_row("Image directory", self.image_dir_edit)
        layout.add_row("Output EBRF", QLineEdit(self))
        self.set_layout(layout)
        self.update_include_images_state()
        self.include_images_checkbox.stateChanged.connect(self.update_include_images_state)

    def update_include_images_state(self):
        self.image_dir_edit.enabled = self.include_images_checkbox.checked


class Brf2EbrfDialog(QDialog):
    def __init__(self, parent: QObject = None):
        super().__init__(parent)
        self.window_title = "Convert BRF to EBRF"
        layout = QVBoxLayout()
        layout.add_widget(Brf2EbrfWidget())
        self.button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        convert_button = self.button_box.add_button("Convert", QDialogButtonBox.ButtonRole.ApplyRole)
        layout.add_widget(self.button_box)
        self.set_layout(layout)
        self.button_box.rejected.connect(self.reject)
        convert_button.clicked.connect(self.on_apply)

    def on_apply(self):
        dlg = QMessageBox(self)
        dlg.window_title = "Converting to EBRF"
        dlg.text = "You would have started a conversion to EBRF"
        dlg.icon = QMessageBox.Icon.Information
        dlg.exec()
