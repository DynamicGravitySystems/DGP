# -*- coding: utf-8 -*-
import pandas as pd
from PyQt5 import QtWidgets
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QAction, QSizePolicy

from dgp.core import StateAction, Icon
from dgp.core.controllers.dataset_controller import DataSetController
from dgp.gui.plotting.helpers import LineUpdate
from dgp.gui.plotting.plotters import LineSelectPlot, TransformPlot
from dgp.gui.widgets.channel_control_widgets import ChannelController
from dgp.gui.widgets.data_transform_widget import TransformWidget
from dgp.gui.utils import ThreadedFunction
from .base import WorkspaceTab, SubTab


class SegmentSelectTab(SubTab):
    """Sub-tab displayed within the DataSetTab Workspace"""
    def __init__(self, dataset: DataSetController, parent=None):
        super().__init__(parent=parent, flags=Qt.Widget)
        self.dataset: DataSetController = dataset
        self._state = {}

        self._plot = LineSelectPlot(rows=2)
        self._plot.sigSegmentChanged.connect(self._on_modified_segment)

        for segment in self.dataset.segments:
            group = self._plot.add_segment(segment.get_attr('start'),
                                           segment.get_attr('stop'),
                                           segment.get_attr('label'),
                                           segment.uid, emit=False)
            segment.add_reference(group)

        # Create/configure the tab layout/widgets/controls
        qhbl_main_layout = QtWidgets.QHBoxLayout(self)
        qvbl_plot_layout = QtWidgets.QVBoxLayout()
        qhbl_main_layout.addLayout(qvbl_plot_layout)
        self.toolbar = self._plot.get_toolbar(self)
        qvbl_plot_layout.addWidget(self.toolbar, alignment=Qt.AlignLeft)
        qvbl_plot_layout.addWidget(self._plot)

        self.controller = ChannelController(self._plot, parent=self)
        qhbl_main_layout.addWidget(self.controller)

        # Toggle control to hide/show data channels dock
        qa_channel_toggle = QAction(Icon.PLOT_LINE.icon(), "Data Channels", self)
        qa_channel_toggle.setCheckable(True)
        qa_channel_toggle.setChecked(True)
        qa_channel_toggle.toggled.connect(self.controller.setVisible)
        self.toolbar.addAction(qa_channel_toggle)

        # Load data channel selection widget
        th = ThreadedFunction(self.dataset.dataframe, parent=self)
        th.result.connect(self._dataframe_loaded)
        th.start()

    def _dataframe_loaded(self, df):
        data_cols = ('gravity', 'long_accel', 'cross_accel', 'beam', 'temp',
                     'pressure', 'Etemp', 'gps_week', 'gps_sow', 'lat', 'long',
                     'ell_ht')
        cols = [df[col] for col in df if col in data_cols]
        stat_cols = [df[col] for col in df if col not in data_cols]
        self.controller.set_series(*cols)
        self.controller.set_binary_series(*stat_cols)
        self.sigLoaded.emit(self)

    def get_state(self):
        """Get the current state of the dataset workspace

        The 'state' of the workspace refers to things which we would like the
        ability to restore based on user preferences when they next load the tab

        This may include which channels are plotted, and on which plot/axis.
        This may also include the plot configuration, e.g. how many rows/columns
        and perhaps visibility settings (grid alpha, line alpha, axis display)

        Returns
        -------
        dict
            Dictionary of state key/values, possibly nested

        """
        return self.controller.get_state()

    def restore_state(self, state):
        self.controller.restore_state(state)

    def _on_modified_segment(self, update: LineUpdate):
        if update.action is StateAction.DELETE:
            self.dataset.remove_segment(update.uid)
            return

        start: pd.Timestamp = update.start
        stop: pd.Timestamp = update.stop
        assert isinstance(start, pd.Timestamp)
        assert isinstance(stop, pd.Timestamp)

        if update.action is StateAction.UPDATE:
            self.dataset.update_segment(update.uid, start, stop, update.label)
        else:
            seg = self.dataset.add_segment(update.uid, start, stop, update.label)
            seg.add_reference(self._plot.get_segment(seg.uid))


class DataTransformTab(SubTab):
    def __init__(self, dataset: DataSetController, parent=None):
        super().__init__(parent=parent, flags=Qt.Widget)
        layout = QtWidgets.QHBoxLayout(self)
        plotter = TransformPlot(rows=1)
        plotter.setSizePolicy(QSizePolicy(QSizePolicy.MinimumExpanding, QSizePolicy.MinimumExpanding))
        plot_layout = QtWidgets.QVBoxLayout()
        plot_layout.addWidget(plotter.get_toolbar(self), alignment=Qt.AlignRight)
        plot_layout.addWidget(plotter)

        transform_control = TransformWidget(dataset, plotter)

        layout.addWidget(transform_control, stretch=0, alignment=Qt.AlignLeft)
        layout.addLayout(plot_layout, stretch=5)

        self.sigLoaded.emit(self)

    def get_state(self):
        pass

    def restore_state(self, state):
        pass


class DataSetTab(WorkspaceTab):
    """Root workspace tab for DataSet controller manipulation"""

    def __init__(self, dataset: DataSetController, parent=None):
        super().__init__(controller=dataset, parent=parent, flags=Qt.Widget)
        self.ws_settings: dict = self.get_state()

        layout = QtWidgets.QVBoxLayout(self)
        self.workspace = QtWidgets.QTabWidget(self)
        self.workspace.setTabPosition(QtWidgets.QTabWidget.West)
        layout.addWidget(self.workspace)

        self.segment_tab = SegmentSelectTab(dataset, parent=self)
        self.segment_tab.sigLoaded.connect(self._tab_loaded)
        self.transform_tab = DataTransformTab(dataset, parent=self)
        self.transform_tab.sigLoaded.connect(self._tab_loaded)

        self.workspace.addTab(self.segment_tab, "Data")
        self.workspace.addTab(self.transform_tab, "Transform")
        self.workspace.setCurrentIndex(0)

    @property
    def title(self):
        return f'{self.controller.get_attr("name")} ' \
               f'[{self.controller.parent().get_attr("name")}]'

    def _tab_loaded(self, tab: SubTab):
        """Restore tab state after initial loading is complete"""
        state = self.ws_settings.get(tab.__class__.__name__, {})
        tab.restore_state(state)

    def save_state(self, state=None):
        """Save current sub-tabs state then accept close event."""
        state = {}
        for i in range(self.workspace.count()):
            tab: SubTab = self.workspace.widget(i)
            state[tab.__class__.__name__] = tab.get_state()

        super().save_state(state=state)
