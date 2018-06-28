# -*- coding: utf-8 -*-

"""
Project Classes V2
JSON Serializable classes, separated from the GUI control plane

"""
import json
from datetime import datetime
from pathlib import Path
from pprint import pprint
from typing import Optional, List, Any, Dict, Union

from dgp.core.oid import OID
from dgp.core.models.flight import Flight, FlightLine, DataFile
from dgp.core.models.meter import Gravimeter

project_entities = {'Flight': Flight, 'FlightLine': FlightLine, 'DataFile': DataFile,
                    'Gravimeter': Gravimeter}


class ProjectEncoder(json.JSONEncoder):
    """
    The ProjectEncoder allows complex project objects to be encoded into
    a standard JSON representation.
    Classes are matched and encoded by type, with Project class instances
    defined in the project_entities module variable.
    Project classes simply have their __slots__ or __dict__ mapped to a JSON
    object (Dictionary), with any recognized complex objects within the class
    iteratively encoded by the encoder.

    A select number of other 'complex' objects are also capable of being
    encoded by this encoder, such as OID's, datetimes, and pathlib.Path objects.
    An _type variable is inserted into the JSON output, and used by the decoder
    to determine how to decode and reconstruct the object into a Python native
    object.

    """

    def default(self, o: Any):
        if isinstance(o, (AirborneProject, *project_entities.values())):
            keys = o.__slots__ if hasattr(o, '__slots__') else o.__dict__.keys()
            attrs = {key.lstrip('_'): getattr(o, key) for key in keys}
            attrs['_type'] = o.__class__.__name__
            return attrs
        if isinstance(o, OID):
            return {'_type': OID.__name__, 'base_uuid': o.base_uuid}
        if isinstance(o, Path):
            return {'_type': Path.__name__, 'path': str(o.resolve())}
        if isinstance(o, datetime):
            return {'_type': datetime.__name__, 'timestamp': o.timestamp()}

        return super().default(o)


class GravityProject:
    def __init__(self, name: str, path: Union[Path, str], description: Optional[str] = None,
                 create_date: Optional[datetime] = None, modify_date: Optional[datetime] = None,
                 uid: Optional[str] = None, **kwargs):
        self._uid = uid or OID(self, tag=name)
        self._uid.set_pointer(self)
        self._name = name
        self._path = path
        self._projectfile = 'dgp.json'
        self._description = description
        self._create_date = create_date or datetime.utcnow()
        self._modify_date = modify_date or self._create_date

        self._gravimeters = kwargs.get('gravimeters', [])  # type: List[Gravimeter]
        self._attributes = kwargs.get('attributes', {})  # type: Dict[str, Any]

    @property
    def uid(self) -> OID:
        return self._uid

    @property
    def name(self) -> str:
        return self._name

    @name.setter
    def name(self, value: str) -> None:
        self._name = value.strip()
        self._modify()

    @property
    def path(self) -> Path:
        return Path(self._path)

    @property
    def description(self) -> str:
        return self._description

    @description.setter
    def description(self, value: str):
        self._description = value.strip()
        self._modify()

    @property
    def creation_time(self) -> datetime:
        return self._create_date

    @property
    def modify_time(self) -> datetime:
        return self._modify_date

    @property
    def gravimeters(self) -> List[Gravimeter]:
        return self._gravimeters

    def get_child(self, child_id: OID):
        return [meter for meter in self._gravimeters if meter.uid == child_id][0]

    def add_child(self, child) -> None:
        if isinstance(child, Gravimeter):
            self._gravimeters.append(child)
            self._modify()
        else:
            print("Invalid child: " + str(type(child)))

    def remove_child(self, child_id: OID) -> bool:
        child = child_id.reference  # type: Gravimeter
        if child in self._gravimeters:
            self._gravimeters.remove(child)
            return True
        return False

    def __repr__(self):
        return '<%s: %s/%s>' % (self.__class__.__name__, self.name, str(self.path))

    def set_attr(self, key: str, value: Union[str, int, float, bool]) -> None:
        """Permit explicit meta-date attributes.
            We don't use the __setattr__ override as it complicates instance
            attribute use within the Class and Sub-classes for no real gain.
        """
        self._attributes[key] = value

    def get_attr(self, key: str) -> Union[str, int, float, bool]:
        """For symmetry with set_attr"""
        return self._attributes[key]

    def __getattr__(self, item):
        # Intercept attribute calls that don't exist - proxy to _attributes
        try:
            return self._attributes[item]
        except KeyError:
            # hasattr/getattr expect an AttributeError if attribute doesn't exist
            raise AttributeError

    def __getitem__(self, item):
        return self._attributes[item]

    # Protected utility methods
    def _modify(self):
        """Set the modify_date to now"""
        self._modify_date = datetime.utcnow()

    # Serialization/De-Serialization methods
    @classmethod
    def object_hook(cls, json_o: Dict):
        """Object Hook in json.load will iterate upwards from the deepest
        nested JSON object (dictionary), calling this hook on each, then passing
        the result up to the next level object.
        Thus we can re-assemble the entire
        Project hierarchy given that all classes can be created via their __init__
        methods (i.e. must accept passing child objects through a parameter)

        The _type attribute is expected (and injected during serialization), for any
        custom objects which should be processed by the project_hook

        The type of the current project class (or sub-class) is injected into
        the class map which allows for this object hook to be utilized by any
        inheritor without modification.
        """
        if '_type' not in json_o:
            return json_o

        _type = json_o.pop('_type')
        params = {key.lstrip('_'): value for key, value in json_o.items()}
        if _type == cls.__name__:
            return cls(**params)
        elif _type == OID.__name__:
            return OID(**params)
        elif _type == datetime.__name__:
            return datetime.fromtimestamp(*params.values())
        elif _type == Path.__name__:
            return Path(*params.values())
        else:
            klass = project_entities.get(_type, None)
        if klass is None:
            raise AttributeError("Unhandled class %s in JSON data. Class is not defined"
                                 " in class map." % _type)
        return klass(**params)

    @classmethod
    def from_json(cls, json_str: str) -> 'GravityProject':
        return json.loads(json_str, object_hook=cls.object_hook)

    def to_json(self, to_file=False, indent=None) -> Union[str, bool]:
        if to_file:
            try:
                with self.path.joinpath(self._projectfile).open('w') as fp:
                    json.dump(self, fp, cls=ProjectEncoder, indent=indent)
            except IOError:
                raise
            else:
                pprint(json.dumps(self, cls=ProjectEncoder, indent=2))
                return True
        return json.dumps(self, cls=ProjectEncoder, indent=indent)


class AirborneProject(GravityProject):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._flights = kwargs.get('flights', [])

    @property
    def flights(self) -> List[Flight]:
        return self._flights

    def add_child(self, child):
        if isinstance(child, Flight):
            self._flights.append(child)
            self._modify()
        else:
            super().add_child(child)

    def get_child(self, child_id: OID) -> Union[Flight, Gravimeter]:
        try:
            return [flt for flt in self._flights if flt.uid == child_id][0]
        except IndexError:
            return super().get_child(child_id)

    def remove_child(self, child_id: OID) -> bool:
        if child_id.reference in self._flights:
            self._flights.remove(child_id.reference)
            return True
        else:
            return super().remove_child(child_id)


class MarineProject(GravityProject):
    pass
