#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Time-stamp: <2024-08-05 21:06:44 krylon>
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


import os
from datetime import datetime
from typing import Optional, Union


# pylint: disable-msg=R0903
class Folder:
    """A folder that (hopefully) contains audio files"""

    __slots__ = [
        "folder_id",
        "path",
        "last_scan",
    ]

    folder_id: int
    path: str
    last_scan: datetime

    def __init__(self, fid: int, path: str, ts: Union[datetime, int, None] = None) -> None:  # noqa: E501 # pylint: disable-msg=C0301
        self.folder_id = fid
        self.path = path
        if isinstance(ts, datetime):
            self.last_scan = ts
        elif isinstance(ts, int):
            self.last_scan = datetime.fromtimestamp(ts)
        else:
            self.last_scan = datetime.fromtimestamp(0)


class File:  # pylint: disable-msg=R0902,R0903
    """File represents an audio file."""

    __slots__ = [
        "file_id",
        "program_id",
        "folder_id",
        "path",
        "ord1",
        "ord2",
        "title",
        "position",
        "last_played",
        "url",
    ]

    file_id: int
    program_id: Optional[int]
    folder_id: int
    path: str
    ord1: int
    ord2: int
    title: str
    position: int
    last_played: datetime
    url: str

    # pylint: disable-msg=R0912
    def __init__(self, **fields) -> None:
        if "file_id" in fields:
            assert isinstance(fields["file_id"], int)
            self.file_id = fields["file_id"]
        if "program_id" in fields:
            assert isinstance(fields["program_id"], int)
            self.program_id = fields["program_id"]
        else:
            self.program_id = None
        if "folder_id" in fields:
            assert isinstance(fields["folder_id"], int)
            self.folder_id = fields["folder_id"]
        else:
            raise ValueError("Missing field folder_id")
        if "path" in fields:
            assert isinstance(fields["path"], str)
            self.path = fields["path"]
        else:
            raise ValueError("Missing field path")
        if "ord1" in fields:
            assert isinstance(fields["ord1"], int), \
                f'ord1 must be an int, not a {type(fields["ord1"])}'
            self.ord1 = fields["ord1"]
        else:
            self.ord1 = 0
        if "ord2" in fields:
            assert isinstance(fields["ord2"], int), \
                f'ord2 must be an int, not a {type(fields["ord2"])}'
            self.ord2 = fields["ord2"]
        else:
            self.ord2 = 0
        if "title" in fields:
            assert isinstance(fields["title"], str)
            self.title = fields["title"]
        if "position" in fields:
            assert isinstance(fields["position"], int)
            self.position = fields["position"]
        else:
            self.position = 0
        if "last_played" in fields:
            assert isinstance(fields["last_played"], datetime)
            self.last_played = fields["last_played"]
        if "url" in fields:
            assert isinstance(fields["url"], str)
            self.url = fields["url"]

    def display_title(self) -> str:
        """Return the File's title if set or the filename otherwise."""
        if self.title != "":
            return self.title
        return os.path.basename(self.path)


class Program:  # pylint: disable-msg=R0903
    """Program is an audiobook, a podcast, or another sequence of audio

    files
    """

    __slots__ = [
        "program_id",
        "title",
        "creator",
        "url",
        "cover",
        "current_file",
    ]

    program_id: int
    title: str
    creator: str
    current_file: int
    cover: str
    url: str

    def __init__(self, **fields):  # pylint: disable-msg=R0912
        if "program_id" in fields:
            assert isinstance(fields["program_id"], int)
            self.program_id = fields["program_id"]
        else:
            self.program_id = 0
        if "title" in fields:
            assert isinstance(fields["title"], str)
            self.title = fields["title"]
        else:
            self.title = f"Untitled #{self.program_id}"
        if "creator" in fields:
            assert isinstance(fields["creator"], str)
            self.creator = fields["creator"]
        else:
            self.creator = ""
        if "url" in fields:
            assert (fields["url"] is None) or isinstance(fields["url"], str)
            self.url = fields["url"]
        else:
            self.url = ""
        if "cover" in fields:
            self.cover = fields["cover"]
        else:
            self.cover = ""
        if "current_file" in fields:
            assert isinstance(fields["current_file"], int)
            self.current_file = fields["current_file"]
        elif "cur_file" in fields:
            assert isinstance(fields["cur_file"], int)
            self.current_file = fields["cur_file"]
        else:
            self.current_file = -1


class Playlist:
    """A collection of files that are played in sequence"""

    __slots__ = [
        "playlist_id",
        "title",
        "files",
    ]

    playlist_id: int
    title: str
    files: list[File]

    def __init__(self, plid: int, title: str, files: list[File]) -> None:
        self.playlist_id = plid
        self.title = title
        self.files = files


# Local Variables: #
# python-indent: 4 #
# End: #
