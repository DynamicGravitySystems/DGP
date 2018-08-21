# -*- coding: utf-8 -*-
import logging
import weakref
from pathlib import Path
from typing import List, Union, Generator, Set

from PyQt5.QtWidgets import QInputDialog
from pandas import DataFrame, Timestamp, concat
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QColor, QBrush, QStandardItemModel, QStandardItem

from dgp.core import OID, Icon
from dgp.core.hdf5_manager import HDF5Manager
from dgp.core.models.datafile import DataFile
from dgp.core.models.dataset import DataSet, DataSegment
from dgp.core.types.enumerations import DataType, StateColor
from dgp.lib.etc import align_frames

from . import controller_helpers
from .gravimeter_controller import GravimeterController
from .controller_interfaces import IFlightController, IDataSetController, AbstractController
from .project_containers import ProjectFolder
from .datafile_controller import DataFileController


class DataSegmentController(AbstractController):
    """Controller for :class:`DataSegment`

    Implements reference tracking feature allowing the mutation of segments
    representations displayed on a plot surface.
    """
    def __init__(self, segment: DataSegment, parent: IDataSetController = None,
                 clone=False):
        super().__init__()
        self._segment = segment
        self._parent = parent
        self._clone = clone
        self.setData(segment, Qt.UserRole)
        self.update()

        self._menu = [
            ('addAction', ('Delete', self.delete))
        ]

    @property
    def uid(self) -> OID:
        return self._segment.uid

    @property
    def datamodel(self) -> DataSegment:
        return self._segment

    @property
    def menu(self):
        return self._menu

    def update(self):
        super().update()
        self.setText(str(self._segment))
        self.setToolTip(repr(self._segment))

    def clone(self) -> 'DataSegmentController':
        return DataSegmentController(self._segment, clone=True)

    def delete(self):
        """Delete this data segment from any active plots (via weak ref), and
        from its parent DataSet/Controller

        """
        super().delete()
        try:
            self._parent.remove_segment(self.uid)
        except KeyError:
            pass


