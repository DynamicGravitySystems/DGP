# -*- coding: utf-8 -*-

import json
from datetime import datetime
from pathlib import Path
from typing import Union, Any

from .oid import OID


class ProjectEncoder(json.JSONEncoder):
    def default(self, o: Any) -> dict:
        print("Serializing object: " + str(o))
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


