# -*- coding: utf-8 -*-
import logging
import warnings
from pathlib import Path

import PyQt5.QtWidgets as QtWidgets
from PyQt5.QtCore import Qt, pyqtSlot, pyqtSignal, QByteArray
from PyQt5.QtGui import QColor, QCloseEvent, QDesktopServices
from PyQt5.QtWidgets import QProgressDialog, QFileDialog, QMessageBox, QMenu

from dgp import __about__
from dgp.core.oid import OID
from dgp.core.types.enumerations import Links
from dgp.core.controllers.controller_interfaces import IBaseController
from dgp.core.controllers.project_controllers import AirborneProjectController
from dgp.core.controllers.project_treemodel import ProjectTreeModel
from dgp.core.models.project import AirborneProject, GravityProject
from dgp.gui import settings, SettingsKey, RecentProjectManager, UserSettings
from dgp.gui.utils import (ConsoleHandler, LOG_FORMAT, LOG_LEVEL_MAP,
                           LOG_COLOR_MAP, ProgressEvent, load_project_from_path)
from dgp.gui.dialogs.create_project_dialog import CreateProjectDialog
from dgp.gui.dialogs.recent_project_dialog import RecentProjectDialog
from dgp.gui.widgets.workspace_widget import WorkspaceWidget
from dgp.gui.workspaces import tab_factory
from dgp.gui.ui.main_window import Ui_MainWindow


