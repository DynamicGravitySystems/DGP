# -*- coding: utf-8 -*-
import logging

from PyQt5.QtWidgets import QWidget

from dgp.core.oid import OID
from dgp.core.controllers.controller_interfaces import IBaseController


class TaskTab(QWidget):
    """Base Workspace Tab Widget - Subclass to specialize function
    Provides interface to root tab object e.g. Flight, DataSet and a property
    to access the UID associated with this tab (via the root object)

    Parameters
    ----------
    label : str
    root : :class:`IBaseController`
        Root project object encapsulated by this tab
    parent : QWidget, Optional
        Parent widget
    kwargs
        Key-word arguments passed to QWidget constructor

    """
    def __init__(self, label: str, root: IBaseController, parent=None, **kwargs):
        super().__init__(parent, **kwargs)
        self.log = logging.getLogger(__name__)
        self.label = label
        self._root = root

    @property
    def uid(self) -> OID:
        return self._root.uid

    @property
    def root(self) -> IBaseController:
        """Return the root data object/controller associated with this tab."""
        return self._root
