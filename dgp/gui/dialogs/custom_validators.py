# -*- coding: utf-8 -*-
from pathlib import Path
from typing import Tuple

from PyQt5.QtGui import QValidator

ValidationState = Tuple[int, str, int]


class DGPValidator(QValidator):
    @property
    def reason(self) -> str:
        raise NotImplementedError


class FileExistsValidator(DGPValidator):
    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self._reason = ""

    @property
    def reason(self) -> str:
        return self._reason

    def validate(self, value: str, pos: int) -> ValidationState:
        """Note, the Python implementation of this differs from the C++ API
        value and pos are passed as pointers in C++ allowing them to be mutated
        within the validate function.
        As this cannot be done in Python, the return type signature is changed instead
        to incorporate value and pos as a tuple with the QValidator State
        """
        try:
            path = Path(value)
        except TypeError:
            self._reason = "Invalid path, cannot convert to pathlib.Path"
            return QValidator.Invalid, value, pos

        if path.is_file():
            # Checking .exists() is redundant
            self._reason = ""
            return QValidator.Acceptable, value, pos

        self._reason = "Path is not a valid file"
        return QValidator.Intermediate, value, pos


class DirectoryValidator(DGPValidator):
    """Used to validate a directory path.

    If exist_ok is True, validation will be successful if the directory already exists.
    If exist_ok is False, validation will only be successful if the parent of the specified
    path is a directory, and it exists.
    """

    def __init__(self, exist_ok=True, parent=None):
        super().__init__(parent=parent)
        self._exist_ok = exist_ok
        self._reason = ""

    @property
    def reason(self) -> str:
        return self._reason

    def validate(self, value: str, pos: int) -> ValidationState:
        """TODO: Think about the logic here, allow nonexistent path if parent exists? e.g. creating new dir"""
        try:
            path = Path(value)
        except TypeError:
            return QValidator.Invalid, value, pos

        if path.is_reserved():
            return QValidator.Invalid, value, pos
        if path.is_file():
            return QValidator.Invalid, value, pos

        if path.is_dir() and self._exist_ok:
            return QValidator.Acceptable, str(path.absolute()), pos

        if path.is_dir() and not self._exist_ok:
            return QValidator.Intermediate, value, pos

        return QValidator.Intermediate, value, pos


class ValueExistsValidator(DGPValidator):
    def __init__(self, *values, case_sensitive=False, parent=None):
        super().__init__(parent=parent)
        self._reason = ""
        if not case_sensitive:
            self._values = [value.lower() for value in values]
        else:
            self._values = values

        self._case_sensitive = case_sensitive

    @property
    def reason(self) -> str:
        return self._reason

    def validate(self, value: str, pos: int) -> ValidationState:
        if not self._case_sensitive:
            check = value.lower()
        else:
            check = value

        if check in self._values:
            self._reason = "Name already exists"
            return QValidator.Intermediate, value, pos

        self._reason = ""
        return QValidator.Acceptable, value, pos
