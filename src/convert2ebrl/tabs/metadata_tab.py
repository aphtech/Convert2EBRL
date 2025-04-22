#  Copyright (c) 2025. American Printing House for the Blind.
#
# This file is part of Convert2EBRL.
# Convert2EBRL is free software: you can redistribute it and/or modify it under the terms of the GNU General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# Convert2EBRL is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License for more details.
# You should have received a copy of the GNU General Public License along with Convert2EBRL. If not, see <https://www.gnu.org/licenses/>.
from collections.abc import Iterable, Callable

from PySide6.QtCore import QObject, Slot
from PySide6.QtGui import QAction
from PySide6.QtWidgets import QWidget, QVBoxLayout, QTableView, QAbstractItemView, QGroupBox, QHBoxLayout, QPushButton, \
    QMenu
from brf2ebrl.utils.metadata import MetadataItem, Creator, Title, Identifier, Language, BrailleSystem, DateCopyrighted, \
    DateTranscribed, Producer, CellType, CompleteTranscription

from convert2ebrl.tabs.metadata_model import MetadataTableModel

REQUIRED_METADATA_TYPES = (Identifier, Title, Creator, Producer, Language, BrailleSystem, CellType, CompleteTranscription, DateCopyrighted, DateTranscribed)
ADDITIONAL_METADATA_TYPES = {Title().name: Title, Creator().name: Creator, Producer().name: Producer, Language().name: Language, BrailleSystem().name: BrailleSystem}

class MetadataTableWidget(QGroupBox):
    def __init__(self, title: str, metadata_entries: Iterable[MetadataItem]=(), editable: bool=False, parent: QObject|None=None):
        super().__init__(title, parent)
        self._table_model = MetadataTableModel(metadata_entries=metadata_entries)
        layout = QVBoxLayout(self)
        self._table_view = QTableView()
        self._table_view.setAccessibleDescription("Press F2 to edit a item.")
        self._table_view.horizontalHeader().hide()
        self._table_view.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self._table_view.setTabKeyNavigation(False)
        self._table_view.setModel(self._table_model)
        layout.addWidget(self._table_view)
        if editable:
            def create_add_metadata_action(metadata_name: str, metadata_factory: Callable[[], MetadataItem]) -> QAction:
                action = QAction(metadata_name, self)
                action.triggered.connect(lambda x: self.add_metadata_item(metadata_factory()))
                return action
            add_menu = QMenu(parent=self)
            for name, metadata_type in ADDITIONAL_METADATA_TYPES.items():
                add_menu.addAction(create_add_metadata_action(name, metadata_type))
            button_layout = QHBoxLayout()
            add_button = QPushButton("Add")
            add_button.setMenu(add_menu)
            button_layout.addWidget(add_button)
            remove_button = QPushButton("Remove")
            button_layout.addWidget(remove_button)
            layout.addLayout(button_layout)
            remove_button.clicked.connect(self.remove_current_selection)
    @property
    def metadata_entries(self) -> Iterable[MetadataItem]:
        return self._table_model.metadata_entries
    def add_metadata_item(self, item: MetadataItem):
        index = self._table_view.currentIndex()
        self._table_model.insertRows(row=(index.row() + 1), data=[item])
        index = self._table_model.index(index.row() + 1, 0)
        print(f"index={index.row()}:{index.column()}")
        self._table_view.setCurrentIndex(index)
        self._table_view.edit(index)
    @Slot()
    def remove_current_selection(self):
        index = self._table_view.currentIndex()
        self._table_model.removeRows(index.row())


class MetadataWidget(QWidget):
    def __init__(self, parent: QObject | None = None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        self._required_metadata = MetadataTableWidget("Required metadata", metadata_entries=[x() for x in REQUIRED_METADATA_TYPES], editable=False)
        layout.addWidget(self._required_metadata)
        self._additional_metadata = MetadataTableWidget("Additional metadata", metadata_entries=(), editable=True)
        layout.addWidget(self._additional_metadata)
    @property
    def metadata_entries(self) -> Iterable[MetadataItem]:
        return *self._required_metadata.metadata_entries, *self._additional_metadata.metadata_entries