#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Time-stamp: <2023-11-08 19:32:17 krylon>
#
# /data/code/python/vox/ui.py
# created on 04. 11. 2023
# (c) 2023 Benjamin Walkenhorst
#
# This file is part of the Vox audiobook reader. It is distributed under the
# terms of the GNU General Public License 3. See the file LICENSE for details
# or find a copy online at https://www.gnu.org/licenses/gpl-3.0

"""
vox.ui

(c) 2023 Benjamin Walkenhorst
"""

# pylint: disable-msg=C0413,R0902,C0411

import gi  # type: ignore

from vox import common, database
from vox.data import Program

gi.require_version("Gtk", "3.0")
from gi.repository import \
    GdkPixbuf as gpb  # noqa: E402,E501 # pylint: disable-msg=C0411
from gi.repository import \
    GLib as glib  # noqa: E402,E501 # pylint: disable-msg=C0411
from gi.repository import Gtk as gtk  # noqa: E402 # pylint: disable-msg=C0411


# pylint: disable-msg=R0903
class VoxUI:
    """The graphical interface to the application, built using gtk3"""

    def __init__(self) -> None:
        self.log = common.get_logger("GUI")
        self.db = database.Database(common.path.db())

        #######################################################
        # Create widgets  #####################################
        #######################################################

        self.win = gtk.Window()
        self.win.set_title(f"{common.APP_NAME} {common.APP_VERSION}")
        self.mbox = gtk.Box(orientation=gtk.Orientation.VERTICAL)

        self.menubar = gtk.MenuBar()
        # menu stuff tbd ...
        self.file_menu_item = gtk.MenuItem.new_with_mnemonic("_File")
        self.play_menu_item = gtk.MenuItem.new_with_mnemonic("_Playback")

        self.file_menu = gtk.Menu()
        self.play_menu = gtk.Menu()

        self.fm_scan_item = gtk.MenuItem.new_with_mnemonic("_Scan folder")
        self.fm_quit_item = gtk.MenuItem.new_with_mnemonic("_Quit")

        self.menubar.add(self.file_menu_item)
        self.menubar.add(self.play_menu_item)
        self.file_menu_item.set_submenu(self.file_menu)
        self.play_menu_item.set_submenu(self.play_menu)

        self.file_menu.add(self.fm_scan_item)
        self.file_menu.add(self.fm_quit_item)

        self.fm_quit_item.connect("activate", gtk.main_quit)

        self.notebook = gtk.Notebook()
        self.page1 = gtk.Box()

        self.prog_store = gtk.TreeStore(
            int,  # Program ID
            str,  # Program Title
            int,  # File ID
            str,  # File Title
            int,  # Ord1
            int,  # Ord2
            str,  # Duration
        )
        self.prog_view = gtk.TreeView(model=self.prog_store)

        columns = [
            (0, "PID"),
            (1, "Program"),
            (2, "FID"),
            (3, "Title"),
            (4, "Disc #"),
            (5, "Track #"),
            (6, "Dur"),
        ]

        for c in columns:
            col = gtk.TreeViewColumn(
                c[1],
                gtk.CellRendererText(),
                text=c[0],
                weight=1,
            )
            self.prog_view.append_column(col)

        # Fill the model!
        programs: list[Program] = self.db.program_get_all()

        for p in programs:
            piter = self.prog_store.append(None)
            piter[0] = p.program_id
            piter[1] = p.title
            files = self.db.file_get_by_program(p.program_id)
            for f in files:
                citer = self.prog_store.append(piter)
                citer[2] = f.file_id
                citer[3] = f.title
                citer[4] = f.ord1
                citer[5] = f.ord2

        #######################################################
        # Assemble Window #####################################
        #######################################################

        # pylint: disable-msg=E1101
        self.win.add(self.mbox)
        self.mbox.pack_start(self.menubar, False, True, 0)
        self.mbox.pack_start(self.notebook, False, True, 0)

        #######################################################
        # Connect signal handlers #############################
        #######################################################
        self.win.connect("destroy", gtk.main_quit)

        self.win.show_all()


def main() -> None:
    """Display the GUI and run the gtk mainloop"""
    mw = VoxUI()
    mw.log.debug("Let's go")
    gtk.main()


if __name__ == "__main__":
    main()

# Local Variables: #
# python-indent: 4 #
# End: #
