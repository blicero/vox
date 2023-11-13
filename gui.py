#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Time-stamp: <2023-11-13 19:14:13 krylon>
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
from threading import Lock, Thread
from typing import Any

import gi  # type: ignore

from vox import common, database, scanner
from vox.data import File, Program

gi.require_version("Gtk", "3.0")
gi.require_version("GdkPixbuf", "2.0")
# from gi.repository import \
#     GdkPixbuf as \
#     gpb  # noqa: F401,E402,E501 # pylint: disable-msg=C0411,W0611 # type: ignore
# from gi.repository import \
#     GLib as \
#     glib  # noqa: F401,E402,E501 # pylint: disable-msg=C0411,W0611 # type: ignore
from gi.repository import Gtk as gtk  # noqa: E402 # pylint: disable-msg=C0411


# pylint: disable-msg=R0903
class VoxUI:
    """The graphical interface to the application, built using gtk3"""

    def __init__(self) -> None:
        self.log = common.get_logger("GUI")
        self.db = database.Database(common.path.db())
        # self.scanner = scanner.Scanner()
        self.lock = Lock()

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
        self.fm_reload_item = gtk.MenuItem.new_with_mnemonic("_Reload")
        self.fm_quit_item = gtk.MenuItem.new_with_mnemonic("_Quit")

        self.menubar.add(self.file_menu_item)
        self.menubar.add(self.play_menu_item)
        self.file_menu_item.set_submenu(self.file_menu)
        self.play_menu_item.set_submenu(self.play_menu)

        self.file_menu.add(self.fm_scan_item)
        self.file_menu.add(self.fm_reload_item)
        self.file_menu.add(self.fm_quit_item)

        # self.fm_quit_item.connect("activate", gtk.main_quit)

        self.notebook = gtk.Notebook()
        self.page1 = gtk.Box()
        self.prog_scroll = gtk.ScrolledWindow()

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

        self.__load_data()

        #######################################################
        # Assemble Window #####################################
        #######################################################

        # pylint: disable-msg=E1101
        self.win.add(self.mbox)
        self.mbox.pack_start(self.menubar, False, True, 0)
        self.mbox.pack_start(self.notebook, False, True, 0)

        self.notebook.append_page(self.page1, gtk.Label(label="Program"))
        self.page1.pack_start(self.prog_scroll, False, True, 0)
        self.prog_scroll.set_vexpand(True)
        self.prog_scroll.set_hexpand(True)
        self.prog_scroll.add(self.prog_view)

        #######################################################
        # Connect signal handlers #############################
        #######################################################
        self.win.connect("destroy", gtk.main_quit)
        self.fm_quit_item.connect("activate", self.__quit)
        self.fm_scan_item.connect("activate", self.scan_folder)
        self.fm_reload_item.connect("activate", self.__refresh)

        self.win.show_all()

    def __quit(self, *_ignore: Any) -> None:
        self.win.destroy()
        gtk.main_quit()

    def __refresh(self, *_ignore: Any) -> None:
        """Wipe and recreate the data model"""
        self.prog_store.clear()
        self.__load_data()

    def __load_data(self) -> None:
        """Load programs and files from the database, display them."""
        # Fill the model!
        programs: list[Program] = self.db.program_get_all()

        for p in programs:
            piter = self.prog_store.append(None)
            piter[0] = p.program_id
            piter[1] = p.title
            files = self.db.file_get_by_program(p.program_id)
            for f in files:
                citer = self.prog_store.append(piter)
                self.prog_store[citer][2] = f.file_id
                self.prog_store[citer][3] = f.title
                self.prog_store[citer][4] = f.ord1
                self.prog_store[citer][5] = f.ord2

        no_prog: list[File] = self.db.file_get_no_program()
        if len(no_prog) > 0:
            piter = self.prog_store.append(None)
            for f in no_prog:
                citer = self.prog_store.append(piter)
                self.prog_store[citer][2] = f.file_id
                self.prog_store[citer][3] = f.title
                self.prog_store[citer][4] = f.ord1
                self.prog_store[citer][5] = f.ord2

    def scan_folder(self, *_ignored) -> None:
        """Prompt the user for a folder to scan, then scan it."""
        dlg = gtk.FileChooserDialog(
            title="Pick a folder...",
            parent=self.win,
            action=gtk.FileChooserAction.SELECT_FOLDER)
        dlg.add_buttons(
            gtk.STOCK_CANCEL,
            gtk.ResponseType.CANCEL,
            gtk.STOCK_OPEN,
            gtk.ResponseType.OK)

        try:
            # pylint: disable-msg=E1101
            res = dlg.run()
            if res != gtk.ResponseType.OK:
                self.log.debug("Response from dialog: %s", res)
                return

            path = dlg.get_filename()
            self.log.info("Scan folder %s", path)
            thr: Thread = Thread(target=self.__scan_worker, args=(path, ))
            thr.start()
        finally:
            dlg.destroy()

    def __scan_worker(self, path: str) -> None:
        """Boo"""

        sc = scanner.Scanner()

        try:
            self.log.debug("Start scanning %s", path)
            sc.scan(path)
            # files = sc.db.file_get_by_folder(folder)  # noqa: F841
        finally:
            self.log.debug("Finished scanning %s", path)

    def display_msg(self, msg: str) -> None:
        """Display a message in a dialog."""
        dlg = gtk.Dialog(
            parent=self.win,
            title="Attention",
            flags=gtk.DialogFlags.MODAL,
        )

        area = dlg.get_content_area()
        lbl = gtk.Label(msg)
        area.add(lbl)

        try:
            dlg.run()
        finally:
            dlg.destroy()


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
