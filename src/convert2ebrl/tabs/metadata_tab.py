#  Copyright (c) 2025. American Printing House for the Blind.
#
# This file is part of Convert2EBRL.
# Convert2EBRL is free software: you can redistribute it and/or modify it under the terms of the GNU General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# Convert2EBRL is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License for more details.
# You should have received a copy of the GNU General Public License along with Convert2EBRL. If not, see <https://www.gnu.org/licenses/>.
import datetime
from collections.abc import Iterable, Sequence, Callable

from PySide6.QtCore import QModelIndex, QPersistentModelIndex, QObject, Qt, QDate, \
    QAbstractListModel, Slot
from PySide6.QtGui import QAction
from PySide6.QtWidgets import QWidget, QVBoxLayout, QTableView, QAbstractItemView, QGroupBox, QHBoxLayout, QPushButton, \
    QMenu
# noinspection PyUnresolvedReferences
from __feature__ import snake_case, true_property
from brf2ebrl.utils.metadata import MetadataItem, Creator, Title, Identifier, Language, BrailleSystem, DateCopyrighted, \
    DateTranscribed, Producer, CellType, CompleteTranscription

REQUIRED_METADATA_TYPES = (Identifier, Title, Creator, Producer, Language, BrailleSystem, CellType, CompleteTranscription, DateCopyrighted, DateTranscribed)
ADDITIONAL_METADATA_TYPES = {Title().name: Title, Creator().name: Creator, Producer().name: Producer, Language().name: Language, BrailleSystem().name: BrailleSystem}

class MetadataTableModel(QAbstractListModel):
    def __init__(self, metadata_entries: Iterable[MetadataItem]=None, parent=None):
        super().__init__(parent)
        self._metadata_entries = list(metadata_entries) if metadata_entries is not None else []

    @property
    def metadata_entries(self) -> Iterable[MetadataItem]:
        return self._metadata_entries

    def row_count(self, index: QModelIndex | QPersistentModelIndex = QModelIndex()):
        return len(self._metadata_entries)

    def insert_rows(self, row: int, data: Sequence[MetadataItem], parent: QModelIndex=QModelIndex()) -> bool:
        self.begin_insert_rows(QModelIndex(), row, row + len(data) - 1)
        for i, v in enumerate(data):
            self._metadata_entries.insert(row + i, v)
        self.end_insert_rows()
        return True

    def remove_rows(self, row: int, count: int=1, parent:QModelIndex=QModelIndex()) -> bool:
        self.begin_remove_rows(QModelIndex(), row, row + count - 1)
        del self._metadata_entries[row:row+count]
        self.end_remove_rows()
        return True
    def data(self, index, role=Qt.ItemDataRole.DisplayRole):
        if index.is_valid() and 0 <= index.row() < len(self._metadata_entries):
            item = self._metadata_entries[index.row()]
            if role in (Qt.ItemDataRole.DisplayRole, Qt.ItemDataRole.EditRole):
                match item.value:
                    case datetime.date(year=y, month=m, day=d):
                        return QDate(y, m, d)
                    case value:
                        return value
        return None

    def set_data(self, index, value, /, role = Qt.ItemDataRole.EditRole):
        if index.is_valid() and 0 <= index.row() < len(self._metadata_entries):
            item = self._metadata_entries[index.row()]
            match value:
                case QDate(year=y, month=m, day=d):
                    item.value = datetime.date(year=y, month=m, day=d)
                case _:
                    item.value = value
            self.dataChanged.emit(index, index, 0)
            return True
        return False

    def header_data(self, section, orientation, role = Qt.ItemDataRole.DisplayRole):
        if role != Qt.ItemDataRole.DisplayRole:
            return None
        if orientation == Qt.Orientation.Vertical:
            item = self._metadata_entries[section]
            return item.name
        return None

    def flags(self, index):
        if not index.is_valid():
            return Qt.ItemFlag.ItemIsEnabled
        return QAbstractListModel.flags(self, index) | Qt.ItemFlag.ItemIsEditable

class MetadataTableWidget(QGroupBox):
    def __init__(self, title: str, metadata_entries: Iterable[MetadataItem]=(), editable: bool=False, parent: QObject|None=None):
        super().__init__(title, parent)
        self._table_model = MetadataTableModel(metadata_entries=metadata_entries)
        layout = QVBoxLayout(self)
        self._table_view = QTableView()
        self._table_view.accessible_description = "Press F2 to edit a item."
        self._table_view.horizontal_header().hide()
        self._table_view.selection_mode = QAbstractItemView.SelectionMode.SingleSelection
        self._table_view.tab_key_navigation = False
        self._table_view.set_model(self._table_model)
        layout.add_widget(self._table_view)
        if editable:
            def create_add_metadata_action(metadata_name: str, metadata_factory: Callable[[], MetadataItem]) -> QAction:
                action = QAction(metadata_name, self)
                action.triggered.connect(lambda x: self.add_metadata_item(metadata_factory()))
                return action
            add_menu = QMenu(parent=self)
            for name, metadata_type in ADDITIONAL_METADATA_TYPES.items():
                add_menu.add_action(create_add_metadata_action(name, metadata_type))
            button_layout = QHBoxLayout()
            add_button = QPushButton("Add")
            add_button.set_menu(add_menu)
            button_layout.add_widget(add_button)
            remove_button = QPushButton("Remove")
            button_layout.add_widget(remove_button)
            layout.add_layout(button_layout)
            remove_button.clicked.connect(self.remove_current_selection)
    @property
    def metadata_entries(self) -> Iterable[MetadataItem]:
        return self._table_model.metadata_entries
    def add_metadata_item(self, item: MetadataItem):
        index = self._table_view.current_index()
        self._table_model.insert_rows(row=index.row(), data=[item])
    @Slot()
    def remove_current_selection(self):
        index = self._table_view.current_index()
        self._table_model.remove_rows(index.row())


class MetadataWidget(QWidget):
    def __init__(self, parent: QObject | None = None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        self._required_metadata = MetadataTableWidget("Required metadata", metadata_entries=[x() for x in REQUIRED_METADATA_TYPES], editable=False)
        layout.add_widget(self._required_metadata)
        self._additional_metadata = MetadataTableWidget("Additional metadata", metadata_entries=(Creator(""),), editable=True)
        layout.add_widget(self._additional_metadata)
    @property
    def metadata_entries(self) -> Iterable[MetadataItem]:
        return self._required_metadata.metadata_entries