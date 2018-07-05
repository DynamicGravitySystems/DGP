# -*- coding: utf-8 -*-
from typing import List

from PyQt5.QtGui import QValidator, QRegExpValidator, QIntValidator, QDoubleValidator
from PyQt5.QtWidgets import (QFormLayout, QWidget, QLineEdit, QLabel, QHBoxLayout, QLayoutItem,
                             QVBoxLayout)

__all__ = ['FormValidator', 'VALIDATION_ERR_MSG']
VALIDATION_ERR_MSG = "Ensure all marked fields are completed."


class FormValidator:
    """FormValidator Mixin Class

    This mixin provides a simple interface to run automatic validation
    on one or more QFormLayout objects in a Qt Object (typically within
    a QDialog).

    The mixin also supports validation of fields that are nested within a
    layout, for example it is common to use a QHBoxLayout (horizontal layout)
    within the FormLayout field area to have both a QLineEdit input and a
    QPushButton next to it (to browse for a file for example).
    The validate method will introspect any sub-layouts and retrieve the FIRST
    widget that can be validated, which has a validator or input mask set.

    TODO: Create a subclass of QRegExpValidator that allows a human error
    message to be set
    TODO: Consider some way to hook into fields and validate on changes
    That is a dynamic validation, so when the user corrects an invalid field
    the state is updated


    """
    ERR_STYLE = "QLabel { color: red; }"
    _CAN_VALIDATE = (QLineEdit,)

    @property
    def validation_targets(self) -> List[QFormLayout]:
        """Override this property with the QFormLayout object to be validated"""
        raise NotImplementedError

    @property
    def validation_error(self) -> QLabel:
        return QLabel()

    def _validate_field(self, widget: QWidget, label: QLabel) -> bool:
        validator: QValidator = widget.validator()
        if widget.hasAcceptableInput():
            label.setStyleSheet("")
            return True
        else:
            label.setStyleSheet(self.ERR_STYLE)
            if isinstance(validator, QRegExpValidator):
                reason = "Input must match regular expression: {0!s}".format(validator.regExp().pattern())
            elif isinstance(validator, (QIntValidator, QDoubleValidator)):
                reason = "Input must be between {0} and {1}".format(
                    validator.bottom(), validator.top())
            elif isinstance(validator, QValidator):  # TODO: Test Coverage
                reason = "Input does not pass validation."
            else:
                reason = "Invalid Input: input must conform to mask: {}".format(widget.inputMask())
            label.setToolTip(reason)
            return False

    def _validate_form(self, form: QFormLayout):
        res = []
        for i in range(form.rowCount()):
            try:
                label: QLabel = form.itemAt(i, QFormLayout.LabelRole).widget()
            except AttributeError:
                label = QLabel()
            field: QLayoutItem = form.itemAt(i, QFormLayout.FieldRole)
            if field is None:
                continue

            if field.layout() is not None and isinstance(field.layout(), (QHBoxLayout, QVBoxLayout)):
                layout = field.layout()
                for j in range(layout.count()):
                    _field = layout.itemAt(j)
                    _widget: QWidget = _field.widget()
                    if isinstance(_widget, self._CAN_VALIDATE):
                        if _widget.validator() or _widget.inputMask():
                            field = _field
                            break

            if field.widget() is not None and isinstance(field.widget(), self._CAN_VALIDATE):
                res.append(self._validate_field(field.widget(), label))

        return all(result for result in res)

    def validate(self, notify=True) -> bool:
        res = []
        for form in self.validation_targets:
            res.append(self._validate_form(form))
        valid = all(result for result in res)
        if not valid and notify:
            self.validation_error.setText(VALIDATION_ERR_MSG)

        return valid
