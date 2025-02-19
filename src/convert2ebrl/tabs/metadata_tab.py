#  Copyright (c) 2025. American Printing House for the Blind.
#
# This file is part of Convert2EBRL.
# Convert2EBRL is free software: you can redistribute it and/or modify it under the terms of the GNU General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# Convert2EBRL is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License for more details.
# You should have received a copy of the GNU General Public License along with Convert2EBRL. If not, see <https://www.gnu.org/licenses/>.

from PySide6.QtCore import QAbstractTableModel, QModelIndex, QPersistentModelIndex, QObject, Qt
from PySide6.QtWidgets import QWidget, QVBoxLayout, QTableView, QAbstractItemView
# noinspection PyUnresolvedReferences
from __feature__ import snake_case, true_property
from brf2ebrl.utils.metadata import DEFAULT_METADATA, MetadataItem


class MetaDataTableModel(QAbstractTableModel):
    def __init__(self, metadata_entries: list[MetadataItem]=None, parent=None):
        super().__init__(parent)
        self._metadata_entries = metadata_entries if metadata_entries is not None else DEFAULT_METADATA

    def row_count(self, index: QModelIndex | QPersistentModelIndex = QModelIndex()):
        return len(self._metadata_entries)
    def column_count(self, index: QModelIndex | QPersistentModelIndex = QModelIndex()):
        return 1
    def data(self, index, role=Qt.ItemDataRole.DisplayRole):
        if index.is_valid() and 0 <= index.row() < len(self._metadata_entries):
            item = self._metadata_entries[index.row()]
            if role == Qt.ItemDataRole.DisplayRole:
                return item.value
            elif role == Qt.ItemDataRole.EditRole:
                return item.value
        return None
    def set_data(self, index, value, /, role = Qt.ItemDataRole.EditRole):
        if index.is_valid() and 0 <= index.row() < len(self._metadata_entries):
            item = self._metadata_entries[index.row()]
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
        return QAbstractTableModel.flags(self, index) | Qt.ItemFlag.ItemIsEditable

class MetadataWidget(QWidget):
    def __init__(self, parent: QObject | None = None):
        super().__init__(parent)
        self._table_model = MetaDataTableModel()
        layout = QVBoxLayout(self)
        self._table_view = QTableView()
        self._table_view.horizontal_header().hide()
        self._table_view.selection_mode = QAbstractItemView.SelectionMode.SingleSelection
        self._table_view.tab_key_navigation = False
        self._table_view.set_model(self._table_model)
        layout.add_widget(self._table_view)