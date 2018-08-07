# -*- coding: utf-8 -*-
import sys
import json
import logging
from pathlib import Path
from typing import Union

import PyQt5.QtWidgets as QtWidgets
from PyQt5.QtCore import QModelIndex

from dgp.core.controllers.project_controllers import AirborneProjectController
from dgp.core.models.project import AirborneProject, GravityProject
from dgp.gui import settings, RecentProjectManager
from dgp.gui.main import MainWindow
from dgp.gui.utils import ConsoleHandler, LOG_FORMAT, LOG_COLOR_MAP, get_project_file
from dgp.gui.dialogs.create_project_dialog import CreateProjectDialog
from dgp.gui.ui.splash_screen import Ui_ProjectLauncher


class SplashScreen(QtWidgets.QDialog, Ui_ProjectLauncher):
    def __init__(self, *args):
        super().__init__(*args)
        self.setupUi(self)

        # Configure Logging
        self.log = self.setup_logging()
        # Experimental: Add a logger that sets the label_error text
        error_handler = ConsoleHandler(self.write_error)
        error_handler.setFormatter(logging.Formatter('%(levelname)s: %(message)s'))
        error_handler.setLevel(logging.DEBUG)
        self.log.addHandler(error_handler)

        self.recents = RecentProjectManager(settings())

        self.qpb_new_project.clicked.connect(self.new_project)
        self.qpb_browse.clicked.connect(self.browse_project)
        self.qpb_clear_recents.clicked.connect(self.recents.clear)

        self.qlv_recents.setModel(self.recents.model)
        self.qlv_recents.doubleClicked.connect(self._activated)

        self.show()

    @staticmethod
    def setup_logging(level=logging.DEBUG):
        root_log = logging.getLogger()
        std_err_handler = logging.StreamHandler(sys.stderr)
        std_err_handler.setLevel(level)
        std_err_handler.setFormatter(LOG_FORMAT)
        root_log.addHandler(std_err_handler)
        return logging.getLogger(__name__)

    def _activated(self, index: QModelIndex):
        self.accept()

    @property
    def project_path(self) -> Union[Path, None]:
        return self.recents.path(self.qlv_recents.currentIndex())

    def load_project_from_dir(self, path: Path):
        if not path.exists():
            self.log.error("Path does not exist")
            return
        prj_file = get_project_file(path)
        # TODO: Err handling and project type handling/dispatch
        with prj_file.open('r') as fd:
            project = AirborneProject.from_json(fd.read())
        return project

    def load_project(self, project, path: Path = None, spawn: bool = True):
        if isinstance(project, AirborneProject):
            controller = AirborneProjectController(project, path=path or project.path)
        else:
            raise TypeError(f"Unsupported project type {type(project)}")
        if spawn:
            window = MainWindow(controller)
            window.load()
            super().accept()
            return window
        else:
            return controller

    def accept(self):
        if self.project_path is not None:
            project = self.load_project_from_dir(self.project_path)
            self.load_project(project, self.project_path, spawn=True)
            super().accept()

    def new_project(self):
        """Allow the user to create a new project"""
        dialog = CreateProjectDialog(parent=self)
        dialog.sigProjectCreated.connect(self.load_project)
        dialog.exec_()

    def browse_project(self):
        """Allow the user to browse for a project directory and load."""
        path = QtWidgets.QFileDialog.getExistingDirectory(self, "Select Project Dir")
        if not path:
            return
        project = self.load_project_from_dir(Path(path))
        self.load_project(project, path, spawn=True)

    def write_error(self, msg, level=None) -> None:
        self.label_error.setText(msg)
        self.label_error.setStyleSheet('color: {}'.format(LOG_COLOR_MAP[level]))
