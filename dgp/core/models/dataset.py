# -*- coding: utf-8 -*-
from pathlib import Path
from typing import List
from datetime import datetime

import pandas as pd

from dgp.core.hdf5_manager import HDF5Manager
from dgp.core.models.data import DataFile
from dgp.core.oid import OID

__all__ = ['DataSegment', 'DataSet']


class DataSegment:
    def __init__(self, uid: OID, start: float, stop: float, sequence: int,
                 label: str = None):
        self.uid = uid
        self.uid.set_pointer(self)
        self._start = start
        self._stop = stop
        self.sequence = sequence
        self.label = label

    @property
    def start(self) -> datetime:
        return datetime.fromtimestamp(self._start)

    @start.setter
    def start(self, value: float) -> None:
        self._start = value

    @property
    def stop(self) -> datetime:
        return datetime.fromtimestamp(self._stop)

    @stop.setter
    def stop(self, value: float) -> None:
        self._stop = value

    def __str__(self):
        return "Segment <{:%H:%M} -> {:%H:%M}>".format(self.start, self.stop)


class DataSet:
    """DataSet is a paired set of Gravity and Trajectory Data

    DataSets can have segments defined, e.g. for an Airborne project these
    would be Flight Lines.

    Notes
    -----
    Once this class is implemented, DataFiles will be created and added only to
    a DataSet, they will not be permitted as direct children of Flights

    """
    def __init__(self, path: Path = None, gravity: DataFile = None,
                 trajectory: DataFile = None, segments: List[DataSegment]=None,
                 uid: OID = None, parent=None):
        self._parent = parent
        self.uid = uid or OID(self)
        self.uid.set_pointer(self)
        self._path: Path = path
        self._active: bool = False
        self._aligned: bool = False
        self._segments = segments or []

        self._gravity = gravity
        if self._gravity is not None:
            self._gravity.set_parent(self)
        self._trajectory = trajectory
        if self._trajectory is not None:
            self._trajectory.set_parent(self)

    def _align_frames(self):
        pass

    @property
    def gravity(self) -> DataFile:
        return self._gravity

    @property
    def trajectory(self) -> DataFile:
        return self._trajectory

    @property
    def dataframe(self) -> pd.DataFrame:
        """Return the concatenated DataFrame of gravity and trajectory data."""
        grav_data = HDF5Manager.load_data(self.gravity, self._path)
        traj_data = HDF5Manager.load_data(self.trajectory, self._path)
        frame: pd.DataFrame = pd.concat([grav_data, traj_data])
        # Or use align_frames?
        return frame

    def add_segment(self, segment: DataSegment):
        segment.sequence = len(self._segments)
        self._segments.append(segment)

    def get_segment(self, uid: OID):

        pass

    def remove_segment(self, uid: OID):
        # self._segments.remove()
        pass

    def update_segment(self):
        pass

    def set_active(self, active: bool = True):
        self._active = bool(active)

    def set_parent(self, parent):
        self._parent = parent


    # TODO: Implement align_frames functionality as below
    # TODO: Consider the implications of multiple data files
    # OR: insert align_frames into the transform graph and deal with it there

    # gravity = flight.gravity
    # trajectory = flight.trajectory
    # if gravity is not None and trajectory is not None:
    #     # align and crop the gravity and trajectory frames
    #
    #     from lib.gravity_ingestor import DGS_AT1A_INTERP_FIELDS
    #     from lib.trajectory_ingestor import TRAJECTORY_INTERP_FIELDS
    #
    #     fields = DGS_AT1A_INTERP_FIELDS | TRAJECTORY_INTERP_FIELDS
    #     new_gravity, new_trajectory = align_frames(gravity, trajectory,
    #                                                interp_only=fields)
