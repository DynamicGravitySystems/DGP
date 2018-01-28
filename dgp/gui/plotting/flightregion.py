# coding: utf-8

import PyQt5.QtCore as QtCore
from PyQt5.QtWidgets import QMenu, QAction
from pyqtgraph.graphicsItems.LinearRegionItem import LinearRegionItem


class LinearFlightRegion(LinearRegionItem):
    """Custom LinearRegionItem class to provide override methods on various
    click events."""
    def __init__(self, values=(0, 1),
                 orientation=LinearRegionItem.Vertical, brush=None,
                 movable=True, bounds=None, parent=None):
        super().__init__(values=values, orientation=orientation, brush=brush,
                         movable=movable, bounds=bounds)

        self.parent = parent
        self._menu = QMenu()
        self._menu.addAction(QAction('Remove', self, triggered=self._remove))

    def mouseClickEvent(self, ev):
        if ev.button() == QtCore.Qt.RightButton and not self.moving:
            ev.accept()
            pos = ev.screenPos().toPoint()
            pop_point = QtCore.QPoint(pos.x(), pos.y())
            self._menu.popup(pop_point)
            return True
        else:
            return super().mouseClickEvent(ev)

    def _remove(self):
        try:
            self.parent.remove(self)
        except AttributeError:
            return


