# coding: utf-8


import sys
import json
import logging
from pathlib import Path
from typing import Dict, Union

import PyQt5.QtWidgets as QtWidgets
import PyQt5.QtCore as QtCore
from PyQt5.uic import loadUiType

from dgp.gui.main import MainWindow
from dgp.gui.utils import ConsoleHandler, LOG_FORMAT, LOG_COLOR_MAP, get_project_file
from dgp.gui.dialogs import CreateProject
import dgp.lib.project as prj

splash_screen, _ = loadUiType('dgp/gui/ui/splash_screen.ui')


class SplashScreen(QtWidgets.QDialog, splash_screen):
    def __init__(self, *args):
        super().__init__(*args)
        self.log = self.setup_logging()
        # Experimental: Add a logger that sets the label_error text
        error_handler = ConsoleHandler(self.write_error)
        error_handler.setFormatter(logging.Formatter('%(levelname)s: %(message)s'))
        error_handler.setLevel(logging.DEBUG)
        self.log.addHandler(error_handler)

        self.setupUi(self)

        self.settings_dir = Path.home().joinpath(
            'AppData\Local\DynamicGravitySystems\DGP')
        self.recent_file = self.settings_dir.joinpath('recent.json')
        if not self.settings_dir.exists():
            self.log.info("Settings Directory doesn't exist, creating.")
            self.settings_dir.mkdir(parents=True)

        # self.dialog_buttons.accepted.connect(self.accept)
        self.btn_newproject.clicked.connect(self.new_project)
        self.btn_browse.clicked.connect(self.browse_project)
        self.list_projects.currentItemChanged.connect(
            lambda item: self.set_selection(item, accept=False))
        self.list_projects.itemDoubleClicked.connect(
            lambda item: self.set_selection(item, accept=True))

        self.project_path = None  # type: Path

        self.set_recent_list()
        self.show()

    @staticmethod
    def setup_logging(level=logging.DEBUG):
        root_log = logging.getLogger()
        std_err_handler = logging.StreamHandler(sys.stderr)
        std_err_handler.setLevel(level)
        std_err_handler.setFormatter(LOG_FORMAT)
        root_log.addHandler(std_err_handler)
        return logging.getLogger(__name__)

    def accept(self, project=None):
        """
        Runs some basic verification before calling super(QDialog).accept().
        """

        # Case where project object is passed to accept()
        if isinstance(project, prj.GravityProject):
            self.log.debug("Opening new project: {}".format(project.name))
        elif not self.project_path:
            self.log.error("No valid project selected.")
        else:
            try:
                project = prj.AirborneProject.load(self.project_path)
            except FileNotFoundError:
                self.log.error("Project could not be loaded from path: {}"
                               .format(self.project_path))
                return

        self.update_recent_files(self.recent_file,
                                 {project.name: project.projectdir})

        main_window = MainWindow(project)
        main_window.load()
        super().accept()
        return main_window

    def set_recent_list(self) -> None:
        recent_files = self.get_recent_files(self.recent_file)
        if not recent_files:
            no_recents = QtWidgets.QListWidgetItem("No Recent Projects",
                                                   self.list_projects)
            no_recents.setFlags(QtCore.Qt.NoItemFlags)
            return None

        for name, path in recent_files.items():
            item = QtWidgets.QListWidgetItem('{name} :: {path}'.format(
                name=name, path=str(path)), self.list_projects)
            item.setData(QtCore.Qt.UserRole, path)
            item.setToolTip(str(path.resolve()))
        self.list_projects.setCurrentRow(0)
        return None

    def set_selection(self, item: QtWidgets.QListWidgetItem, accept=False):
        """Called when a recent item is selected"""
        self.project_path = get_project_file(item.data(QtCore.Qt.UserRole))
        if not self.project_path:
            item.setText("{} - Project Moved or Deleted"
                         .format(item.data(QtCore.Qt.UserRole)))
            return

        self.log.debug("Project path set to {}".format(self.project_path))
        if accept:
            self.accept()

    def new_project(self):
        """Allow the user to create a new project"""
        dialog = CreateProject()
        if dialog.exec_():
            project = dialog.project  # type: prj.AirborneProject
            project.save()
            self.accept(project)

    def browse_project(self):
        """Allow the user to browse for a project directory and load."""
        path = QtWidgets.QFileDialog.getExistingDirectory(self,
                                                          "Select Project Dir")
        if not path:
            return

        prj_file = get_project_file(Path(path))
        if not prj_file:
            self.log.error("No project files found")
            return

        self.project_path = prj_file
        self.accept()

    def write_error(self, msg, level=None) -> None:
        self.label_error.setText(msg)
        self.label_error.setStyleSheet('color: {}'.format(LOG_COLOR_MAP[level]))

    @staticmethod
    def update_recent_files(path: Path, update: Dict[str, Path]) -> None:
        recents = SplashScreen.get_recent_files(path)
        recents.update(update)
        SplashScreen.set_recent_files(recents, path)

    @staticmethod
    def get_recent_files(path: Path) -> Dict[str, Path]:
        """
        Ingests a JSON file specified by path, containing project_name:
        project_directory mappings and returns dict of valid projects (
        conducting path checking and conversion to pathlib.Path)
        Parameters
        ----------
        path : Path
            Path object referencing JSON object containing mappings of recent
            projects -> project directories

        Returns
        -------
        Dict
            Dictionary of (str) project_name: (pathlib.Path) project_directory mappings
            If the specified path cannot be found, an empty dictionary is returned
        """
        try:
            with path.open('r') as fd:
                raw_dict = json.load(fd)
            _checked = {}
            for name, strpath in raw_dict.items():
                _path = Path(strpath)
                if get_project_file(_path) is not None:
                    _checked[name] = _path
        except FileNotFoundError:
            return {}
        else:
            return _checked

    @staticmethod
    def set_recent_files(recent_files: Dict[str, Path], path: Path) -> None:
        """
        Take a dictionary of recent projects (project_name: project_dir) and
        write it out to a JSON formatted file
        specified by path
        Parameters
        ----------
        recent_files : Dict[str, Path]

        path : Path

        Returns
        -------
        None
        """
        serializable = {name: str(path) for name, path in recent_files.items()}
        with path.open('w+') as fd:
            json.dump(serializable, fd)
