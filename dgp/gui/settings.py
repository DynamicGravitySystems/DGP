# -*- coding: utf-8 -*-
import time
from contextlib import contextmanager
from enum import Enum
from pathlib import Path
from typing import Union, Generator

from PyQt5.QtCore import QSettings, QModelIndex, QObject, pyqtSignal
from PyQt5.QtGui import QStandardItemModel, QStandardItem

from dgp.core import OID

PathRole = 0x101
RefRole = 0x102
UidRole = 0x103
ModRole = 0x104

MaybePath = Union[Path, None]

_ORG = "DynamicGravitySystems"
_APP = "DynamicGravityProcessor"
_settings = QSettings(QSettings.NativeFormat, QSettings.UserScope, _ORG, _APP)
_recent_model = QStandardItemModel()


def set_settings(handle: QSettings):
    """Set the global QSettings object to a custom handler"""
    global _settings
    _settings = handle


def settings() -> QSettings:
    """Expose the global QSettings object"""
    return _settings


class SettingsKey(Enum):
    WindowState = "Window/state"
    WindowGeom = "Window/geom"
    LastProjectPath = "Project/latest/path"
    LastProjectName = "Project/latest/name"
    LastProjectUid = "Project/latest/uid"
    RecentProjects = "Project/recent"

    # User Option Properties
    LoadLastProject = "User/LoadLast"
    RestoreWorkspace = "User/RestoreWorkspace"
    OpenInNewWindow = "User/OpenInNewWindow"
    LastExportPath = "User/LastExportPath"

    def __call__(self):
        """Allow retrieval of the enum value using call syntax `()` """
        return self.value


@contextmanager
def settings_group(key: str):
    _settings.beginGroup(key)
    yield settings
    _settings.endGroup()


class RecentProject:
    """Simple project reference, contains the metadata required to load or refer
    to a DGP project on the local computer.
    Used by the RecentProjectManager to maintain a structured reference to any
    specific project.

    RecentProject provides a __hash__ method allowing references to be compared
    by their UID hash
    """
    def __init__(self, uid: str, name: str, path: str, modified=None, **kwargs):
        self.uid: str = uid
        self.name: str = name
        self.path: str = str(path)
        self.modified = modified or time.time()

    def __hash__(self):
        return hash(self.uid)


class RecentProjectManager(QObject):
    """QSettings wrapper used to manage the retrieval/setting of recent projects
    that have been loaded for the user.

    """
    sigRecentProjectsChanged = pyqtSignal()

    def __init__(self, qsettings: QSettings = None, parent=None):
        super().__init__(parent=parent)
        self._settings = qsettings or _settings
        self._key = SettingsKey.RecentProjects()
        self._model = _recent_model
        self._load_recent_projects()

    @property
    def model(self):
        return self._model

    @property
    def project_refs(self) -> Generator[RecentProject, None, None]:
        for i in range(self.model.rowCount()):
            yield self.model.item(i).data(RefRole)

    def last_project_path(self) -> MaybePath:
        raw_path = self._settings.value(SettingsKey.LastProjectPath(), None)
        if raw_path is not None:
            return Path(raw_path)
        else:
            return None

    def last_project_name(self) -> Union[str, None]:
        return self._settings.value(SettingsKey.LastProjectName(), None)

    def add_recent_project(self, uid: OID, name: str, path: Path) -> None:
        """Add a project to the list of recent projects, managed via the
        QSettings object

        If the project UID already exists in the recent projects list, update
        the entry, otherwise create a new entry, commit it, and add an item
        to the model representation.

        Parameters
        ----------
        uid : OID
        name : str
        path : :class:`pathlib.Path`

        """
        self.refresh()
        str_path = str(path.absolute())
        ref = RecentProject(uid.base_uuid, name, str_path)

        for i in range(self._model.rowCount()):
            child: QStandardItem = self._model.item(i)
            if child.data(UidRole) == uid:
                child.setText(name)
                child.setToolTip(str_path)
                child.setData(path, PathRole)
                child.setData(ref, RefRole)
                break
        else:  # no break
            item = self.item_from_ref(ref)
            self._model.insertRow(0, item)

        self._commit_recent_projects()
        self.sigRecentProjectsChanged.emit()

    def clear(self) -> None:
        """Clear recent projects from the model AND persistent settings state"""
        self._model.clear()
        self._settings.remove(self._key)
        self.sigRecentProjectsChanged.emit()

    def refresh(self) -> None:
        """Force a refresh of the recent projects list by reloading state

        Alias for _load_recent_projects

        """
        self._load_recent_projects()

    def path(self, index: QModelIndex) -> MaybePath:
        """Retrieve path data from a model item, given the items QModelIndex

        Returns
        -------
        Path or None
            pathlib.Path object if the item and data exists, else None

        """
        item: QStandardItem = self._model.itemFromIndex(index)
        if item == 0:
            return None
        return item.data(PathRole)

    def _commit_recent_projects(self) -> None:
        """Commit the recent projects model to file (via QSettings interface),
        replacing any current items at the recent projects key.

        """
        self._settings.remove(self._key)
        self._settings.beginWriteArray(self._key)
        for i in range(self._model.rowCount()):
            self._settings.setArrayIndex(i)
            ref = self._model.item(i).data(RefRole)
            for key in ref.__dict__:
                self._settings.setValue(key, getattr(ref, key, None))

        self._settings.endArray()

    def _load_recent_projects(self) -> None:
        self._model.clear()

        size = self._settings.beginReadArray(self._key)
        for i in range(size):
            self._settings.setArrayIndex(i)
            keys = self._settings.childKeys()
            params = {key: self._settings.value(key) for key in keys}

            ref = RecentProject(**params)
            item = self.item_from_ref(ref)
            self._model.appendRow(item)
        self._settings.endArray()
        self.sigRecentProjectsChanged.emit()

    @staticmethod
    def item_from_ref(ref: RecentProject) -> QStandardItem:
        """Create a standardized QStandardItem for the model given a RecentProject

        """
        item = QStandardItem(ref.name)
        item.setToolTip(str(ref.path))
        item.setData(Path(ref.path), PathRole)
        item.setData(ref.uid, UidRole)
        item.setData(ref, RefRole)
        item.setEditable(False)
        return item


class UserSettings:
    @property
    def reopen_last(self) -> bool:
        return bool(_settings.value(SettingsKey.LoadLastProject(), False))

    @property
    def new_window(self) -> bool:
        return bool(_settings.value(SettingsKey.OpenInNewWindow(), False))