class MainWindow(QtWidgets.QMainWindow, Ui_MainWindow):
    """An instance of the Main Program Window"""
    sigStatusMessage = pyqtSignal(str)

    def __init__(self, *args):
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

        self.workspace: WorkspaceWidget
        self.recents = RecentProjectManager()
        self.user_settings = UserSettings()
        self._progress_events = {}

        # Instantiate the Project Model and display in the ProjectTreeView
        self.model = ProjectTreeModel(parent=self)
        self.project_tree.setModel(self.model)

        # Add sub-menu to display recent projects
        self.recent_menu = QMenu("Recent Projects")
        self.menuFile.addMenu(self.recent_menu)

        self.import_base_path = Path('~').expanduser().joinpath('Desktop')
        self._default_status_timeout = 5000  # Status Msg timeout in milli-sec

        # Initialize signal/slot connections:

        # Model Event Signals #
        self.model.tabOpenRequested.connect(self._tab_open_requested)
        self.model.tabCloseRequested.connect(self.workspace.close_tab)
        self.model.progressNotificationRequested.connect(self._progress_event_handler)
        self.model.projectMutated.connect(self._project_mutated)
        self.model.projectClosed.connect(lambda x: self._update_recent_menu())

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

        # Help Menu Actions #
        self.action_docs.triggered.connect(self.show_documentation)
        self.action_about.triggered.connect(self.show_about)

        # Project Control Buttons #
        self.prj_add_flight.clicked.connect(self.model.add_flight)
        self.prj_add_meter.clicked.connect(self.model.add_gravimeter)
        self.prj_import_gps.clicked.connect(self.model.import_gps)
        self.prj_import_grav.clicked.connect(self.model.import_gravity)

        # Console Window Actions #
        self.combo_console_verbosity.currentIndexChanged[str].connect(
            self.set_logging_level)

        # Define recent projects menu action
        self.recents.sigRecentProjectsChanged.connect(self._update_recent_menu)
        self._update_recent_menu()

    def load(self, project: GravityProject = None, restore: bool = True):
        """Interactively load the DGP MainWindow, restoring previous widget/dock
        state, and any saved geometry state.

        If a project is explicitly specified then the project will be loaded into
        the MainWindow, and the window shown.
        If no project is specified, the users local settings are checked for the
        last project that was active/opened, and it will be loaded into the
        window.
        Otherwise, a RecentProjectDialog is shown where the user can select from
        a list of known recent projects, browse for a project folder, or create
        a new project.

        Parameters
        ----------
        project : :class:`GravityProject`
            Explicitly pass a GravityProject or sub-type to be loaded into the
            main window.
        restore : bool, optional
            If True (default) the MainWindow state and geometry will be restored
            from the local settings repository.

        """
        if restore:
            self.restoreState(settings().value(SettingsKey.WindowState(), QByteArray()))
            self.restoreGeometry(settings().value(SettingsKey.WindowGeom(), QByteArray()))

        if project is not None:
            self.sigStatusMessage.emit(f'Loading project {project.name}')
            self.add_project(project)
        elif self.recents.last_project_path() is not None and self.user_settings.reopen_last:
            self.sigStatusMessage.emit(f'Loading last project')
            self.log.info(f"Loading most recent project.")
            project = load_project_from_path(self.recents.last_project_path())
            self.add_project(project)
        else:
            self.sigStatusMessage.emit("Selecting project")
            recent_dlg = RecentProjectDialog()
            recent_dlg.sigProjectLoaded.connect(self.add_project)
            recent_dlg.exec_()

        self.project_tree.expandAll()
        self.show()

    def add_project(self, project: GravityProject):
        """Add a project model to the window, first wrapping it in an
        appropriate controller class

        Parameters
        ----------
        project : :class:`GravityProject`
        path : :class:`pathlib.Path`


        """
        if isinstance(project, AirborneProject):
            control = AirborneProjectController(project)
        else:
            raise TypeError(f'Unsupported project type: {type(project)}')

        self.model.add_project(control)
        self.project_tree.setExpanded(control.index(), True)
        self.recents.add_recent_project(control.uid, control.get_attr('name'),
                                        control.path)

    def open_project(self, path: Path, prompt: bool = True) -> None:
        """Open/load a project from the given path.

        Parameters
        ----------
        path : :class:`pathlib.Path`
            Directory path containing valid DGP project *.json file
        prompt : bool, optional
            If True display a message box asking the user if they would like to
            open the project in a new window.
            Else the project is opened into the current MainWindow

        """
        project = load_project_from_path(path)
        if prompt and self.model.rowCount() > 0:
            msg_dlg = QMessageBox(QMessageBox.Question,
                                  "Open in New Window",
                                  "Open Project in New Window?",
                                  QMessageBox.Yes | QMessageBox.No, self)
            res = msg_dlg.exec_()
        else:
            res = QMessageBox.No

        if res == QMessageBox.Yes:  # Open new MainWindow instance
            window = MainWindow()
            window.load(project, restore=False)
            window.activateWindow()
        elif res == QMessageBox.No:  # Open in current MainWindow
            if project.uid in [p.uid for p in self.model.projects]:
                self.log.warning("Project already opened in current workspace")
            else:
                self.add_project(project)
                self.raise_()

    def closeEvent(self, event: QCloseEvent):
        self.log.info("Saving project and closing.")
        self.save_projects()
        settings().setValue(SettingsKey.WindowState(), self.saveState())
        settings().setValue(SettingsKey.WindowGeom(), self.saveGeometry())

        # Set last project to active project
        if self.model.active_project is not None:
            settings().setValue(SettingsKey.LastProjectUid(),
                                self.model.active_project.uid.base_uuid)
            settings().setValue(SettingsKey.LastProjectPath(),
                                str(self.model.active_project.path.absolute()))
            settings().setValue(SettingsKey.LastProjectName(),
                                self.model.active_project.get_attr("name"))
        super().closeEvent(event)

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

    def _update_recent_menu(self):
        """Regenerate the recent projects' menu actions

        Retrieves the recent projects references from the
        :class:`RecentProjectManager` and adds them to the recent projects list
        if they are not already active/open in the workspace.
        """
        self.recent_menu.clear()
        recents = [ref for ref in self.recents.project_refs
                   if ref.uid not in [p.uid for p in self.model.projects]]
        if len(recents) == 0:
            self.recent_menu.setEnabled(False)
        else:
            self.recent_menu.setEnabled(True)
        for ref in recents:
            self.recent_menu.addAction(ref.name, lambda: self.open_project(Path(ref.path)))

    def _tab_open_requested(self, uid: OID, controller: IBaseController):
        """pyqtSlot(OID, IBaseController, str)

        Parameters
        ----------
        uid
        controller

        """
        existing = self.workspace.get_tab(uid)
        if existing is not None:
            self.workspace.setCurrentWidget(existing)
        else:
            constructor = tab_factory(controller)
            if constructor is not None:
                tab = constructor(controller)
                self.workspace.addTab(tab)
            else:
                warnings.warn(f"Tab control not implemented for type "
                              f"{type(controller)}")

    @pyqtSlot(name='_project_mutated')
    def _project_mutated(self):
        """pyqtSlot(None)

        Update the MainWindow title bar to reflect unsaved changes in the project
        """
        self.setWindowModified(True)

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

    def save_projects(self) -> None:
        self.model.save_projects()
        self.setWindowModified(False)
        self.log.info("Project saved.")

    # Project create/open dialog functions  ###################################

    def new_project_dialog(self) -> QtWidgets.QDialog:
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
        dialog = CreateProjectDialog(parent=self)
        dialog.sigProjectCreated.connect(lambda prj: self.open_project(prj.path, prompt=False))
        dialog.show()
        return dialog

    def open_project_dialog(self, *args):  # pragma: no cover
        """pyqtSlot()
        Opens an existing project within the current Project MainWindow,
        adding the opened project as a tree item to the Project Tree navigator.

        Parameters
        ----------
        args
            Consume positional arguments, some buttons connected to this slot
            will pass a 'checked' boolean flag which is not applicable here.

        """
        dialog = QFileDialog(self, "Open Project", str(self.import_base_path))
        dialog.setFileMode(QFileDialog.DirectoryOnly)
        dialog.setViewMode(QFileDialog.List)
        dialog.fileSelected.connect(lambda file: self.open_project(Path(file)))
        dialog.exec_()

    def show_documentation(self):  # pragma: no cover
        """Launch DGP's online documentation (RTD) in the default browser"""
        QDesktopServices.openUrl(Links.DEV_DOCS.url())

    def show_about(self):  # pragma: no cover
        """Display 'About' information for the DGP project"""
        QMessageBox.about(self, "About DGP", __about__)
