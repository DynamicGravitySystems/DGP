# -*- coding: utf-8 -*-
from typing import Any


class PropertiesProxy:
    """
    This mixin provides an interface to selectively allow getattr calls against the
    proxied or underlying object in a wrapper class. getattr returns sucessfully only
    for attributes decorated with @property in the proxied instance.
    """
    @property
    def proxied(self) -> object:
        raise NotImplementedError

    def __getattr__(self, key: str):
        klass = self.proxied.__class__
        if key in klass.__dict__ and isinstance(klass.__dict__[key], property):
            return getattr(self.proxied, key)
        raise AttributeError(klass.__name__ + " has not public attribute %s" % key)
