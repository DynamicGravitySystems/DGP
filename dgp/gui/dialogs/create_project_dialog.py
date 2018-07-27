# -*- coding: utf-8 -*-
import logging
from pathlib import Path
from typing import List

from PyQt5.QtCore import Qt, QRegExp, pyqtSignal
from PyQt5.QtGui import QIcon, QRegExpValidator
from PyQt5.QtWidgets import QDialog, QListWidgetItem, QFileDialog, QFormLayout

from dgp.core.models.project import AirborneProject
from dgp.core.types.enumerations import ProjectTypes
from dgp.gui.ui.create_project_dialog import Ui_CreateProjectDialog
from .dialog_mixins import FormValidator
from .custom_validators import DirectoryValidator


class CreateProjectDialog(QDialog, Ui_CreateProjectDialog, FormValidator):
    sigProjectCreated = pyqtSignal(AirborneProject, bool)

    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.setupUi(self)

        self._project = None

        self.prj_browse.clicked.connect(self.select_dir)
        desktop = Path().home().joinpath('Desktop')
        self.prj_dir.setText(str(desktop))

        # Populate the type selection list
        flt_icon = QIcon(':icons/airborne')
        boat_icon = QIcon(':icons/marine')
        dgs_airborne = QListWidgetItem(flt_icon, 'DGS Airborne',
                                       self.prj_type_list)
        dgs_airborne.setData(Qt.UserRole, ProjectTypes.AIRBORNE)
        self.prj_type_list.setCurrentItem(dgs_airborne)
        dgs_marine = QListWidgetItem(boat_icon, 'DGS Marine',
                                     self.prj_type_list)
        dgs_marine.setData(Qt.UserRole, ProjectTypes.MARINE)

        # Configure Validation
        self.prj_name.setValidator(QRegExpValidator(QRegExp("[A-Za-z]+.{3,30}")))
        self.prj_dir.setValidator(DirectoryValidator(exist_ok=True))

    @property
    def validation_targets(self) -> List[QFormLayout]:
        return [self.qfl_create_form]

    @property
    def validation_error(self):
        return self.ql_validation_err

    def accept(self):
        """
        Called upon 'Create' button push, do some basic validation of fields
        then accept() if required fields are filled, otherwise color the
        labels red and display a warning message.
        """
        if not self.validate():
            return

        # TODO: Future implementation for Project types other than DGS AT1A
        prj_type = self.prj_type_list.currentItem().data(Qt.UserRole)
        if prj_type == ProjectTypes.AIRBORNE:
            name = str(self.prj_name.text()).rstrip()
            name = "".join([word.capitalize() for word in name.split(' ')])
            path = Path(self.prj_dir.text()).joinpath(name)
            if not path.exists():  # pragma: no branch
                path.mkdir(parents=True)

            self._project = AirborneProject(name=name, path=path, description=self.qpte_notes.toPlainText())
            self.sigProjectCreated.emit(self._project, False)
        else:  # pragma: no cover
            self.ql_validation_err.setText("Invalid Project Type - Not Implemented")
            return

        super().accept()

    def select_dir(self):  # pragma: no cover
        path = QFileDialog.getExistingDirectory(
            self, "Select Project Parent Directory")
        if path:
            self.prj_dir.setText(path)

    def show(self):
        self.setModal(True)
        super().show()

    @property
    def project(self):
        return self._project
