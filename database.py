#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Time-stamp: <2023-11-27 23:35:05 krylon>
#
# /data/code/python/vox/database.py
# created on 28. 10. 2023
# (c) 2023 Benjamin Walkenhorst
#
# This file is part of the Vox audiobook reader. It is distributed under the
# terms of the GNU General Public License 3. See the file LICENSE for details
# or find a copy online at https://www.gnu.org/licenses/gpl-3.0

"""
vox.database

(c) 2023 Benjamin Walkenhorst
"""

import logging
import sqlite3
import threading
from datetime import datetime
from enum import Enum, auto
from typing import Final, Optional, Union

import krylib

from vox import common
from vox.data import File, Folder, Program

INIT_QUERIES: Final[list[str]] = [
    """
    CREATE TABLE folder (
        id		INTEGER PRIMARY KEY,
        path		TEXT UNIQUE NOT NULL,
        last_scan       INTEGER NOT NULL DEFAULT 0,
        CHECK (path LIKE '/%')
    ) STRICT
    """,

    """
CREATE TABLE program (
    id                   INTEGER PRIMARY KEY,
    title                TEXT UNIQUE NOT NULL,
    creator              TEXT NOT NULL DEFAULT '',
    url                  TEXT NOT NULL DEFAULT '',
    cur_file             INTEGER NOT NULL DEFAULT -1
) STRICT
    """,
    "CREATE UNIQUE INDEX prog_title_idx ON program (title)",
    "CREATE INDEX prog_creator_idx ON program (creator)",

    """
CREATE TABLE file (
    id                   INTEGER PRIMARY KEY,
    program_id           INTEGER,
    folder_id            INTEGER NOT NULL,
    path                 TEXT UNIQUE NOT NULL,
    ord1                 INTEGER NOT NULL DEFAULT 0,
    ord2                 INTEGER NOT NULL DEFAULT 0,
    title                TEXT NOT NULL DEFAULT '',
    position             INTEGER NOT NULL DEFAULT 0,
    last_played          INTEGER NOT NULL DEFAULT 0,
    url                  TEXT,
    FOREIGN KEY (program_id) REFERENCES program (id)
        ON DELETE CASCADE
        ON UPDATE RESTRICT,
    FOREIGN KEY (folder_id) REFERENCES folder (id)
        ON DELETE CASCADE
        ON UPDATE RESTRICT
) STRICT
    """,
    "CREATE INDEX file_prog_idx ON file (program_id)",
    "CREATE INDEX file_path_idx ON file (path)",
    "CREATE INDEX file_title_idx ON file (title)",
    "CREATE INDEX file_ord_index ON file (ord1, ord2)",

    """
 CREATE TABLE playlist (
    id INTEGER PRIMARY KEY,
    title TEXT UNIQUE NOT NULL
) STRICT
    """,

    """
CREATE TABLE playlist_entry (
    id INTEGER PRIMARY KEY,
    playlist_id INTEGER NOT NULL,
    file_id INTEGER NOT NULL,
    trackno INTEGER NOT NULL,
    UNIQUE (playlist_id, file_id),
    CHECK (trackno > 0)
) STRICT
""",
]

OPEN_LOCK: Final[threading.Lock] = threading.Lock()


# pylint: disable-msg=C0103,R0904
class QueryID(Enum):
    """Provides symbolic constants for database queries"""
    ProgramAdd = auto()
    ProgramDel = auto()
    ProgramGetAll = auto()
    ProgramGetByID = auto()
    ProgramGetByTitle = auto()
    ProgramSetTitle = auto()
    ProgramSetURL = auto()
    ProgramSetCreator = auto()
    ProgramSetCurFile = auto()
    FileAdd = auto()
    FileDel = auto()
    FileGetByID = auto()
    FileGetByPath = auto()
    FileGetByFolder = auto()
    FileGetByProgram = auto()
    FileGetNoProgram = auto()
    FileSetTitle = auto()
    FileSetPosition = auto()
    FileSetProgram = auto()
    FileSetOrd = auto()
    FolderAdd = auto()
    FolderGetAll = auto()
    FolderGetByPath = auto()
    FolderGetByID = auto()
    FolderUpdateScan = auto()


