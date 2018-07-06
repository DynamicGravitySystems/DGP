# -*- coding: utf-8 -*-
from typing import Any


class AttributeProxy:
    """
    This mixin class provides an interface to selectively allow getattr calls against the
    proxied or underlying object in a wrapper class. getattr returns successfully only
    for attributes decorated with @property in the proxied instance.
    """

    @property
    def proxied(self) -> object:
        raise NotImplementedError

    def update(self):
        """Called when an attribute is set, override this to perform
        UI specific updates, e.g. set the DisplayRole data for a component.
        """
        pass

    def get_attr(self, key: str) -> Any:
        if hasattr(self.proxied, key):
            return getattr(self.proxied, key)
        else:
            raise AttributeError("Object {!r} has no attribute {}".format(self.proxied, key))

    def set_attr(self, key: str, value: Any):
        if hasattr(self.proxied, key):
            setattr(self.proxied, key, value)
            self.update()
        else:
            raise AttributeError("Object {!r} has no attribute {}".format(self.proxied, key))
