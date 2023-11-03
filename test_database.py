#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Time-stamp: <2023-11-03 20:31:36 krylon>
#
# /data/code/python/vox/test_database.py
# created on 03. 11. 2023
# (c) 2023 Benjamin Walkenhorst
#
# This file is part of the Vox audiobook reader. It is distributed under the
# terms of the GNU General Public License 3. See the file LICENSE for details
# or find a copy online at https://www.gnu.org/licenses/gpl-3.0

"""
vox.test_database

(c) 2023 Benjamin Walkenhorst
"""

import os
from datetime import datetime

from krylib import isdir

from vox import common
from vox import database as db

test_root: str = "/tmp/"

if isdir("/data/ram"):
    test_root = "/data/ram"


class DatabaseTest:
    """Test the Database class. Duh."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.folder = os.path.join(test_root,
                                  datetime.now().strftime("memex_test_database_%Y%m%d_%H%M%S"))  # noqa: E501
        common.set_basedir(cls.folder)

    @classmethod
    def tearDownClass(cls) -> None:
        os.system(f"/bin/rm -rf {test_root}")


# Local Variables: #
# python-indent: 4 #
# End: #