db_queries: Final[dict[QueryID, str]] = {
    QueryID.ProgramAdd:        """
    INSERT INTO program (title, creator, url)
                 VALUES (?,     ?,         ?)
    RETURNING id
    """,
    QueryID.ProgramDel:        "DELETE FROM program WHERE id = ?",
    QueryID.ProgramGetAll:     """
    SELECT
        id,
        title,
        creator,
        url,
        cur_file
    FROM program""",
    QueryID.ProgramGetByID:    """
    SELECT
        title,
        creator,
        url,
        cur_file
    FROM program
    WHERE id = ?""",
    QueryID.ProgramGetByTitle: """
    SELECT
        id,
        creator,
        url,
        cur_file
    FROM program
    WHERE title = ?""",
    QueryID.ProgramSetTitle:   "UPDATE program SET title = ? WHERE id = ?",
    QueryID.ProgramSetCreator: "UPDATE program SET creator = ? WHERE id = ?",
    QueryID.ProgramSetURL:     "UPDATE program SET url = ? WHERE id = ?",
    QueryID.ProgramSetCurFile: "UPDATE program SET cur_file = ? WHERE id = ?",
    QueryID.FileAdd:           """
    INSERT INTO file (path, folder_id, ord1, ord2)
              VALUES (?,    ?,         ?,    ?)
    RETURNING id""",
    QueryID.FileDel:           "DELETE FROM file WHERE id = ?",
    QueryID.FileGetByID:       """
    SELECT
        COALESCE(program_id, 0),
        folder_id,
        path,
        title,
        position,
        last_played,
        ord1,
        ord2
    FROM file
    WHERE id = ?""",
    QueryID.FileGetByPath:     """
    SELECT
        id,
        COALESCE(program_id, 0),
        folder_id,
        title,
        position,
        last_played,
        ord1,
        ord2
    FROM file
    WHERE path = ?""",
    QueryID.FileGetByFolder: """
SELECT
    id,
    program_id,
    path,
    title,
    position,
    last_played,
    url,
    ord1,
    ord2
FROM file
WHERE folder_id = ?
ORDER BY ord1, ord2, title, path ASC
    """,
    QueryID.FileGetByProgram: """
SELECT
    id,
    folder_id,
    path,
    title,
    position,
    last_played,
    url,
    ord1,
    ord2
FROM file
WHERE program_id = ?
ORDER BY ord1, ord2, title, path ASC
""",
    QueryID.FileGetNoProgram: """
SELECT
    id,
    folder_id,
    path,
    title,
    position,
    last_played,
    ord1,
    ord2
FROM file
WHERE program_id IS NULL
ORDER BY ord1, ord2, title, path ASC
""",
    QueryID.FileSetTitle:     "UPDATE file SET title = ? WHERE id = ?",
    QueryID.FileSetPosition:  """
    UPDATE file SET
        position = ?,
        last_played = ?
    WHERE id = ?""",
    QueryID.FileSetProgram:   "UPDATE file SET program_id = ? WHERE id = ?",
    QueryID.FileSetOrd:       """
    UPDATE file SET
        ord1 = ?,
        ord2 = ?
    WHERE id = ?""",
    QueryID.FolderAdd:        "INSERT INTO folder (path) VALUES (?) RETURNING id",  # noqa: E501
    QueryID.FolderGetAll:     "SELECT id, path, last_scan FROM folder",
    QueryID.FolderGetByPath:  """
    SELECT
        id,
        last_scan
    FROM folder
    WHERE path = ?""",
    QueryID.FolderGetByID:    """
    SELECT
        path,
        last_scan
    FROM folder
    WHERE id = ?""",
    QueryID.FolderUpdateScan: "UPDATE folder SET last_scan = ? WHERE id = ?",
}


