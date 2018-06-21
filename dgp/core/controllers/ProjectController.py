# -*- coding: utf-8 -*-
from typing import Optional

from PyQt5.QtCore import QObject
from PyQt5.QtGui import QStandardItem

from core.project import GravityProject


class ProjectController(QStandardItem):
    def __init__(self, project: GravityProject, parent: Optional[QObject]=None):
        super().__init__(parent)
        self._project = project


