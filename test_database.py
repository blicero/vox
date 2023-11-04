#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Time-stamp: <2023-11-04 18:51:12 krylon>
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
from typing import Final

from krylib import isdir

from vox import common, database
from vox.data import File, Folder

test_root: str = "/tmp/"

if isdir("/data/ram"):
    test_root = "/data/ram"

tst_folder: Final[str] = "/tmp/audio"


class DatabaseTest:
    """Test the Database class. Duh."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.folder = os.path.join(test_root,
                                  datetime.now().strftime("vox_test_database_%Y%m%d_%H%M%S"))  # noqa: E501
        common.set_basedir(cls.folder)

    @classmethod
    def tearDownClass(cls) -> None:
        os.system(f"/bin/rm -rf {test_root}")

    def test_01_db_open(self) -> None:
        try:
            self.__class__.db = database.Database(common.path.db())
        except Exception as e:
            self.fail(f"Failed to open database: {e}")

    def test_02_folder_add(self):
        f = Folder(path=tst_folder)
        try:
            self.__class__.db.folder_add(f)
        except Exception as e:
            self.fail(f"Failed to add folder {f.path}: {e}")
        else:
            self.assertIsNotNone(f.folder_id)
            self.assertIsInstance(f.folder_id, int)
            self.assertGreater(f.folder_id, 0)

    def test_03_folder_get_by_path(self):
        try:
            f = self.__class__.db.folder_get_by_path(tst_folder)
        except Exception as e:
            self.fail(f"Failed to look up folder /tmp/audio: {e}")
        else:
            self.assertIsNotNone(f)
            self.assertIsInstance(f, Folder)

    def test_04_folder_get_all(self):
        try:
            folders = self.__class__.db.folder_get_all()
        except Exception as e:
            self.fail(f"Failed to load all folders: {e}")
        else:
            self.assertIsNotNone(folders)
            self.assertIsInstance(folders, list)
            self.assertIsEqual(len(folders), 1)

    def test_05_file_add(self):
        folder = self.__class__.db.folder_get_by_path(tst_folder)
        files: list[File] = []
        for i in range(1, 11):
            f = File(
                folder_id=folder.folder_id,
                path=os.path.join(tst_folder, f"audio{i:02d}.mp3"),
                ord1=0,
                ord2=i,
            )
            files.append(f)
            try:
                self.__class__.db.file_add(f)
            except Exception as e:
                self.fail(f"Cannot add file {f.path} to datbase: {e}")
            else:
                self.assertIsNotNone(f.file_id)
                self.assertIsInstance(f.file_id, int)
                self.assertIsGreater(f.file_id, 0)


# Local Variables: #
# python-indent: 4 #
# End: #
