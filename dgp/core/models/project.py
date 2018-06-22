# -*- coding: utf-8 -*-

"""
Project Classes V2
JSON Serializable classes, separated from the GUI control plane

"""
import json
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Any, Dict, Union

from core.oid import OID
from .flight import Flight
from .meter import Gravimeter


class ProjectEncoder(json.JSONEncoder):
    def default(self, o: Any) -> dict:
        r_dict = {'_type': o.__class__.__name__}
        for key, value in o.__dict__.items():
            if isinstance(value, OID) or key == '_uid':
                r_dict[key] = value.base_uuid
            elif isinstance(value, Path):
                r_dict[key] = str(value)
            elif isinstance(value, datetime):
                r_dict[key] = value.timestamp()
            else:
                r_dict[key] = value
        return r_dict


class GravityProject:
    def __init__(self, name: str, path: Union[Path, str], description: Optional[str]=None,
                 create_date: Optional[float]=datetime.utcnow().timestamp(), uid: Optional[str]=None, **kwargs):
        self._uid = OID(self, uid)
        self._name = name
        self._path = path
        self._description = description
        self._create_date = datetime.fromtimestamp(create_date)
        self._modify_date = datetime.utcnow()

        self._gravimeters = []  # type: List[Gravimeter]
        self._attributes = {}  # type: Dict[str, Any]

    @property
    def uid(self) -> OID:
        return self._uid

    @property
    def name(self) -> str:
        return self._name

    @property
    def path(self) -> Path:
        return Path(self._path)

    @property
    def description(self) -> str:
        return self._description

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
        return self._attributes[item]

    def __getitem__(self, item):
        return self._attributes[item]

    # Protected utility methods
    def _modify(self):
        """Set the modify_date to now"""
        self._modify_date = datetime.utcnow()

    # Serialization/De-Serialization methods
    @classmethod
    def from_json(cls, json_str: str) -> 'GravityProject':
        raise NotImplementedError("from_json must be implemented in base class.")

    def to_json(self, indent=None) -> str:
        return json.dumps(self, cls=ProjectEncoder, indent=indent)


class AirborneProject(GravityProject):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._flights = []

    @property
    def flights(self) -> List[Flight]:
        return self._flights

    def add_child(self, child):
        if isinstance(child, Flight):
            self._flights.append(child)
            self._modify()
        else:
            super().add_child(child)

    def get_child(self, child_id: OID):
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

    @classmethod
    def from_json(cls, json_str: str) -> 'AirborneProject':
        decoded = json.loads(json_str)

        flights = decoded.pop('_flights')
        meters = decoded.pop('_gravimeters')
        attrs = decoded.pop('_attributes')

        params = {}
        for key, value in decoded.items():
            param_key = key[1:]  # strip leading underscore
            params[param_key] = value

        klass = cls(**params)
        for key, value in attrs.items():
            klass.set_attr(key, value)

        for flight in flights:
            flt = Flight.from_dict(flight)
            klass.add_child(flt)

        for meter in meters:
            mtr = Gravimeter.from_dict(meter)
            klass.add_child(mtr)

        return klass


class MarineProject(GravityProject):
    @classmethod
    def from_json(cls, json_str: str) -> 'MarineProject':
        pass
