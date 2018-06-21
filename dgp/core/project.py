# -*- coding: utf-8 -*-

"""
Project Classes V2
JSON Serializable classes, segregated from the GUI control plane

"""
import json
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Any, Dict, Union

from .oid import OID
from .flight import Flight
from .serialization import ProjectEncoder
from .meter import MeterConfig


class GravityProject:
    def __init__(self, name: str, path: Union[Path, str], description: Optional[str]=None,
                 create_date: Optional[float]=datetime.utcnow().timestamp(), uid: Optional[str]=None, **kwargs):
        self._uid = OID(self, uid)
        self._name = name
        self._path = path
        self._description = description
        self._create_date = datetime.fromtimestamp(create_date)
        self._modify_date = datetime.utcnow()

        self._meter_configs = []  # type: List[MeterConfig]
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
    def meter_configs(self) -> List[MeterConfig]:
        return self._meter_configs

    def add_meter_config(self, config: MeterConfig) -> None:
        self._meter_configs.append(config)
        self._modify()

    def remove_meter_config(self, config_id: str) -> bool:
        pass

    def meter_config(self, config_id: str) -> MeterConfig:
        pass

    def meter_config_count(self) -> int:
        return len(self._meter_configs)

    def __repr__(self):
        return '<%s: %s/%s>' % (self.__class__.__name__, self.name, str(self.path))

    # Attribute setting/access
    # Allow arbitrary attributes to be set on Project objects (metadata, survey parameters etc.)
    def set_attr(self, key: str, value: Union[str, int, float, bool]) -> None:
        """Permit explicit meta-date attributes.
            We don't use the __setattr__ override as it complicates instance
            attribute use within the Class and Sub-classes for no real gain.
        """
        self._attributes[key] = value

    def get_attr(self, key: str) -> Union[str, int, float, bool]:
        """For symmetry of attribute setting/getting"""
        return self[key]

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

    def add_flight(self, flight: Flight):
        self._flights.append(flight)
        self._modify()

    def remove_flight(self, flight_id: OID):
        pass

    def flight(self, flight_id: OID) -> Flight:
        flt_ids = [flt.uid for flt in self._flights]
        index = flt_ids.index(flight_id)
        return self._flights[index]

    @classmethod
    def from_json(cls, json_str: str) -> 'AirborneProject':
        decoded = json.loads(json_str)

        flights = decoded.pop('_flights')
        meters = decoded.pop('_meter_configs')
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
            klass.add_flight(flt)

        for meter in meters:
            mtr = MeterConfig.from_dict(meter)
            klass.add_meter_config(mtr)

        return klass










