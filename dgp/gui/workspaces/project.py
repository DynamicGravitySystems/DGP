# -*- coding: utf-8 -*-
from PyQt5.QtCore import Qt

from dgp.core.controllers.project_controllers import AirborneProjectController
from .base import WorkspaceTab


class ProjectTab(WorkspaceTab):
    def __init__(self, project: AirborneProjectController, parent=None):
        super().__init__(parent=parent, flags=Qt.Widget)
        self.project = project

    @property
    def title(self) -> str:
        return f'{self.project.get_attr("name")}'

    @property
    def uid(self):
        return self.project.uid
