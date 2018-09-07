# -*- coding: utf-8 -*-
import json
import logging
from pathlib import Path

from PyQt5.QtCore import (QModelIndex, Qt, pyqtSignal, QSortFilterProxyModel,
                          QAbstractProxyModel, QItemSelection, QPoint)
from PyQt5.QtGui import QStandardItemModel, QStandardItem
from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QDialogButtonBox, QListView,
                             QLineEdit, QHBoxLayout, QPushButton, QFileDialog,
                             QGroupBox, QGridLayout, QFormLayout, QComboBox,
                             QAbstractItemView, QLabel, QTreeView, QSizePolicy, QMenu)

from dgp.core import Icon
from dgp.core.types.enumerations import Cardinal
from dgp.core.controllers.controller_helpers import confirm_action
from dgp.core.controllers.controller_interfaces import AbstractController
from dgp.gui import settings, SettingsKey
from dgp.gui.dialogs.input_dialog import InputDialog
from dgp.lib.exporters import Exporter, ExportProfile, ColumnProfile, TimeFormat, Category
from .custom_validators import DirectoryValidator, ValueExistsValidator

ExporterRole = 0x101
ProfileRole = 0x0102
ColumnRole = 0x103
ColumnIdRole = 0x104
CategoryRole = 0x105

default_path = Path('~').expanduser()
_log = logging.getLogger(__name__)


def _load_user_profiles():
    """Profiles must be loaded and registered exactly once per execution.

    Any profiles created during runtime session will already be in ExportProfile
    registry for use by the dialog.
    """
    settings().beginGroup(SettingsKey.UserExportProfiles())
    for child in settings().childKeys():
        value = settings().value(child)
        try:
            profile = ExportProfile.from_json(value)
            ExportProfile.register(profile)
            _log.debug(f"Loaded and registered profile {profile.name}")
        except json.decoder.JSONDecodeError:
            _log.warning(f"Invalid user-profile detected for key {child}")
    settings().endGroup()


_load_user_profiles()


