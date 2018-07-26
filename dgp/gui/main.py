# -*- coding: utf-8 -*-

import pathlib
import logging

import PyQt5.QtWidgets as QtWidgets
from PyQt5.QtCore import Qt, pyqtSlot
from PyQt5.QtGui import QColor
from PyQt5.QtWidgets import QMainWindow, QProgressDialog, QFileDialog, QDialog

from dgp.core.oid import OID
from dgp.core.controllers.controller_interfaces import IBaseController
from dgp.core.controllers.project_controllers import AirborneProjectController
from dgp.core.controllers.project_treemodel import ProjectTreeModel
from dgp.core.models.project import AirborneProject
from dgp.gui.utils import (ConsoleHandler, LOG_FORMAT, LOG_LEVEL_MAP,
                           LOG_COLOR_MAP, get_project_file, ProgressEvent)
from dgp.gui.dialogs.create_project_dialog import CreateProjectDialog

from dgp.gui.workspace import WorkspaceTab, MainWorkspace
from dgp.gui.ui.main_window import Ui_MainWindow


class MainWindow(QMainWindow, Ui_MainWindow):
    """An instance of the Main Program Window"""

    def __init__(self, project: AirborneProjectController, *args):
        super().__init__(*args)

        self.setupUi(self)
        self.workspace: MainWorkspace

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

        # Initialize Variables
        self.import_base_path = pathlib.Path('~').expanduser().joinpath(
            'Desktop')
        self._default_status_timeout = 5000  # Status Msg timeout in milli-sec

        self._progress_events = {}
        self._mutated = False

        self._init_slots()

    def _init_slots(self):  # pragma: no cover
        """Initialize PyQt Signals/Slots for UI Buttons and Menus"""

        # Model Event Signals #
        self.model.tabOpenRequested.connect(self._tab_open_requested)
        self.model.tabCloseRequested.connect(self.workspace.close_tab)
        self.model.progressNotificationRequested.connect(self._progress_event_handler)
        self.model.projectMutated.connect(self._project_mutated)

        # File Menu Actions #
        self.action_exit.triggered.connect(self.close)
        self.action_file_new.triggered.connect(self.new_project_dialog)
        self.action_file_open.triggered.connect(self.open_project_dialog)
        self.action_file_save.triggered.connect(self.save_projects)

        # Project Menu Actions #
        self.action_import_gps.triggered.connect(self.model.import_gps)
        self.action_import_grav.triggered.connect(self.model.import_gravity)
        self.action_add_flight.triggered.connect(self.model.add_flight)
        self.action_add_meter.triggered.connect(self.model.add_gravimeter)

        # Project Control Buttons #
        self.prj_add_flight.clicked.connect(self.model.add_flight)
        self.prj_add_meter.clicked.connect(self.model.add_gravimeter)
        self.prj_import_gps.clicked.connect(self.model.import_gps)
        self.prj_import_grav.clicked.connect(self.model.import_gravity)

        # Tab Browser Actions #
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
        """pyqtSlot(OID, IBaseController, str)

        Parameters
        ----------
        uid
        controller
        label

        Returns
        -------

        """
        tab = self.workspace.get_tab(uid)
        if tab is not None:
            self.workspace.setCurrentWidget(tab)
        else:
            self.log.debug("Creating new tab and adding to workspace")
            ntab = WorkspaceTab(controller)
            self.workspace.addTab(ntab, label)
            self.workspace.setCurrentWidget(ntab)

    @pyqtSlot(name='_project_mutated')
    def _project_mutated(self):
        """pyqtSlot(None)
        Update the MainWindow title bar to reflect unsaved changes in the project

        """
        self._mutated = True
        self.setWindowModified(True)

    @pyqtSlot(int, name='_tab_index_changed')
    def _tab_index_changed(self, index: int):
        """pyqtSlot(int)
        Notify the project model when the in-focus Workspace tab changes

        """
        current: WorkspaceTab = self.workspace.currentWidget()
        if current is not None:
            self.model.notify_tab_changed(current.root)
        else:
            self.log.debug("No flight tab open")

    @pyqtSlot(ProgressEvent, name='_progress_event_handler')
    def _progress_event_handler(self, event: ProgressEvent):
        if event.uid in self._progress_events:
            # Update progress
            self.log.debug(f"Updating progress bar for UID {event.uid}")
            dlg: QProgressDialog = self._progress_events[event.uid]
            dlg.setValue(event.value)

            if event.completed:
                self.log.debug("Event completed, closing progress dialog")
                dlg.reset()
                dlg.close()
                del self._progress_events[event.uid]
                return

            dlg.setLabelText(event.label)
        else:
            flags = (Qt.WindowSystemMenuHint |
                     Qt.WindowTitleHint |
                     Qt.WindowMinimizeButtonHint)
            dlg = QProgressDialog(event.label, "", event.start, event.stop, self, flags)
            dlg.setMinimumDuration(0)
            dlg.setModal(event.modal)
            dlg.setValue(event.value)
            if event.receiver:
                dlg.open(event.receiver)
            else:
                dlg.setValue(1)
                dlg.show()
            self._progress_events[event.uid] = dlg

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
        """pyqtSlot()
        Launch a :class:`CreateProjectDialog` to enable the user to create a new
        project instance.
        If a new project is created it is opened in a new MainWindow if the
        dialog's sigProjectCreated new_window flag is True, else it is added
        to the current window Project Tree View, below any already opened
        projects.

        Returns
        -------
        :class:`CreateProjectDialog`
            Reference to modal CreateProjectDialog

        """
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

    def open_project_dialog(self, *args, path: pathlib.Path=None) -> QFileDialog:
        """pyqtSlot()
        Opens an existing project within the current Project MainWindow,
        adding the opened project as a tree item to the Project Tree navigator.

        ToDo: Add prompt or flag to launch project in new MainWindow

        Parameters
        ----------
        args
            Consume positional arguments, some buttons connected to this slot
            will pass a 'checked' boolean flag which is not applicable here.
        path : :class:`pathlib.Path`
            Path to a directory containing a dgp json project file.
            Used to programmatically load a project (without launching the
            FileDialog).

        Returns
        -------
        QFileDialog
            Reference to QFileDialog file-browser dialog when called with no
            path argument.

        """

        def _project_selected(directory):
            prj_dir = pathlib.Path(directory[0])
            prj_file = get_project_file(prj_dir)
            if prj_file is None:
                self.log.warning("No valid DGP project file found in directory")
                return
            with prj_file.open('r') as fd:
                project = AirborneProject.from_json(fd.read())
                if project.uid in [p.uid for p in self.model.projects]:
                    self.log.warning("Project is already opened")
                else:
                    control = AirborneProjectController(project, path=prj_dir)
                    control.set_parent_widget(self)
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
