#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Time-stamp: <2023-10-26 18:04:55 krylon>
#
# /data/code/python/vox/data.py
# created on 25. 10. 2023
# (c) 2023 Benjamin Walkenhorst
#
# This file is part of the Vox audiobook reader. It is distributed under the
# terms of the GNU General Public License 3. See the file LICENSE for details
# or find a copy online at https://www.gnu.org/licenses/gpl-3.0

"""
vox.data

(c) 2023 Benjamin Walkenhorst
"""


from datetime import datetime


class File:  # pylint: disable-msg=R0902,R0903
    """File represents an audio file."""

    __slots__ = [
        "file_id",
        "program_id",
        "path",
        "title",
        "disc_no",
        "track_no",
        "timestamp",
        "position",
    ]

    file_id: int
    program_id: int
    path: str
    title: str
    disc_no: int
    track_no: int
    timestamp: datetime
    position: int

    def __init__(self, **fields):
        if "file_id" in fields:
            self.file_id = fields["file_id"]
        if "program_id" in fields:
            self.program_id = fields["program_id"]
        if "path" in fields:
            self.path = fields["path"]
        if "title" in fields:
            self.title = fields["title"]
        if "disc_no" in fields:
            self.disc_no = fields["disc_no"]
        if "track_no" in fields:
            self.track_no = fields["track_no"]
        if "timestamp" in fields:
            self.timestamp = fields["timestamp"]
        if "position" in fields:
            self.position = fields["position"]


class Program:  # pylint: disable-msg=R0903
    """Program is an audiobook, a podcast, or another sequence of audio
    files"""

    __slots__ = [
        "program_id",
        "title",
        "last_played",
        "current_file",
    ]

    program_id: int
    title: str
    last_played: datetime
    current_file: int

    def __init__(self, **fields):
        if "program_id" in fields:
            self.program_id = fields["program_id"]
        if "title" in fields:
            self.title = fields["title"]
        if "last_played" in fields:
            self.last_played = fields["last_played"]
        if "current_file" in fields:
            self.current_file = fields["current_file"]

# Local Variables: #
# python-indent: 4 #
# End: #
