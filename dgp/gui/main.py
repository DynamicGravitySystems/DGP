# coding: utf-8

import os
import pathlib
import functools
import logging
from typing import Union

import PyQt5.QtCore as QtCore
import PyQt5.QtGui as QtGui
from PyQt5.QtWidgets import (QMainWindow, QTabWidget, QAction, QMenu,
                             QProgressDialog, QFileDialog, QTreeView)
from PyQt5.QtCore import pyqtSignal, pyqtBoundSignal
from PyQt5.QtGui import QColor
from PyQt5.uic import loadUiType

import dgp.lib.project as prj
import dgp.lib.types as types
from dgp.gui.loader import LoadFile
from dgp.gui.utils import (ConsoleHandler, LOG_FORMAT, LOG_LEVEL_MAP,
                           get_project_file)
from dgp.gui.dialogs import (AddFlight, CreateProject, InfoDialog,
                             AdvancedImport)
from dgp.gui.models import TableModel, ProjectModel
from dgp.gui.widgets import FlightTab, TabWorkspace


# Load .ui form
main_window, _ = loadUiType('dgp/gui/ui/main_window.ui')


def autosave(method):
    """Decorator to call save_project for functions that alter project state."""
    def enclosed(self, *args, **kwargs):
        if kwargs:
            result = method(self, *args, **kwargs)
        elif len(args) > 1:
            result = method(self, *args)
        else:
            result = method(self)
        self.save_project()
        return result
    return enclosed


