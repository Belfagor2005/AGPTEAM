# -*- coding: utf-8 -*-

from os.path import exists
from subprocess import run, CalledProcessError, TimeoutExpired
from Components.Converter.Converter import Converter
from Components.Element import cached
import logging

# update from #lululla 20250401

"""
<!-- Verifica qualsiasi VPN attiva -->
<widget
    source="session.VideoPicture"
    render="Label"
    position="100,100"
    size="200,25">
    <convert type="AglareVpn">vpn</convert>
</widget>

<!-- Verifica solo WireGuard -->
<widget
    source="session.VideoPicture"
    render="Label"
    position="100,130"
    size="200,25">
    <convert type="AglareVpn">wireguard</convert>
</widget>

<!-- Verifica solo OpenVPN -->
<widget
    source="session.VideoPicture"
    render="Label"
    position="100,160"
    size="200,25">
    <convert type="AglareVpn">openvpn</convert>
</widget>

"""


class AglareVpn(Converter):
    """
    VPN Status Converter for Enigma2
    Detects active VPN connections (WireGuard and OpenVPN)
    """

    VPNLOAD = 0
    VPN_TYPE_WIREGUARD = 1
    VPN_TYPE_OPENVPN = 2

    def __init__(self, type):
        Converter.__init__(self, type)
        self.logger = logging.getLogger("AglareVpn")
        self.type = self.VPNLOAD
        self.vpn_type = None
        self.timeout = 2  # seconds for command timeout

        # Detect available VPN services
        self.has_wireguard = exists("/usr/bin/wg")
        self.has_openvpn = exists(
            "/usr/sbin/openvpn") or exists("/var/run/openvpn")

        if type == "wireguard":
            self.vpn_type = self.VPN_TYPE_WIREGUARD
        elif type == "openvpn":
            self.vpn_type = self.VPN_TYPE_OPENVPN

    @cached
    def getBoolean(self):
        """Check for active VPN connection"""
        try:
            # Check specific VPN type if specified
            if self.vpn_type == self.VPN_TYPE_WIREGUARD:
                return self._check_wireguard()
            elif self.vpn_type == self.VPN_TYPE_OPENVPN:
                return self._check_openvpn()

            # Auto-detect VPN type
            if self.has_wireguard and self._check_wireguard():
                return True
            if self.has_openvpn and self._check_openvpn():
                return True

        except (CalledProcessError, FileNotFoundError, TimeoutExpired, Exception) as e:
            self.logger.warning("Error checking VPN status: " + str(e))

        return False

    def _check_wireguard(self):
        """Check WireGuard VPN status"""
        try:
            result = run(
                ["ip", "link", "show", "wg0"],
                capture_output=True,
                text=True,
                timeout=self.timeout
            )
            return result.returncode == 0 and "wg0" in result.stdout
        except Exception as e:
            self.logger.debug("WireGuard check failed: " + str(e))
            return False

    def _check_openvpn(self):
        """Check OpenVPN status"""
        try:
            # First check for tun0 interface
            result = run(
                ["ip", "link", "show", "tun0"],
                capture_output=True,
                text=True,
                timeout=self.timeout
            )
            if result.returncode == 0 and "tun0" in result.stdout:
                return True

            # Fallback to checking process or status file
            if exists("/var/run/openvpn"):
                return True

            # Check running processes
            result = run(
                ["pgrep", "-x", "openvpn"],
                capture_output=True,
                timeout=self.timeout
            )
            return result.returncode == 0

        except Exception as e:
            self.logger.debug("OpenVPN check failed: " + str(e))
            return False

    boolean = property(getBoolean)

    def changed(self, what):
        """Handle change notifications"""
        Converter.changed(self, what)

    def destroy(self):
        """Clean up resources"""
        self.logger = None
        super().destroy()
