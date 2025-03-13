#  Copyright (c) 2025. American Printing House for the Blind.
#
# This file is part of Convert2EBRL.
# Convert2EBRL is free software: you can redistribute it and/or modify it under the terms of the GNU General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# Convert2EBRL is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License for more details.
# You should have received a copy of the GNU General Public License along with Convert2EBRL. If not, see <https://www.gnu.org/licenses/>.
import datetime
from collections.abc import Iterable, Sequence

from PySide6.QtCore import QModelIndex, QPersistentModelIndex, QObject, Qt, QDate, \
    QAbstractListModel
from PySide6.QtWidgets import QWidget, QVBoxLayout, QTableView, QAbstractItemView, QGroupBox, QHBoxLayout, QPushButton
# noinspection PyUnresolvedReferences
from __feature__ import snake_case, true_property
from brf2ebrl.utils.metadata import DEFAULT_METADATA, MetadataItem


class MetadataTableModel(QAbstractListModel):
    def __init__(self, metadata_entries: list[MetadataItem]=None, parent=None):
        super().__init__(parent)
        self._metadata_entries = metadata_entries if metadata_entries is not None else DEFAULT_METADATA

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
    def __init__(self, title: str, editable: bool=False, parent: QObject|None=None):
        super().__init__(title, parent)
        self._table_model = MetadataTableModel()
        layout = QVBoxLayout(self)
        self._table_view = QTableView()
        self._table_view.accessible_description = "Press F2 to edit a item."
        self._table_view.horizontal_header().hide()
        self._table_view.selection_mode = QAbstractItemView.SelectionMode.SingleSelection
        self._table_view.tab_key_navigation = False
        self._table_view.set_model(self._table_model)
        layout.add_widget(self._table_view)
        if editable:
            button_layout = QHBoxLayout()
            add_button = QPushButton("Add")
            button_layout.add_widget(add_button)
            remove_button = QPushButton("Remove")
            button_layout.add_widget(remove_button)
            layout.add_layout(button_layout)
    @property
    def metadata_entries(self) -> Iterable[MetadataItem]:
        return self._table_model.metadata_entries


class MetadataWidget(QWidget):
    def __init__(self, parent: QObject | None = None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        self._required_metadata = MetadataTableWidget("Required metadata", editable=False)
        layout.add_widget(self._required_metadata)
    @property
    def metadata_entries(self) -> Iterable[MetadataItem]:
        return self._required_metadata.metadata_entries