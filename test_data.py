#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Time-stamp: <2024-08-05 20:57:45 krylon>
#
# /data/code/python/vox/test_data.py
# created on 26. 10. 2023
# (c) 2023 Benjamin Walkenhorst
#
# This file is part of the Vox audiobook reader. It is distributed under the
# terms of the GNU General Public License 3. See the file LICENSE for details
# or find a copy online at https://www.gnu.org/licenses/gpl-3.0

"""
vox.test_data

(c) 2023 Benjamin Walkenhorst
"""

import unittest
from datetime import datetime
from typing import Any, NamedTuple

from vox.data import File


class FileCreateTestData(NamedTuple):
    """Data for a single test of File creation"""

    args: dict[str, Any]
    expect_error: bool


create_test_cases: list[FileCreateTestData] = [
    FileCreateTestData({}, False),
    FileCreateTestData(
        {
            "file_id": 23,
            "folder_id": 1,
            "program_id": 90,
            "title": "Wer das liest, ist doof",
            "disc_no": 42,
            "timestamp": datetime.now(),
        },
        False),
    FileCreateTestData(
        {
            "file_id": "Karl",
        },
        True,
    ),
    FileCreateTestData(
        {
            "position": -25,
        },
        True,
    ),
]


class FileTest(unittest.TestCase):
    """Test creating and manipulating File objects"""

    def test_create_file(self):
        """Test creating File objects"""
        for c in create_test_cases:  # pylint: disable-msg=C0103
            if c.expect_error:
                with self.assertRaises((AssertionError, ValueError)):
                    t = File(**c.args)  # pylint: disable-msg=C0103
                    self.assertIsNone(t)


# Local Variables: #
# python-indent: 4 #
# End: #
