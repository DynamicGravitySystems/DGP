# -*- coding: utf-8 -*-
from PyQt5.QtCore import Qt

from dgp.core.controllers.project_controllers import AirborneProjectController
from dgp.gui.widgets.workspace_widget import WorkspaceTab


class ProjectTab(WorkspaceTab):
    def __init__(self, project: AirborneProjectController, parent=None):
        super().__init__(parent=parent, flags=Qt.Widget)
        self.project = project

    @property
    def uid(self):
        return self.project.uid