class ProfileEditDialog(QDialog):
    sigProfileUpdated = pyqtSignal(object)
    sigProfileMoved = pyqtSignal(object, str)

    def __init__(self, profile: ExportProfile, parent=None):
        super().__init__(parent=parent, flags=Qt.Dialog)
        self._profile = profile
        self.enabled = not profile.readonly

        if self.enabled:
            self.setWindowTitle(f'Edit Profile - {profile.name}')
        else:
            self.setWindowTitle(f'Profile - {profile.name} (Read Only)')

        self._layout = QGridLayout(self)

        name_layout = QHBoxLayout()
        name_label = QLabel("Profile:")
        self.name_edit = QLineEdit(profile.name)
        names = [name for name in ExportProfile.names() if name != profile.name]
        self.name_edit.setValidator(ValueExistsValidator(*names))
        self.name_edit.setEnabled(self.enabled)
        name_layout.addWidget(name_label)
        name_layout.addWidget(self.name_edit)

        source_group = QGroupBox("Source Columns")
        source_layout = QVBoxLayout(source_group)

        self.source_category = QComboBox()
        source_layout.addWidget(self.source_category)
        self.source_category.currentTextChanged.connect(self._category_changed)

        self.source_view = QListView()
        source_layout.addWidget(self.source_view)
        self.source_view.setEnabled(self.enabled)
        self.source_view.doubleClicked.connect(self._slot_move_column)
        self.source_view.setSelectionMode(QListView.ExtendedSelection)

        self.source_model = QStandardItemModel()
        self.source_proxy = QSortFilterProxyModel()
        self.source_proxy.setSourceModel(self.source_model)
        self.source_proxy.setFilterRole(CategoryRole)
        self.source_proxy.setSortRole(ColumnIdRole)
        self.source_proxy.setSortCaseSensitivity(Qt.CaseInsensitive)
        self.source_proxy.sort(0, Qt.AscendingOrder)
        self.source_view.setModel(self.source_proxy)

        if self.enabled:
            source_controls = QDialogButtonBox()
            add_column = QPushButton("&Add")
            add_column.clicked.connect(lambda: self._action_move_columns(
                self.source_view, self.export_model))
            info_column = QPushButton("Deta&ils")
            source_controls.addButton(add_column, QDialogButtonBox.ActionRole)
            source_controls.addButton(info_column, QDialogButtonBox.HelpRole)
            source_layout.addWidget(source_controls)

        export_group = QGroupBox("Export Columns")
        export_layout = QGridLayout(export_group)
        self.export_view = QListView()
        export_layout.addWidget(self.export_view, 0, 0, 2, 2)
        self.export_view.setEnabled(self.enabled)
        self.export_model = QStandardItemModel()
        self.export_view.setModel(self.export_model)
        self.export_view.doubleClicked.connect(self._slot_move_column)
        self.export_view.setSelectionMode(QListView.ExtendedSelection)

        if self.enabled:
            export_controls = QDialogButtonBox()
            export_layout.addWidget(export_controls, 2, 0, 1, 2)
            export_controls.setEnabled(self.enabled)
            remove_column = QPushButton("&Remove")
            remove_column.clicked.connect(lambda: self._action_move_columns(
                self.export_view, self.source_model))
            remove_all_columns = QPushButton("Remove All")
            remove_all_columns.clicked.connect(self._action_remove_all)
            export_controls.addButton(remove_column, QDialogButtonBox.DestructiveRole)
            export_controls.addButton(remove_all_columns, QDialogButtonBox.DestructiveRole)

            export_order = QDialogButtonBox(Qt.Vertical)
            export_layout.addWidget(export_order, 1, 2)
            move_up = QPushButton(Icon.ARROW_UP.icon(), "")
            move_up.clicked.connect(lambda: self._action_reorder(Cardinal.NORTH))
            move_down = QPushButton(Icon.ARROW_DOWN.icon(), "")
            move_down.clicked.connect(lambda: self._action_reorder(Cardinal.SOUTH))
            export_order.addButton(move_up, QDialogButtonBox.ActionRole)
            export_order.addButton(move_down, QDialogButtonBox.ActionRole)

        self.ext_selector = QLineEdit(f'.{profile.ext}' if profile.ext else "")
        self.ext_selector.setEnabled(self.enabled)
        self.ext_selector.setToolTip("Override export format file extension.")
        self.ext_selector.setPlaceholderText("Using Exporter default extension")
        self.date_selector = QComboBox()
        self.date_selector.setEnabled(self.enabled)
        self.date_selector.addItems([fmt.name for fmt in TimeFormat])
        current_fmt = self.date_selector.findText(self._profile.dateformat.name)
        self.date_selector.setCurrentIndex(current_fmt)
        param_layout = QFormLayout()
        param_layout.addRow("File Extension", self.ext_selector)
        param_layout.addRow("Time Format", self.date_selector)

        dlg_btns = QDialogButtonBox(self)
        if self.enabled:
            dlg_btns.setStandardButtons(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        else:
            dlg_btns.setStandardButtons(QDialogButtonBox.Close)
        dlg_btns.accepted.connect(self.accept)
        dlg_btns.rejected.connect(self.reject)

        # Populate root layout
        self._layout.addLayout(name_layout, 0, 0, alignment=Qt.AlignLeft)
        self._layout.addWidget(source_group, 1, 0)
        self._layout.addWidget(export_group, 1, 1)
        self._layout.addLayout(param_layout, 2, 0)
        self._layout.addWidget(dlg_btns, 2, 1, alignment=Qt.AlignBottom)

        # Populate models
        for column in ColumnProfile.columns():
            item = QStandardItem(column.name)
            item.setData(column, ColumnRole)
            item.setData(column.identifier, ColumnIdRole)
            item.setData(column.category.name, CategoryRole)
            item.setEditable(False)
            item.setToolTip(f'{column.name} ({column.display_unit}) :: <{column.group}>')
            if column.identifier in self._profile.columns:
                self.export_model.appendRow(item)
            else:
                self.source_model.appendRow(item)

        for category in Category:
            self.source_category.addItem(category.name)

    def accept(self):
        if not self.name_edit.hasAcceptableInput():
            return

        columns = []
        for i in range(self.export_model.rowCount()):
            item: QStandardItem = self.export_model.item(i)
            col_profile: ColumnProfile = item.data(ColumnRole)
            columns.append(col_profile.identifier)

        self._profile.columns = columns

        ext = self.ext_selector.text().strip('.')
        self._profile.ext = ext

        dateformat = TimeFormat[self.date_selector.currentText()]
        self._profile.dateformat = dateformat

        name = self.name_edit.text()
        if name != self._profile.name:
            old_name = self._profile.name
            self._profile.name = name
            self.sigProfileMoved.emit(self._profile, old_name)
        self.sigProfileUpdated.emit(self._profile)
        super().accept()

    @staticmethod
    def _action_move_columns(from_view: QAbstractItemView,
                             dest_model: QStandardItemModel) -> None:
        """Move any selected items from the source view to destination model

        Parameters
        ----------
        from_view : :class:`QAbstractItemView`
        dest_model : :class:`QStandardItemModel`

        """
        model: QStandardItemModel = from_view.model()
        selection: QItemSelection = from_view.selectionModel().selection()
        if isinstance(model, QAbstractProxyModel):
            proxy = from_view.model()
            model: QStandardItemModel = proxy.sourceModel()
            selection: QItemSelection = proxy.mapSelectionToSource(selection)

        _to_remove = []
        for index in selection.indexes():  # type: QModelIndex
            item = model.takeItem(index.row())
            _to_remove.append(index.row())
            dest_model.appendRow(item)

        # Remove rows bottom to top, otherwise row indexes are invalidated
        for row in reversed(sorted(_to_remove)):
            model.removeRow(row)

    def _slot_move_column(self, index: QModelIndex):
        """Moves a column profile to the opposite model on double click"""
        model: QStandardItemModel = index.model()
        if isinstance(model, QAbstractProxyModel):
            model, proxy = model.sourceModel(), model
            proxy: QAbstractProxyModel
            index: QModelIndex = proxy.mapToSource(index)

        item = model.takeItem(index.row())
        model.removeRow(index.row())

        other = next((m for m in [self.export_model, self.source_model]
                      if m is not model))
        other.appendRow(item)

    def _action_reorder(self, direction: Cardinal):
        """Reorder items in the export view up or down"""
        idx: QModelIndex = self.export_view.currentIndex()
        if not idx.isValid():
            return
        model: QStandardItemModel = idx.model()
        if direction is Cardinal.NORTH:
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

    def _action_remove_all(self):
        """Remove all columns from Export model and move them to source model"""
        for i in range(self.export_model.rowCount()):
            item = self.export_model.takeItem(i)
            self.source_model.appendRow(item)
        self.export_model.clear()

    def _category_changed(self, text: str):
        if text == Category.All.name:
            self.source_proxy.setFilterFixedString("")
        else:
            self.source_proxy.setFilterFixedString(text)


class ExportDialog(QDialog):
    """ExportDialog provides a UI dialog allowing the user to export data to
    various file formats.

    Parameters
    ----------
    context : :class:`AbstractController`
    parent : QWidget

    """

    def __init__(self, context: AbstractController, parent=None):
        super().__init__(parent=parent, flags=Qt.Dialog)
        self._context = context

        self.setWindowTitle("Export Data")
        self._layout = QVBoxLayout(self)
        sp = QSizePolicy(QSizePolicy.MinimumExpanding, QSizePolicy.Maximum)

        # Model Definitions
        self.context_model = QStandardItemModel(self)
        self.export_model = QStandardItemModel(self)
        self.profile_model = QStandardItemModel(self)

        # Export Path Controls
        path_group = QGroupBox("Output Configuration")
        path_layout = QVBoxLayout(path_group)
        directory_layout = QHBoxLayout()
        path_layout.addLayout(directory_layout)
        self.file_path = QLineEdit()
        self.file_path.setValidator(DirectoryValidator())
        self.file_path.setPlaceholderText("Browse for directory")
        self.file_path.setToolTip("Export Directory")
        self.file_path.setText(self.last_dir)
        # self._file_path.textChanged.connect(lambda x: self._validate_input(self._file_path))
        self._browse = QPushButton('Browse...')
        self._browse.clicked.connect(self._browse_for_dir)
        directory_layout.addWidget(self.file_path, stretch=3)
        directory_layout.addWidget(self._browse)

        self.file_name = QLineEdit()
        self.file_name.setPlaceholderText("Customize output filename")
        path_layout.addWidget(self.file_name)

        # Export Context View
        context_group = QGroupBox("Export Context")
        context_layout = QVBoxLayout(context_group)
        self.context_view = QTreeView()
        self.context_view.setSizePolicy(sp)
        self.context_view.setToolTip("Select an object to narrow export scope")
        self.context_view.setHeaderHidden(True)
        self.context_view.setUniformRowHeights(True)
        self.context_view.setModel(self.context_model)
        context_layout.addWidget(self.context_view)

        # Exporter Selection View/Controls
        exporters_group = QGroupBox("Exporters")
        exporters_layout = QVBoxLayout(exporters_group)
        self.exporter_view = QListView()
        self.exporter_view.setSizePolicy(sp)
        self.exporter_view.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.exporter_view.setModel(self.export_model)
        exporters_layout.addWidget(self.exporter_view)

        # Export Profile Selection View/Controls
        profiles_group = QGroupBox("Profiles")
        profile_layout = QVBoxLayout(profiles_group)
        self.profile_view = QListView()
        self.profile_view.setSizePolicy(sp)
        self.profile_view.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.profile_view.setModel(self.profile_model)
        self.profile_view.doubleClicked.connect(self._action_edit_profile)
        self.profile_view.setContextMenuPolicy(Qt.CustomContextMenu)
        self.profile_view.customContextMenuRequested.connect(self._slot_profile_menu)

        profile_layout.addWidget(self.profile_view)

        # Profile List Actions
        profile_btns = QDialogButtonBox()
        profile_btns.setCenterButtons(True)

        add_profile = QPushButton("Add")
        edit_profile = QPushButton("Edit")
        copy_profile = QPushButton("Copy")
        self.del_profile = QPushButton("Delete")
        profile_btns.addButton(add_profile, QDialogButtonBox.ActionRole)
        profile_btns.addButton(edit_profile, QDialogButtonBox.ActionRole)
        profile_btns.addButton(copy_profile, QDialogButtonBox.ActionRole)
        profile_btns.addButton(self.del_profile, QDialogButtonBox.DestructiveRole)
        profile_layout.addWidget(profile_btns)

        add_profile.clicked.connect(self._action_new_profile)
        edit_profile.clicked.connect(self._action_edit_profile)
        copy_profile.clicked.connect(self._action_copy_profile)
        self.del_profile.clicked.connect(self._action_delete_profile)

        dlg_btns = QDialogButtonBox(QDialogButtonBox.Ok |
                                    QDialogButtonBox.Cancel,
                                    parent=self)
        dlg_btns.accepted.connect(self.accept)
        dlg_btns.rejected.connect(self.reject)

        self._err = QLabel()
        self._err.setStyleSheet("QLabel { color: red };")

        # Populate Root Layout
        self._layout.addWidget(path_group)
        self._layout.addWidget(context_group, stretch=0)
        self._layout.addSpacing(10)
        self._layout.addWidget(exporters_group, stretch=2)
        self._layout.addWidget(profiles_group, stretch=2)
        self._layout.addWidget(self._err)
        self._layout.addWidget(dlg_btns)

        # Populate Item Models
        self.context_model.appendRow(self._context.clone())

        for exporter in Exporter.exporters():
            self._mk_exporter_item(exporter)

        for profile in ExportProfile.profiles():
            self._mk_profile_item(profile)

        self.context_view.expandToDepth(1)
        self.context_view.setCurrentIndex(self.context_model.index(0, 0))
        # self.exporter_view.selectionModel().selectionChanged.connect(self._exporter_changed)
        self.profile_view.selectionModel().selectionChanged.connect(self._profile_changed)

        self.setSizePolicy(QSizePolicy(QSizePolicy.Preferred, QSizePolicy.Maximum))
        self.adjustSize()

    def accept(self):
        if not self.file_path.hasAcceptableInput():
            self.set_err(f"Invalid export path specified")
            return
        if self.exporter is None:
            self.set_err(f'No exporter selected')
            return
        if self.profile is None:
            self.set_err(f'No profile selected')
            return

        exporter = self.exporter(self.profile, self.selected_context)
        fullpath = self.path.joinpath(f'{self.filename}.{self.extension}')

        with fullpath.open('w') as fd:
            exporter.export(fd)

        _log.info(f"Sucessfully exported data from "
                  f"{self.selected_context.get_attr('name')}")

        settings().setValue(SettingsKey.LastExportPath(), str(self.path))
        super().accept()

    def set_err(self, text: str, prefix: str = "Error"):
        value = f'{prefix}: {text}' if text else ""
        self._err.setText(value)

    @property
    def path(self) -> Path:
        return Path(self.file_path.text())

    @property
    def filename(self) -> str:
        if self.file_name.text():
            return self.file_name.text()
        else:
            return self._context.get_attr('name')

    @property
    def extension(self) -> str:
        return self.profile.ext if self.profile.ext else self.exporter.ext

    @property
    def last_dir(self) -> str:
        return settings().value(SettingsKey.LastExportPath(), str(default_path))

    def _mk_exporter_item(self, exporter: Exporter, append=True) -> QStandardItem:
        item = QStandardItem(exporter.name)
        item.setData(exporter, ExporterRole)
        item.setToolTip(exporter.help)
        if append:
            self.export_model.appendRow(item)
        return item

    def _mk_profile_item(self, profile: ExportProfile, append=True) -> QStandardItem:
        item = QStandardItem(profile.name)
        item.setData(profile, ProfileRole)
        item.setToolTip(profile.description)
        if append:
            self.profile_model.appendRow(item)
        return item

    @property
    def selected_context(self) -> AbstractController:
        idx: QModelIndex = self.context_view.selectionModel().currentIndex()
        if not idx.isValid():
            return self._context
        item = self.context_model.itemFromIndex(idx)
        if not isinstance(item, AbstractController):
            return self._context
        return item

    @property
    def data(self):
        return self.selected_context.export()

    @property
    def exporter(self):
        idx: QModelIndex = self.exporter_view.currentIndex()
        return self.export_model.data(idx, ExporterRole)

    # def _exporter_changed(self, selected: QModelIndex, deselected: QModelIndex):
    #     print(f"Exporter changed to {self.exporter}")

    def get_profile_item(self, profile: ExportProfile) -> QStandardItem:
        for i in range(self.profile_model.rowCount()):
            item: QStandardItem = self.profile_model.item(i)
            if item.data(ProfileRole) == profile:
                return item

    @property
    def profile(self) -> ExportProfile:
        idx = self.profile_view.currentIndex()
        return self.profile_model.data(idx, ProfileRole)

    def _profile_changed(self, selected: QModelIndex, deselected: QModelIndex):
        if self.profile.readonly:
            self.del_profile.setEnabled(False)
        else:
            self.del_profile.setEnabled(True)

    def _browse_for_dir(self):
        path = QFileDialog.getExistingDirectory(self, "Select Directory",
                                                self.last_dir,
                                                QFileDialog.ShowDirsOnly)
        if path != "":
            self.file_path.setText(path)

    def _edit_profile(self, profile: ExportProfile):
        edit_dlg = ProfileEditDialog(profile, parent=self)
        edit_dlg.sigProfileUpdated.connect(self._write_user_profile)
        edit_dlg.sigProfileMoved.connect(self._move_user_profile)
        edit_dlg.exec_()

    def _action_new_profile(self):
        dlg = InputDialog("Create Profile", "New Profile Name:",
                          validator=ValueExistsValidator(*ExportProfile.names()),
                          parent=self)
        if dlg.exec_():
            profile = ExportProfile(dlg.value)
            self._mk_profile_item(profile, append=True)
            self._edit_profile(profile)

    def _action_copy_profile(self):
        if self.profile is None:
            return
        profile = self.profile.copy()
        dlg = InputDialog("Copy Profile", "Enter new name",
                          f'{profile.name} (copy)',
                          ValueExistsValidator(*ExportProfile.names()),
                          self)
        assert profile.uid != self.profile.uid
        if dlg.exec_():
            profile.name = dlg.value
            self._write_user_profile(profile)
            self._mk_profile_item(profile)

    def _action_delete_profile(self):
        if self.profile is None or self.profile.readonly:
            return
        name = self.profile.name
        if confirm_action("Delete Profile?",
                          f"Are you sure you want to delete profile: "
                          f"<{name}>",
                          parent=self):
            settings().beginGroup(SettingsKey.UserExportProfiles())
            settings().remove(self.profile.uid)
            settings().endGroup()

            self.profile_model.removeRow(self.profile_view.currentIndex().row())
            _log.debug(f'Deleted profile {name}')

    def _action_edit_profile(self, *args):
        if self.profile is None:
            return
        else:
            self._edit_profile(self.profile)

    def _slot_profile_menu(self, point: QPoint):
        idx: QModelIndex = self.profile_view.indexAt(point)
        menu = QMenu(self)
        if idx.isValid():
            menu.addAction("Export Profile Definition", lambda: self._action_export_profile(idx))
        menu.addAction("Import Profile", self._action_import_profile)
        return menu.popup(self.profile_view.mapToGlobal(point))

    def _action_export_profile(self, index: QModelIndex):
        profile: ExportProfile = index.model().data(index, ProfileRole)

        dest = QFileDialog.getExistingDirectory(self, "Select Export Directory",
                                                ".", QFileDialog.ShowDirsOnly)
        if dest:
            path = Path(dest).joinpath(f'{profile.name.strip()}.json')
            with path.open('w') as fd:
                fd.write(profile.to_json(indent=2))
            _log.debug(f'Profile {profile.name} exported to {path!s}')

    def _action_import_profile(self):
        path, _ = QFileDialog.getOpenFileName(self, "Import Profile",
                                              ".", "Profile (*.json);;Any (*.*)")
        if path:
            with Path(path).open('r') as fd:
                # TODO: Name verification, option to rename
                profile = ExportProfile.from_json(fd.read())
                ExportProfile.register(profile)

    def _move_user_profile(self, profile: ExportProfile, old_name: str):
        settings().beginGroup(SettingsKey.UserExportProfiles())
        settings().remove(old_name)
        settings().endGroup()

        item = self.get_profile_item(profile)
        item.setText(profile.name)

    @staticmethod
    def _write_user_profile(profile: ExportProfile) -> None:
        """Write user defined profile to QSettings"""
        _json_str = profile.to_json()
        settings().beginGroup(SettingsKey.UserExportProfiles())
        settings().setValue(profile.uid, _json_str)
        settings().endGroup()

    @classmethod
    def export_context(cls, context, parent=None):
        """Utility slot which returns a bare lambda which executes the dialog
        when called.
        """
        return lambda: cls(context, parent).exec_()
