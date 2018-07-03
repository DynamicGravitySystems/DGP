# -*- coding: utf-8 -*-
import logging
from pathlib import Path

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import QDialog, QListWidgetItem, QLabel, QFileDialog

from dgp.core.models.project import AirborneProject
from dgp.core.types.enumerations import ProjectTypes
from dgp.gui.ui.create_project_dialog import Ui_CreateProjectDialog


class CreateProjectDialog(QDialog, Ui_CreateProjectDialog):
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

    # TODO: Replace this with method to show warning in dialog
    def show_message(self, message, **kwargs):  # pragma: no cover
        """Shim to replace BaseDialog method"""
        print(message)

    def accept(self):
        """
        Called upon 'Create' button push, do some basic validation of fields
        then accept() if required fields are filled, otherwise color the
        labels red and display a warning message.
        """

        invld_fields = []
        for attr, label in self.__dict__.items():
            if not isinstance(label, QLabel):
                continue
            text = str(label.text())
            if text.endswith('*'):
                buddy = label.buddy()
                if buddy and not buddy.text():
                    label.setStyleSheet('color: red')
                    invld_fields.append(text)
                elif buddy:
                    label.setStyleSheet('color: black')

        base_path = Path(self.prj_dir.text())
        if not base_path.exists():
            self.show_message("Invalid Directory - Does not Exist",
                              buddy_label='label_dir')
            return

        if invld_fields:
            self.show_message('Verify that all fields are filled.')
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
        else:  # pragma: no cover
            self.show_message("Invalid Project Type (Not yet implemented)",
                              log=logging.WARNING, color='red')
            return

        super().accept()

    def select_dir(self):  # pragma: no cover
        path = QFileDialog.getExistingDirectory(
            self, "Select Project Parent Directory")
        if path:
            self.prj_dir.setText(path)

    @property
    def project(self):
        return self._project
