# -*- coding: utf-8 -*-
from pathlib import Path
from typing import List
from datetime import datetime

from dgp.core.models.datafile import DataFile
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
        return f'<{self.start:%H:%M} - {self.stop:%H:%M}>'

    def __repr__(self):
        return f'<DataSegment {self.uid!s} {self.start:%H:%M} - {self.stop:%H:%M}>'


class DataSet:
    """DataSet is a paired set of Gravity and Trajectory Data

    DataSets can have segments defined, e.g. for an Airborne project these
    would be Flight Lines.

    Parameters
    ----------
    path : Path, optional
        File system path to the HDF5 file where data from this dataset will reside
    gravity : :obj:`DataFile`, optional
        Optional Gravity DataFile to initialize this DataSet with
    trajectory : :obj:`DataFile`, optional
        Optional Trajectory DataFile to initialize this DataSet with
    segments : List[:obj:`DataSegment`], optional
        Optional list of DataSegment's to initialize this DataSet with
    uid

    Notes
    -----
    Once this class is implemented, DataFiles will be created and added only to
    a DataSet, they will not be permitted as direct children of Flights

    """
    def __init__(self, gravity: DataFile = None, trajectory: DataFile = None,
                 segments: List[DataSegment]=None, sensor=None, uid: OID = None):
        self.uid = uid or OID(self)
        self.uid.set_pointer(self)
        self.segments = segments or []

        self.gravity: DataFile = gravity
        self.trajectory: DataFile = trajectory

    @property


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
