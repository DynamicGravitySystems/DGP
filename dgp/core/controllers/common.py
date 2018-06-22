# -*- coding: utf-8 -*-
from PyQt5.QtGui import QStandardItem


class StandardProjectContainer(QStandardItem):
    def __init__(self, label: str, icon: str=None, **kwargs):
        super().__init__(label)
        self.setEditable(False)
        self._attributes = kwargs

    def properties(self):
        print(self.__class__.__name__)
