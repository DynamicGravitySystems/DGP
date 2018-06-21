# -*- coding: utf-8 -*-
from typing import Optional

from PyQt5 import QtCore
from PyQt5.QtCore import QAbstractItemModel, QModelIndex, QVariant, QObject
from PyQt5.QtGui import QStandardItem, QStandardItemModel

from gui.qtenum import QtDataRoles, QtItemFlags

__all__ = ['ProjectTreeModel']


class ProjectTreeModel(QStandardItemModel):
    def __init__(self, parent: Optional[QObject]=None):
        super().__init__(parent)


