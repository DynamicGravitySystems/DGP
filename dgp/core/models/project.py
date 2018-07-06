# -*- coding: utf-8 -*-

"""
Project Classes V2
JSON Serializable classes, separated from the GUI control plane
"""

import json
import json.decoder
import datetime
from pathlib import Path
from pprint import pprint
from typing import Optional, List, Any, Dict, Union

from dgp.core.oid import OID
from .flight import Flight, FlightLine, DataFile
from .meter import Gravimeter

PROJECT_FILE_NAME = 'dgp.json'
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

    The parent/_parent attribute is another special case in the
    Serialization/De-serialization of the project. A parent can be set
    on any project child object (Flight, FlightLine, DataFile, Gravimeter etc.)
    which is simply a reference to the object that contains it within the hierarchy.
    As this creates a circular reference, for any _parent attribute of a project
    entity, the parent's OID is instead serialized - which allows us to recreate
    the structure upon decoding with :obj:`ProjectDecoder`
    """

    def default(self, o: Any):
        if isinstance(o, (AirborneProject, *project_entities.values())):
            keys = o.__slots__ if hasattr(o, '__slots__') else o.__dict__.keys()
            attrs = {key.lstrip('_'): getattr(o, key) for key in keys}
            attrs['_type'] = o.__class__.__name__
            if 'parent' in attrs:
                # Serialize the UID of the parent, not the parent itself (circular-reference)
                attrs['parent'] = getattr(attrs['parent'], 'uid', None)
            return attrs
        j_complex = {'_type': o.__class__.__name__}
        if isinstance(o, OID):
            j_complex['base_uuid'] = o.base_uuid
            return j_complex
        if isinstance(o, datetime.datetime):
            j_complex['timestamp'] = o.timestamp()
            return j_complex
        if isinstance(o, datetime.date):
            j_complex['ordinal'] = o.toordinal()
            return j_complex
        if isinstance(o, Path):
            # Path requires special handling due to OS dependant internal classes
            return {'_type': 'Path', 'path': str(o.resolve())}

        return super().default(o)


class ProjectDecoder(json.JSONDecoder):
    """
    ProjectDecoder is a custom JSONDecoder object which enables us to de-serialize
    circular references. This is useful in our case as the gravity projects are
    represented in a tree-type hierarchy. Objects in the tree keep a reference to
    their parent to facilitate a variety of actions.

    The :obj:`ProjectEncoder` serializes any references with the key '_parent' into
    a serialized OID type.

    All project entities are decoded and a reference is stored in an internal registry
    to facilitate the re-linking of parent/child entities after decoding is complete.

    The decoder (this class), will then inspect each object passed to its object_hook
    for a 'parent' attribute (leading _ are stripped); objects with a parent attribute
    are added to an internal map, mapping the child's UID to the parent's UID.

    A second pass is made over the decoded project structure due to the way the
    JSON is decoded (depth-first), such that the deepest nested children will contain
    references to a parent object which has not been decoded yet.
    This allows us to store only a single canonical serialized representation of the
    parent objects in the hierarchy, and then assemble the references after the fact.
    """

    def __init__(self, klass):
        super().__init__(object_hook=self.object_hook)
        self._registry = {}
        self._child_parent_map = {}
        self._klass = klass

    def decode(self, s, _w=json.decoder.WHITESPACE.match):
        decoded = super().decode(s)
        # Re-link parents & children
        for child_uid, parent_uid in self._child_parent_map.items():
            child = self._registry[child_uid]
            child.set_parent(self._registry.get(parent_uid, None))

        return decoded

    def object_hook(self, json_o: dict):
        """Object Hook in json.load will iterate upwards from the deepest
        nested JSON object (dictionary), calling this hook on each, then passing
        the result up to the next level object.
        Thus we can re-assemble the entire Project hierarchy given that all classes
        can be created via their __init__ methods
        (i.e. must accept passing child objects through a parameter)

        The _type attribute is expected (and injected during serialization), for any
        custom objects which should be processed by the project_hook

        The type of the current project class (or sub-class) is injected into
        the class map which allows for this object hook to be utilized by any
        inheritor without modification.

        """
        if '_type' not in json_o:
            return json_o
        _type = json_o.pop('_type')

        if 'parent' in json_o:
            parent = json_o.pop('parent')  # type: OID
        else:
            parent = None

        params = {key.lstrip('_'): value for key, value in json_o.items()}
        if _type == OID.__name__:
            return OID(**params)
        elif _type == datetime.datetime.__name__:
            return datetime.datetime.fromtimestamp(*params.values())
        elif _type == datetime.date.__name__:
            return datetime.date.fromordinal(*params.values())
        elif _type == Path.__name__:
            return Path(*params.values())
        else:
            # Handle project entity types
            klass = {self._klass.__name__: self._klass, **project_entities}.get(_type, None)
        if klass is None:  # pragma: no cover
            raise AttributeError("Unhandled class %s in JSON data. Class is not defined"
                                 " in entity map." % _type)
        instance = klass(**params)
        if parent is not None:
            self._child_parent_map[instance.uid] = parent
        self._registry[instance.uid] = instance
        return instance


class GravityProject:
    def __init__(self, name: str, path: Union[Path], description: Optional[str] = None,
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
        self._attributes = kwargs.get('attributes', {})  # type: Dict[str, Any]

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
        return '<%s: %s/%s>' % (self.__class__.__name__, self.name, str(self.path))

    # TODO: Are these useful, or just fluff that should be removed
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
        print("Updating project modify time")
        self._modify_date = datetime.datetime.utcnow()

    # Serialization/De-Serialization methods
    @classmethod
    def from_json(cls, json_str: str) -> 'GravityProject':
        return json.loads(json_str, cls=ProjectDecoder, klass=cls)

    def to_json(self, to_file=False, indent=None) -> Union[str, bool]:
        # TODO: Dump file to a temp file, then if successful overwrite the original
        # Else an error in the serialization process can corrupt the entire project
        if to_file:
            try:
                with self.path.joinpath(self._projectfile).open('w') as fp:
                    json.dump(self, fp, cls=ProjectEncoder, indent=indent)
            except IOError:
                raise
            else:
                # pprint(json.dumps(self, cls=ProjectEncoder, indent=2))
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
        child.set_parent(self)

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
