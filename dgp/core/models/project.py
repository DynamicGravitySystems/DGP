# -*- coding: utf-8 -*-
import json
import json.decoder
import datetime
import warnings
from pathlib import Path
from typing import Optional, List, Any, Dict, Union, Tuple, Callable

from dgp.core import DataType
from dgp.core.types.reference import Reference
from dgp.core.oid import OID
from .flight import Flight
from .meter import Gravimeter
from .dataset import DataSet, DataSegment
from .datafile import DataFile

PROJECT_FILE_NAME = 'dgp.json'
project_entities = {'Flight': Flight,
                    'DataSet': DataSet,
                    'DataFile': DataFile,
                    'DataSegment': DataSegment,
                    'Gravimeter': Gravimeter}

ObjectTransform = Tuple[str, Callable[[object], str]]

# Declare object -> serialized value transforms
object_value_map: Dict[object, ObjectTransform] = {
    OID: ('base_uuid', lambda o: o.base_uuid),
    datetime.datetime: ('timestamp', lambda o: o.timestamp()),
    datetime.date: ('ordinal', lambda o: o.toordinal()),
    Path: ('path', lambda o: f'{o.resolve()!s}'),
    DataType: ('value', lambda o: o.value)
}

# Declare serialized value -> object transforms
value_object_map: Dict[str, Callable[[Dict], str]] = {
    OID.__name__: lambda x: OID(**x),
    datetime.datetime.__name__: lambda x: datetime.datetime.fromtimestamp(*x.values()),
    datetime.date.__name__: lambda x: datetime.date.fromordinal(*x.values()),
    Path.__name__: lambda x: Path(*x.values()),
    DataType.__name__: lambda x: DataType(**x)
}


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

    The object_value_map is used to declare various types and their serialization
    method (a lambda function). This provides an extensible way to add new types
    to the projects serialization process. Note that the inverse
    (de-serialization) declaration should also be added to the value_object_map
    when adding any new type.

    The :class:`Reference` object is a special case; project model objects may
    utilize the Reference class to maintain links to a parent or other related
    model object. The Project Encoder/Decoders identify Reference objects and
    serialize the metadata of the Reference in order to facilitate re-linking
    during de-serialization.

    """

    def default(self, o: Any):
        if isinstance(o, (AirborneProject, *project_entities.values())):
            keys = o.__slots__ if hasattr(o, '__slots__') else o.__dict__.keys()
            attrs = {key.lstrip('_'): getattr(o, key) for key in keys}
            attrs['_type'] = o.__class__.__name__
            attrs['_module'] = o.__class__.__module__
            return attrs
        json_str = {'_type': o.__class__.__name__,
                    '_module': o.__class__.__module__}
        if o.__class__ in object_value_map:
            attr, serializer = object_value_map[o.__class__]
            json_str[attr] = serializer(o)
            return json_str
        elif isinstance(o, Path):
            # Path requires special handling due to OS dependant class names
            json_str['_type'] = 'Path'
            json_str['path'] = str(o.resolve())
            return json_str
        elif isinstance(o, Reference):
            # Reference is a special case, as it can return None
            return o.serialize()

        return super().default(o)


JsonRef = Tuple[str, str, str]


class ProjectDecoder(json.JSONDecoder):
    """
    ProjectDecoder is a custom JSONDecoder object which enables us to de-serialize
    circular references. This is useful in our case as the gravity projects are
    represented in a tree-type hierarchy. Objects in the tree keep a reference to
    their parent to facilitate a variety of actions.

    All project entities are decoded and a reference is stored in an internal
    registry (keyed by UID) to facilitate the re-linking of :class:`Reference`
    entities after decoding is complete.

    A second pass is made over the decoded project structure due to the way the
    JSON is decoded (depth-first), such that the deepest nested children may
    contain references to a parent object which has not been decoded yet.
    This allows us to store only a single canonical serialized representation of
    the parent objects in the hierarchy, and then assemble the references after
    the fact.

    """

    def __init__(self, klass):
        super().__init__(object_hook=self.object_hook)
        self._registry = {}
        self._references: List[JsonRef] = []
        self._klass = klass

    def decode(self, s, _w=json.decoder.WHITESPACE.match):
        decoded = super().decode(s)
        # Re-link References
        for parent_uid, attr, child_uid in self._references:
            parent = self._registry[parent_uid]
            child = self._registry[child_uid]
            setattr(parent, attr, child)

        return decoded

    def object_hook(self, json_o: dict):
        """Object Hook in json.load will iterate upwards from the deepest
        nested JSON object (dictionary), calling this hook on each, then passing
        the result up to the next level object.
        Thus we can re-assemble the entire Project hierarchy given that all classes
        can be created via their __init__ methods
        (i.e. they must accept passing child objects through a parameter)

        The _type attribute is expected (and injected during serialization), for
        any custom objects which should be processed by the project_hook.

        The type of the current project class (or sub-class) is injected into
        the class map which allows for this object hook to be utilized by any
        inheritor without modification.

        The value_object_map dictionary is used to define custom de-serialization
        routines for specific objects in a declarative fashion. This is due to
        the non-uniform way in which various objects are serialized and
        de-serialized.
        For example a :obj:`datetime` object's serial representation is its float
        'timestamp' value. In order to reconstruct the datetime object we must
        call datetime.fromtimestamp(ts). Thus we need some object specific
        declarations to de-serialize certain types.

        """
        if '_type' not in json_o:
            # JSON objects without _type are interpreted as Python dictionaries
            return json_o
        _type = json_o.pop('_type')
        try:
            _module = json_o.pop('_module')
        except KeyError:
            _module = None

        params = {key.lstrip('_'): value for key, value in json_o.items()}
        if _type in value_object_map:
            factory = value_object_map[_type]
            return factory(params)
        elif _type == Reference.__name__:
            # References are a special case, None is returned as an interim val
            self._references.append((json_o['parent'], json_o['attr'], json_o['ref']))
            return None
        else:
            # Handle project entity types (also inject the Project sub-class)
            klass = {self._klass.__name__: self._klass, **project_entities}.get(_type, None)
        if klass is None:  # pragma: no cover
            raise AttributeError(f"Unhandled class {_type} in JSON data. Class is not defined"
                                 f" in entity map.")
        else:
            try:
                instance = klass(**params)
                self._registry[instance.uid] = instance
                return instance
            except TypeError:  # pragma: no cover
                # This may occur if an outdated project JSON file is loaded
                print(f'Exception instantiating class {klass} with params {params}')
                raise


class GravityProject:
    """GravityProject base class.

    This class is not designed to be instantiated directly, but is used
    as the common base-class for Airborne Gravity Projects, and in future Marine
    Gravity Projects.

    This base class stores common attributes such as the Project name,
    description, path, and Gravimeters (which all Gravity Projects may use).

    Modification time is tracked on the project, and any mutations made via
    properties in this class will update the modify time.

    The GravityProject class also provides the utility to_json/from_json methods
    which should work with any child classes. The JSON serialization methods
    simply call the appropriate :class:`ProjectEncoder` or
    :class:`ProjectDecoder` to serialize/de-serialize the project respectively.

    Parameters
    ----------
    name : str
        Name of the project
    path : :class:`Path`
        Directory path where the project is located
    description : str, optional
        Optional, description for the project
    create_date : :class:`datetime`, optional
        Specify creation date of the project, current UTC time is used if None
    modify_date : :class:`datetime`, optional
        This parameter should be used only during the de-serialization process,
        otherwise the modification date is automatically handled by the class
        properties.

    See Also
    --------
    :class:`AirborneProject`

    """

    def __init__(self, name: str, path: Path, description: Optional[str] = None,
                 create_date: Optional[datetime.datetime] = None,
                 modify_date: Optional[datetime.datetime] = None,
                 uid: Optional[str] = None, **kwargs):
        self.uid = uid or OID(self, tag=name)
        self.uid.set_pointer(self)
        self._name = name
        self._path = path
        self._projectfile = PROJECT_FILE_NAME
        self._description = description or ""
        self.create_date = create_date or datetime.datetime.utcnow()
        self.modify_date = modify_date or datetime.datetime.utcnow()

        self._gravimeters = kwargs.get('gravimeters', [])  # type: List[Gravimeter]

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

    @path.setter
    def path(self, value: str) -> None:
        self._path = Path(value)
        self._modify()

    @property
    def description(self) -> str:
        return self._description

    @description.setter
    def description(self, value: str):
        self._description = value.strip()
        self._modify()

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
            raise TypeError("Invalid child type: {!r}".format(child))

    def remove_child(self, child_id: OID) -> bool:
        child = child_id.reference  # type: Gravimeter
        if child in self._gravimeters:
            self._gravimeters.remove(child)
            return True
        return False

    def __repr__(self):
        return f'<{self.__class__.__name__}: {self.name}/{self.path!s}>'

    # Protected utility methods
    def _modify(self):
        """Set the modify_date to now"""
        self._modify_date = datetime.datetime.utcnow()

    # Serialization/De-Serialization methods
    @classmethod
    def from_json(cls, json_str: str) -> 'GravityProject':
        return json.loads(json_str, cls=ProjectDecoder, klass=cls)

    def to_json(self, to_file=False, indent=None) -> Union[str, bool]:
        """Encode the Project to a JSON string, optionally writing to disk

        This function will perform the json encoding operation and store the
        result in memory before writing the result to the project file
        (if to_file is True), this should prevent corruption of the project file
        in cases where the JSON encoder fails partway through the serialization,
        leaving the output file in an inconsistent state.

        Parameters
        ----------
        to_file : bool, optional
            If False the JSON string will be returned to the caller
            If True the JSON string will be written to the project file
        indent : None, int, optional
            Optionally provide an indent value to nicely format the JSON output
        """
        try:
            json_s = json.dumps(self, cls=ProjectEncoder, indent=indent)
        except TypeError as e:
            warnings.warn(f"Unable to encode project: {e!s}")
            return False

        if to_file:
            with self.path.joinpath(self._projectfile).open('w') as fp:
                fp.write(json_s)
            return True
        else:
            return json_s


class AirborneProject(GravityProject):
    """AirborneProject class

    This class is a sub-class of :class:`GravityProject` and simply extends the
    functionality of the base GravityProject, allowing the addition/removal
    of :class:`Flight` objects, in addition to :class:`Gravimeter`s

    Parameters
    ----------
    kwargs
        See :class:`GravityProject` for permitted key-word arguments.

    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._flights = kwargs.get('flights', [])
        for flight in self._flights:
            flight.parent = self

    @property
    def flights(self) -> List[Flight]:
        return self._flights

    def add_child(self, child):
        if isinstance(child, Flight):
            self._flights.append(child)
            self._modify()
        else:
            super().add_child(child)
        child.parent = self

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
