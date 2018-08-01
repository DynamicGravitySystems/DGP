# -*- coding: utf-8 -*-
from pathlib import Path
from typing import List, Union

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QColor, QBrush, QIcon, QStandardItemModel, QStandardItem
from pandas import DataFrame, concat

from dgp.core.hdf5_manager import HDF5Manager
from dgp.core.controllers.project_containers import ProjectFolder
from dgp.core.models.datafile import DataFile
from dgp.core.types.enumerations import DataTypes
from dgp.core.oid import OID
from dgp.core.controllers.controller_interfaces import (IFlightController,
                                                        IDataSetController)
from dgp.core.controllers.datafile_controller import DataFileController
from dgp.core.controllers.controller_bases import BaseController
from dgp.core.models.dataset import DataSet, DataSegment

ACTIVE_COLOR = "#85acea"
INACTIVE_COLOR = "#ffffff"


class DataSegmentController(BaseController):
    def __init__(self, segment: DataSegment, clone=False):
        super().__init__()
        self._segment = segment
        self._clone = clone
        self.setData(segment, Qt.UserRole)
        self.update()

    @property
    def uid(self) -> OID:
        return self._segment.uid

    @property
    def datamodel(self) -> DataSegment:
        return self._segment

    def update(self):
        self.setText(str(self._segment))
        self.setToolTip(repr(self._segment))

    def clone(self) -> 'DataSegmentController':
        return DataSegmentController(self._segment, clone=True)