class DataSetController(IDataSetController):
    def __init__(self, dataset: DataSet, flight: IFlightController):
        super().__init__()
        self._dataset = dataset
        self._flight = weakref.ref(flight)
        # self._project = self._flight().project
        self.log = logging.getLogger(__name__)

        self.setEditable(False)
        self.setText(self._dataset.name)
        self.setIcon(Icon.PLOT_LINE.icon())
        self.setBackground(QBrush(QColor(StateColor.INACTIVE.value)))
        self._grav_file = DataFileController(self._dataset.gravity, self)
        self._traj_file = DataFileController(self._dataset.trajectory, self)
        self._child_map = {DataType.GRAVITY: self._grav_file,
                           DataType.TRAJECTORY: self._traj_file}

        self._segments = ProjectFolder("Segments", Icon.LINE_MODE.icon())
        for segment in dataset.segments:
            seg_ctrl = DataSegmentController(segment, parent=self)
            self._segments.appendRow(seg_ctrl)

        self.appendRow(self._grav_file)
        self.appendRow(self._traj_file)
        self.appendRow(self._segments)

        self._sensor = None
        if dataset.sensor is not None:
            ctrl = self.project.get_child(dataset.sensor.uid)
            if ctrl is not None:
                self._sensor = ctrl.clone()
                self.appendRow(self._sensor)

        self._gravity: DataFrame = DataFrame()
        self._trajectory: DataFrame = DataFrame()
        self._dataframe: DataFrame = DataFrame()

        self._channel_model = QStandardItemModel()

        self._menu_bindings = [  # pragma: no cover
            ('addAction', ('Open', lambda: self.model().item_activated(self.index()))),
            ('addAction', ('Set Name', self._action_set_name)),
            ('addAction', (Icon.METER.icon(), 'Set Sensor',
                           self._action_set_sensor_dlg)),
            ('addSeparator', ()),
            ('addAction', (Icon.GRAVITY.icon(), 'Import Gravity',
                           lambda: self.project.load_file_dlg(DataType.GRAVITY, dataset=self))),
            ('addAction', (Icon.TRAJECTORY.icon(), 'Import Trajectory',
                           lambda: self.project.load_file_dlg(DataType.TRAJECTORY, dataset=self))),
            ('addAction', ('Align Data', self.align)),
            ('addSeparator', ()),
            ('addAction', ('Delete', self._action_delete)),
            ('addAction', ('Properties', lambda: None))
        ]

        self._clones: Set[DataSetController] = weakref.WeakSet()

    @property
    def children(self):
        return None

    def clone(self):
        return DataSetController(self._dataset, self.get_parent())

    @property
    def project(self):
        return self.get_parent().get_parent()

    @property
    def uid(self) -> OID:
        return self._dataset.uid

    @property
    def is_active(self):
        return False

    @property
    def hdfpath(self) -> Path:
        return self.get_parent().get_parent().hdfpath

    @property
    def menu(self):  # pragma: no cover
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
    def segments(self) -> Generator[DataSegmentController, None, None]:
        for i in range(self._segments.rowCount()):
            yield self._segments.child(i)

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
        if self._dataset.gravity is None:
            return self._gravity
        try:
            self._gravity = HDF5Manager.load_data(self._dataset.gravity, self.hdfpath)
        except Exception:
            self.log.exception(f'Exception loading gravity from HDF')
        finally:
            return self._gravity

    @property
    def trajectory(self) -> Union[DataFrame, None]:
        if not self._trajectory.empty:
            return self._trajectory
        if self._dataset.trajectory is None:
            return self._trajectory
        try:
            self._trajectory = HDF5Manager.load_data(self._dataset.trajectory, self.hdfpath)
        except Exception:
            self.log.exception(f'Exception loading trajectory data from HDF')
        finally:
            return self._trajectory

    def dataframe(self) -> DataFrame:
        if self._dataframe.empty:
            self._dataframe: DataFrame = concat([self.gravity, self.trajectory], axis=1, sort=True)
        return self._dataframe

    def align(self):
        if self.gravity.empty or self.trajectory.empty:
            self.log.info(f'Gravity or Trajectory is empty, cannot align.')
            return
        from dgp.lib.gravity_ingestor import DGS_AT1A_INTERP_FIELDS
        from dgp.lib.trajectory_ingestor import TRAJECTORY_INTERP_FIELDS

        fields = DGS_AT1A_INTERP_FIELDS | TRAJECTORY_INTERP_FIELDS
        n_grav, n_traj = align_frames(self._gravity, self._trajectory,
                                      interp_only=fields)
        self._gravity = n_grav
        self._trajectory = n_traj
        self.log.info(f'DataFrame aligned.')

    def get_parent(self) -> IFlightController:
        return self._flight()

    def add_datafile(self, datafile: DataFile) -> None:
        if datafile.group is DataType.GRAVITY:
            self.datamodel.gravity = datafile
            self._grav_file.set_datafile(datafile)
            self._gravity = DataFrame()
        elif datafile.group is DataType.TRAJECTORY:
            self.datamodel.trajectory = datafile
            self._traj_file.set_datafile(datafile)
            self._trajectory = DataFrame()
        else:
            raise TypeError("Invalid DataFile group provided.")

        self._dataframe = DataFrame()
        self._update_channel_model()

    def get_datafile(self, group) -> DataFileController:
        return self._child_map[group]

    def add_segment(self, uid: OID, start: Timestamp, stop: Timestamp,
                    label: str = "") -> DataSegmentController:
        segment = DataSegment(uid, start, stop,
                              self._segments.rowCount(), label)
        self._dataset.segments.append(segment)
        seg_ctrl = DataSegmentController(segment, parent=self)
        self._segments.appendRow(seg_ctrl)
        return seg_ctrl

    def get_segment(self, uid: OID) -> DataSegmentController:
        for segment in self._segments.items():  # type: DataSegmentController
            if segment.uid == uid:
                return segment

    def update_segment(self, uid: OID, start: Timestamp = None,
                       stop: Timestamp = None, label: str = None):
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

    # Context Menu Handlers
    def _action_set_name(self):
        name = controller_helpers.get_input("Set DataSet Name", "Enter a new name:",
                                            self.get_attr('name'),
                                            parent=self.parent_widget)
        if name:
            self.set_attr('name', name)

    def _action_set_sensor_dlg(self):
        sensors = {}
        for i in range(self.project.meter_model.rowCount()):
            sensor = self.project.meter_model.item(i)
            sensors[sensor.text()] = sensor

        item, ok = QInputDialog.getItem(self.parent_widget, "Select Gravimeter",
                                        "Sensor", sensors.keys(), editable=False)
        if ok:
            if self._sensor is not None:
                self.removeRow(self._sensor.row())

            sensor: GravimeterController = sensors[item]
            self.set_attr('sensor', sensor)
            self._sensor: GravimeterController = sensor.clone()
            self.appendRow(self._sensor)

    def _action_delete(self, confirm: bool = True):
        self.get_parent().remove_child(self.uid, confirm)
