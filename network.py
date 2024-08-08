#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Time-stamp: <2024-08-08 18:33:25 krylon>
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
from threading import RLock
from typing import Final

from zeroconf import IPVersion, ServiceInfo, ServiceListener, Zeroconf

DefaultPort: Final[int] = 5281


class VoxListener(ServiceListener):
    """Represent."""

    def update_service(self, zc: Zeroconf, type_: str, name: str) -> None:
        """Update a Service definition."""
        print(f"Service {name} updated")

    def remove_service(self, zc: Zeroconf, type_: str, name: str) -> None:
        """Remove a Service definition."""
        print(f"Service {name} removed")

    def add_service(self, zc: Zeroconf, type_: str, name: str) -> None:
        """Add a Service definition."""
        info = zc.get_service_info(type_, name)
        print(f"Service {name} added, service info: {info}")


class Network:
    """Network provides discovery and synchronization across multiple devices."""

    __slots__ = [
        "hostname",
        "mdns",
        "info",
        "lock",
        "active",
        "peers",
    ]

    hostname: str
    mdns: Zeroconf
    info: ServiceInfo
    lock: RLock
    active: bool
    peers: dict

    def __init__(self) -> None:
        self.hostname = gethostname()
        self.mdns = Zeroconf(ip_version=IPVersion.All)
        self.lock = RLock()
        self.active = False
        self.peers = {}

        self.info = ServiceInfo(
            "_http._tcp.local.",
            f"vox@{self.hostname}._http._tcp.local.",
            port=DefaultPort,
        )

    def __enter__(self) -> None:
        self.start()

    def __exit__(self, ex_type, ex_val, traceback) -> None:
        self.stop()

    def start(self) -> None:
        """Publish the service info."""
        with self.lock:
            self.active = True
            self.mdns.register_service(self.info)

    def stop(self) -> None:
        """Un-publish the service info."""
        with self.lock:
            self.active = True
            self.mdns.unregister_service(self.info)
            self.mdns.close()


if __name__ == '__main__':
    nw = Network()

    with nw:
        input("Press enter to quit.\n\n")

# Local Variables: #
# python-indent: 4 #
# End: #
