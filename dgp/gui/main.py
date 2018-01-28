# coding: utf-8

import os
import pathlib
import logging
from typing import Union

import PyQt5.QtCore as QtCore
import PyQt5.QtWidgets as QtWidgets
from PyQt5.QtGui import QColor
from PyQt5.QtCore import pyqtSignal, pyqtBoundSignal
from PyQt5.QtWidgets import QMainWindow, QProgressDialog, QFileDialog


import dgp.lib.project as prj
import dgp.lib.types as types
import dgp.lib.enums as enums
import dgp.gui.loader as loader
import dgp.lib.datamanager as dm
from dgp.gui.utils import (ConsoleHandler, LOG_FORMAT, LOG_LEVEL_MAP,
                           LOG_COLOR_MAP, get_project_file)
from dgp.gui.dialogs import (AddFlightDialog, CreateProjectDialog,
                             AdvancedImportDialog)
from dgp.gui.workspace import FlightTab
from dgp.gui.ui.main_window import Ui_MainWindow


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


class MainWindow(QMainWindow, Ui_MainWindow):
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
        sb_handler = ConsoleHandler(self.show_status)
        sb_handler.setFormatter(logging.Formatter("%(message)s"))
        self.log.addHandler(console_handler)
        self.log.addHandler(sb_handler)
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
                image: url(:/icons/chevron-right);
            }
            QTreeView::branch:open:has-children {
                background: none;
                image: url(:/icons/chevron-down);
            }
        """)

        # Initialize Variables
        self.import_base_path = pathlib.Path('~').expanduser().joinpath(
            'Desktop')
        self._default_status_timeout = 5000  # Status Msg timeout in milli-sec

        # Issue #50 Flight Tabs
        self._flight_tabs = self.flight_tabs  # type: QtWidgets.QTabWidget
        # self._flight_tabs = CustomTabWidget()
        self._open_tabs = {}  # Track opened tabs by {uid: tab_widget, ...}

        # Initialize Project Tree Display
        self.project_tree.set_project(self.project)

    @property
    def current_flight(self) -> Union[prj.Flight, None]:
        """Returns the active flight based on which Flight Tab is in focus."""
        if self._flight_tabs.count() > 0:
            return self._flight_tabs.currentWidget().flight
        return None

    @property
    def current_tab(self) -> Union[FlightTab, None]:
        """Get the active FlightTab (returns None if no Tabs are open)"""
        if self._flight_tabs.count() > 0:
            return self._flight_tabs.currentWidget()
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
        # self.action_import_data.triggered.connect(self.import_data_dialog)
        self.action_import_gps.triggered.connect(
            lambda: self.import_data_dialog(enums.DataTypes.TRAJECTORY))
        self.action_import_grav.triggered.connect(
            lambda: self.import_data_dialog(enums.DataTypes.GRAVITY))
        self.action_add_flight.triggered.connect(self.add_flight_dialog)

        # Project Tree View Actions #
        self.project_tree.doubleClicked.connect(self._launch_tab)
        self.project_tree.item_removed.connect(self._project_item_removed)

        # Project Control Buttons #
        self.prj_add_flight.clicked.connect(self.add_flight_dialog)
        # self.prj_import_data.clicked.connect(self.import_data_dialog)
        self.prj_import_gps.clicked.connect(
            lambda: self.import_data_dialog(enums.DataTypes.TRAJECTORY))
        self.prj_import_grav.clicked.connect(
            lambda: self.import_data_dialog(enums.DataTypes.GRAVITY))

        # Tab Browser Actions #
        self._flight_tabs.currentChanged.connect(self._flight_tab_changed)
        self._flight_tabs.tabCloseRequested.connect(self._tab_closed)

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
                self._flight_tabs.setCurrentWidget(self._open_tabs[flight.uid])
                self.project_tree.toggle_expand(index)
                return

        self.log.info("Launching tab for flight: UID<{}>".format(flight.uid))
        new_tab = FlightTab(flight)
        new_tab.contextChanged.connect(self._update_context_tree)
        self._open_tabs[flight.uid] = new_tab
        t_idx = self._flight_tabs.addTab(new_tab, flight.name)
        self._flight_tabs.setCurrentIndex(t_idx)

    def _tab_closed(self, index: int):
        # TODO: Should we delete the tab, or pop it off the stack to a cache?
        self.log.warning("Tab close requested for tab: {}".format(index))
        flight_id = self._flight_tabs.widget(index).flight.uid
        self._flight_tabs.removeTab(index)
        tab = self._open_tabs.pop(flight_id)

    def _flight_tab_changed(self, index: int):
        self.log.info("Flight Tab changed to index: {}".format(index))
        if index == -1:  # If no tabs are displayed
            # self._context_tree.setModel(None)
            return
        tab = self._flight_tabs.widget(index)  # type: FlightTab
        if tab.subtab_widget():
            print("Active flight subtab has a widget")
        # self._context_tree.setModel(tab.context_model)
        # self._context_tree.expandAll()

    def _update_context_tree(self, model):
        self.log.debug("Tab subcontext changed. Changing Tree Model")
        # self._context_tree.setModel(model)
        # self._context_tree.expandAll()

    def _project_item_removed(self, item: types.BaseTreeItem):
        print("Got item: ", type(item), " in _prj_item_removed")
        if isinstance(item, types.DataSource):
            flt = item.flight
            print("Dsource flt: ", flt)
            # Error here, flt.uid is not in open_tabs when it should be.
            if not flt.uid not in self._open_tabs:
                print("Flt not in open tabs")
                return
            tab = self._open_tabs.get(flt.uid, None)  # type: FlightTab
            if tab is None:
                print("tab not open")
                return
            try:
                print("Calling tab.data_deleted")
                tab.data_deleted(item)
            except:
                print("Exception of some sort encountered deleting item")
            else:
                print("Data deletion sucessful?")

        else:
            return

    def show_progress_dialog(self, title, start=0, stop=1, label=None,
                             cancel="Cancel", modal=False,
                             flags=None) -> QProgressDialog:
        """Generate a progress bar to show progress on long running event."""
        if flags is None:
            flags = (QtCore.Qt.WindowSystemMenuHint |
                     QtCore.Qt.WindowTitleHint |
                     QtCore.Qt.WindowMinimizeButtonHint)

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
        progress.setAttribute(QtCore.Qt.WA_DeleteOnClose)
        progress.setToolTip(label)
        sb.addWidget(progress)
        return progress

    @autosave
    def add_data(self, data, dtype, flight, path):
        uid = dm.get_manager().save_data(dm.HDF5, data)
        if uid is None:
            self.log.error("Error occured writing DataFrame to HDF5 store.")
            return

        cols = list(data.keys())
        ds = types.DataSource(uid, path, cols, dtype, x0=data.index.min(),
                              x1=data.index.max())
        flight.register_data(ds)
        if flight.uid not in self._open_tabs:
            # If flight is not opened we don't need to update the plot
            return
        else:
            tab = self._open_tabs[flight.uid]  # type: FlightTab
            tab.new_data(ds)  # tell the tab that new data is available
            return

    def load_file(self, dtype, flight, **params):
        """Loads a file in the background by using a QThread
        Calls :py:class: dgp.ui.loader.LoaderThread to create threaded file
        loader.

        Parameters
        ----------
        dtype : enums.DataTypes

        flight : prj.Flight

        params : dict


        """
        self.log.debug("Loading {dtype} into {flt}, with params: {param}"
                       .format(dtype=dtype.name, flt=flight, param=params))

        prog = self.show_progress_status(0, 0)
        prog.setValue(1)

        def _complete(data):
            self.add_data(data, dtype, flight, params.get('path', None))

        def _result(result):
            err, exc = result
            prog.close()
            if err:
                msg = "Error loading {typ}::{fname}".format(
                    typ=dtype.name.capitalize(), fname=params.get('path', ''))
                self.log.error(msg)
            else:
                msg = "Loaded {typ}::{fname}".format(
                    typ=dtype.name.capitalize(), fname=params.get('path', ''))
                self.log.info(msg)

        ld = loader.get_loader(parent=self, dtype=dtype, on_complete=_complete,
                               on_error=_result, **params)
        ld.start()

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

    # Project dialog functions ################################################

    def import_data_dialog(self, dtype=None) -> None:
        """
        Launch a dialog window for user to specify path and parameters to
        load a file of dtype.
        Params gathered by dialog will be passed to :py:meth: self.load_file
        which constrcuts the loading thread and performs the import.

        Parameters
        ----------
        dtype : enums.DataTypes
            Data type for which to launch dialog: GRAVITY or TRAJECTORY

        """
        dialog = AdvancedImportDialog(self.project, self.current_flight,
                                      dtype=dtype, parent=self)
        dialog.browse()
        if dialog.exec_():
            # TODO: Should path be contained within params or should we take
            # it as its own parameter
            self.load_file(dtype, dialog.flight, **dialog.params)

    def new_project_dialog(self) -> QMainWindow:
        new_window = True
        dialog = CreateProjectDialog()
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
        dialog = AddFlightDialog(self.project)
        if dialog.exec_():
            flight = dialog.flight
            self.log.info("Adding flight {}".format(flight.name))
            self.project.add_flight(flight)

            # if dialog.gravity:
            #     self.import_data(dialog.gravity, 'gravity', flight)
            # if dialog.gps:
            #     self.import_data(dialog.gps, 'gps', flight)
            self._launch_tab(flight=flight)
            return
        self.log.info("New flight creation aborted.")
        return
