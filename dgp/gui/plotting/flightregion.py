# coding: utf-8

import PyQt5.QtWidgets as QtWidgets
import PyQt5.QtCore as QtCore
from PyQt5.QtWidgets import QMenu, QAction
from pyqtgraph.graphicsItems.LinearRegionItem import LinearRegionItem
from pyqtgraph.graphicsItems.TextItem import TextItem


class LinearFlightRegion(LinearRegionItem):
    """Custom LinearRegionItem class to provide override methods on various
    click events."""
    def __init__(self, values=(0, 1), orientation=None, brush=None,
                 movable=True, bounds=None, parent=None, label=None):
        super().__init__(values=values, orientation=orientation, brush=brush,
                         movable=movable, bounds=bounds)

        self.parent = parent
        self._grpid = None
        self._label_text = label or ''
        self.label = TextItem(text=self._label_text, color=(0, 0, 0),
                              anchor=(0, 0))
        # self.label.setPos()
        self._menu = QMenu()
        self._menu.addAction(QAction('Remove', self, triggered=self._remove))
        self._menu.addAction(QAction('Set Label', self,
                                     triggered=self._getlabel))
        self.sigRegionChanged.connect(self._move_label)

    def mouseClickEvent(self, ev):
        if not self.parent.selection_mode:
            return
        if ev.button() == QtCore.Qt.RightButton and not self.moving:
            ev.accept()
            pos = ev.screenPos().toPoint()
            pop_point = QtCore.QPoint(pos.x(), pos.y())
            self._menu.popup(pop_point)
            return True
        else:
            return super().mouseClickEvent(ev)

    def _move_label(self, lfr):
        x0, x1 = self.getRegion()

        self.label.setPos(x0, 0)

    def _remove(self):
        try:
            self.parent.remove(self)
        except AttributeError:
            return

    def _getlabel(self):
        text, result = QtWidgets.QInputDialog.getText(None,
                                                      "Enter Label",
                                                      "Line Label:",
                                                      text=self._label_text)
        if not result:
            return
        try:
            self.parent.set_label(self, str(text).strip())
        except AttributeError:
            return

    def set_label(self, text):
        self.label.setText(text)

    @property
    def group(self):
        return self._grpid

    @group.setter
    def group(self, value):
        self._grpid = value
