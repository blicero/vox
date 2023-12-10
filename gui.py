#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Time-stamp: <2023-12-10 11:01:50 krylon>
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
from threading import RLock, Thread, current_thread, local
from typing import Any, Callable, Final, Optional

import gi  # type: ignore
from krylib import cmp, sign

from vox import common, database, scanner
from vox.data import File, Program

gi.require_version("Gtk", "3.0")
gi.require_version("Gdk", "3.0")
gi.require_version("GdkPixbuf", "2.0")
gi.require_version("Gst", "1.0")
gi.require_version("GLib", "2.0")
from gi.repository import Gdk as gdk  # noqa: E402
from gi.repository import Gst as gst  # noqa: E402
from gi.repository import \
    Gtk as gtk  # noqa: E402,E501 # pylint: disable-msg=C0411,E0611
from gi.repository import GLib as glib  # noqa: E402


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
        self.lock: Final[RLock] = RLock()
        self.playlist: list[File] = []
        self.playidx: int = 0
        self.prog: Optional[Program] = None

        # Prepare gstreamer pipeline for audio playback
        self.state: PlayerState = PlayerState.STOPPED
        gst.init(None)
        self.gstloop = glib.MainLoop()
        self.player = gst.ElementFactory.make("playbin", "player")
        self.player.set_property("volume", 0.5)
        self.gbus = self.player.get_bus()
        self.gbus.add_signal_watch()
        self.gbus.connect("message", self.handle_player_msg)

        #######################################################
        # Create widgets  #####################################
        #######################################################

        self.win = gtk.Window()
        self.win.set_title(f"{common.APP_NAME} {common.APP_VERSION}")
        self.mbox = gtk.Box(orientation=gtk.Orientation.VERTICAL)

        self.sbox = gtk.Box(orientation=gtk.Orientation.HORIZONTAL)
        self.slabel = gtk.Label(label="Nothing to see here, move along...")

        self.cbox = gtk.ButtonBox(orientation=gtk.Orientation.HORIZONTAL)
        # pylint: disable-msg=E1101
        self.cb_play = gtk.Button.new_from_stock(gtk.STOCK_MEDIA_PLAY)
        self.cb_stop = gtk.Button.new_from_stock(gtk.STOCK_MEDIA_STOP)
        self.cb_next = gtk.Button.new_from_stock(gtk.STOCK_MEDIA_NEXT)
        self.cb_prev = gtk.Button.new_from_stock(gtk.STOCK_MEDIA_PREVIOUS)

        self.control_box = gtk.Box(orientation=gtk.Orientation.HORIZONTAL)
        self.seek = gtk.Scale.new_with_range(gtk.Orientation.HORIZONTAL,
                                             0,
                                             100,
                                             1)

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
        self.sort_store = gtk.TreeModelSort(model=self.prog_store)
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
        self.mbox.pack_start(self.control_box, False, True, 1)
        self.mbox.pack_start(self.sbox, False, True, 1)
        self.mbox.pack_start(self.notebook, False, True, 0)

        self.sbox.pack_start(self.slabel, False, True, 0)

        self.cbox.add(self.cb_prev)
        self.cbox.add(self.cb_play)
        self.cbox.add(self.cb_stop)
        self.cbox.add(self.cb_next)

        self.control_box.pack_start(self.cbox, False, False, 0)
        self.control_box.pack_start(self.seek, True, True, 0)

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
        self.cb_play.connect("clicked", self.toggle_play_pause)
        self.cb_stop.connect("clicked", self.stop)
        self.cb_prev.connect("clicked", self.play_previous)
        self.cb_next.connect("clicked", self.play_next)
        self.seek.connect("format-value", self.format_position)
        self.seek_handler_id = self.seek.connect("value-changed",
                                                 self.handle_seek)
        self.prog_view.connect("button-press-event",
                               self.__handle_prog_view_click)

        self.loop_thr = Thread(target=self.__gst_loop)
        self.loop_thr.daemon = True
        self.loop_thr.start()
        glib.timeout_add(1000, self.handle_tick)
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

    def __quit(self, *_ignore: Any) -> None:
        self.win.destroy()
        self.stop()
        self.gstloop.quit()
        gtk.main_quit()

    def __handle_prog_view_click(self, _widget, evt: gdk.Event) -> None:
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
        db = self.__get_db()
        prog: Optional[Program] = db.program_get_by_id(prog_id)
        if prog is None:
            self.log.error("Did not find Program %d in database", prog_id)
            return None

        edit_item = gtk.MenuItem.new_with_mnemonic("_Edit")
        play_item = gtk.MenuItem.new_with_mnemonic("_Play")

        edit_item.connect("activate", self.__mk_prog_edit_handler(prog))
        play_item.connect("activate", self.__mk_prog_play_handler(prog))

        menu: gtk.Menu = gtk.Menu()
        menu.append(edit_item)
        menu.append(play_item)

        return menu

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

    def __mk_prog_play_handler(self, prog: Program) -> Callable:
        def handler(*_ignore: Any) -> None:
            self.play_program(prog)

        return handler

    def __mk_prog_edit_handler(self, prog: Program) -> Callable:
        def handler(*_ignore: Any) -> None:
            self.log.debug("Edit Program %s: IMPLEMENTME",
                           prog.title)
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
        """Scan a single directory tree.
        This method is meant to be called in a background thread."""

        sc = scanner.Scanner()

        try:
            self.log.debug("Start scanning %s", path)
            sc.scan(path)
            # files = sc.db.file_get_by_folder(folder)  # noqa: F841
        finally:
            self.log.debug("Finished scanning %s", path)

    def display_msg(self, msg: str) -> None:
        """Display a message in a dialog."""
        self.log.info(msg)

        dlg = gtk.Dialog(
            parent=self.win,
            title="Attention",
            modal=True,
        )

        dlg.add_buttons(
            gtk.STOCK_OK,
            gtk.ResponseType.OK,
        )

        area = dlg.get_content_area()
        lbl = gtk.Label(label=msg)
        area.add(lbl)
        dlg.show_all()  # pylint: disable-msg=E1101

        try:
            dlg.run()  # pylint: disable-msg=E1101
        finally:
            dlg.destroy()

    def handle_player_msg(self, _bus, msg) -> None:
        """React to messages sent by the Player"""
        mtype = msg.type
        # self.log.debug("Got Message from Player: %s", mtype)
        match mtype:
            case gst.MessageType.EOS:
                db = self.__get_db()
                with self.lock:
                    if self.prog is None:
                        return
                    if self.playidx < len(self.playlist):
                        self.playidx += 1
                        self.play_file(self.playlist[self.playidx])
                        fid: Final[int] = self.playlist[self.playidx].file_id
                        db.program_set_cur_file(self.prog,
                                                fid)
                    else:
                        db.program_set_cur_file(self.prog, -1)
                        self.prog = None
                        self.playlist = []
                        self.playidx = 0
                        self.state = PlayerState.STOPPED
                        self.format_status_line()
            case gst.MessageType.ERROR:
                self.stop()
                err, debug = msg.parse_error()
                m = f"GStreamer signalled an error: {err} - {debug}"
                self.log.error(m)
                self.display_msg(m)

    def handle_tick(self) -> bool:
        """Update the slider for seeking."""
        try:
            self.format_status_line()
            with self.lock:
                if self.state != PlayerState.PLAYING:
                    return True
                success, duration = self.player.query_duration(gst.Format.TIME)
                if not success:
                    self.log.error("Cannot query track duration")
                    return True
                self.seek.set_range(0, duration / gst.SECOND)
                success, position = self.player.query_position(gst.Format.TIME)
                if not success:
                    self.log.error("Cannot query playback position")
                    return True
                self.seek.handler_block(self.seek_handler_id)
                self.seek.set_value(float(position) / gst.SECOND)
                self.seek.handler_unblock(self.seek_handler_id)
                db = self.__get_db()
                f: File = self.playlist[self.playidx]
                pos: int = int(position / gst.SECOND)
                with db:
                    db.file_set_position(f, pos)
        finally:
            return True  # noqa: B012 pylint: disable-msg=W0134,W0150

    def handle_seek(self, _ignore: gtk.Widget) -> None:
        """Seek to the selected position."""
        new_pos: Final[float] = self.seek.get_value()
        self.player.seek_simple(gst.Format.TIME,
                                gst.SeekFlags.FLUSH | gst.SeekFlags.KEY_UNIT,
                                new_pos * gst.SECOND)

    def format_position(self, _ignore: gtk.Widget, pos: float) -> str:
        """Format the position for the seek Scale as HH:MM:ss"""
        hours: int = 0
        minutes: int = 0
        seconds: int = int(pos)

        if seconds >= 3600:
            hours, seconds = divmod(seconds, 3600)
        if seconds >= 60:
            minutes, seconds = divmod(seconds, 60)
        return f"{hours:02d}:{minutes:02d}:{seconds:02d}"

    def format_status_line(self, txt: Optional[str] = None) -> None:
        """Update the status line.
        If playing or paused, display the program title, the track number
        and the title of the current track."""
        with self.lock:
            if txt is None:
                match self.state:
                    case PlayerState.PLAYING | PlayerState.PAUSED:
                        assert self.prog is not None
                        ptitle: Final[str] = self.prog.title
                        pidx: Final[int] = self.playidx + 1
                        ftitle: Final[str] = \
                            self.playlist[self.playidx].display_title()
                        status: Final[str] = \
                            f"{ptitle} - {pidx:4d} - {ftitle}"
                        self.slabel.set_label(status)
                    case _:
                        self.slabel.set_label("")
            else:
                self.slabel.set_label(txt)

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

    def play_program(self, prog: Program) -> None:
        """Start playing a Program"""
        db = self.__get_db()
        files: list[File] = db.file_get_by_program(prog.program_id)
        if len(files) == 0:
            self.display_msg(f"Program {prog.title} has 0 files")
            return

        self.log.debug("Play Program %s (%d files)",
                       prog.title,
                       len(files))
        with self.lock:
            self.prog = prog
            self.playlist = files
            if prog.current_file < 1:
                self.log.debug("Play Program %s from the beginning",
                               prog.title)
                db.program_set_cur_file(prog, files[0].file_id)
                self.playidx = 0
            else:
                self.log.debug("Current file is %d, looking for index",
                               prog.current_file)
                success: bool = False
                for i in range(len(files)):  # pylint: disable-msg=C0200
                    if prog.current_file == files[i].file_id:
                        self.log.debug("Current file is %s, index %d",
                                       files[i].display_title(),
                                       i)
                        self.playidx = i
                        success = True
                        break
                if not success:
                    self.log.error("Did not find current track in list, starting from beginning")  # noqa: E501 pylint: disable-msg=C0301
                    prog.current_file = -1
                    self.play_program(prog)
                    return
        self.play_file(files[self.playidx])
        self.format_status_line()

    def play_previous(self, _ignore) -> None:
        """Skip backwards one track in the playlist."""
        self.log.debug("Skipping backwards one title.")
        db = self.__get_db()
        with self.lock:
            if len(self.playlist) == 0:
                self.log.info("Playlist is empty.")
                return
            if self.playidx == 0:
                self.log.info("We are at the beginning of playlist")
                return
            if self.prog is None:
                self.log.info("No Program is currently playing.")
                return
            self.playidx -= 1
        db.program_set_cur_file(self.prog,
                                self.playlist[self.playidx].file_id)
        self.play_file(self.playlist[self.playidx])
        self.format_status_line()

    def play_next(self, _ignore) -> None:
        """Skip forward one track in the playlist."""
        self.log.debug("Skipt to next track")
        db = self.__get_db()
        with self.lock:
            if len(self.playlist) == 0:
                self.log.info("Playlist is empty.")
                return
            if self.playidx == len(self.playlist) - 1:
                self.log.info("Playing last track")
                return
            if self.prog is None:
                self.log.info("No Program is currently playing.")
                return
            self.playidx += 1
        db.program_set_cur_file(self.prog,
                                self.playlist[self.playidx].file_id)
        self.play_file(self.playlist[self.playidx])
        self.format_status_line()

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
            self.format_status_line()

    def stop(self, *_ignore) -> None:
        """Stop the player (if it's playing)"""
        with self.lock:
            self.state = PlayerState.STOPPED
            self.player.set_state(gst.State.NULL)
            self.seek.handler_block(self.seek_handler_id)
            self.seek.set_range(0, 0)
            self.seek.set_value(0)
            self.seek.handler_unblock(self.seek_handler_id)
            self.format_status_line("")

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
        dlg.show_all()  # pylint: disable-msg=E1101

        try:
            response = dlg.run()  # pylint: disable-msg=E1101
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


def cmp_iter(m: gtk.TreeModel, a, b: gtk.TreeIter, _) -> int:
    """Comparison function for sorting."""
    v1 = m.get(a, 0, 1, 2, 3, 4, 5, 6)
    v2 = m.get(b, 0, 1, 2, 3, 4, 5, 6)
    res: int = 0
    match (sign(v1[0]), sign(v2[0])):
        case (1, 1):
            res = cmp(v1[0], v2[0])
        case (-1, -1):
            if v1[0] == v2[0]:
                match cmp(v1[4], v2[4]):
                    case -1:
                        res = -1
                    case 1:
                        res = 1
                    case 0:
                        res = cmp(v1[5], v2[5])
            else:
                res = cmp(v2[0], v1[0])
        case (1, -1):
            res = cmp(v1[0], -v2[0])
        case (-1, 1):
            res = cmp(-v1[0], v2[0])

    return res


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
