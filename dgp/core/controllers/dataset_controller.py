# -*- coding: utf-8 -*-
import functools
import logging
from PyQt5.QtGui import QColor, QBrush, QIcon, QStandardItemModel
from pandas import DataFrame

from core.hdf5_manager import HDF5Manager
from dgp.core.controllers.project_containers import ProjectFolder
from dgp.core.file_loader import FileLoader
from dgp.core.models.data import DataFile
from dgp.core.types.enumerations import DataTypes
from dgp.core.oid import OID
from dgp.core.controllers.controller_interfaces import (IFlightController,
                                                        IDataSetController)
from dgp.core.controllers.datafile_controller import DataFileController
from dgp.core.controllers.controller_bases import BaseController
from dgp.core.models.dataset import DataSet, DataSegment
from dgp.gui.dialogs.data_import_dialog import DataImportDialog
from dgp.lib.gravity_ingestor import read_at1a
from dgp.lib.trajectory_ingestor import import_trajectory


class DataSegmentController(BaseController):
    def __init__(self, segment: DataSegment):
        super().__init__()
        self._segment = segment
        self.setText(str(self._segment))

    @property
    def uid(self) -> OID:
        return self._segment.uid

    @property
    def datamodel(self) -> object:
        return self._segment

    def update(self):
        self.setText(str(self._segment))


class DataSetController(IDataSetController):
    def __init__(self, dataset: DataSet, flight: IFlightController,
                 name: str = ""):
        super().__init__()
        self._dataset = dataset
        self._flight = flight
        self._name = name

        self.setText("DataSet")
        self.setIcon(QIcon(":icons/folder_open.png"))
        self._grav_file = DataFileController(self._dataset.gravity)
        self._traj_file = DataFileController(self._dataset.gravity)
        self._segments = ProjectFolder("Segments")
        self.appendRow(self._grav_file)
        self.appendRow(self._traj_file)
        self.appendRow(self._segments)

        self._channel_model = QStandardItemModel()

        self._menu_bindings = [
            ('addAction', ('Set Name', lambda: None)),
            ('addAction', ('Set Active', lambda: None)),
            ('addAction', ('Add Segment', lambda: None)),
            ('addAction', ('Import Gravity', lambda: None)),
            ('addAction', ('Import Trajectory', lambda: None)),
            ('addAction', ('Delete', lambda: None)),
            ('addAction', ('Properties', lambda: None))
        ]

    @property
    def uid(self) -> OID:
        return self._dataset.uid

    @property
    def menu_bindings(self):
        return self._menu_bindings

    @property
    def datamodel(self) -> DataSet:
        return self._dataset

    @property
    def channel_model(self) -> QStandardItemModel:
        return self._channel_model

    def get_parent(self) -> IFlightController:
        return self._flight

    def set_parent(self, parent: IFlightController) -> None:
        self._flight = parent

    def add_segment(self, uid: OID, start: float, stop: float, label: str = ""):
        print("Adding data segment {!s}".format(uid))
        segment = DataSegment(uid, start, stop, self._segments.rowCount(), label)
        seg_ctrl = DataSegmentController(segment)
        # TODO: Need DataSegmentController
        self._dataset.add_segment(segment)
        self._segments.appendRow(seg_ctrl)

    def get_segment(self, uid: OID) -> DataSegmentController:
        for segment in self._segments.items():
            if segment.uid == uid:
                return segment

    def update_segment(self, uid: OID, start: float, stop: float,
                       label: str = ""):
        segment = self.get_segment(uid)

        # TODO: Get the controller from the ProjectFolder instance instead
        if segment is None:
            raise KeyError("Invalid UID, DataSegment does not exist.")

        segment.set_attr('start', start)
        segment.set_attr('stop', stop)
        segment.set_attr('label', label)

    def remove_segment(self, uid: OID):
        segment = self.get_segment(uid)
        if segment is None:
            print("NO matching segment found to remove")
            return

        self._segments.removeRow(segment.row())

    def set_active(self, active: bool = True) -> None:
        self._dataset.set_active(active)
        if active:
            self.setBackground(QBrush(QColor("#85acea")))
        else:
            self.setBackground(QBrush(QColor("white")))

    def _add_datafile(self, datafile: DataFile, data: DataFrame):
        # TODO: Refactor
        HDF5Manager.save_data(data, datafile, '')  # TODO: Get prj HDF Path
        if datafile.group == 'gravity':
            self.removeRow(self._grav_file.row())
            dfc = DataFileController(datafile, dataset=self.datamodel)
            self._grav_file = dfc
            self.appendRow(dfc)

        elif datafile.group == 'trajectory':
            pass
        else:
            raise TypeError("Invalid data group")

    def load_file_dlg(self, datatype: DataTypes = DataTypes.GRAVITY,
                      destination: IFlightController = None):  # pragma: no cover
        """
        Launch a Data Import dialog to load a Trajectory/Gravity data file into
        a dataset.

        Parameters
        ----------
        datatype
        destination

        Returns
        -------

        """
        parent = self.model().parent()

        def load_data(datafile: DataFile, params: dict):
            if datafile.group == 'gravity':
                method = read_at1a
            elif datafile.group == 'trajectory':
                method = import_trajectory
            else:
                print("Unrecognized data group: " + datafile.group)
                return
            loader = FileLoader(datafile.source_path, method, parent=parent,
                                **params)
            loader.completed.connect(functools.partial(self._add_datafile,
                                                       datafile))
            # TODO: Connect completed to add_child method of the flight
            loader.start()

        dlg = DataImportDialog(self, datatype, parent=parent)
        if destination is not None:
            dlg.set_initial_flight(destination)
        dlg.load.connect(load_data)
        dlg.exec_()


