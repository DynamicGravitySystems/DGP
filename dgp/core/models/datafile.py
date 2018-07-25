# -*- encoding: utf-8 -*-
from datetime import datetime
from pathlib import Path
from typing import Optional

from dgp.core.oid import OID


class DataFile:
    """The DataFile is a model reference object which maintains the path and
    identifier for an entity stored in a project's HDF5 file database.

    In addition to storing the HDF5 Node Path, the DataFile maintains some
    meta-data attributes such as the date associated with the file, its original
    absolute path on the file-system where it was imported, the data
    column-format used to import the data, and the name of the file.

    The reason why the DataFile does not provide any direct access to the data
    it references is due to the nature of the project structure. The HDF5 data
    file is assumed to contain many data entities, and is maintained by the base
    project. To avoid passing references to the HDF5 file throughout the project
    hierarchy, we delegate the loading of data to a higher level controller,
    which simply uses the :class:`DataFile` as the address.

    """
    __slots__ = ('uid', 'date', 'name', 'group', 'source_path',
                 'column_format')

    def __init__(self, group: str, date: datetime, source_path: Path,
                 name: Optional[str] = None, column_format=None,
                 uid: Optional[OID] = None):
        self.uid = uid or OID(self)
        self.uid.set_pointer(self)
        self.group = group.lower()
        self.date = date
        self.source_path = Path(source_path)
        self.name = name or self.source_path.name
        self.column_format = column_format

    @property
    def label(self) -> str:
        return f'[{self.group}] {self.name}'

    @property
    def nodepath(self) -> str:
        """Returns the HDF5 Node where the data associated with this
        DataFile is stored within the project's HDF5 file.

        Notes
        -----
        An underscore (_) is prepended to the parent and uid ID's to avoid the
        NaturalNameWarning generated if the UID begins with a number.
        """
        return f'/{self.group}/_{self.uid.base_uuid}'

    def __str__(self):
        return f'({self.group}) :: {self.nodepath}'

    def __hash__(self):
        return hash(self.uid)


