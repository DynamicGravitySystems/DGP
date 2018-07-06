# -*- coding: utf-8 -*-
from core.oid import OID
from dgp.core.controllers.controller_interfaces import IBaseController


class BaseController(IBaseController):
    def __init__(self, parent=None):
        super().__init__()

    @property
    def uid(self) -> OID:
        raise NotImplementedError

    @property
    def datamodel(self) -> object:
        raise NotImplementedError

