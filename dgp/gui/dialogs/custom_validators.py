# -*- coding: utf-8 -*-
from pathlib import Path
from typing import Tuple

from PyQt5.QtGui import QValidator


class FileExistsValidator(QValidator):
    # TODO: Move this into its own module (custom_validators?)
    def __init__(self, parent=None):
        super().__init__(parent=parent)

    def validate(self, value: str, pos: int):
        """Note, the Python implementation of this differs from the C++ API
        value and pos are passed as pointers in C++ allowing them to be mutated
        within the validate function.
        As this cannot be done in Python, the return type signature is changed instead
        to incorporate value and pos as a tuple with the QValidator State
        """
        try:
            path = Path(value)
        except TypeError:
            return QValidator.Invalid, value, pos

        if path.is_file():
            # Checking .exists() is redundant
            return QValidator.Acceptable, value, pos
        return QValidator.Intermediate, value, pos


class DirectoryValidator(QValidator):
    def __init__(self, exist_ok=True, parent=None):
        super().__init__(parent=parent)
        self._exist_ok = exist_ok

    def validate(self, value: str, pos: int) -> Tuple[int, str, int]:
        """TODO: Think about the logic here, allow nonexistent path if parent exists? e.g. creating new dir"""
        try:
            path = Path(value)
        except TypeError:
            return QValidator.Invalid, value, pos

        if path.is_file():
            return QValidator.Invalid, value, pos

        if path.is_dir() and self._exist_ok:
            return QValidator.Acceptable, str(path.absolute()), pos

        if path.is_dir() and not self._exist_ok:
            return QValidator.Intermediate, value, pos

        return QValidator.Intermediate, value, pos
