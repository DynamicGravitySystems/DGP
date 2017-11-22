# coding: utf-8

import os
import pathlib
import functools
import logging
from typing import Dict, Union

from pandas import Series, DataFrame
import PyQt5.QtCore as QtCore
import PyQt5.QtGui as QtGui
from PyQt5.QtWidgets import (QWidget, QMainWindow, QTabWidget, QVBoxLayout,
    QAction, QMenu, QProgressDialog, QFileDialog, QTreeView)
from PyQt5.QtCore import pyqtSignal, pyqtBoundSignal, Qt
from PyQt5.QtGui import QColor, QStandardItemModel, QStandardItem, QIcon
from PyQt5.uic import loadUiType

import dgp.lib.project as prj
from dgp.gui.loader import LoadFile
from dgp.lib.plotter import LineGrabPlot, LineUpdate
from dgp.lib.types import PlotCurve, AbstractTreeItem
from dgp.gui.utils import ConsoleHandler, LOG_FORMAT, LOG_LEVEL_MAP, get_project_file
from dgp.gui.dialogs import ImportData, AddFlight, CreateProject, InfoDialog, AdvancedImport
from dgp.gui.models import TableModel, ProjectModel
from dgp.gui.widgets import FlightTab


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

    def __init__(self, project: Union[prj.GravityProject, prj.AirborneProject]=None, *args):
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

        # Store StandardItemModels for Flight channel selection
        self._flight_channel_models = {}

        # Issue #50 Flight Tabs
        self._tabs = self.tab_workspace  # type: QTabWidget
        self._open_tabs = {}  # Track opened tabs by {uid: tab_widget, ...}

        # Initialize Project Tree Display
        self.project_tree = ProjectTreeView(parent=self, project=self.project)
        self.project_tree.setMinimumWidth(300)
        self.project_dock_grid.addWidget(self.project_tree, 0, 0, 1, 2)

        # Issue #36 Channel Selection Model
        self.std_model = None  # type: QStandardItemModel

    @property
    def current_flight(self) -> Union[prj.Flight, None]:
        if self._tabs.count() > 0:
            return self._tabs.currentWidget().flight
        return None

    @property
    def current_plot(self) -> Union[LineGrabPlot, None]:
        if self._tabs.count() > 0:
            return self._tabs.currentWidget().plot
        return None

    @property
    def current_tab(self) -> Union[FlightTab, None]:
        if self._tabs.count() > 0:
            return self._tabs.currentWidget()
        return None

    def load(self):
        self._init_slots()
        self.setWindowState(QtCore.Qt.WindowMaximized)
        self.save_project()
        self.show()
        try:
            self.progress.disconnect()
            self.status.disconnect()
        except TypeError:
            # This will happen if there are no slots connected, ignore it.
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

        # Channel Panel Buttons #
        # self.selectAllChannels.clicked.connect(self.set_channel_state)

        # Console Window Actions #
        self.combo_console_verbosity.currentIndexChanged[str].connect(
            self.set_logging_level)

    def populate_channel_tree(self, flight: prj.Flight=None):

        self.log.debug("Populating channel tree")
        if flight is None:
            flight = self.current_flight

        if flight.uid in self._flight_channel_models:
            self.tree_channels.setModel(self._flight_channel_models[flight.uid])
            self.tree_channels.expandAll()
            return
        else:
            # Generate new StdModel
            model = QStandardItemModel()
            model.itemChanged.connect(self._update_channel_tree)

            header_flags = Qt.ItemIsSelectable | Qt.ItemIsEnabled | Qt.ItemIsDropEnabled
            headers = {}  # ax_index: header
            for ax in range(len(self._open_tabs[flight.uid].plot)):
                plot_header = QStandardItem("Plot {idx}".format(idx=ax))
                plot_header.setData(ax, Qt.UserRole)
                plot_header.setFlags(header_flags)
                plot_header.setBackground(QColor("LightBlue"))
                headers[ax] = plot_header
                model.appendRow(plot_header)

            channels_header = QStandardItem("Available Channels::")
            channels_header.setBackground(QColor("Orange"))
            channels_header.setFlags(Qt.NoItemFlags)
            model.appendRow(channels_header)

            items = {}  # uid: item
            item_flags = Qt.ItemIsEnabled | Qt.ItemIsSelectable | Qt.ItemIsDragEnabled
            for uid, label in flight.channels.items():
                item = QStandardItem(label)
                item.setData(uid, role=Qt.UserRole)
                item.setFlags(item_flags)
                items[uid] = item

            state = flight.get_plot_state()  # returns: {uid: (label, axes), ...}
            for uid in state:
                label, axes = state[uid]
                headers[axes].appendRow(items[uid])

            for uid in items:
                if uid not in state:
                    model.appendRow(items[uid])

            self._flight_channel_models[flight.uid] = model
            self.tree_channels.setModel(model)
            self.tree_channels.expandAll()

    def _update_channel_tree(self, item):
        """Update the data channel selection Tree/Model"""
        self.log.debug("Updating model: {}".format(item.text()))
        parent = item.parent()
        plot = self.current_plot
        uid = item.data(Qt.UserRole)
        if parent is not None:
            # TODO: Logic here to remove from previous sub-plots (Done, I think)
            plot.remove_series(uid)
            label = item.text()
            plot_ax = parent.data(Qt.UserRole)
            self.log.debug("Item new parent: {}".format(item.parent().text()))
            self.log.debug("Adding plot on axes: {}".format(plot_ax))
            data = self.current_flight.get_channel_data(uid)
            curve = PlotCurve(uid, data, label, plot_ax)
            plot.add_series(curve, propogate=True)
        else:
            self.log.debug("Item has no parent (remove from plot)")
            plot.remove_series(uid)

    def set_logging_level(self, name: str):
        """Slot: Changes logging level to passed string logging level name."""
        self.log.debug("Changing logging level to: {}".format(name))
        level = LOG_LEVEL_MAP[name.lower()]
        self.log.setLevel(level)

    def write_console(self, text, level):
        """PyQt Slot: Logs a message to the GUI console"""
        log_color = {'DEBUG': QColor('DarkBlue'), 'INFO': QColor('Green'),
                     'WARNING': QColor('Red'), 'ERROR': QColor('Pink'),
                     'CRITICAL': QColor('Orange')}.get(level.upper(),
                                                       QColor('Black'))

        self.text_console.setTextColor(log_color)
        self.text_console.append(str(text))
        self.text_console.verticalScrollBar().setValue(
            self.text_console.verticalScrollBar().maximum())

    def _launch_tab(self, index: QtCore.QModelIndex=None, flight=None):
        """
        TODO: This function will be responsible for launching a new flight tab.
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
        self._open_tabs[flight.uid] = new_tab
        t_idx = self._tabs.addTab(new_tab, flight.name)
        self._tabs.setCurrentIndex(t_idx)

    def _tab_closed(self, index: int):
        # TODO: This will handle close requests for a tab
        self.log.warning("Tab close requested for tab: {}".format(index))

    def _tab_changed(self, index: int):
        self.log.info("Tab changed to index: {}".format(index))
        flight = self._tabs.widget(index).flight
        self.populate_channel_tree(flight)

    def update_plot(self, flight: prj.Flight) -> None:
        """

        Parameters
        ----------
        flight : prj.Flight
            Flight object with related Gravity and GPS properties to plot

        Returns
        -------
        None
        """
        if flight.uid not in self._open_tabs:
            # If flight is not opened, don't need to update plot
            return
        else:
            self.current_tab.update_plot()
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
        self.log.info("Importing <{dtype}> from: Path({path}) into"
                      " <Flight({name})>".format(dtype=dtype, path=str(path),
                                                 name=flight.name))
        if path is None:
            return False
        loader = LoadFile(path, dtype, flight.uid, fields=fields, parent=self)

        # Curry functions to execute on thread completion.
        add_data = functools.partial(self.project.add_data, flight_uid=flight.uid)
        update_plot = functools.partial(self.update_plot, flight)
        prog = self.progress_dialog("Loading", 0, 0)

        loader.data.connect(add_data)
        loader.progress.connect(prog.setValue)
        # loader.loaded.connect(tree_refresh)
        loader.loaded.connect(update_plot)
        loader.loaded.connect(self.save_project)
        loader.loaded.connect(prog.close)
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
            # Delete flight model to force update
            try:
                del self._flight_channel_models[flight.uid]
            except KeyError:
                pass
            self.import_data(path, dtype, flight, fields=fields)
            return

        return
        # Old dialog:
        dialog = ImportData(self.project, self.current_flight)
        if dialog.exec_():
            path, dtype, flt_id = dialog.content
            flight = self.project.get_flight(flt_id)
            # plot, _ = self.flight_plots[flt_id]
            # plot.plotted = False
            self.log.info("Importing {} file from {} into flight: {}".format(dtype, path, flight.uid))
            self.import_data(path, dtype, flight)

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
            self.log.info("Adding flight:")
            flight = dialog.flight
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
        print("Project model inited")

    def _init_model(self):
        """Initialize a new-style ProjectModel from models.py"""
        model = ProjectModel(self._project, parent=self)
        # model.rowsAboutToBeInserted.connect(self.begin_insert)
        # model.rowsInserted.connect(self.end_insert)
        self.setModel(model)
        self.expandAll()

    def toggle_expand(self, index):
        self.setExpanded(index, (not self.isExpanded(index)))

    def begin_insert(self, index, start, end):
        print("Inserting rows: {}, {}".format(start, end))

    def end_insert(self, index, start, end):
        print("Finixhed inserting rows, running update")
        # index is parent index
        model = self.model()
        uindex = model.index(row=start, parent=index)
        self.update(uindex)
        self.expandAll()

    def contextMenuEvent(self, event: QtGui.QContextMenuEvent, *args, **kwargs):
        # get the index of the item under the click event
        context_ind = self.indexAt(event.pos())
        context_focus = self.model().itemFromIndex(context_ind)
        print(context_focus.uid)

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
        print("Opening new plot for item")
        pass

    def _info_action(self, item):
        data = item.data(QtCore.Qt.UserRole)
        if not (isinstance(item, prj.Flight)
                or isinstance(item, prj.GravityProject)):
            return
        model = TableModel(['Key', 'Value'])
        model.set_object(item)
        dialog = InfoDialog(model, parent=self)
        dialog.exec_()
        print(dialog.updates)
