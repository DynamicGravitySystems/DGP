# -*- coding: utf-8 -*-
from datetime import datetime
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
        self._fctrl = flight

        self.cb_gravimeters.setModel(project.meter_model)
        self.qde_flight_date.setDate(datetime.today())
        self.qsb_sequence.setValue(project.flight_model.rowCount())

        self.qpb_add_sensor.clicked.connect(self._project.add_gravimeter)

    def accept(self):
        name = self.qle_flight_name.text()
        qdate: QDate = self.qde_flight_date.date()
        date = datetime(qdate.year(), qdate.month(), qdate.day())
        notes = self.qte_notes.toPlainText()
        sequence = self.qsb_sequence.value()
        duration = self.qsb_duration.value()

        meter = self.cb_gravimeters.currentData(role=Qt.UserRole)  # type: Gravimeter

        # TODO: Add meter association to flight
        # how to make a reference that can be retrieved after loading from JSON?

        if self._fctrl is not None:
            # Existing flight - update
            self._fctrl.set_attr('name', name)
            self._fctrl.set_attr('date', date)
            self._fctrl.set_attr('notes', notes)
            self._fctrl.set_attr('sequence', sequence)
            self._fctrl.set_attr('duration', duration)
            self._fctrl.add_child(meter)
        else:
            flt = Flight(self.qle_flight_name.text(), date=date,
                         notes=self.qte_notes.toPlainText(),
                         sequence=sequence, duration=duration)
            self._project.add_child(flt)

        super().accept()

    @classmethod
    def from_existing(cls, flight: IFlightController, project: IAirborneController,
                      parent: Optional[QWidget] = None):
        dialog = cls(project, flight, parent=parent)
        dialog.setWindowTitle("Properties: " + flight.name)
        dialog.qle_flight_name.setText(flight.name)
        dialog.qte_notes.setText(flight.notes)
        dialog.qsb_duration.setValue(flight.duration)
        dialog.qsb_sequence.setValue(flight.sequence)
        if flight.date is not None:
            dialog.qde_flight_date.setDate(flight.date)

        return dialog
