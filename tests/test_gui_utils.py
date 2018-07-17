# -*- coding: utf-8 -*-
from pathlib import Path

import dgp.gui.utils as utils


def test_get_project_file(tmpdir):
    _dir = Path(tmpdir)
    # _other_file = _dir.joinpath("abc.json")
    # _other_file.touch()
    _prj_file = _dir.joinpath("dgp.json")
    _prj_file.touch()

    file = utils.get_project_file(_dir)
    assert _prj_file.resolve() == file

