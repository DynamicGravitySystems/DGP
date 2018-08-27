# -*- coding: utf-8 -*-
import datetime
from typing import Optional, List

from PyQt5.QtCore import Qt, QDate, QRegExp
from PyQt5.QtGui import QRegExpValidator
from PyQt5.QtWidgets import QDialog, QWidget, QFormLayout

from dgp.core.models.meter import Gravimeter
from dgp.core.controllers.controller_interfaces import IAirborneController, IFlightController
from dgp.core.models.flight import Flight
from .dialog_mixins import FormValidator
from ..ui.add_flight_dialog import Ui_NewFlight


class AddFlightDialog(QDialog, Ui_NewFlight, FormValidator):
    def __init__(self, project: IAirborneController, flight: IFlightController = None,
                 parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setupUi(self)
        self._project = project
        self._flight = flight

        # Configure Form Validation
        self._name_validator = QRegExpValidator(QRegExp("[A-Za-z]+.{2,20}"))
        self.qle_flight_name.setValidator(self._name_validator)

        if self._flight is not None:
            self._set_flight(self._flight)
        else:
            self.qde_flight_date.setDate(datetime.date.today())
            self.qsb_sequence.setValue(project.flight_model.rowCount())

    @property
    def validation_targets(self) -> List[QFormLayout]:
        return [self.qfl_flight_form]

    @property
    def validation_error(self):
        return self.ql_validation_err

    def accept(self):
        if not self.validate():
            return

        name = self.qle_flight_name.text()
        qdate: QDate = self.qde_flight_date.date()
        date = datetime.date(qdate.year(), qdate.month(), qdate.day())
        notes = self.qte_notes.toPlainText()
        sequence = self.qsb_sequence.value()
        duration = self.qsb_duration.value()

        if self._flight is not None:
            # Existing flight - update
            self._flight.set_attr('name', name)
            self._flight.set_attr('date', date)
            self._flight.set_attr('notes', notes)
            self._flight.set_attr('sequence', sequence)
            self._flight.set_attr('duration', duration)
        else:
            # Create new flight and add it to project
            flt = Flight(self.qle_flight_name.text(), date=date,
                         notes=self.qte_notes.toPlainText(),
                         sequence=sequence, duration=duration)
            self._project.add_child(flt)

        super().accept()

    def _set_flight(self, flight: IFlightController):
        self.setWindowTitle("Properties: " + flight.get_attr('name'))
        self.qle_flight_name.setText(flight.get_attr('name'))
        self.qte_notes.setText(flight.get_attr('notes'))
        self.qsb_duration.setValue(flight.get_attr('duration'))
        self.qsb_sequence.setValue(flight.get_attr('sequence'))
        self.qde_flight_date.setDate(flight.get_attr('date'))

    @classmethod
    def from_existing(cls, flight: IFlightController,
                      project: IAirborneController,
                      parent: Optional[QWidget] = None):
        return cls(project, flight, parent=parent)
