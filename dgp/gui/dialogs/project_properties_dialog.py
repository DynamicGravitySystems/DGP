# -*- coding: utf-8 -*-
from datetime import datetime
from pathlib import Path
from typing import List, Any

from PyQt5.QtWidgets import QFormLayout, QLineEdit, QDateTimeEdit, QWidget
from PyQt5.QtWidgets import QDialog

from dgp.core.oid import OID
from dgp.core.controllers.controller_interfaces import IAirborneController
from .dialog_mixins import FormValidator
from ..ui.project_properties_dialog import Ui_ProjectPropertiesDialog


class ProjectPropertiesDialog(QDialog, Ui_ProjectPropertiesDialog, FormValidator):

    def __init__(self, project: IAirborneController, parent=None):
        super().__init__(parent=parent)
        self.setupUi(self)
        self._project = project
        self.setWindowTitle(self._project.get_attr('name'))
        self._updates = {}
        self._field_map = {
            str: (lambda v: v.strip(), QLineEdit),
            Path: (lambda v: str(v.resolve()), QLineEdit),
            datetime: (lambda v: v, QDateTimeEdit),
            OID: (lambda v: v.base_uuid, QLineEdit)
        }

        self._setup_properties_tab()

    def _get_field_attr(self, _type: Any):
        try:
            attrs = self._field_map[_type]
        except KeyError:
            for key in self._field_map.keys():
                if issubclass(_type, key):
                    return self._field_map[key]
            return None
        return attrs

    def _setup_properties_tab(self):
        for key in self._project.fields:
            enabled = self._project.writeable(key)
            validator = self._project.validator(key)

            raw_value = self._project.get_attr(key)
            data_type = type(raw_value)

            value_lambda, widget_type = self._get_field_attr(data_type)

            widget: QWidget = widget_type(value_lambda(raw_value))
            widget.setEnabled(enabled)
            if validator:
                widget.setValidator(validator)

            self.qfl_properties.addRow(str(key.strip('_')).capitalize(), widget)
            if enabled:
                self._updates[key] = data_type, widget

    @property
    def validation_targets(self) -> List[QFormLayout]:
        return [self.qfl_properties]

    @property
    def validation_error(self):
        return self.ql_validation_err

    def accept(self):
        print("Updating values for fields:")
        for key in self._updates:
            print(key)
            try:
                self._project.set_attr(key, self._updates[key][1].text())
            except AttributeError:
                print("Can't update key: {}".format(key))

        if not self.validate():
            print("A value is invalid")
            return

        super().accept()
