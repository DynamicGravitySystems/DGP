# -*- coding: utf-8 -*-

import pathlib
import logging

import PyQt5.QtWidgets as QtWidgets
from PyQt5.QtCore import Qt, pyqtSlot
from PyQt5.QtGui import QColor
from PyQt5.QtWidgets import QMainWindow, QProgressDialog, QFileDialog, QWidget, QDialog

import dgp.core.types.enumerations as enums
from dgp.core.oid import OID
from dgp.core.controllers.controller_interfaces import IAirborneController, IBaseController
from dgp.core.controllers.project_controllers import AirborneProjectController
from dgp.core.controllers.project_treemodel import ProjectTreeModel
from dgp.core.models.project import AirborneProject
from dgp.gui.utils import (ConsoleHandler, LOG_FORMAT, LOG_LEVEL_MAP,
                           LOG_COLOR_MAP, get_project_file)
from dgp.gui.dialogs.create_project_dialog import CreateProjectDialog

from dgp.gui.workspace import WorkspaceTab
from dgp.gui.ui.main_window import Ui_MainWindow


class MainWindow(QMainWindow, Ui_MainWindow):
    """An instance of the Main Program Window"""

    def __init__(self, project: AirborneProjectController, *args):
        super().__init__(*args)

        self.setupUi(self)
        self.title = 'Dynamic Gravity Processor [*]'
        self.setWindowTitle(self.title)

        # Attach to the root logger to capture all child events
        self.log = logging.getLogger()
        # Setup logging handler to log to GUI panel
        console_handler = ConsoleHandler(self.write_console)
        console_handler.setFormatter(LOG_FORMAT)
        sb_handler = ConsoleHandler(self.show_status)
        sb_handler.setFormatter(logging.Formatter("%(message)s"))
        self.log.addHandler(console_handler)
        self.log.addHandler(sb_handler)
        self.log.setLevel(logging.DEBUG)

        # Setup Project
        project.set_parent_widget(self)

        # Instantiate the Project Model and display in the ProjectTreeView
        self.model = ProjectTreeModel(project)
        self.project_tree.setModel(self.model)
        self.project_tree.expandAll()

        # Support for multiple projects
        self.model.tabOpenRequested.connect(self._tab_open_requested)
        self.model.tabCloseRequested.connect(self._tab_close_requested)

        # Initialize Variables
        self.import_base_path = pathlib.Path('~').expanduser().joinpath(
            'Desktop')
        self._default_status_timeout = 5000  # Status Msg timeout in milli-sec

        # Issue #50 Flight Tabs
        # workspace is a custom Qt Widget (dgp.gui.workspace) promoted within the .ui file
        self.workspace: QtWidgets.QTabWidget
        self._open_tabs = {}  # Track opened tabs by {uid: tab_widget, ...}

        self._mutated = False

        self._init_slots()

    def _init_slots(self):  # pragma: no cover
        """Initialize PyQt Signals/Slots for UI Buttons and Menus"""

        # Event Signals #
        # self.model.flight_changed.connect(self._flight_changed)
        self.model.projectMutated.connect(self._project_mutated)

        # File Menu Actions #
        self.action_exit.triggered.connect(self.close)
        self.action_file_new.triggered.connect(self.new_project_dialog)
        self.action_file_open.triggered.connect(self.open_project_dialog)
        self.action_file_save.triggered.connect(self.save_projects)

        # Project Menu Actions #
        self.action_import_gps.triggered.connect(self._import_gps)
        self.action_import_grav.triggered.connect(self._import_gravity)
        self.action_add_flight.triggered.connect(self._add_flight)
        self.action_add_meter.triggered.connect(self._add_gravimeter)

        # Project Control Buttons #
        self.prj_add_flight.clicked.connect(self._add_flight)
        self.prj_add_meter.clicked.connect(self._add_gravimeter)
        self.prj_import_gps.clicked.connect(self._import_gps)
        self.prj_import_grav.clicked.connect(self._import_gravity)

        # Tab Browser Actions #
        self.workspace.tabCloseRequested.connect(self._tab_close_requested_local)
        self.workspace.currentChanged.connect(self._tab_index_changed)

        # Console Window Actions #
        self.combo_console_verbosity.currentIndexChanged[str].connect(
            self.set_logging_level)

    def load(self):
        """Called from splash screen to initialize and load main window.
        This may be safely deprecated as we currently do not perform any long
        running operations on initial load as we once did."""
        self.setWindowState(Qt.WindowMaximized)
        self.save_projects()
        self.show()

    def closeEvent(self, *args, **kwargs):
        self.log.info("Saving project and closing.")
        self.save_projects()
        super().closeEvent(*args, **kwargs)

    def set_logging_level(self, name: str):
        """PyQt Slot: Changes logging level to passed logging level name."""
        self.log.debug("Changing logging level to: {}".format(name))
        level = LOG_LEVEL_MAP[name.lower()]
        self.log.setLevel(level)

    def write_console(self, text, level):
        """PyQt Slot: Logs a message to the GUI console"""
        log_color = QColor(LOG_COLOR_MAP.get(level.lower(), 'black'))
        self.text_console.setTextColor(log_color)
        self.text_console.append(str(text))
        self.text_console.verticalScrollBar().setValue(
            self.text_console.verticalScrollBar().maximum())

    def show_status(self, text, level):
        """Displays a message in the MainWindow's status bar for specific
        log level events."""
        if level.lower() == 'error' or level.lower() == 'info':
            self.statusBar().showMessage(text, self._default_status_timeout)

    def _tab_open_requested(self, uid: OID, controller: IBaseController, label: str):
        self.log.debug("Tab Open Requested")
        if uid in self._open_tabs:
            self.workspace.setCurrentWidget(self._open_tabs[uid])
        else:
            self.log.debug("Creating new tab and adding to workspace")
            ntab = WorkspaceTab(controller)
            self._open_tabs[uid] = ntab
            self.workspace.addTab(ntab, label)
            self.workspace.setCurrentWidget(ntab)

    @pyqtSlot(OID, name='_flight_close_requested')
    def _tab_close_requested(self, uid: OID):
        """pyqtSlot(:class:`OID`)

        Close/dispose of the tab for the supplied flight if it exists, else
        do nothing.

        """
        if uid in self._open_tabs:
            tab = self._open_tabs[uid]
            index = self.workspace.indexOf(tab)
            self.workspace.removeTab(index)
            del self._open_tabs[uid]

    @pyqtSlot(int, name='_tab_close_requested_local')
    def _tab_close_requested_local(self, index):
        """pyqtSlot(int)

        Close/dispose of tab specified by int index.
        This slot is used to handle user interaction when clicking the close (x)
        button on an opened tab.

        """
        self.log.debug(f'Tab close requested for tab at index {index}')
        tab = self.workspace.widget(index)  # type: WorkspaceTab
        del self._open_tabs[tab.uid]
        self.workspace.removeTab(index)

    @pyqtSlot(name='_project_mutated')
    def _project_mutated(self):
        self._mutated = True
        self.setWindowModified(True)

    @pyqtSlot(int, name='_tab_index_changed')
    def _tab_index_changed(self, index: int):
        self.log.debug("Tab index changed to %d", index)
        current: WorkspaceTab = self.workspace.currentWidget()
        if current is not None:
            self.model.notify_tab_changed(current.root)
        else:
            self.log.debug("No flight tab open")

    def show_progress_dialog(self, title, start=0, stop=1, label=None,
                             cancel="Cancel", modal=False,
                             flags=None) -> QProgressDialog:
        """Generate a progress bar to show progress on long running event."""
        if flags is None:
            flags = (Qt.WindowSystemMenuHint |
                     Qt.WindowTitleHint |
                     Qt.WindowMinimizeButtonHint)

        dialog = QProgressDialog(label, cancel, start, stop, self, flags)
        dialog.setWindowTitle(title)
        dialog.setModal(modal)
        dialog.setMinimumDuration(0)
        # dialog.setCancelButton(None)
        dialog.setValue(1)
        dialog.show()
        return dialog

    def show_progress_status(self, start, stop, label=None) -> QtWidgets.QProgressBar:
        """Show a progress bar in the windows Status Bar"""
        label = label or 'Loading'
        sb = self.statusBar()  # type: QtWidgets.QStatusBar
        progress = QtWidgets.QProgressBar(self)
        progress.setRange(start, stop)
        progress.setAttribute(Qt.WA_DeleteOnClose)
        progress.setToolTip(label)
        sb.addWidget(progress)
        return progress

    def save_projects(self) -> None:
        self.model.save_projects()
        self.setWindowModified(False)
        self.log.info("Project saved.")

    # Project create/open dialog functions  ###################################

    def new_project_dialog(self) -> QDialog:
        def _add_project(prj: AirborneProject, new_window: bool):
            self.log.info("Creating new project.")
            control = AirborneProjectController(prj)
            if new_window:
                return MainWindow(control)
            else:
                self.model.add_project(control)
                self.save_projects()

        dialog = CreateProjectDialog(parent=self)
        dialog.sigProjectCreated.connect(_add_project)
        dialog.show()
        return dialog

    def open_project_dialog(self, checked: bool = False, path=None) -> QFileDialog:
        # TODO: Enable open in new window option
        def _project_selected(directory):
            prj_file = get_project_file(pathlib.Path(directory[0]))
            if prj_file is None:
                self.log.warning("No valid DGP project file found in directory")
                return
            with prj_file.open('r') as fd:
                project = AirborneProject.from_json(fd.read())
                if project.uid in [p.uid for p in self.model.projects]:
                    self.log.warning("Project is already opened")
                else:
                    control = AirborneProjectController(project)
                    self.model.add_project(control)
                    self.save_projects()

        if path is not None:
            _project_selected([path])
        else:  # pragma: no cover
            dialog = QFileDialog(self, "Open Project", str(self.import_base_path))
            dialog.setFileMode(QFileDialog.DirectoryOnly)
            dialog.setViewMode(QFileDialog.List)
            dialog.accepted.connect(lambda: _project_selected(dialog.selectedFiles()))
            dialog.setModal(True)
            dialog.show()

            return dialog

    # Active Project Action Slots
    @property
    def project_(self) -> IAirborneController:
        return self.model.active_project

    def _import_gps(self):  # pragma: no cover
        self.project_.load_file_dlg(enums.DataTypes.TRAJECTORY, )

    def _import_gravity(self):  # pragma: no cover
        self.project_.load_file_dlg(enums.DataTypes.GRAVITY, )

    def _add_gravimeter(self):  # pragma: no cover
        self.project_.add_gravimeter()

    def _add_flight(self):  # pragma: no cover
        self.project_.add_flight()
