#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Time-stamp: <2023-11-08 08:26:03 krylon>
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

import gi

from vox import common, database

gi.require_foreign("Gtk", "3.0")
from gi.repository import \
    GdkPixbuf as gpb  # noqa: E402,E501,F401 # pylint: disable-msg=C0411,C0413,W0611
from gi.repository import \
    GLib as glib  # noqa: E402,E501,F401 # pylint: disable-msg=C0411,C0413,W0611
from gi.repository import Gtk as gtk  # noqa: E402,E501,F401 # pylint: disable-msg=C0411,C0413,W0611


# pylint: disable-msg=R0903
class VoxUI:
    """The graphical interface to the application, built using gtk3"""

    def __init__(self):
        self.log = common.get_logger("GUI")
        self.db = database.Database(common.path.db())

        # Create widgets
        self.win = gtk.Window()
        self.mbox = gtk.Box(orientation=gtk.Orientation.VERTICAL)
        self.menubar = gtk.MenuBar()
        # menu stuff tbd ...
        self.notebook = gtk.Notebook()
        self.page1 = gtk.Box()
        # self.prog_view = 

# Local Variables: #
# python-indent: 4 #
# End: #