class DataSetController(IDataSetController):
    def __init__(self, dataset: DataSet, flight: IFlightController,
                 name: str = ""):
        super().__init__()
        self._dataset = dataset
        self._flight: IFlightController = flight
        self._project = self._flight.project
        self._name = name
        self._active = False

        self.setEditable(False)
        self.setText("DataSet")
        self.setIcon(QIcon(":icons/folder_open.png"))
        self.setBackground(QBrush(QColor(INACTIVE_COLOR)))
        self._grav_file = DataFileController(self._dataset.gravity, self)
        self._traj_file = DataFileController(self._dataset.trajectory, self)
        self._child_map = {'gravity': self._grav_file,
                           'trajectory': self._traj_file}

        self._segments = ProjectFolder("Segments")
        for segment in dataset.segments:
            seg_ctrl = DataSegmentController(segment)
            self._segments.appendRow(seg_ctrl)

        self.appendRow(self._grav_file)
        self.appendRow(self._traj_file)
        self.appendRow(self._segments)

        self._gravity: DataFrame = DataFrame()
        self._trajectory: DataFrame = DataFrame()
        self._dataframe: DataFrame = DataFrame()

        self._channel_model = QStandardItemModel()

        self._menu_bindings = [  # pragma: no cover
            ('addAction', ('Set Name', self._set_name)),
            ('addAction', ('Set Active', lambda: self.get_parent().activate_child(self.uid))),
            ('addAction', (QIcon(':/icons/meter_config.png'), 'Set Sensor',
                           self._set_sensor_dlg)),
            ('addSeparator', ()),
            ('addAction', (QIcon(':/icons/gravity'), 'Import Gravity',
                           lambda: self._project.load_file_dlg(DataTypes.GRAVITY, dataset=self))),
            ('addAction', (QIcon(':/icons/gps'), 'Import Trajectory',
                           lambda: self._project.load_file_dlg(DataTypes.TRAJECTORY, dataset=self))),
            ('addAction', ('Align Data', self.align)),
            ('addSeparator', ()),
            ('addAction', ('Delete', lambda: self.get_parent().remove_child(self.uid))),
            ('addAction', ('Properties', lambda: None))
        ]

    def clone(self):
        return DataSetController(self._dataset, self._flight)

    @property
    def uid(self) -> OID:
        return self._dataset.uid

    @property
    def hdfpath(self) -> Path:
        return self._flight.get_parent().hdf5path

    @property
    def menu_bindings(self):  # pragma: no cover
        return self._menu_bindings

    @property
    def datamodel(self) -> DataSet:
        return self._dataset

    @property
    def series_model(self) -> QStandardItemModel:
        if 0 == self._channel_model.rowCount():
            self._update_channel_model()
        return self._channel_model

    @property
    def segment_model(self) -> QStandardItemModel:
        return self._segments.internal_model

    @property
    def columns(self) -> List[str]:
        return [col for col in self.dataframe()]

    def _update_channel_model(self):
        df = self.dataframe()
        self._channel_model.clear()
        for col in df:
            series_item = QStandardItem(col)
            series_item.setData(df[col], Qt.UserRole)
            self._channel_model.appendRow(series_item)

    @property
    def gravity(self) -> Union[DataFrame]:
        if not self._gravity.empty:
            return self._gravity
        try:
            self._gravity = HDF5Manager.load_data(self._dataset.gravity, self.hdfpath)
        except Exception as e:
            pass
        finally:
            return self._gravity

    @property
    def trajectory(self) -> Union[DataFrame, None]:
        if not self._trajectory.empty:
            return self._trajectory
        try:
            self._trajectory = HDF5Manager.load_data(self._dataset.trajectory, self.hdfpath)
        except Exception as e:
            pass
        finally:
            return self._trajectory

    def dataframe(self) -> DataFrame:
        if self._dataframe.empty:
            self._dataframe: DataFrame = concat([self.gravity, self.trajectory])
        return self._dataframe

    # def slice(self, segment_uid: OID):
    #     df = self.dataframe()
    #     if df is None:
    #         return None
    #
    #     segment = self.get_segment(segment_uid).datamodel
    #     # start = df.index.searchsorted(segment.start)
    #     # stop = df.index.searchsorted(segment.stop)
    #
    #     segment_df = df.loc[segment.start:segment.stop]
    #     return segment_df

    def get_parent(self) -> IFlightController:
        return self._flight

    def set_parent(self, parent: IFlightController) -> None:
        self._flight.remove_child(self.uid, confirm=False)
        self._flight = parent
        self._flight.add_child(self.datamodel)

    def add_datafile(self, datafile: DataFile) -> None:
        # datafile.set_parent(self)
        if datafile.group == 'gravity':
            self.datamodel.gravity = datafile
            self._grav_file.set_datafile(datafile)
            self._gravity = DataFrame()
        elif datafile.group == 'trajectory':
            self.datamodel.trajectory = datafile
            self._traj_file.set_datafile(datafile)
            self._trajectory = DataFrame()
        else:
            raise TypeError("Invalid DataFile group provided.")

        self._dataframe = DataFrame()
        self._update_channel_model()

    def get_datafile(self, group) -> DataFileController:
        return self._child_map[group]

    def add_segment(self, uid: OID, start: float, stop: float,
                    label: str = "") -> DataSegmentController:
        segment = DataSegment(uid, start, stop, self._segments.rowCount(), label)
        self._dataset.segments.append(segment)
        seg_ctrl = DataSegmentController(segment)
        self._segments.appendRow(seg_ctrl)
        return seg_ctrl

    def get_segment(self, uid: OID) -> DataSegmentController:
        for segment in self._segments.items():  # type: DataSegmentController
            if segment.uid == uid:
                return segment

    def update_segment(self, uid: OID, start: float = None, stop: float = None,
                       label: str = None):
        segment = self.get_segment(uid)
        # TODO: Find a better way to deal with model item clones
        if segment is None:
            raise KeyError(f'Invalid UID, no segment exists with UID: {uid!s}')

        segment_clone = self.segment_model.item(segment.row())
        if start:
            segment.set_attr('start', start)
            segment_clone.set_attr('start', start)
        if stop:
            segment.set_attr('stop', stop)
            segment_clone.set_attr('stop', stop)
        if label:
            segment.set_attr('label', label)
            segment_clone.set_attr('label', label)

    def remove_segment(self, uid: OID):
        segment = self.get_segment(uid)
        if segment is None:
            raise KeyError(f'Invalid UID, no segment exists with UID: {uid!s}')

        self._segments.removeRow(segment.row())
        self._dataset.segments.remove(segment.datamodel)

    def update(self):
        self.setText(self._dataset.name)
        super().update()

    def set_active(self, state: bool):
        self._active = bool(state)
        if self._active:
            self.setBackground(QColor(StateColor.ACTIVE.value))
        else:
            self.setBackground(QColor(StateColor.INACTIVE.value))

    @property
    def is_active(self) -> bool:
        return self._active

    # Context Menu Handlers
    def _set_name(self):
        name = controller_helpers.get_input("Set DataSet Name", "Enter a new name:",
                                            self.get_attr('name'),
                                            parent=self.parent_widget)
        if name:
            self.set_attr('name', name)

    def _set_sensor_dlg(self):

        pass
