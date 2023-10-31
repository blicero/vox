#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Time-stamp: <2023-10-31 19:49:30 krylon>
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

import threading
from enum import Enum, auto
from typing import Final

INIT_QUERIES: Final[list[str]] = [
    """
    CREATE TABLE folder (
        id		INTEGER PRIMARY KEY,
        path		TEXT UNIQUE NOT NULL,
        last_scan       INTEGER NOT NULL DEFAULT 0,
        CHECK (path LIKE '/%')
    )
    """,

    """
CREATE TABLE program (
    id                   INTEGER PRIMARY KEY,
    title                TEXT UNIQUE NOT NULL,
    creator              TEXT NOT NULL DEFAULT '',
    url                  TEXT NOT NULL DEFAULT '',
    cur_file             INTEGER NOT NULL DEFAULT -1
)
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
)
    """,
    "CREATE INDEX file_prog_idx ON file (program_id)",
    "CREATE INDEX file_path_idx ON file (path)",
    "CREATE INDEX file_title_idx ON file (title)",
    "CREATE INDEX file_ord_index ON file (ord1, ord2)",
]

OPEN_LOCK: Final[threading.Lock] = threading.Lock()


# pylint: disable-msg=C0103
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
    INSERT INTO program (title, creator)
                 VALUES (?,     ?)""",
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
              VALUES (?,    ?,         ?,    ?)""",
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
    QueryID.FolderAdd:        "INSERT INTO folder (path) VALUES (?)",
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

# Local Variables: #
# python-indent: 4 #
# End: #
