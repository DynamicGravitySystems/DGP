# coding: utf-8

from PyQt5.QtWidgets import QGridLayout

from ..plotting.plotters import TransformPlot
from . import BaseTab


class LineProcessTab(BaseTab):
    """Thoughts: This tab can be created and opened when data is connected to
    the Transform tab output node. Or simply when a button is clicked in the
    Transform tab interface."""
    _name = "Line Processing"

    def __init__(self, label, flight):
        super().__init__(label, flight)
        self.setLayout(QGridLayout())
        plot_widget = TransformPlot(rows=2, cols=4, sharex=True,
                                    sharey=True, grid=True)
        self.layout().addWidget(plot_widget.widget, 0, 0)
