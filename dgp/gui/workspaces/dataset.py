# -*- coding: utf-8 -*-
import pandas as pd
from PyQt5 import QtWidgets
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QWidget, QAction, QSizePolicy

from dgp.core import StateAction, Icon
from dgp.core.controllers.dataset_controller import DataSetController
from dgp.gui.plotting.helpers import LineUpdate
from dgp.gui.plotting.plotters import LineSelectPlot, TransformPlot
from dgp.gui.widgets.channel_control_widgets import ChannelController
from dgp.gui.widgets.data_transform_widget import TransformWidget
from dgp.gui.widgets.workspace_widget import WorkspaceTab


class SegmentSelectTab(QWidget):

    def __init__(self, dataset: DataSetController, parent=None):
        super().__init__(parent=parent, flags=Qt.Widget)

        self.dataset: DataSetController = dataset

        self._plot = LineSelectPlot(rows=2)
        self._plot.sigSegmentChanged.connect(self._on_modified_segment)

        for segment in self.dataset.segments:
            group = self._plot.add_segment(segment.get_attr('start'),
                                           segment.get_attr('stop'),
                                           segment.get_attr('label'),
                                           segment.uid, emit=False)
            segment.add_reference(group)

        # Create/configure the tab layout/widgets/controls
        qhbl_main_layout = QtWidgets.QHBoxLayout()
        qvbl_plot_layout = QtWidgets.QVBoxLayout()
        qhbl_main_layout.addItem(qvbl_plot_layout)
        self.toolbar = self._plot.get_toolbar(self)
        # self.toolbar.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)
        qvbl_plot_layout.addWidget(self.toolbar, alignment=Qt.AlignLeft)
        qvbl_plot_layout.addWidget(self._plot)

        # Toggle control to hide/show data channels dock
        qa_channel_toggle = QAction(Icon.PLOT_LINE.icon(), "Data Channels", self)
        qa_channel_toggle.setCheckable(True)
        qa_channel_toggle.setChecked(True)
        self.toolbar.addAction(qa_channel_toggle)

        # Load data channel selection widget
        df = self.dataset.dataframe()
        data_cols = ('gravity', 'long_accel', 'cross_accel', 'beam', 'temp',
                     'pressure', 'Etemp', 'gps_week', 'gps_sow', 'lat', 'long',
                     'ell_ht')
        cols = [df[col] for col in df if col in data_cols]
        stat_cols = [df[col] for col in df if col not in data_cols]
        controller = ChannelController(self._plot, *cols,
                                       binary_series=stat_cols, parent=self)

        qa_channel_toggle.toggled.connect(controller.setVisible)
        qhbl_main_layout.addWidget(controller)
        self.setLayout(qhbl_main_layout)

    def get_state(self):
        # TODO
        pass

    def load_state(self, state):
        # TODO
        pass

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


class DataTransformTab(QWidget):
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


class DataSetTab(WorkspaceTab):
    """Root workspace tab for DataSet controller manipulation"""
    def __init__(self, dataset: DataSetController, parent=None):
        super().__init__(parent=parent, flags=Qt.Widget)
        self.dataset = dataset

        layout = QtWidgets.QVBoxLayout(self)
        self.workspace = QtWidgets.QTabWidget(self)
        self.workspace.setTabPosition(QtWidgets.QTabWidget.West)

        segment_tab = SegmentSelectTab(dataset, parent=self)
        transform_tab = DataTransformTab(dataset, parent=self)

        self.workspace.addTab(segment_tab, "Data")
        self.workspace.addTab(transform_tab, "Transform")
        self.workspace.setCurrentIndex(0)
        layout.addWidget(self.workspace)

    @property
    def uid(self):
        return self.dataset.uid
