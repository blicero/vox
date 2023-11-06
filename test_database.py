#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Time-stamp: <2023-11-06 20:49:37 krylon>
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
import unittest
from datetime import datetime
from typing import Final

from krylib import isdir

from vox import common, database
from vox.data import File, Folder

TEST_ROOT: str = "/tmp/"

if isdir("/data/ram"):
    TEST_ROOT = "/data/ram"

TST_FOLDER: Final[str] = "/tmp/audio"


class DatabaseTest(unittest.TestCase):
    """Test the Database class. Duh."""

    folder: str
    db: database.Database

    @classmethod
    def setUpClass(cls) -> None:
        stamp = datetime.now()
        folder_name = stamp.strftime("vox_test_database_%Y%m%d_%H%M%S")
        cls.folder = os.path.join(TEST_ROOT,
                                  folder_name)
        common.set_basedir(cls.folder)

    @classmethod
    def tearDownClass(cls) -> None:
        os.system(f"/bin/rm -rf {cls.folder}")

    def test_01_db_open(self) -> None:
        """Test opening the database."""
        try:
            self.__class__.db = database.Database(common.path.db())
        except Exception as e:  # pylint: disable-msg=W0718
            self.fail(f"Failed to open database: {e}")

    def test_02_folder_add(self) -> None:
        """Test adding a Folder"""
        f = Folder(0, TST_FOLDER)
        try:
            self.__class__.db.folder_add(f)
        except Exception as e:  # pylint: disable-msg=W0718
            self.fail(f"Failed to add folder {f.path}: {e}")
        else:
            self.assertIsNotNone(f.folder_id)
            self.assertIsInstance(f.folder_id, int)
            self.assertGreater(f.folder_id, 0)

    def test_03_folder_get_by_path(self) -> None:
        """Test looking up a Folder by the path"""
        try:
            f = self.__class__.db.folder_get_by_path(TST_FOLDER)
        except Exception as e:  # pylint: disable-msg=W0718
            self.fail(f"Failed to look up folder /tmp/audio: {e}")
        else:
            self.assertIsNotNone(f)
            self.assertIsInstance(f, Folder)

    def test_04_folder_get_all(self) -> None:
        """Test loading all Folders"""
        try:
            folders = self.__class__.db.folder_get_all()
        except Exception as e:  # pylint: disable-msg=W0718
            self.fail(f"Failed to load all folders: {e}")
        else:
            self.assertIsNotNone(folders)
            self.assertIsInstance(folders, list)
            self.assertEqual(len(folders), 1)

    def test_05_file_add(self) -> None:
        """Test adding a File"""
        self.maxDiff = None  # pylint: disable-msg=C0103
        folder = self.__class__.db.folder_get_by_path(TST_FOLDER)
        self.assertIsInstance(folder, Folder)
        assert isinstance(folder, Folder)
        files: list[File] = []
        with self.__class__.db:
            for i in range(1, 11):
                f = File(
                    folder_id=folder.folder_id,
                    path=os.path.join(TST_FOLDER, f"audio{i:02d}.mp3"),
                    ord1=0,
                    ord2=i,
                )
                files.append(f)
                try:
                    self.__class__.db.file_add(f)
                except Exception as e:  # pylint: disable-msg=W0718
                    self.fail(f"Cannot add file {f.path} to datbase: {e}")
                else:
                    self.assertIsNotNone(f.file_id)
                    self.assertIsInstance(f.file_id, int)
                    self.assertGreater(f.file_id, 0)

        result = self.__class__.db.file_get_no_program()
        self.assertIsNotNone(result)
        self.assertIsInstance(result, list)
        self.assertEqual(len(result), len(files))


# Local Variables: #
# python-indent: 4 #
# End: #
