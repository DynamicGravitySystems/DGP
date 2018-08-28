# -*- coding: utf-8 -*-
import json
import weakref

from PyQt5.QtCore import pyqtSignal
from PyQt5.QtGui import QCloseEvent
from PyQt5.QtWidgets import QWidget

from dgp.core import OID
from dgp.gui import settings

__all__ = ['WorkspaceTab', 'SubTab']


class WorkspaceTab(QWidget):
    def __init__(self, controller: AbstractController, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setAttribute(Qt.WA_DeleteOnClose, True)
        controller.register_observer(self, self.close, StateAction.DELETE)
        controller.register_observer(self, self._slot_update, StateAction.UPDATE)
        self._controller = weakref.ref(controller)

    @property
    def uid(self) -> OID:
        raise NotImplementedError
    @property
    def controller(self) -> AbstractController:
        return self._controller()

    @property
    def title(self) -> str:
        raise NotImplementedError

    @property
    def state_key(self) -> str:
        return f'Workspace/{self.uid!s}'

    def get_state(self) -> dict:
        key = f'Workspace/{self.uid!s}'
        return json.loads(settings().value(key, '{}'))

    def save_state(self, state=None) -> None:
        """Save/dump the current state of the WorkspaceTab

        This method is called when the tab is closed, and should be used to
        retrieve and store the state of the WorkspaceTab and its sub-tabs or
        other components.

        Override this method to provide state handling for a WorkspaceTab
        """
        _jsons = json.dumps(state)
        settings().setValue(self.state_key, _jsons)

    def closeEvent(self, event: QCloseEvent):
        self.save_state()
        event.accept()


class SubTab(QWidget):
    sigLoaded = pyqtSignal(object)

    def get_state(self):
        """Get a representation of the current state of the SubTab

        This method should be overridden by sub-classes of SubTab, in order to
        provide a tab/context specific state representation.

        The returned dictionary and all of its values (including nested dicts)
        must be serializable by the default Python json serializer.

        The state dictionary returned by this method will be supplied to the
        restore_state method when the tab is loaded.

        Returns
        -------
        dict
            dict of JSON serializable key: value pairs

        """
        return {}

    def restore_state(self, state: dict) -> None:
        """Restore the tab to reflect the saved state supplied to this method

        Parameters
        ----------
        state : dict
            Dictionary containing the state representation for this object. As
            produced by :meth:`get_state`

        """
        pass
