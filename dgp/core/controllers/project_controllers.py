# -*- coding: utf-8 -*-
import functools
import itertools
import logging
from pathlib import Path
from typing import Union, List, Generator, cast

from PyQt5.QtCore import Qt, QRegExp
from PyQt5.QtGui import QColor, QStandardItemModel, QRegExpValidator
from pandas import DataFrame, concat

from .project_treemodel import ProjectTreeModel
from .flight_controller import FlightController
from .gravimeter_controller import GravimeterController
from .project_containers import ProjectFolder
from .controller_helpers import confirm_action, get_input, show_in_explorer
from .controller_interfaces import IAirborneController, IDataSetController
from dgp.core.oid import OID
from dgp.core.file_loader import FileLoader
from dgp.core.hdf5_manager import HDF5Manager
from dgp.core.models.datafile import DataFile
from dgp.core.models.flight import Flight
from dgp.core.models.meter import Gravimeter
from dgp.core.models.project import GravityProject, AirborneProject
from dgp.core.types.enumerations import DataType, Icon, StateColor
from dgp.gui.utils import ProgressEvent
from dgp.gui.dialogs.add_flight_dialog import AddFlightDialog
from dgp.gui.dialogs.add_gravimeter_dialog import AddGravimeterDialog
from dgp.gui.dialogs.data_import_dialog import DataImportDialog
from dgp.gui.dialogs.project_properties_dialog import ProjectPropertiesDialog
from dgp.gui.dialogs.export_dialog import ExportDialog
from dgp.lib.gravity_ingestor import read_at1a
from dgp.lib.trajectory_ingestor import import_trajectory


