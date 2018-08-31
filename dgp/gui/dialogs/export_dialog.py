# -*- coding: utf-8 -*-
from pathlib import Path

from PyQt5.QtCore import QModelIndex, Qt, pyqtSignal
from PyQt5.QtGui import QStandardItemModel, QStandardItem
from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QDialogButtonBox, QListView,
                             QLineEdit, QHBoxLayout, QPushButton, QFileDialog,
                             QGroupBox, QGridLayout, QFormLayout, QComboBox, QSpinBox, QSizePolicy)
from pandas import DataFrame

from dgp.core import Icon
from dgp.core.controllers.controller_interfaces import AbstractController
from dgp.gui import settings, SettingsKey
from dgp.lib.exporters import Exporter, ExportProfile, ColumnProfile, TimeFormat
from .custom_validators import DirectoryValidator

ExporterRole = 0x101
ProfileRole = 0x0102
ColumnRole = 0x103
ColumnIdRole = 0x104

default_path = Path('~').expanduser()


class ProfileEditDialog(QDialog):
    sigProfileUpdated = pyqtSignal(object)

    def __init__(self, profile: ExportProfile, parent=None):
        super().__init__(parent=parent, flags=Qt.Dialog)
        self._profile = profile

        self.setWindowTitle(f'Edit Profile - {profile.name}')
        self._layout = QGridLayout(self)

        source_layout = QVBoxLayout()
        group_source = QGroupBox("Source Columns")
        group_source.setLayout(source_layout)

        self.source_view = QListView()
        self.source_model = QStandardItemModel()
        self.source_view.setModel(self.source_model)
        self.source_view.doubleClicked.connect(self._action_move_column)

        source_controls = QDialogButtonBox()
        add_column = QPushButton("&Add")
        info_column = QPushButton("Deta&ils")
        source_controls.addButton(add_column, QDialogButtonBox.ActionRole)
        source_controls.addButton(info_column, QDialogButtonBox.HelpRole)

        add_column.clicked.connect(self._action_add_column)

        source_layout.addWidget(self.source_view)
        source_layout.addWidget(source_controls)

        group_export = QGroupBox("Export Columns")
        export_layout = QGridLayout()
        group_export.setLayout(export_layout)

        self.export_view = QListView()
        self.export_model = QStandardItemModel()
        self.export_view.setModel(self.export_model)
        self.export_view.doubleClicked.connect(self._action_move_column)

        export_controls = QDialogButtonBox()
        remove_column = QPushButton("&Remove")
        remove_column.clicked.connect(self._action_remove_column)
        remove_all_columns = QPushButton("Remove All")
        export_controls.addButton(remove_column, QDialogButtonBox.DestructiveRole)
        export_controls.addButton(remove_all_columns, QDialogButtonBox.DestructiveRole)

        export_order = QDialogButtonBox(Qt.Vertical)
        move_up = QPushButton(Icon.ARROW_UP.icon(), "")
        move_up.clicked.connect(lambda: self._action_reorder('up'))
        move_down = QPushButton(Icon.ARROW_DOWN.icon(), "")
        move_down.clicked.connect(lambda: self._action_reorder('down'))
        export_order.addButton(move_up, QDialogButtonBox.ActionRole)
        export_order.addButton(move_down, QDialogButtonBox.ActionRole)

        export_layout.addWidget(self.export_view, 0, 0, 2, 2)
        export_layout.addWidget(export_controls, 2, 0, 1, 2)
        export_layout.addWidget(export_order, 1, 2)

        for column in ColumnProfile.columns():
            item = QStandardItem(column.name)
            item.setData(column, ColumnRole)
            item.setData(column.identifier, ColumnIdRole)
            item.setEditable(False)
            item.setToolTip(f'{column.name} ({column.display_unit})')
            if column.identifier in self._profile.columns:
                self.export_model.appendRow(item)
            else:
                self.source_model.appendRow(item)

        self._layout.addWidget(group_source, 1, 0)
        self._layout.addWidget(group_export, 1, 1)

        param_layout = QFormLayout()
        self.ext_selector = QLineEdit(f'.{profile.ext}')
        self.date_selector = QComboBox()
        self.date_selector.addItems([fmt.name for fmt in TimeFormat])
        current_fmt = self.date_selector.findText(self._profile.dateformat.name)
        self.date_selector.setCurrentIndex(current_fmt)

        param_layout.addRow("File Extension", self.ext_selector)
        param_layout.addRow("Time Format", self.date_selector)

        self._layout.addLayout(param_layout, 2, 0)

        dlg_btns = QDialogButtonBox(self)
        dlg_btns.setStandardButtons(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        dlg_btns.accepted.connect(self.accept)
        dlg_btns.rejected.connect(self.reject)

        self._layout.addWidget(dlg_btns, 2, 1, alignment=Qt.AlignBottom)

    def accept(self):
        columns = []
        for i in range(self.export_model.rowCount()):
            item: QStandardItem = self.export_model.item(i)
            col_profile: ColumnProfile = item.data(ColumnRole)
            columns.append(col_profile.identifier)

        ext = self.ext_selector.text().strip('.')
        dateformat = TimeFormat[self.date_selector.currentText()]

        self._profile.columns = columns
        self._profile.ext = ext
        self._profile.dateformat = dateformat

        self.sigProfileUpdated.emit(self._profile)
        super().accept()

    def _action_add_column(self):
        """Move a Column from Source Model -> Export Model"""
        idx: QModelIndex = self.source_view.currentIndex()
        if not idx.isValid():
            return
        item = self.source_model.takeItem(idx.row(), idx.column())
        self.source_model.removeRow(idx.row())
        self.export_model.appendRow(item)

    def _action_remove_column(self):
        """Move a Column from Export Model -> Source Model"""
        idx: QModelIndex = self.export_view.currentIndex()
        if not idx.isValid():
            return
        item = self.export_model.takeItem(idx.row(), idx.column())
        self.export_model.removeRow(idx.row())
        self.source_model.appendRow(item)

    def _action_move_column(self, index: QModelIndex):
        model: QStandardItemModel = index.model()
        item = model.takeItem(index.row())
        model.removeRow(index.row())

        other: QStandardItemModel = next((m for m in [self.export_model, self.source_model] if m is not model))
        other.appendRow(item)

    def _action_reorder(self, direction):
        """Reorder items in the export view up or down"""
        idx: QModelIndex = self.export_view.currentIndex()
        model: QStandardItemModel = idx.model()
        if direction.lower() == 'up':
            dest_row = idx.row() - 1
            if dest_row < 0:
                return
        else:
            dest_row = idx.row() + 1
            if dest_row > model.rowCount() - 1:
                return

        item = model.takeItem(idx.row())
        model.removeRow(idx.row())
        model.insertRow(dest_row, item)
        self.export_view.setCurrentIndex(model.index(dest_row, 0))


class ExportDialog(QDialog):
    def __init__(self, context: AbstractController, data: DataFrame, parent=None):
        super().__init__(parent=parent, flags=Qt.Dialog)
        self._context = context
        self._data = data

        self.setWindowTitle("Export Data")
        self._layout = QVBoxLayout(self)

        self.exporter_view = QListView()
        self.export_model = QStandardItemModel()
        self.exporter_view.setModel(self.export_model)
        self.profile_view = QListView()
        self.profile_model = QStandardItemModel()
        self.profile_view.setModel(self.profile_model)
        self.profile_view.doubleClicked.connect(self._action_edit_profile)

        path_layout = QHBoxLayout()
        self._layout.addLayout(path_layout)
        self._file_path = QLineEdit()
        self._file_path.setPlaceholderText("Browse for directory")
        self._file_path.setText(self.last_dir)
        self._file_path.setValidator(DirectoryValidator())
        self._file_path.textChanged.connect(lambda x: self._validate_input(self._file_path))
        self._browse = QPushButton('Browse...')
        self._browse.clicked.connect(self._browse_for_dir)
        path_layout.addWidget(self._file_path, stretch=3)
        path_layout.addWidget(self._browse)

        group_exporters = QGroupBox("Exporters")
        export_layout = QVBoxLayout()
        export_layout.addWidget(self.exporter_view)
        group_exporters.setLayout(export_layout)

        group_profiles = QGroupBox("Profiles")
        profile_layout = QVBoxLayout()
        group_profiles.setLayout(profile_layout)
        profile_layout.addWidget(self.profile_view)

        profile_btns = QDialogButtonBox()
        profile_btns.setCenterButtons(True)

        # Profile List Actions
        add_profile = QPushButton("Add")
        edit_profile = QPushButton("Edit")
        del_profile = QPushButton("Delete")
        profile_btns.addButton(add_profile, QDialogButtonBox.ActionRole)
        profile_btns.addButton(edit_profile, QDialogButtonBox.ActionRole)
        profile_btns.addButton(del_profile, QDialogButtonBox.DestructiveRole)
        profile_layout.addWidget(profile_btns)

        edit_profile.clicked.connect(self._action_edit_profile)

        self._layout.addWidget(group_exporters, stretch=1)
        self._layout.addWidget(group_profiles, stretch=1)
        # self._layout.addStretch(1)

        dlg_btns = QDialogButtonBox(QDialogButtonBox.Ok |
                                    QDialogButtonBox.Cancel,
                                    parent=self)
        dlg_btns.accepted.connect(self.accept)
        dlg_btns.rejected.connect(self.reject)

        self._layout.addWidget(dlg_btns)

        self._exporters = {}
        for exporter in Exporter.exporters():
            self._exporters[exporter.name] = exporter
            item = QStandardItem(exporter.name)
            item.setEditable(False)
            item.setData(exporter.name, ExporterRole)
            self.export_model.appendRow(item)

        for profile in ExportProfile.profiles():
            item = QStandardItem(profile.name)
            item.setEditable(False)
            item.setData(profile, ProfileRole)
            self.profile_model.appendRow(item)

        self.exporter_view.selectionModel().selectionChanged.connect(self._exporter_changed)
        self.profile_view.selectionModel().selectionChanged.connect(self._profile_changed)

    @property
    def path(self) -> Path:
        return Path(self._file_path.text())

    @property
    def last_dir(self) -> str:
        return settings().value(SettingsKey.LastExportPath(), str(default_path))

    @last_dir.setter
    def last_dir(self, value):
        settings().setValue(SettingsKey.LastExportPath(), str(value))

    def accept(self):
        if self.exporter is None:
            print(f'Invalid (None) exporter selected')
            return
        if self.profile is None:
            print(f'Invalid (None) profile selected')
            return

        print(f'Exporting data with {self.exporter} :: {self.profile}')

        exp = self.exporter(self._context.get_attr('name'),
                            self._data,
                            profile=self.profile)
        exp.export(self.path)
        self.last_dir = str(self.path)

        super().accept()


    @property
    def exporter(self):
        idx: QModelIndex = self.exporter_view.currentIndex()
        return self._exporters.get(self.export_model.data(idx, ExporterRole), None)

    def _exporter_changed(self, selected: QModelIndex, deselected: QModelIndex):
        print(f"Exporter changed to {self.exporter}")

    @property
    def profile(self) -> ExportProfile:
        idx = self.profile_view.currentIndex()
        return self.profile_model.data(idx, ProfileRole)

    def _profile_changed(self, selected: QModelIndex, deselected: QModelIndex):
        print(f"Profile changed to {self.profile}")

    def _validate_input(self, widget: QLineEdit):
        if not widget.hasAcceptableInput():
            widget.setStyleSheet("QLineEdit { background: red; }")
        else:
            widget.setStyleSheet("background: white;")

    def _browse_for_dir(self):
        path = QFileDialog.getExistingDirectory(self, "Select Directory",
                                                self.last_dir,
                                                QFileDialog.ShowDirsOnly)
        if path != "":
            self.last_dir = path
            self._file_path.setText(path)

    def _action_edit_profile(self, *args):
        if self.profile is None:
            return
        edit_dlg = ProfileEditDialog(self.profile, self)
        edit_dlg.exec_()
