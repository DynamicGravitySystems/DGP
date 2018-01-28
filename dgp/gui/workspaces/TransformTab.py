# coding: utf-8

from PyQt5.Qt import Qt
from PyQt5.QtWidgets import QGridLayout
from pyqtgraph.flowchart import Flowchart

from dgp.lib.transform import LIBRARY
from dgp.lib.types import DataSource
from dgp.gui.plotting.plotters import TransformPlot
from . import BaseTab, Flight, DataTypes


class TransformTab(BaseTab):
    _name = "Transform"

    def __init__(self, label: str, flight: Flight):
        super().__init__(label, flight)
        self._layout = QGridLayout()
        self.setLayout(self._layout)

        self.fc = None
        self.plots = []
        self._nodes = {}
        self._init_flowchart()
        self.demo_graph()

    def _init_flowchart(self):
        fc_terminals = {"Gravity": dict(io='in'),
                        "Trajectory": dict(io='in'),
                        "Output": dict(io='out')}
        fc = Flowchart(library=LIBRARY, terminals=fc_terminals)
        fc.outputNode.graphicsItem().setPos(650, 0)
        fc_ctrl_widget = fc.widget()
        chart_window = fc_ctrl_widget.cwWin
        # Force the Flowchart pop-out window to close when the main app exits
        chart_window.setAttribute(Qt.WA_QuitOnClose, False)

        fc_layout = fc_ctrl_widget.ui.gridLayout
        fc_layout.removeWidget(fc_ctrl_widget.ui.reloadBtn)
        fc_ctrl_widget.ui.reloadBtn.setEnabled(False)
        fc_ctrl_widget.ui.reloadBtn.hide()

        self._layout.addWidget(fc_ctrl_widget, 0, 0, 2, 1)

        plot_mgr = TransformPlot(rows=2)
        self._layout.addWidget(plot_mgr.widget, 0, 1)
        plot_node = fc.createNode('PGPlotNode', pos=(650, -150))
        plot_node.setPlot(plot_mgr.plots[0])

        plot_node2 = fc.createNode('PGPlotNode', pos=(650, 150))
        plot_node2.setPlot(plot_mgr.plots[1])

        self.plots.append(plot_node)
        self.plots.append(plot_node2)

        self.fc = fc
        grav = self.flight.get_source(DataTypes.GRAVITY)
        gps = self.flight.get_source(DataTypes.TRAJECTORY)
        if grav is not None:
            fc.setInput(Gravity=grav.load())

        if gps is not None:
            fc.setInput(Trajectory=gps.load())

    def populate_flowchart(self):
        """Populate the flowchart/Transform interface with a default
        'example'/base network of Nodes dependent on available data."""
        if self.fc is None:
            return
        else:
            fc = self.fc
        grav = self.flight.get_source(DataTypes.GRAVITY)
        gps = self.flight.get_source(DataTypes.TRAJECTORY)
        if grav is not None:
            fc.setInput(Gravity=grav.load())
            # self.line_chart.setInput(Gravity1=grav.load())
            filt_node = fc.createNode('FIRLowpassFilter', pos=(150, 150))
            fc.connectTerminals(fc['Gravity'], filt_node['data_in'])
            fc.connectTerminals(filt_node['data_out'], self.plots[0]['In'])

        if gps is not None:
            fc.setInput(Trajectory=gps.load())
            # self.line_chart.setInput(Trajectory1=gps.load())
            eotvos = fc.createNode('Eotvos', pos=(0, 0))
            fc.connectTerminals(fc['Trajectory'], eotvos['data_in'])
            fc.connectTerminals(eotvos['data_out'], self.plots[0]['In'])

    def demo_graph(self):
        eotvos = self.fc.createNode('Eotvos', pos=(0, 0))
        comp_delay = self.fc.createNode('ComputeDelay', pos=(150, 0))
        comp_delay.bypass(True)
        shift = self.fc.createNode('ShiftFrame', pos=(300, -125))
        add_ser = self.fc.createNode('AddSeries', pos=(300, 125))
        fir_0 = self.fc.createNode('FIRLowpassFilter', pos=(0, -150))
        fir_1 = self.fc.createNode('FIRLowpassFilter', pos=(300, 0))
        free_air = self.fc.createNode('FreeAirCorrection', pos=(0, 200))
        lat_corr = self.fc.createNode('LatitudeCorrection', pos=(150, 200))

        # Gravity Connections
        self.fc.connectTerminals(self.fc['Gravity'], shift['frame'])
        self.fc.connectTerminals(self.fc['Gravity'], fir_0['data_in'])
        self.fc.connectTerminals(fir_0['data_out'], comp_delay['s1'])
        self.fc.connectTerminals(fir_0['data_out'], self.plots[0]['In'])

        # Trajectory Connections
        self.fc.connectTerminals(self.fc['Trajectory'], eotvos['data_in'])
        self.fc.connectTerminals(self.fc['Trajectory'], free_air['data_in'])
        self.fc.connectTerminals(self.fc['Trajectory'], lat_corr['data_in'])
        self.fc.connectTerminals(eotvos['data_out'], comp_delay['s2'])
        self.fc.connectTerminals(eotvos['data_out'], add_ser['A'])
        self.fc.connectTerminals(comp_delay['data_out'], shift['delay'])
        self.fc.connectTerminals(shift['data_out'], fir_1['data_in'])

        self.fc.connectTerminals(fir_1['data_out'], add_ser['B'])
        self.fc.connectTerminals(add_ser['data_out'], self.plots[1]['In'])

    def data_modified(self, action: str, dsrc: DataSource):
        """Slot: Called when a DataSource has been added/removed from the
        Flight this tab/workspace is associated with."""
        if action.lower() == 'add':
            if dsrc.dtype == DataTypes.TRAJECTORY:
                self.fc.setInput(Trajectory=dsrc.load())
            elif dsrc.dtype == DataTypes.GRAVITY:
                self.fc.setInput(Gravity=dsrc.load())
