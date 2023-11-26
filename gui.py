#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Time-stamp: <2023-11-26 16:10:17 krylon>
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
from enum import Enum, auto
from threading import Lock, Thread, current_thread, local
from typing import Any, Callable, Final, Optional

import gi  # type: ignore

from krylib import cmp, is_natural, is_negative

from vox import common, database, scanner
from vox.data import File, Program

gi.require_version("Gtk", "3.0")
gi.require_version("Gdk", "3.0")
gi.require_version("GdkPixbuf", "2.0")
gi.require_version("Gst", "1.0")
# from gi.repository import \
#     GLib as \
#     glib  # noqa: F401,E402,E501 # pylint: disable-msg=C0411,W0611 # type: ignore
# from gi.repository import \
#     GdkPixbuf as \
#     gpb  # noqa: F401,E402,E501 # pylint: disable-msg=C0411,W0611 # type: ignore
from gi.repository import Gdk as gdk  # noqa: E402
from gi.repository import GObject as gobject  # noqa: E402
from gi.repository import Gst as gst  # noqa: E402
from gi.repository import \
    Gtk as gtk  # noqa: E402,E501 # pylint: disable-msg=C0411,E0611


class PlayerState(Enum):
    """Symbolic constants for the player's state."""
    STOPPED = auto()
    PLAYING = auto()
    PAUSED = auto()
    OTHER = auto()