class Database:
    """Database provides a wrapper around the actual database connection."""

    __slots__ = [
        "db",
        "log",
        "path",
    ]

    db: sqlite3.Connection
    log: logging.Logger
    path: Final[str]

    def __init__(self, path: str) -> None:
        self.path = path
        self.log = common.get_logger("database")
        self.log.debug("Open database at %s", path)
        with OPEN_LOCK:
            exist: bool = krylib.fexist(path)
            self.db = sqlite3.connect(path)  # pylint: disable-msg=C0103
            self.db.isolation_level = None

            cur: sqlite3.Cursor = self.db.cursor()
            cur.execute("PRAGMA foreign_keys = true")
            cur.execute("PRAGMA journal_mode = WAL")

            if not exist:
                self.__create_db()

    def __create_db(self) -> None:
        """Initialize a freshly created database"""
        with self.db:
            for query in INIT_QUERIES:
                cur: sqlite3.Cursor = self.db.cursor()
                cur.execute(query)

    def __enter__(self) -> None:
        self.db.__enter__()

    def __exit__(self, ex_type, ex_val, traceback):
        return self.db.__exit__(ex_type, ex_val, traceback)

    def program_add(self, prog: Program) -> None:
        """Add a Program to the database."""
        cur: sqlite3.Cursor = self.db.cursor()
        cur.execute(db_queries[QueryID.ProgramAdd],
                    (prog.title, prog.creator, prog.url))
        row = cur.fetchone()
        prog.program_id = row[0]

    def program_delete(self, prog) -> None:
        """Remove a program from the database."""
        cur: sqlite3.Cursor = self.db.cursor()
        cur.execute(db_queries[QueryID.ProgramDel], (prog.program_id, ))

    def program_get_all(self) -> list[Program]:
        """Load all Programs from the database."""
        cur: sqlite3.Cursor = self.db.cursor()
        cur.execute(db_queries[QueryID.ProgramGetAll])
        progs: list[Program] = []
        for row in cur:
            p = Program(
                program_id=row[0],
                title=row[1],
                creator=row[2],
                url=row[3],
                cur_file=row[4])
            progs.append(p)
        return progs

    def program_get_by_id(self, pid: int) -> Optional[Program]:
        """Fetch a Program by its database ID"""
        cur: sqlite3.Cursor = self.db.cursor()
        cur.execute(db_queries[QueryID.ProgramGetByID], (pid, ))
        row = cur.fetchone()
        if row is not None:
            prog = Program(
                program_id=pid,
                title=row[0],
                creator=row[1],
                url=row[2],
                cur_file=row[3],
            )
            return prog
        return None

    def program_get_by_title(self, title: str) -> Optional[Program]:
        """Fetch a Program by its title"""
        cur: sqlite3.Cursor = self.db.cursor()
        cur.execute(db_queries[QueryID.ProgramGetByTitle], (title, ))
        row = cur.fetchone()
        if row is not None:
            prog = Program(
                program_id=row[0],
                title=title,
                creator=row[1],
                url=row[2],
                cur_file=row[3],
            )
            return prog
        return None

    def program_set_title(self, prog: Program, title: str) -> None:
        """Update the title in a Program."""
        cur: sqlite3.Cursor = self.db.cursor()
        cur.execute(db_queries[QueryID.ProgramSetTitle], (title, prog.program_id))  # noqa: E501
        prog.title = title

    def program_set_creator(self, prog: Program, creator: str) -> None:
        """Update the Program creator in the database."""
        cur: sqlite3.Cursor = self.db.cursor()
        cur.execute(db_queries[QueryID.ProgramSetCreator], (creator, prog.program_id))  # noqa: E501
        prog.creator = creator

    def program_set_url(self, prog: Program, url: str) -> None:
        """Update the program's URL."""
        cur: sqlite3.Cursor = self.db.cursor()
        cur.execute(db_queries[QueryID.ProgramSetURL], (url, prog.program_id))  # noqa: E501
        prog.url = url

    def program_set_cur_file(self, prog: Program, file_id: int) -> None:
        """Update the current file of a Program"""
        cur: sqlite3.Cursor = self.db.cursor()
        cur.execute(db_queries[QueryID.ProgramSetCurFile], (file_id, prog.program_id))  # noqa: E501
        prog.current_file = file_id

    def file_add(self, f: File) -> None:
        """Add a File to the database."""
        cur: sqlite3.Cursor = self.db.cursor()
        args = (f.path,
                f.folder_id,
                f.ord1,
                f.ord2)
        cur.execute(db_queries[QueryID.FileAdd], args)
        row = cur.fetchone()
        f.file_id = row[0]

    def file_delete(self, f: File) -> None:
        """Remove a file from the database."""
        cur: sqlite3.Cursor = self.db.cursor()
        cur.execute(db_queries[QueryID.FileDel], (f.file_id, ))

    def file_get_by_id(self, file_id: int) -> Optional[File]:
        """Fetch a File by its ID"""
        cur: sqlite3.Cursor = self.db.cursor()
        cur.execute(db_queries[QueryID.FileGetByID], (file_id, ))
        row = cur.fetchone()
        if row is not None:
            f = File(
                file_id=file_id,
                program_id=row[0],
                folder_id=row[1],
                path=row[2],
                title=row[3],
                position=row[4],
                last_played=datetime.fromtimestamp(row[5]),
                ord1=row[6],
                ord2=row[7],
            )
            return f
        return None

    def file_get_by_path(self, path: str) -> Optional[File]:
        """Fetch a File by its path"""
        cur: sqlite3.Cursor = self.db.cursor()
        cur.execute(db_queries[QueryID.FileGetByPath], (path, ))
        row = cur.fetchone()
        if row is not None:
            f = File(
                file_id=row[0],
                program_id=row[1],
                folder_id=row[2],
                path=path,
                title=row[3],
                position=row[4],
                last_played=datetime.fromtimestamp(row[5]),
                ord1=row[6],
                ord2=row[7],
            )
            return f
        return None

    def file_get_by_program(self, prog_id: int) -> list[File]:
        """Load all Files that belong to a given Program."""
        cur: sqlite3.Cursor = self.db.cursor()
        cur.execute(db_queries[QueryID.FileGetByProgram], (prog_id, ))
        files: list[File] = []
        for row in cur:
            f = File(
                file_id=row[0],
                program_id=prog_id,
                folder_id=row[1],
                path=row[2],
                title=row[3],
                position=row[4],
                last_played=datetime.fromtimestamp(row[5]),
                ord1=(row[7] or 0),
                ord2=(row[8] or 0),
            )
            files.append(f)
        return files

    def file_get_by_folder(self, folder: Union[int, Folder]) -> list[File]:
        """Load all Files that live in the given Folder."""
        folder_id: int = 0
        if isinstance(folder, int):
            folder_id = folder
        elif isinstance(folder, Folder):
            folder_id = folder.folder_id

        cur: sqlite3.Cursor = self.db.cursor()
        cur.execute(db_queries[QueryID.FileGetByProgram], (folder_id, ))
        files: list[File] = []
        for row in cur:
            f = File(
                file_id=row[0],
                folder_id=folder_id,
                program_id=row[1],
                path=row[2],
                title=row[3],
                position=row[4],
                last_played=datetime.fromtimestamp(row[5]),
                ord1=row[6],
                ord2=row[7],
            )
            files.append(f)
        return files

    def file_get_no_program(self) -> list[File]:
        """Return all Files that have no program associated with them."""
        cur: sqlite3.Cursor = self.db.cursor()
        files: list[File] = []
        cur.execute(db_queries[QueryID.FileGetNoProgram])
        for row in cur:
            f = File(
                file_id=row[0],
                folder_id=row[1],
                path=row[2],
                title=row[3],
                position=row[4],
                last_played=datetime.fromtimestamp(row[5]),
                ord1=row[6],
                ord2=row[7],
            )
            files.append(f)
        return files

    def file_set_title(self, f: File, title: str) -> None:
        """Update a File's title."""
        cur: sqlite3.Cursor = self.db.cursor()
        cur.execute(db_queries[QueryID.FileSetTitle], (title, f.file_id))
        f.title = title

    def file_set_position(self, f: File, pos: int) -> None:
        """Update a File's playback position."""
        cur: sqlite3.Cursor = self.db.cursor()
        cur.execute(db_queries[QueryID.FileSetPosition], (pos, f.file_id))
        f.position = pos

    def file_set_ord(self, f: File, o1: int, o2: int) -> None:
        """Set a File's sorting indices."""
        cur: sqlite3.Cursor = self.db.cursor()
        cur.execute(db_queries[QueryID.FileSetOrd], (o1, o2, f.file_id))
        f.ord1 = o1
        f.ord2 = o2

    def file_set_program(self, f: File, pid: int) -> None:
        """Set a File's Program."""
        cur: sqlite3.Cursor = self.db.cursor()
        cur.execute(db_queries[QueryID.FileSetProgram], (pid, f.file_id))
        f.program_id = pid

    def folder_add(self, folder: Folder) -> None:
        """Add a Folder to the database."""
        cur: sqlite3.Cursor = self.db.cursor()
        cur.execute(db_queries[QueryID.FolderAdd], (folder.path, ))
        row = cur.fetchone()
        folder.folder_id = row[0]

    def folder_get_all(self) -> list[Folder]:
        """Fetch all folders from the database"""
        cur: sqlite3.Cursor = self.db.cursor()
        cur.execute(db_queries[QueryID.FolderGetAll])
        folders: list[Folder] = []
        for row in cur:
            f = Folder(row[0], row[1], row[2])
            folders.append(f)
        return folders

    def folder_get_by_id(self, folder_id: int) -> Optional[Folder]:
        """Look up a Folder by its ID"""
        cur = self.db.cursor()
        cur.execute(db_queries[QueryID.FolderGetByID], (folder_id, ))
        row = cur.fetchone()
        if row is not None:
            f = Folder(folder_id, row[0], row[1])
            return f
        return None

    def folder_get_by_path(self, path: str) -> Optional[Folder]:
        """Look up a Folder by its path"""
        cur = self.db.cursor()
        cur.execute(db_queries[QueryID.FolderGetByPath], (path, ))
        row = cur.fetchone()
        if row is not None:
            f = Folder(row[0], path, row[1])
            return f
        return None

    def folder_update_scan(self, folder: Folder, timestamp: datetime) -> None:
        """Update a Folder's scan timestamp."""
        cur = self.db.cursor()
        cur.execute(db_queries[QueryID.FolderUpdateScan],
                    (int(timestamp.timestamp()),
                     folder.folder_id))
        folder.last_scan = timestamp

# Local Variables: #
# python-indent: 4 #
# End: #
