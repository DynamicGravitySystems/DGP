# -*- coding: utf-8 -*-

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QVBoxLayout, QWidget, QComboBox

import pandas as pd
import numpy as np

from dgp.lib.types import DataSource
from dgp.lib.transform.transform_graphs import SyncGravity, AirbornePost, TransformGraph
from dgp.gui.plotting.plotters import TransformPlot
from . import BaseTab, Flight
from ..ui.transform_tab_widget import Ui_TransformInterface


class TransformWidget(QWidget, Ui_TransformInterface):
    def __init__(self, flight: Flight):
        super().__init__()
        self.setupUi(self)

        self._flight = flight
        self._plot = TransformPlot()
        self.hlayout.addWidget(self._plot.widget, Qt.AlignLeft | Qt.AlignTop)

        self.cb_line_select.addItem('All')
        self.cb_line_select.addItems([str(line.start) for line in flight.lines])
        self.transform.addItems(['Airborne Post'])

        self._trajectory = self._flight.trajectory
        self._gravity = self._flight.gravity

        self.bt_execute_transform.clicked.connect(self.execute_transform)

    @property
    def transform(self) -> QComboBox:
        return self.cb_transform_select

    @property
    def plot(self):
        return self._plot

    def execute_transform(self):
        if self._trajectory is None or self._gravity is None:
            print("Missing trajectory or gravity")
            return

        print("Executing transform")
        c_transform = self.transform.currentText().lower()
        if c_transform == 'sync gravity':
            print("Running sync grav transform")
        elif c_transform == 'airborne post':
            print("Running airborne post transform")
            graph = AirbornePost(self._trajectory, self._gravity, 0, 0)
            print("Executing graph")
            results = graph.execute()
            print(results.keys())

            time = pd.Series(self._trajectory.index.astype(np.int64) / 10 ** 9, index=self._trajectory.index,
                             name='unix_time')
            output_frame = pd.concat([time, self._trajectory[['lat', 'long', 'ell_ht']],
                                      results['aligned_eotvos'],
                                      results['aligned_kin_accel'], results['lat_corr'],
                                      results['fac'], results['total_corr'],
                                      results['abs_grav'], results['corrected_grav']],
                                     axis=1)
            output_frame.columns = ['unix_time', 'lat', 'lon', 'ell_ht', 'eotvos',
                                    'kin_accel', 'lat_corr', 'fac', 'total_corr',
                                    'vert_accel', 'gravity']

            print(output_frame.describe())
            # self.plot.add_series(output_frame['eotvos'])
            # self.plot.add_series(output_frame['gravity'])
            # self.plot.add_series(output_frame['fac'])
            self.plot.add_series(output_frame['vert_accel'])
            # self.plot.add_series(output_frame['total_corr'])


class TransformTab(BaseTab):
    """Sub-tab displayed within Flight tab interface. Displays interface for selecting
    Transform chains and plots for displaying the resultant data sets.
    """
    _name = "Transform"

    def __init__(self, label: str, flight: Flight):
        super().__init__(label, flight)

        self._layout = QVBoxLayout()
        self._layout.addWidget(TransformWidget(flight))
        self.setLayout(self._layout)

    def data_modified(self, action: str, dsrc: DataSource):
        """Slot: Called when a DataSource has been added/removed from the
        Flight this tab/workspace is associated with."""
        if action.lower() == 'add':
            return
        elif action.lower() == 'remove':
            return
