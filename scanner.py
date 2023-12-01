#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Time-stamp: <2023-12-01 16:28:38 krylon>
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
from typing import Final

import mutagen

from vox import common, database
from vox.data import File, Folder, Program

AUDIO_PAT: Final[re.Pattern] = \
    re.compile("[.](?:mp3|og[ga]|opus|m4b|aac|flac)", re.I)
DISC_NO_PAT: Final[re.Pattern] = re.compile("(\\d+\\s*/\\s*(\\d+)")


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

            # pylint: disable-msg=R1702
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
                            try:
                                # meta = mutagen.File(full_path)
                                # # album: str = ""

                                # if "title" in meta:
                                #     db_file.title = meta["title"][0]
                                # if "track" in meta:
                                #     db_file.ord2 = int(meta["track"][0])
                                meta = read_tags(full_path)
                                if meta["album"] == "":
                                    db_file.program_id = 0
                                else:
                                    prog = self.db.program_get_by_title(meta["album"])  # noqa: E501
                                    if prog is None:
                                        prog = Program(
                                            title=meta["album"],
                                            creator=meta["artist"],
                                        )
                                        self.db.program_add(prog)
                                        db_file.program_id = prog.program_id

                                db_file.ord1 = int(meta["ord1"])
                                db_file.ord2 = int(meta["ord2"])
                                db_file.title = meta["title"]
                                self.db.file_add(db_file)
                            except Exception as e:  # pylint: disable-msg=W0718
                                self.log.error("Caught exception while handling metadata: %s", e)  # noqa: E501 # pylint: disable-msg=C0301
                            self.db.file_add(db_file)

        self.db.folder_update_scan(folder, datetime.now())

        return folder

    def refresh(self) -> None:
        """Scan all folders in the database."""
        self.log.debug("Update all folders.")
        folders = self.db.folder_get_all()
        for f in folders:
            self.scan(f.path)


def read_tags(path: str) -> dict[str, str]:
    """Attempt to extract metadata from an audio file.

    path is expected to be the full, absolute path.
    """
    meta = mutagen.File(path)
    tags: dict[str, str] = {
        "artist": "",
        "album": "",
        "title": "",
        "ord1": "0",
        "ord2": "0",
    }

    if "artist" in meta:
        tags["artist"] = meta["artist"]
    elif "TPE1" in meta:
        tags["artist"] = meta["TPE1"].text[0]

    if "album" in meta:
        tags["album"] = meta["album"]
    elif "TALB" in meta:
        tags["album"] = meta["TALB"].text[0]
    else:
        tags["album"] = os.path.basename(os.path.dirname(path))

    if "title" in meta:
        tags["title"] = meta["title"]
    elif "TIT2" in meta:
        tags["title"] = meta["TIT2"].text[0]

    if "tracknumber" in meta:
        tags["ord2"] = meta["tracknumber"]
    elif "TRCK" in meta:
        tags["ord2"] = meta["TRCK"].text[0]

    if "discnumber" in meta:
        tags["ord1"] = meta["discnumber"]

    return tags


# Local Variables: #
# python-indent: 4 #
# End: #