# pylint: disable-msg=R0903
class VoxUI:
    """The graphical interface to the application, built using gtk3"""

    def __init__(self) -> None:  # pylint: disable-msg=R0915
        self.local = local()
        self.log = common.get_logger("GUI")
        # self.db = database.Database(common.path.db())
        # self.scanner = scanner.Scanner()
        self.lock = Lock()

        # Prepare gstreamer pipeline for audio playback

        self.state = PlayerState.STOPPED
        gst.init(None)
        self.gstloop = gobject.MainLoop()
        self.player = gst.ElementFactory.make("playbin", "player")
        self.player.set_property("volume", 0.5)

        #######################################################
        # Create widgets  #####################################
        #######################################################

        self.win = gtk.Window()
        self.win.set_title(f"{common.APP_NAME} {common.APP_VERSION}")
        self.mbox = gtk.Box(orientation=gtk.Orientation.VERTICAL)

        self.menubar = gtk.MenuBar()
        self.file_menu_item = gtk.MenuItem.new_with_mnemonic("_File")
        self.action_menu_item = gtk.MenuItem.new_with_mnemonic("_Action")
        self.play_menu_item = gtk.MenuItem.new_with_mnemonic("_Playback")

        self.file_menu = gtk.Menu()
        self.action_menu = gtk.Menu()
        self.play_menu = gtk.Menu()

        self.fm_scan_item = gtk.MenuItem.new_with_mnemonic("_Scan folder")
        self.fm_reload_item = gtk.MenuItem.new_with_mnemonic("_Reload")
        self.fm_quit_item = gtk.MenuItem.new_with_mnemonic("_Quit")

        self.am_prog_add_item = gtk.MenuItem.new_with_mnemonic("Add _Program")

        self.pm_playpause_item = gtk.MenuItem.new_with_mnemonic("_Play/Pause")
        self.pm_stop_item = gtk.MenuItem.new_with_mnemonic("_Stop")
        self.pm_next_item = gtk.MenuItem.new_with_mnemonic("_Next")
        self.pm_prev_item = gtk.MenuItem.new_with_mnemonic("Pre_vious")

        self.menubar.add(self.file_menu_item)
        self.menubar.add(self.action_menu_item)
        self.menubar.add(self.play_menu_item)
        self.file_menu_item.set_submenu(self.file_menu)
        self.action_menu_item.set_submenu(self.action_menu)
        self.play_menu_item.set_submenu(self.play_menu)

        self.file_menu.add(self.fm_scan_item)
        self.file_menu.add(self.fm_reload_item)
        self.file_menu.add(self.fm_quit_item)

        self.action_menu.add(self.am_prog_add_item)

        self.play_menu.add(self.pm_playpause_item)
        self.play_menu.add(self.pm_stop_item)
        self.play_menu.add(self.pm_next_item)
        self.play_menu.add(self.pm_prev_item)

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
        self.sort_store = gtk.TreeModelSort(self.prog_store)
        self.sort_store.set_default_sort_func(cmp_iter)
        self.prog_view = gtk.TreeView(model=self.sort_store)

        # self.sort_store.set_sort_func(

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
        self.win.connect("destroy", self.__quit)
        self.fm_quit_item.connect("activate", self.__quit)
        self.fm_scan_item.connect("activate", self.scan_folder)
        self.fm_reload_item.connect("activate", self.__refresh)
        self.am_prog_add_item.connect("activate", self.create_program)
        self.pm_playpause_item.connect("activate", self.toggle_play_pause)
        self.pm_stop_item.connect("activate", self.stop)
        self.prog_view.connect("button-press-event",
                               self.__handle_prog_view_click)

        self.loop_thr = Thread(target=self.__gst_loop)
        self.loop_thr.daemon = True
        self.loop_thr.start()
        self.win.show_all()

    def __get_db(self) -> database.Database:
        """Return a database handle that's local to the current thread."""
        try:
            return self.local.db
        except AttributeError:
            self.local.db = database.Database(common.path.db())
            return self.local.db

    def __gst_loop(self) -> None:
        """Run the GStreamer mainloop"""
        try:
            thr = current_thread()
            self.log.debug("GStreamer loop starting in thread %d / %s",
                           thr.ident,
                           thr.name)
            self.gstloop.run()
        finally:
            self.log.info("GStreamer loop has finished.")

    # def decode_src_created(self, _element, pad) -> None:
    #     """Callback for gstreamer."""
    #     self.log.debug("Do the pad link stuff")
    #     pad.link(self.sink.get_static_pad("sink"))

    def __quit(self, *_ignore: Any) -> None:
        self.win.destroy()
        self.stop()
        self.gstloop.quit()
        gtk.main_quit()

    def __handle_prog_view_click(self, widget, evt: gdk.Event) -> None:
        # self.log.debug("We got a click: %s / %s", widget, evt)
        if evt.button != 3:
            # self.log.debug("User did not click right button, we don't care.")
            return
        x: float = evt.x
        y: float = evt.y

        path, col, _, _ = self.prog_view.get_path_at_pos(x, y)
        cpath = self.sort_store.convert_path_to_child_path(path)
        tree_iter: gtk.TreeIter = self.prog_store.get_iter(cpath)
        title = col.get_title()

        self.log.debug("Clicked on column %s", title)

        pid = self.prog_store[tree_iter][0]
        fid = self.prog_store[tree_iter][2]

        self.log.debug("PID = %d / FID = %d",
                       pid, fid)

        menu: Optional[gtk.Menu] = None

        if pid >= 0:  # Did we click on a Program...
            menu = self.__mk_context_menu_program(tree_iter, pid)  # pylint: disable-msg=E1128 # noqa: E501
        elif fid > 0:  # ...or on a File?
            menu = self.__mk_context_menu_file(tree_iter, fid)
        else:
            self.log.debug("Weird: This is not a File nor a Program.")
            return

        assert menu is not None

        menu.show_all()
        menu.popup_at_pointer(evt)

    def __mk_context_menu_file(self, fiter: gtk.TreeIter, file_id: int) -> Optional[gtk.Menu]:  # noqa: E501 # pylint: disable-msg=C0301
        db = self.__get_db()
        file: Optional[File] = db.file_get_by_id(file_id)

        if file is not None:
            self.log.debug("Make context menu for %s", file.display_title())
        else:
            self.log.error("File %d was not found in database", file_id)
            return None

        progs: list[Program] = db.program_get_all()
        menu: gtk.Menu = gtk.Menu()
        prog_menu: gtk.Menu = gtk.Menu()
        play_item = gtk.MenuItem.new_with_mnemonic("_Play")
        edit_item = gtk.MenuItem.new_with_mnemonic("_Edit")
        prog_item = gtk.MenuItem.new_with_label("Program")

        prog_item.set_submenu(prog_menu)

        null_item = gtk.CheckMenuItem.new_with_label("NULL")
        prog_menu.append(null_item)
        null_item.set_active(file.program_id == 0)

        for prog in progs:
            pitem = gtk.CheckMenuItem.new_with_label(prog.title)
            pitem.set_active(prog.program_id == file.program_id)
            prog_menu.append(pitem)
            pitem.connect("activate",
                          self.__mk_set_program_handler(fiter, file, prog))

        menu.append(play_item)
        menu.append(edit_item)
        menu.append(prog_item)

        play_item.connect("activate", self.__mk_play_file_handler(file))

        return menu

    def __mk_context_menu_program(self, _piter: gtk.TreeIter, prog_id: int) -> Optional[gtk.Menu]:  # noqa: E501 # pylint: disable-msg=C0301,R1711
        self.log.debug("IMPLEMENTME: Context menu for Program %d", prog_id)
        return None

    def __mk_play_file_handler(self, file: File) -> Callable:
        def play(*_ignore: Any) -> None:
            self.log.debug("Play File %d (%s)",
                           file.file_id,
                           file.display_title())
            self.play_file(file)
        return play

    # pylint: disable-msg=W0238
    def __mk_set_program_handler(self, fiter: gtk.TreeIter, file: File, prog: Program) -> Callable:  # noqa: E501 # pylint: disable-msg=C0301
        def handler(*_ignore: Any) -> None:
            self.file_set_program(fiter, file.file_id, prog.program_id)
            # Update the model, move the file to its new program.
        return handler

    def __refresh(self, *_ignore: Any) -> None:
        """Wipe and recreate the data model"""
        self.prog_store.clear()
        self.__load_data()

    def __load_data(self) -> None:
        """Load programs and files from the database, display them."""
        # Fill the model!
        db = self.__get_db()
        programs: list[Program] = db.program_get_all()

        for p in programs:
            piter = self.prog_store.append(None)
            self.prog_store[piter][0] = p.program_id
            self.prog_store[piter][1] = p.title
            files = db.file_get_by_program(p.program_id)
            for f in files:
                citer = self.prog_store.append(piter)
                self.prog_store[citer][0] = -p.program_id
                self.prog_store[citer][2] = f.file_id
                self.prog_store[citer][3] = f.display_title()
                self.prog_store[citer][4] = f.ord1
                self.prog_store[citer][5] = f.ord2

        no_prog: list[File] = db.file_get_no_program()
        if len(no_prog) > 0:
            piter = self.prog_store.append(None)
            self.prog_store[piter][0] = 0
            self.prog_store[piter][1] = "None"
            for f in no_prog:
                citer = self.prog_store.append(piter)
                self.prog_store[citer][0] = -1
                self.prog_store[citer][2] = f.file_id
                self.prog_store[citer][3] = f.display_title()
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

    def toggle_play_pause(self, *_ignore: Any) -> None:
        """Toggle the player's status."""
        with self.lock:
            match self.state:
                case PlayerState.PLAYING:
                    self.player.set_state(gst.State.PAUSED)
                    self.state = PlayerState.PAUSED
                    self.log.debug("Playback is paused now")
                case PlayerState.PAUSED:
                    self.player.set_state(gst.State.PLAYING)
                    self.state = PlayerState.PLAYING
                    self.log.debug("Playback is playing now")
                case _:
                    self.log.debug(
                        "PlayerState is %s, cannot toggle play/pause",
                        self.state)

    def play_file(self, file: File) -> None:
        """Play a single file."""
        with self.lock:
            self.log.debug("Play file %s",
                           file.display_title())
            uri: Final[str] = f"file://{file.path}"
            self.player.set_state(gst.State.NULL)
            self.player.set_property("uri", uri)
            self.state = PlayerState.PLAYING
            self.player.set_state(gst.State.PLAYING)

    def stop(self, *_ignore) -> None:
        """Stop the player (if it's playing)"""
        with self.lock:
            self.state = PlayerState.STOPPED
            self.player.set_state(gst.State.NULL)

    # Managing our stuff

    # pylint: disable-msg=R0914
    def create_program(self, *_ignore) -> None:
        """Create a new Program"""
        dlg: gtk.Dialog = gtk.Dialog(
            title="Create Program",
            parent=self.win,
            )
        dlg.add_buttons(
            gtk.STOCK_CANCEL,
            gtk.ResponseType.CANCEL,
            gtk.STOCK_OK,
            gtk.ResponseType.OK,
            )

        grid = gtk.Grid.new()
        title_lbl = gtk.Label.new("Title")
        creator_lbl = gtk.Label.new("Author")
        url_lbl = gtk.Label.new("URL")
        title_txt = gtk.Entry.new()
        creator_txt = gtk.Entry.new()
        url_txt = gtk.Entry.new()

        grid.attach(title_lbl, 0, 0, 1, 1)
        grid.attach(title_txt, 1, 0, 1, 1)
        grid.attach(creator_lbl, 0, 1, 1, 1)
        grid.attach(creator_txt, 1, 1, 1, 1)
        grid.attach(url_lbl, 0, 2, 1, 1)
        grid.attach(url_txt, 1, 2, 1, 1)

        dlg.get_content_area().add(grid)
        dlg.show_all()

        try:
            response = dlg.run()
            if response != gtk.ResponseType.OK:
                return

            title: Final[str] = title_txt.get_text()
            creator: Final[str] = creator_txt.get_text()
            url: Final[str] = url_txt.get_text()
            prog = Program(
                title=title,
                creator=creator,
                url=url,
            )
            db = self.__get_db()
            with db:
                db.program_add(prog)

            # Now we need to add the new Program to the TreeStore.
            piter = self.prog_store.append(None)
            self.prog_store[piter][0] = prog.program_id
            self.prog_store[piter][1] = prog.title
        finally:
            dlg.destroy()

    def file_set_program(self, fiter: gtk.TreeIter, fid: int, pid: int) -> None:  # noqa: E501
        """Set the Program a given File belongs to"""
        self.log.debug("Set Program of File %d to %d",
                       fid,
                       pid)
        db = self.__get_db()
        with db:
            f = db.file_get_by_id(fid)
            if f is not None:
                db.file_set_program(f, pid)
            else:
                self.log.debug("File %d does not exist in database", fid)
                return
            # Now we need to find and update/move the entry in our TreeStore.
            self.prog_store.remove(fiter)
            piter: gtk.TreeIter = self.prog_store.get_iter_first()

            while (piter is not None) and (self.prog_store[piter][0] != pid):
                piter = self.prog_store.iter_next(piter)

            if piter is None:
                self.log.debug("Did not find Program %d in TreeStore!", pid)
                return

            fiter = self.prog_store.append(piter)
            self.prog_store[fiter][0] = -pid
            self.prog_store[fiter][2] = f.file_id
            self.prog_store[fiter][3] = f.display_title()
            self.prog_store[fiter][4] = f.ord1
            self.prog_store[fiter][5] = f.ord2


# pylint: disable-msg=R0911
def cmp_iter(m: gtk.TreeModel, a, b: gtk.TreeIter, _) -> int:
    """Comparison function for sorting."""
    v1 = m.get(a, 0, 1, 2, 3, 4, 5, 6)
    v2 = m.get(b, 0, 1, 2, 3, 4, 5, 6)
    if is_natural(v1[0]) and is_negative(v2[0]):
        return cmp(v1[0], abs(v2[0]))
    if is_natural(v1[0]) and is_natural(v2[0]):
        return cmp(v1[0], v2[0])
    if is_negative(v1[0]) and is_natural(v2[0]):
        return cmp(abs(v1[0]), v2[0])
    if is_negative(v1[0]) and is_negative(v2[0]):
        match cmp(abs(v1[0]), abs(v2[0])):
            case -1:
                return -1
            case 0:
                return cmp(v1[2], v2[2])
            case 1:
                return 1

    return 0


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
