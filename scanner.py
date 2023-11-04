#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Time-stamp: <2023-11-04 21:56:21 krylon>
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
import re

from vox import common, database

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


# Local Variables: #
# python-indent: 4 #
# End: #
