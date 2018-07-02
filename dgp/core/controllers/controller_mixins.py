# -*- coding: utf-8 -*-
from typing import Any


class AttributeProxy:
    """
    This mixin provides an interface to selectively allow getattr calls against the
    proxied or underlying object in a wrapper class. getattr returns successfully only
    for attributes decorated with @property in the proxied instance.
    """

    @property
    def proxied(self) -> object:
        raise NotImplementedError

    def update(self):
        """Called when an attribute is set, use this to update UI values as necessary"""
        raise NotImplementedError

    def get_attr(self, key: str) -> Any:
        klass = self.proxied.__class__
        if key in klass.__dict__ and isinstance(klass.__dict__[key], property):
            return getattr(self.proxied, key)

    def set_attr(self, key: str, value: Any):
        attrs = self.proxied.__class__.__dict__
        if key in attrs and isinstance(attrs[key], property):
            setattr(self.proxied, key, value)
            self.update()
        else:
            raise AttributeError("Attribute {!s} does not exist or is private on class {!s}"
                                 .format(key, self.proxied.__class__.__name__))

    def __getattr__(self, key: str):
        # TODO: This fails if the property is defined in a super-class
        klass = self.proxied.__class__
        if key in klass.__dict__ and isinstance(klass.__dict__[key], property):
            return getattr(self.proxied, key)
        raise AttributeError(klass.__name__ + " has no public attribute %s" % key)