class MainWindow(QMainWindow, main_window):
    """An instance of the Main Program Window"""

    # Define signals to allow updating of loading progress
    status = pyqtSignal(str)  # type: pyqtBoundSignal
    progress = pyqtSignal(int)  # type: pyqtBoundSignal

    def __init__(self, project: Union[prj.GravityProject,
                                      prj.AirborneProject]=None, *args):
        super().__init__(*args)

        self.setupUi(self)
        self.title = 'Dynamic Gravity Processor'

        # Attach to the root logger to capture all child events
        self.log = logging.getLogger()
        # Setup logging handler to log to GUI panel
        console_handler = ConsoleHandler(self.write_console)
        console_handler.setFormatter(LOG_FORMAT)
        self.log.addHandler(console_handler)
        self.log.setLevel(logging.DEBUG)

        # Setup Project
        self.project = project

        # Set Stylesheet customizations for GUI Window, see:
        # http://doc.qt.io/qt-5/stylesheet-examples.html#customizing-qtreeview
        self.setStyleSheet("""
            QTreeView::item {
            }
            QTreeView::branch {
                /*background: palette(base);*/
            }
            QTreeView::branch:closed:has-children {
                background: none;
                image: url(:/images/assets/branch-closed.png);
            }
            QTreeView::branch:open:has-children {
                background: none;
                image: url(:/images/assets/branch-open.png);
            }
        """)

        # Initialize Variables
        # self.import_base_path = pathlib.Path('../tests').resolve()
        self.import_base_path = pathlib.Path('~').expanduser().joinpath(
            'Desktop')

        # Issue #50 Flight Tabs
        self._tabs = self.tab_workspace  # type: TabWorkspace
        # self._tabs = CustomTabWidget()
        self._open_tabs = {}  # Track opened tabs by {uid: tab_widget, ...}
        self._context_tree = self.contextual_tree  # type: QTreeView
        self._context_tree.setRootIsDecorated(False)
        self._context_tree.setIndentation(20)
        self._context_tree.setItemsExpandable(False)

        # Initialize Project Tree Display
        self.project_tree = ProjectTreeView(parent=self, project=self.project)
        self.project_tree.setMinimumWidth(250)
        self.project_dock_grid.addWidget(self.project_tree, 0, 0, 1, 2)

    @property
    def current_flight(self) -> Union[prj.Flight, None]:
        """Returns the active flight based on which Flight Tab is in focus."""
        if self._tabs.count() > 0:
            return self._tabs.currentWidget().flight
        return None

    @property
    def current_tab(self) -> Union[FlightTab, None]:
        """Get the active FlightTab (returns None if no Tabs are open)"""
        if self._tabs.count() > 0:
            return self._tabs.currentWidget()
        return None

    def load(self):
        """Called from splash screen to initialize and load main window.
        This may be safely deprecated as we currently do not perform any long
        running operations on initial load as we once did."""
        self._init_slots()
        self.setWindowState(QtCore.Qt.WindowMaximized)
        self.save_project()
        self.show()
        try:
            self.progress.disconnect()
            self.status.disconnect()
        except TypeError:
            # This can be safely ignored (no slots were connected)
            pass

    def _init_slots(self):
        """Initialize PyQt Signals/Slots for UI Buttons and Menus"""

        # File Menu Actions #
        self.action_exit.triggered.connect(self.close)
        self.action_file_new.triggered.connect(self.new_project_dialog)
        self.action_file_open.triggered.connect(self.open_project_dialog)
        self.action_file_save.triggered.connect(self.save_project)

        # Project Menu Actions #
        self.action_import_data.triggered.connect(self.import_data_dialog)
        self.action_add_flight.triggered.connect(self.add_flight_dialog)

        # Project Tree View Actions #
        self.project_tree.doubleClicked.connect(self._launch_tab)

        # Project Control Buttons #
        self.prj_add_flight.clicked.connect(self.add_flight_dialog)
        self.prj_import_data.clicked.connect(self.import_data_dialog)

        # Tab Browser Actions #
        self.tab_workspace.currentChanged.connect(self._tab_changed)
        self.tab_workspace.tabCloseRequested.connect(self._tab_closed)

        # Console Window Actions #
        self.combo_console_verbosity.currentIndexChanged[str].connect(
            self.set_logging_level)

    def closeEvent(self, *args, **kwargs):
        self.log.info("Saving project and closing.")
        self.save_project()
        super().closeEvent(*args, **kwargs)

    def set_logging_level(self, name: str):
        """PyQt Slot: Changes logging level to passed logging level name."""
        self.log.debug("Changing logging level to: {}".format(name))
        level = LOG_LEVEL_MAP[name.lower()]
        self.log.setLevel(level)

    def write_console(self, text, level):
        """PyQt Slot: Logs a message to the GUI console"""
        # TODO: log_color is defined elsewhere, use it.
        log_color = {'DEBUG': QColor('DarkBlue'), 'INFO': QColor('Green'),
                     'WARNING': QColor('Red'), 'ERROR': QColor('Pink'),
                     'CRITICAL': QColor('Orange')}.get(level.upper(),
                                                       QColor('Black'))

        self.text_console.setTextColor(log_color)
        self.text_console.append(str(text))
        self.text_console.verticalScrollBar().setValue(
            self.text_console.verticalScrollBar().maximum())

    def _launch_tab(self, index: QtCore.QModelIndex=None, flight=None) -> None:
        """
        PyQtSlot:  Called to launch a flight from the Project Tree View.
        This function can also be called independent of the Model if a flight is
        specified, for e.g. when creating a new Flight object.
        Parameters
        ----------
        index : QModelIndex
            Model index pointing to a prj.Flight object to launch the tab for
        flight : prj.Flight
            Optional - required if this function is called without an index

        Returns
        -------
        None
        """
        if flight is None:
            item = index.internalPointer()
            if not isinstance(item, prj.Flight):
                self.project_tree.toggle_expand(index)
                return
            flight = item  # type: prj.Flight
            if flight.uid in self._open_tabs:
                self._tabs.setCurrentWidget(self._open_tabs[flight.uid])
                self.project_tree.toggle_expand(index)
                return

        self.log.info("Launching tab for flight: UID<{}>".format(flight.uid))
        new_tab = FlightTab(flight)
        new_tab.contextChanged.connect(self._update_context_tree)
        self._open_tabs[flight.uid] = new_tab
        t_idx = self._tabs.addTab(new_tab, flight.name)
        self._tabs.setCurrentIndex(t_idx)

    def _tab_closed(self, index: int):
        # TODO: Should we delete the tab, or pop it off the stack to a cache?
        self.log.warning("Tab close requested for tab: {}".format(index))
        flight_id = self._tabs.widget(index).flight.uid
        self._tabs.removeTab(index)
        del self._open_tabs[flight_id]

    def _tab_changed(self, index: int):
        self.log.info("Tab changed to index: {}".format(index))
        if index == -1:  # If no tabs are displayed
            self._context_tree.setModel(None)
            return
        tab = self._tabs.widget(index)  # type: FlightTab
        self._context_tree.setModel(tab.context_model)
        self._context_tree.expandAll()

    def _update_context_tree(self, model):
        self.log.debug("Tab subcontext changed. Changing Tree Model")
        self._context_tree.setModel(model)
        self._context_tree.expandAll()

    def data_added(self, flight: prj.Flight, src: types.DataSource) -> None:
        """
        Register a new data file with a flight and updates the Flight UI
        components if the flight is open in a tab.

        Parameters
        ----------
        flight : prj.Flight
            Flight object with related Gravity and GPS properties to plot
        src : types.DataSource
            DataSource object containing pointer and metadata to a DataFrame

        Returns
        -------
        None
        """
        flight.register_data(src)
        if flight.uid not in self._open_tabs:
            # If flight is not opened we don't need to update the plot
            return
        else:
            tab = self._open_tabs[flight.uid]  # type: FlightTab
            tab.new_data(src)  # tell the tab that new data is available
            return

    def progress_dialog(self, title, start=0, stop=1):
        """Generate a progress bar to show progress on long running event."""
        dialog = QProgressDialog(title, "Cancel", start, stop, self)
        dialog.setWindowTitle("Loading...")
        dialog.setModal(True)
        dialog.setMinimumDuration(0)
        dialog.setCancelButton(None)
        dialog.setValue(0)
        return dialog

    def import_data(self, path: pathlib.Path, dtype: str, flight: prj.Flight,
                    fields=None):
        """
        Load data of dtype from path, using a threaded loader class
        Upon load the data file should be registered with the specified flight.
        """
        assert path is not None
        self.log.info("Importing <{dtype}> from: Path({path}) into"
                      " <Flight({name})>".format(dtype=dtype, path=str(path),
                                                 name=flight.name))

        loader = LoadFile(path, dtype, fields=fields, parent=self)

        progress = self.progress_dialog("Loading", 0, 0)

        loader.data.connect(lambda ds: self.data_added(flight, ds))
        loader.progress.connect(progress.setValue)
        loader.loaded.connect(self.save_project)
        loader.loaded.connect(progress.close)

        loader.start()

    def save_project(self) -> None:
        if self.project is None:
            return
        if self.project.save():
            self.setWindowTitle(self.title + ' - {} [*]'
                                .format(self.project.name))
            self.setWindowModified(False)
            self.log.info("Project saved.")
        else:
            self.log.info("Error saving project.")

    #####
    # Project dialog functions
    #####

    def import_data_dialog(self) -> None:
        """Load data file (GPS or Gravity) using a background Thread, then hand
        it off to the project."""
        dialog = AdvancedImport(self.project, self.current_flight)
        if dialog.exec_():
            path, dtype, fields, flight = dialog.content
            self.import_data(path, dtype, flight, fields=fields)
        return

    def new_project_dialog(self) -> QMainWindow:
        new_window = True
        dialog = CreateProject()
        if dialog.exec_():
            self.log.info("Creating new project")
            project = dialog.project
            if new_window:
                self.log.debug("Opening project in new window")
                return MainWindow(project)
            else:
                self.project = project
                self.project.save()
                self.update_project()

    # TODO: This will eventually require a dialog to allow selection of project
    # type, or a metadata file in the project directory specifying type info
    def open_project_dialog(self) -> None:
        path = QFileDialog.getExistingDirectory(self, "Open Project Directory",
                                                os.path.abspath('..'))
        if not path:
            return

        prj_file = get_project_file(path)
        if prj_file is None:
            self.log.warning("No project file's found in directory: {}"
                             .format(path))
            return
        self.save_project()
        self.project = prj.AirborneProject.load(prj_file)
        self.update_project()
        return

    @autosave
    def add_flight_dialog(self) -> None:
        dialog = AddFlight(self.project)
        if dialog.exec_():
            flight = dialog.flight
            self.log.info("Adding flight {}".format(flight.name))
            self.project.add_flight(flight)

            if dialog.gravity:
                self.import_data(dialog.gravity, 'gravity', flight)
            if dialog.gps:
                self.import_data(dialog.gps, 'gps', flight)
            self._launch_tab(flight=flight)
            return
        self.log.info("New flight creation aborted.")
        return


