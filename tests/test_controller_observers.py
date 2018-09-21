# -*- coding: utf-8 -*-
import weakref

import pytest

from dgp.core import StateAction
from dgp.core.models.flight import Flight
from dgp.core.controllers.controller_interfaces import VirtualBaseController


@pytest.fixture
def mock_model():
    return Flight("TestFlt")


class Observer:
    def __init__(self, control: VirtualBaseController):
        control.register_observer(self, self.on_update, StateAction.UPDATE)
        control.register_observer(self, self.on_delete, StateAction.DELETE)
        self.control = weakref.ref(control)
        self.updated = False
        self.deleted = False

    def on_update(self):
        self.updated = True

    def on_delete(self):
        self.deleted = True


# noinspection PyAbstractClass
class ClonedControl(VirtualBaseController):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.updated = False

    def update(self):
        self.updated = True


def test_observer_notify(mock_model):
    abc = VirtualBaseController(mock_model, project=None)

    assert not abc.is_active
    observer = Observer(abc)
    assert abc.is_active

    assert not observer.updated
    assert not observer.deleted

    abc.update()
    assert observer.updated
    abc.delete()
    assert observer.deleted


def test_controller_clone(mock_model):
    abc = VirtualBaseController(mock_model, project=None)
    assert not abc.is_clone

    # VirtualBaseController doesn't implement clone, so create our own adhoc clone
    clone = ClonedControl(mock_model, None)
    abc.register_clone(clone)

    assert clone.is_clone
    assert not clone.updated
    abc.update()
    assert clone.updated
