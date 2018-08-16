# -*- coding: utf-8 -*-
import sys
import logging
from pathlib import Path
from typing import Union

import PyQt5.QtWidgets as QtWidgets
from PyQt5.QtCore import QModelIndex, pyqtSignal

from dgp.gui import RecentProjectManager
from dgp.gui.utils import ConsoleHandler, LOG_FORMAT, LOG_COLOR_MAP, load_project_from_path
from dgp.gui.dialogs.create_project_dialog import CreateProjectDialog
from dgp.gui.ui.recent_project_dialog import Ui_RecentProjects


class RecentProjectDialog(QtWidgets.QDialog, Ui_RecentProjects):
    """Display a QDialog with a recent project's list, and ability to browse for,
    or create a new project.
    Recent projects are retrieved via the QSettings object and global DGP keys.

    """
    sigProjectLoaded = pyqtSignal(object)

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

        self.recents = RecentProjectManager()

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

    def load_project(self, path: Path):
        """Load a project from file and emit the result

        Parameters
        ----------
        path

        Returns
        -------

        """
        assert isinstance(path, Path)
        project = load_project_from_path(path)
        project.path = path  # update project's path in case folder was moved
        self.sigProjectLoaded.emit(project)
        super().accept()

    def accept(self):
        if self.project_path is not None:
            self.load_project(self.project_path)
            super().accept()
        else:
            self.log.warning("No project selected")

    def new_project(self):
        """Allow the user to create a new project"""
        dialog = CreateProjectDialog(parent=self)
        dialog.sigProjectCreated.connect(self.sigProjectLoaded.emit)
        if dialog.exec_():
            super().accept()

    def browse_project(self):
        """Allow the user to browse for a project directory and load."""
        path = QtWidgets.QFileDialog.getExistingDirectory(self, "Select Project Dir")
        if not path:
            return
        self.load_project(Path(path))

    def write_error(self, msg, level=None) -> None:
        self.label_error.setText(msg)
        self.label_error.setStyleSheet('color: {}'.format(LOG_COLOR_MAP[level]))
