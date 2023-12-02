#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Time-stamp: <2023-12-02 16:08:31 krylon>
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
import traceback
from datetime import datetime
from typing import Final

import mutagen

from vox import common, database
from vox.data import File, Folder, Program

AUDIO_PAT: Final[re.Pattern] = \
    re.compile("[.](?:mp3|og[ga]|opus|m4b|aac|flac)", re.I)
DISC_NO_PAT: Final[re.Pattern] = re.compile("(\\d+)\\s*/\\s*(\\d+)")


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
                        # self.log.debug("Found %s", full_path)
                        db_file = self.db.file_get_by_path(full_path)

                        if db_file is not None:
                            continue

                        self.log.debug("Found new file %s", full_path)

                        db_file = File(
                            folder_id=folder.folder_id,
                            path=full_path,
                        )
                        try:
                            meta = read_tags(full_path)
                            if len(meta) == 0:
                                continue
                            if meta["album"] == "":
                                db_file.program_id = 0
                            else:
                                prog = self.db.program_get_by_title(meta["album"])  # noqa: E501
                                if prog is None:
                                    prog = Program(
                                        title=meta["album"],
                                        creator=meta["artist"],
                                        url="",
                                    )
                                    self.db.program_add(prog)
                                    assert prog.program_id > 0
                                db_file.program_id = prog.program_id

                            db_file.ord1 = int(meta["ord1"])
                            db_file.ord2 = int(meta["ord2"])
                            db_file.title = meta["title"]
                            self.db.file_add(db_file)
                        except Exception as e:  # pylint: disable-msg=W0718
                            self.log.error("Caught exception while handling metadata: %s", e)  # noqa: E501 # pylint: disable-msg=C0301
                            traceback.print_tb(e.__traceback__)

        self.db.folder_update_scan(folder, datetime.now())

        return folder

    def refresh(self) -> None:
        """Scan all folders in the database."""
        self.log.debug("Update all folders.")
        folders = self.db.folder_get_all()
        for f in folders:
            self.scan(f.path)


# pylint: disable-msg=R0912
def read_tags(path: str) -> dict[str, str]:
    """Attempt to extract metadata from an audio file.

    path is expected to be the full, absolute path.
    """
    try:
        meta = mutagen.File(path)
    except mutagen.MutagenError:
        return {}

    tags: dict[str, str] = {
        "artist": "",
        "album": "",
        "title": "",
        "ord1": "0",
        "ord2": "0",
    }

    if "artist" in meta:
        tags["artist"] = meta["artist"][0]
    elif "TPE1" in meta:
        tags["artist"] = meta["TPE1"].text[0]

    if "album" in meta:
        tags["album"] = meta["album"][0]
    elif "TALB" in meta:
        tags["album"] = meta["TALB"].text[0]
    else:
        tags["album"] = os.path.basename(os.path.dirname(path))

    if "title" in meta:
        tags["title"] = meta["title"][0]
    elif "TIT2" in meta:
        tags["title"] = meta["TIT2"].text[0]

    if "tracknumber" in meta:
        tags["ord2"] = meta["tracknumber"][0]
    elif "TRCK" in meta:
        tags["ord2"] = meta["TRCK"].text[0]

    if "discnumber" in meta:
        tags["ord1"] = meta["discnumber"][0]

    m1 = DISC_NO_PAT.search(tags["ord1"])
    if m1 is not None:
        tags["ord1"] = m1[1]

    m2 = DISC_NO_PAT.search(tags["ord2"])
    if m2 is not None:
        tags["ord2"] = m2[1]

    return tags


def scan(folder: str) -> None:
    """Instantiate a Scanner to scan a single directory tree.

    I'll use this for testing and debugging mainly."""
    s: Scanner = Scanner()
    s.scan(folder)


# Local Variables: #
# python-indent: 4 #
# End: #
