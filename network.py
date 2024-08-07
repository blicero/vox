#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Time-stamp: <2024-08-07 18:28:22 krylon>
#
# /data/code/python/vox/network.py
# created on 05. 08. 2024
# (c) 2024 Benjamin Walkenhorst
#
# This file is part of the Vox audiobook reader. It is distributed under the
# terms of the GNU General Public License 3. See the file LICENSE for details
# or find a copy online at https://www.gnu.org/licenses/gpl-3.0

"""
vox.network

(c) 2024 Benjamin Walkenhorst
"""

from socket import gethostname
from typing import Final

from zeroconf import ServiceBrowser, ServiceListener, Zeroconf

DefaultPort: Final[int] = 5281


class VoxListener(ServiceListener):
    """Represent."""

    def update_service(self, zc: Zeroconf, type_: str, name: str) -> None:
        print(f"Service {name} updated")

    def remove_service(self, zc: Zeroconf, type_: str, name: str) -> None:
        print(f"Service {name} removed")

    def add_service(self, zc: Zeroconf, type_: str, name: str) -> None:
        info = zc.get_service_info(type_, name)
        print(f"Service {name} added, service info: {info}")


class Network:
    """Network provides discovery and synchronization across multiple devices."""

    __slots__ = [
        "hostname",
        "mdns",
    ]

    hostname: str
    mdns: Zeroconf

    def __init__(self) -> None:
        self.hostname = gethostname()
        self.mdns = Zeroconf()


if __name__ == '__main__':
    zc = Zeroconf()
    listener = VoxListener()
    browser = ServiceBrowser(zc, "_http._tcp.local.", listener)
    try:
        input("Press enter to quit.\n\n")
    finally:
        zc.close()

# Local Variables: #
# python-indent: 4 #
# End: #
