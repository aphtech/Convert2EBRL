#  Copyright (c) 2025. American Printing House for the Blind.
#
# This file is part of Convert2EBRL.
# Convert2EBRL is free software: you can redistribute it and/or modify it under the terms of the GNU General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# Convert2EBRL is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License for more details.
# You should have received a copy of the GNU General Public License along with Convert2EBRL. If not, see <https://www.gnu.org/licenses/>.
import datetime
from typing import Iterable, Sequence

from PySide6.QtCore import QAbstractListModel, QModelIndex, QPersistentModelIndex, Qt, QDate
from brf2ebrl.utils.metadata import MetadataItem


class MetadataTableModel(QAbstractListModel):
    def __init__(self, metadata_entries: Iterable[MetadataItem]=None, parent=None):
        super().__init__(parent)
        self._metadata_entries = list(metadata_entries) if metadata_entries is not None else []

    @property
    def metadata_entries(self) -> Iterable[MetadataItem]:
        return self._metadata_entries

    def rowCount(self, index: QModelIndex | QPersistentModelIndex = QModelIndex()):
        return len(self._metadata_entries)

    def insertRows(self, row: int, data: Sequence[MetadataItem], parent: QModelIndex=QModelIndex()) -> bool:
        self.beginInsertRows(QModelIndex(), row, row + len(data) - 1)
        for i, v in enumerate(data):
            self._metadata_entries.insert(row + i, v)
        self.endInsertRows()
        return True

    def removeRows(self, row: int, count: int=1, parent:QModelIndex=QModelIndex()) -> bool:
        self.beginRemoveRows(QModelIndex(), row, row + count - 1)
        del self._metadata_entries[row:row+count]
        self.endRemoveRows()
        return True
    def data(self, index, role=Qt.ItemDataRole.DisplayRole):
        if index.isValid() and 0 <= index.row() < len(self._metadata_entries):
            item = self._metadata_entries[index.row()]
            if role in (Qt.ItemDataRole.DisplayRole, Qt.ItemDataRole.EditRole):
                match item.value:
                    case datetime.date(year=y, month=m, day=d):
                        return QDate(y, m, d)
                    case value:
                        return value
        return None

    def setData(self, index, value, /, role = Qt.ItemDataRole.EditRole):
        if index.isValid() and 0 <= index.row() < len(self._metadata_entries):
            item = self._metadata_entries[index.row()]
            match value:
                case QDate(year=y, month=m, day=d):
                    item.value = datetime.date(year=y, month=m, day=d)
                case _:
                    item.value = value
            self.dataChanged.emit(index, index, 0)
            return True
        return False

    def headerData(self, section, orientation, role = Qt.ItemDataRole.DisplayRole):
        if role != Qt.ItemDataRole.DisplayRole:
            return None
        if orientation == Qt.Orientation.Vertical:
            item = self._metadata_entries[section]
            return item.name
        return None

    def flags(self, index):
        if not index.isValid():
            return Qt.ItemFlag.ItemIsEnabled
        return QAbstractListModel.flags(self, index) | Qt.ItemFlag.ItemIsEditable
