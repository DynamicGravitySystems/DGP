# -*- coding: utf-8 -*-
# PyInstaller runtime hook to import 'hidden' pandas cython modules

hiddenimports = [
    'pandas._libs.tslibs.timedeltas',
    'pandas._libs.tslibs.np_datetime',
    'pandas._libs.tslibs.nattype',
    'pandas._libs.skiplist'
]
