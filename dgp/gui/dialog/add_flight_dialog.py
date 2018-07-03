# -*- coding: utf-8 -*-
import datetime
from typing import Optional

from PyQt5.QtCore import Qt, QDate
from PyQt5.QtWidgets import QDialog, QWidget

from dgp.core.models.meter import Gravimeter
from dgp.core.controllers.controller_interfaces import IAirborneController, IFlightController
from dgp.core.models.flight import Flight
from ..ui.add_flight_dialog import Ui_NewFlight


class AddFlightDialog(QDialog, Ui_NewFlight):
    def __init__(self, project: IAirborneController, flight: IFlightController = None,
                 parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setupUi(self)
        self._project = project
        self._flight = flight

        self.cb_gravimeters.setModel(project.meter_model)
        self.qpb_add_sensor.clicked.connect(self._project.add_gravimeter)

        if self._flight is not None:
            self._set_flight(self._flight)
        else:
            self.qde_flight_date.setDate(datetime.date.today())
            self.qsb_sequence.setValue(project.flight_model.rowCount())

    def accept(self):
        name = self.qle_flight_name.text()
        qdate: QDate = self.qde_flight_date.date()
        date = datetime.date(qdate.year(), qdate.month(), qdate.day())
        notes = self.qte_notes.toPlainText()
        sequence = self.qsb_sequence.value()
        duration = self.qsb_duration.value()

        meter = self.cb_gravimeters.currentData(role=Qt.UserRole)  # type: Gravimeter

        # TODO: Add meter association to flight
        # how to make a reference that can be retrieved after loading from JSON?

        if self._flight is not None:
            # Existing flight - update
            self._flight.set_attr('name', name)
            self._flight.set_attr('date', date)
            self._flight.set_attr('notes', notes)
            self._flight.set_attr('sequence', sequence)
            self._flight.set_attr('duration', duration)
            self._flight.add_child(meter)
        else:
            # Create new flight and add it to project
            flt = Flight(self.qle_flight_name.text(), date=date,
                         notes=self.qte_notes.toPlainText(),
                         sequence=sequence, duration=duration)
            self._project.add_child(flt)

        super().accept()

    def _set_flight(self, flight: IFlightController):
        self.setWindowTitle("Properties: " + flight.name)
        self.qle_flight_name.setText(flight.name)
        self.qte_notes.setText(flight.notes)
        self.qsb_duration.setValue(flight.duration)
        self.qsb_sequence.setValue(flight.sequence)
        if flight.date is not None:
            self.qde_flight_date.setDate(flight.date)

    @classmethod
    def from_existing(cls, flight: IFlightController,
                      project: IAirborneController,
                      parent: Optional[QWidget] = None):
        return cls(project, flight, parent=parent)