# TODO: Move this into new module (e.g. gui/views.py)
class ProjectTreeView(QTreeView):
    def __init__(self, project=None, parent=None):
        super().__init__(parent=parent)

        self._project = project
        self.log = logging.getLogger(__name__)

        self.setMinimumSize(QtCore.QSize(0, 300))
        self.setAlternatingRowColors(False)
        self.setAutoExpandDelay(1)
        self.setExpandsOnDoubleClick(False)
        self.setRootIsDecorated(False)
        self.setUniformRowHeights(True)
        self.setHeaderHidden(True)
        self.setObjectName('project_tree')
        self.setContextMenuPolicy(QtCore.Qt.DefaultContextMenu)
        self._init_model()

    def _init_model(self):
        """Initialize a new-style ProjectModel from models.py"""
        model = ProjectModel(self._project, parent=self)
        self.setModel(model)
        self.expandAll()

    def toggle_expand(self, index):
        self.setExpanded(index, (not self.isExpanded(index)))

    def contextMenuEvent(self, event: QtGui.QContextMenuEvent, *args, **kwargs):
        # get the index of the item under the click event
        context_ind = self.indexAt(event.pos())
        context_focus = self.model().itemFromIndex(context_ind)

        info_slot = functools.partial(self._info_action, context_focus)
        plot_slot = functools.partial(self._plot_action, context_focus)
        menu = QMenu()
        info_action = QAction("Info")
        info_action.triggered.connect(info_slot)
        plot_action = QAction("Plot in new window")
        plot_action.triggered.connect(plot_slot)

        menu.addAction(info_action)
        menu.addAction(plot_action)
        menu.exec_(event.globalPos())
        event.accept()

    def _plot_action(self, item):
        raise NotImplementedError

    def _info_action(self, item):
        if not (isinstance(item, prj.Flight)
                or isinstance(item, prj.GravityProject)):
            return
        model = TableModel(['Key', 'Value'])
        model.set_object(item)
        dialog = InfoDialog(model, parent=self)
        dialog.exec_()
