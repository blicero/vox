#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Time-stamp: <2023-11-06 19:14:11 krylon>
#
# /data/code/python/vox/scanner.py
# created on 04. 11. 2023
# (c) 2023 Benjamin Walkenhorst
#
# This file is part of the Vox audiobook reader. It is distributed under the
# terms of the GNU General Public License 3. See the file LICENSE for details
# or find a copy online at https://www.gnu.org/licenses/gpl-3.0

"""
vox.scanner

(c) 2023 Benjamin Walkenhorst
"""


import logging
import os
import os.path
import re
from datetime import datetime

from vox import common, database
from vox.data import File, Folder

AUDIO_PAT: re.Pattern = re.compile("[.](?:mp3|og[ga]|opus|m4b|aac|flac)", re.I)


class Scanner:
    """The Scanner traverses directory trees and attempts to
    spot audio files."""

    __slots__ = [
        "db",
        "log",
    ]

    db: database.Database
    log: logging.Logger

    def __init__(self):
        self.log = common.get_logger("scanner")
        self.db = database.Database(common.path.db())

    def scan(self, path: str) -> Folder:
        """Scan a directory tree"""
        self.log.debug("Scan folder %s", path)

        with self.db:
            folder = self.db.folder_get_by_path(path)
            if folder is None:
                folder = Folder(0, path, datetime.now())
                self.db.folder_add(folder)

            for dirpath, _subfolders, files in os.walk(path):
                for f in files:
                    if AUDIO_PAT.search(f) is not None:
                        full_path: str = os.path.join(dirpath, f)
                        self.log.debug("Found %s", full_path)
                        db_file = self.db.file_get_by_path(full_path)
                        if db_file is None:
                            db_file = File(
                                folder_id=folder.folder_id,
                                path=full_path,
                            )
                            self.db.file_add(db_file)

        self.db.folder_update_scan(folder, datetime.now())

        return folder

    def refresh(self) -> None:
        """Scan all folders in the database."""
        self.log.debug("Update all folders.")
        folders = self.db.folder_get_all()
        for f in folders:
            self.scan(f.path)

# Local Variables: #
# python-indent: 4 #
# End: #
