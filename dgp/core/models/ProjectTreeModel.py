# -*- coding: utf-8 -*-
from typing import Optional

from PyQt5.QtCore import QObject
from PyQt5.QtGui import QStandardItemModel

__all__ = ['ProjectTreeModel']


class ProjectTreeModel(QStandardItemModel):
    def __init__(self, parent: Optional[QObject]=None):
        super().__init__(parent)

