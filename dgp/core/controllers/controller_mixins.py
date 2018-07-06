# -*- coding: utf-8 -*-
from typing import Any, Union

from PyQt5.QtGui import QValidator


class AttributeProxy:
    """
    This mixin class provides an interface to selectively allow getattr calls
    against the proxied or underlying object in a wrapper class. getattr
    returns successfully only for attributes decorated with @property in the
    proxied instance.
    """

    @property
    def datamodel(self) -> object:
        """Return the underlying model of the proxy class."""
        raise NotImplementedError

    def update(self):
        """Called when an attribute is set, override this to perform
        UI specific updates, e.g. set the DisplayRole data for a component.
        """
        pass

    def get_attr(self, key: str) -> Any:
        if hasattr(self.datamodel, key):
            return getattr(self.datamodel, key)
        else:
            raise AttributeError("Object {!r} has no attribute {}".format(self.datamodel, key))

    def set_attr(self, key: str, value: Any):
        if not hasattr(self.datamodel, key):
            raise AttributeError("Object {!r} has no attribute {}".format(self.datamodel, key))
        if not self.writeable(key):
            raise AttributeError("Attribute [{}] is not writeable".format(key))

        validator = self.validator(key)
        if validator is not None:
            valid = validator.validate(value, 0)[0]
            if not valid == QValidator.Acceptable:
                raise ValueError("Value does not pass validation")

        setattr(self.datamodel, key, value)
        self.update()

    def writeable(self, key: str) -> bool:
        """Get the write status for a specified proxied attribute key.

        Override this method to implement write-protection on proxied attributes.

        Parameters
        ----------
        key : str
            The attribute key to retrieve write status of

        Returns
        -------
        bool
            True if attribute is writeable
            False if attribute is write-protected (set_attr calls will fail)

        """
        return True

    def validator(self, key: str) -> Union[QValidator, None]:
        """Get the QValidator class for a specified proxied attribute key.

        Override this method to implement write-validation on attributes.

        This method should return a QValidator subtype for the specified
        key, or None if no validation should occur.
        """
        return None
