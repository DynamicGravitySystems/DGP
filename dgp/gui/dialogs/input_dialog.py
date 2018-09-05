# -*- coding: utf-8 -*-
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtWidgets import (QDialog, QLabel, QWidget, QLineEdit,
                             QDialogButtonBox, QVBoxLayout)

from dgp.gui.dialogs.custom_validators import DGPValidator


class InputDialog(QDialog):
    sigValueAccepted = pyqtSignal(str)

    """InputDialog provides a simple dialog for string input by the user
    
    This dialog also supports Validation of the input, by supplying a validator
    to the constructor, the dialog will automatically run the validation when 
    the text changes, and when the user attempts to accept the dialog.
    
    An error message will be displayed as soon as an invalid value is entered
    into the editor.
    
    The valid value is emitted via sigValueAccepted when the dialog is accepted.
    The value can also be retrieved via the value property (not guaranteed to be
    valid).
    
    Parameters
    ----------
    title : str
    label : str
    value : str, optional
    validator : :class:`DGPValidator`, optional
    parent : QWidget, optional
    
    """
    def __init__(self, title: str, label: str,
                 value: str = "", validator: DGPValidator = None,
                 parent: QWidget = None):
        super().__init__(parent=parent, flags=Qt.Dialog)
        self.setWindowTitle(title)

        _layout = QVBoxLayout(self)
        self._label = QLabel(label)
        self._err = QLabel("")
        self._err.setStyleSheet("QLabel { color: red };")
        self._err.setVisible(False)
        self._editor = QLineEdit(value)
        if validator is not None:
            self._editor.setValidator(validator)
            self._editor.textChanged.connect(self._validate)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

        _layout.addWidget(self._label)
        _layout.addWidget(self._editor)
        _layout.addWidget(self._err, alignment=Qt.AlignRight)
        _layout.addWidget(buttons)
        self.adjustSize()

    def accept(self):
        if self._editor.hasAcceptableInput():
            self.sigValueAccepted.emit(self._editor.text())
            super().accept()

    def set_err(self, value: str):
        if not value:
            self._err.clear()
            self._err.setVisible(False)
            self._editor.setToolTip(value)
            self.adjustSize()
        else:
            self._err.setText(value)
            self._err.setVisible(True)
            self._editor.setToolTip("")
            self.adjustSize()

    @property
    def max_length(self):
        return self._editor.maxLength()

    @max_length.setter
    def max_length(self, value: int):
        self._editor.setMaxLength(value)

    @property
    def editor(self) -> QLineEdit:
        return self._editor

    @property
    def value(self) -> str:
        return self._editor.text()

    def _validate(self, text):
        validator = self._editor.validator()
        if not validator:
            return True

        valid, _, _ = validator.validate(text, self._editor.cursorPosition())
        if valid != DGPValidator.Acceptable:
            self.set_err(validator.reason)
            return False
        else:
            self.set_err("")
            return True