class AirborneProjectController(IAirborneController):
    """Construct an AirborneProjectController around an AirborneProject

    Parameters
    ----------
    project : :class:`AirborneProject`
    path : :class:`pathlib.Path`, Optional
        Optionally supply the directory path where the project was loaded from
        in order to update the stored state.

    """
    def __init__(self, project: AirborneProject, path: Path = None):
        super().__init__(model=project)
        self.log = logging.getLogger(__name__)
        if path:
            self.entity.path = path

        self._active = None

        self.setIcon(Icon.DGP_NOTEXT.icon())
        self.setToolTip(str(self.entity.path.resolve()))

        self.flights = ProjectFolder("Flights")
        self.appendRow(self.flights)
        self.meters = ProjectFolder("Gravimeters")
        self.appendRow(self.meters)

        self._child_map = {Flight: self.flights,
                           Gravimeter: self.meters}

        # It is important that GravimeterControllers are defined before Flights
        # Flights may create references to a Gravimeter object, but not vice versa
        for meter in self.entity.gravimeters:
            controller = GravimeterController(meter, parent=self)
            self.meters.appendRow(controller)

        for flight in self.entity.flights:
            controller = FlightController(flight, project=self)
            self.flights.appendRow(controller)

        self._bindings = [
            ('addAction', ('Set Project Name', self.set_name)),
            ('addAction', ('Show in Explorer',
                           lambda: show_in_explorer(self.path))),
            ('addAction', ('Export', ExportDialog.export_context(self, self.parent_widget))),
            ('addAction', ('Project Properties', self.properties_dlg)),
            ('addAction', ('Close Project', self._close_project))
        ]

        # Experiment - declare underlying properties for UI use
        # dict key is the attr name (use get_attr to retrieve the value)
        # tuple of ( editable: True/False, Validator: QValidator )
        self._fields = {
            'name': (True, QRegExpValidator(QRegExp("[A-Za-z]+.{4,30}"))),
            'uid': (False, None),
            'path': (False, None),
            'description': (True, None),
            'create_date': (False, None),
            'modify_date': (False, None)
        }

    def validator(self, key: str):  # pragma: no cover
        if key in self._fields:
            return self._fields[key][1]
        return None

    def writeable(self, key: str):  # pragma: no cover
        if key in self._fields:
            return self._fields[key][0]
        return True

    @property
    def entity(self) -> AirborneProject:
        return cast(AirborneProject, super().entity)

    @property
    def menu(self):  # pragma: no cover
        return self._bindings

    def clone(self):
        clone = AirborneProjectController(self.entity)
        self.register_clone(clone)
        return clone

    def export(self, recursive=True):
        child_frames = {}
        for child in self.flights.items():
            child_frames[child.get_attr('name')] = child.export()

        return concat(child_frames.values(), keys=child_frames.keys(), sort=True)

    @property
    def children(self) -> Generator[FlightController, None, None]:
        for child in itertools.chain(self.flights.items(), self.meters.items()):
            yield child

    @property
    def fields(self) -> List[str]:
        """Return list of public attribute keys (for UI display)"""
        return list(self._fields.keys())

    @property
    def path(self) -> Path:
        return self.entity.path

    @property
    def hdfpath(self) -> Path:
        return self.entity.path.joinpath("dgpdata.hdf5")

    @property
    def meter_model(self) -> QStandardItemModel:
        return self.meters.internal_model

    @property
    def flight_model(self) -> QStandardItemModel:
        return self.flights.internal_model

    def add_child(self, child: Union[Flight, Gravimeter]) -> Union[FlightController, GravimeterController]:
        if isinstance(child, Flight):
            controller = FlightController(child, project=self)
            self.flights.appendRow(controller)
        elif isinstance(child, Gravimeter):
            controller = GravimeterController(child, parent=self)
            self.meters.appendRow(controller)
        else:
            raise ValueError("{0!r} is not a valid child type for {1.__name__}".format(child, self.__class__))
        self.entity.add_child(child)
        self.update()
        return controller

    def remove_child(self, uid: OID, confirm: bool = True):
        child = self.get_child(uid)
        if child is None:
            self.log.warning(f'UID {uid!s} has no corresponding object in this '
                             f'project')
            raise KeyError(f'{uid!s}')
        if confirm:  # pragma: no cover
            if not confirm_action("Confirm Deletion",
                                  "Are you sure you want to delete {!s}"
                                  .format(child.get_attr('name')),
                                  parent=self.parent_widget):
                return

        child.delete()
        self.entity.remove_child(child.uid)
        self._child_map[child.entity.__class__].removeRow(child.row())
        self.update()

    def get_parent(self) -> ProjectTreeModel:
        return self.model()

    def get_child(self, uid: Union[str, OID]) -> Union[FlightController,
                                                       GravimeterController]:
        return super().get_child(uid)

    def set_active(self, state: bool):
        self._active = bool(state)
        if self._active:
            self.setBackground(QColor(StateColor.ACTIVE.value))
        else:
            self.setBackground(QColor(StateColor.INACTIVE.value))

    @property
    def is_active(self):
        return self._active

    def save(self, to_file=True):
        return self.entity.to_json(indent=2, to_file=to_file)

    def set_name(self):  # pragma: no cover
        new_name = get_input("Set Project Name", "Enter a Project Name",
                             self.entity.name, parent=self.parent_widget)
        if new_name:
            self.set_attr('name', new_name)

    def add_flight_dlg(self):  # pragma: no cover
        dlg = AddFlightDialog(project=self, parent=self.parent_widget)
        return dlg.exec_()

    def add_gravimeter_dlg(self):  # pragma: no cover
        """Launch a Dialog to import a Gravimeter configuration"""
        dlg = AddGravimeterDialog(self, parent=self.parent_widget)
        return dlg.exec_()

    def update(self):  # pragma: no cover
        """Emit an update event from the parent Model, signalling that
        data has been added/removed/modified in the project."""
        self.setText(self.entity.name)
        try:
            self.get_parent().project_mutated(self)
        except AttributeError:
            self.log.warning(f"project {self.get_attr('name')} has no parent")
        super().update()

    def _post_load(self, datafile: DataFile, dataset: IDataSetController,
                   data: DataFrame) -> None:  # pragma: no cover
        """
        This is a slot called upon successful loading of a DataFile by a
        FileLoader Thread.

        Parameters
        ----------
        datafile : :obj:`dgp.core.models.data.DataFile`
            The DataFile reference object to be processed
        data : DataFrame
            The ingested pandas DataFrame to be dumped to the HDF5 store

        """
        if HDF5Manager.save_data(data, datafile, path=self.hdfpath):
            self.log.info("Data imported and saved to HDF5 Store")
        dataset.add_datafile(datafile)
        try:
            self.get_parent().project_mutated(self)
        except AttributeError:
            self.log.warning(f"project {self.get_attr('name')} has no parent")

    def load_file_dlg(self, datatype: DataType = DataType.GRAVITY,
                      flight: FlightController = None,
                      dataset: IDataSetController = None) -> None:  # pragma: no cover
        """
        Project level dialog for importing/loading Gravity or Trajectory data
        files. The Dialog generates a DataFile and a parameter map (dict) which
        is passed along to a FileLoader thread to ingest the raw data-file.
        On completion of the FileLoader, AirborneProjectController._post_load is
        called, which saves the ingested data to the project's HDF5 file, and
        adds the DataFile object to the relevant parent.

        Parameters
        ----------
        datatype : DataType

        flight : IFlightController, optional
            Set the default flight selected when launching the dialog
        dataset : IDataSetController, optional
            Set the default Dataset selected when launching the dialog

        """
        def _on_load(datafile: DataFile, params: dict, parent: IDataSetController):
            if datafile.group is DataType.GRAVITY:
                method = read_at1a
            elif datafile.group is DataType.TRAJECTORY:
                method = import_trajectory
            else:
                self.log.error("Unrecognized data group: " + datafile.group)
                return
            progress_event = ProgressEvent(self.uid, f"Loading "
                                                     f"{datafile.group.value}",
                                           stop=0)
            self.get_parent().progressNotificationRequested.emit(progress_event)
            loader = FileLoader(datafile.source_path, method,
                                parent=self.parent_widget, **params)
            loader.loaded.connect(functools.partial(self._post_load, datafile,
                                                    parent))
            loader.finished.connect(lambda: self.get_parent().progressNotificationRequested.emit(progress_event))
            loader.start()

        dlg = DataImportDialog(self, datatype, parent=self.parent_widget)
        if flight is not None:
            dlg.set_initial_flight(flight)
        dlg.load.connect(_on_load)
        dlg.exec_()

    def properties_dlg(self):  # pragma: no cover
        dlg = ProjectPropertiesDialog(self, parent=self.parent_widget)
        dlg.exec_()

    def _close_project(self):
        try:
            self.get_parent().remove_project(self)
        except AttributeError:
            self.log.warning(f"project {self.get_attr('name')} has no parent")
