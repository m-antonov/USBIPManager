# This file is a part of the USBIPManager software
# library/compatibility.py
# Implements cross-platform compatibility
#
# Copyright (c) 2018-2019 Mikhail Antonov
# Repository: https://github.com/lompal/USBIPManager
# Documentation: https://gthb.in/blog/post/2019/9/5/35-usbip-manager-cross-platform-compatibility-api-reference

from library import config, ini

import asyncio
import subprocess
from sys import path
from platform import system
from collections import namedtuple


class Base(metaclass=config.Singleton):
    """ Base class for cross-platform compatibility """
    def __init__(self):
        self._platform = system()

    def _get_action(self, action):
        """ Function template for compatibility instance """
        def _template():
            """ Get compatibility parameter depending on the operating system """
            return {
                'Linux': getattr(self, f'_unix{action}'),
                'Windows': getattr(self, f'_win{action}')
            }.get(self._platform, getattr(self, f'_unix{action}'))
        return _template


# noinspection PyMethodMayBeStatic
class System(Base, metaclass=config.Singleton):
    """ Cross-platform system compatibility """
    def __init__(self):
        super(System, self).__init__()
        self._loop = None
        self._startupinfo = None

        # Generate functions for getting compatibility parameters by a template depending on the operating system
        self._actions = ('_loop', '_startupinfo')
        for action in self._actions:
            setattr(self, action, self._get_action(action))

    def _unix_loop(self):
        """  """
        return asyncio.get_event_loop()

    def _win_loop(self):
        """  """
        _param = asyncio.ProactorEventLoop()
        asyncio.set_event_loop(_param)
        return _param

    def _unix_startupinfo(self):
        """  """
        return None

    def _win_startupinfo(self):
        """  """
        _param = subprocess.STARTUPINFO()
        _param.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        return _param

    def loop(self):
        """  """
        return self._loop()()

    def startupinfo(self):
        """  """
        return self._startupinfo()()


class USBIP(Base, metaclass=config.Singleton):
    """ Cross-platform USBIP compatibility """
    def __init__(self, base):
        super(USBIP, self).__init__()
        self._base = base

        self._sw_config = ini.SWConfig(self._base)

        self._version_type = namedtuple('version_type', 'original barbalion cezanne')

        self._unix_section = self._version_type('\r\n\r\n', '\r\n\r\n', '\r\n\r\n')
        self._win_section = self._version_type('\r\n \r\n', '\r\n \r\n', '\r\n\r\n')

        self._unix_row = self._version_type('\n', '\n', '\n')
        self._win_row = self._version_type('\r\n', '\r\n', '\r\n')

        self._unix_pipe = self._version_type('stdout', 'stdout', 'stdout')
        self._win_pipe = self._version_type('stderr', 'stderr', 'stdout')

        self._root = path[0]
        self._unix_path = self._version_type('/sbin/', '/sbin/', '/sbin/')
        self._win_path = self._version_type(
            f'{self._root}\\usbip\\original\\bin\\',
            f'{self._root}\\usbip\\barbalion\\bin\\',
            f'{self._root}\\usbip\\cezanne\\bin\\'
        )

        self._unix_seaq = self._version_type('list -r', 'list -r', 'list -r')
        self._win_seaq = self._version_type('-l', '-l', 'list -r')

        self._unix_atchq = self._version_type('attach -r {0} -b {1}', 'attach -r {0} -b {1}', 'attach -r {0} -b {1}')
        self._win_atchq = self._version_type('-a {0} {1}', '-a {0} {1}', 'attach -r {0} -b {1}')

        self._unix_dtchq = self._version_type('detach -p', 'detach -p', 'detach -p')
        self._win_dtchq = self._version_type('-d', '-d', 'detach -p')

        self._section = None
        self._row = None
        self._pipe = None
        self._path = None
        self._seaq = None
        self._atchq = None
        self._dtchq = None

        # Generate functions for getting compatibility parameters by a template depending on the operating system
        self._actions = ('_section', '_row', '_pipe', '_path', '_seaq', '_atchq', '_dtchq')
        for action in self._actions:
            setattr(self, action, self._get_action(action))

    def section(self):
        """  """
        return getattr(self._section(), self._sw_config.clt_ver)

    def row(self):
        """  """
        return getattr(self._row(), self._sw_config.clt_ver)

    def pipe(self, proc):
        """  """
        return getattr(proc, getattr(self._pipe(), self._sw_config.clt_ver))

    def search(self, ip_addr):
        """ Look for USBIP devices on the specific daemon """
        _clt = self._sw_config.clt_ver
        _path = getattr(self._path(), _clt)
        _seaq = getattr(self._seaq(), _clt)
        return f'{_path}usbip {_seaq} {ip_addr}'

    def attach(self, ip_addr, bid):
        """  """
        _clt = self._sw_config.clt_ver
        _path = getattr(self._path(), _clt)
        _atchq = getattr(self._atchq(), _clt)
        return f'{_path}usbip {_atchq.format(ip_addr, bid)}'

    def detach(self, port):
        """  """
        _clt = self._sw_config.clt_ver
        _path = getattr(self._path(), _clt)
        _dtchq = getattr(self._dtchq(), _clt)
        return f'{_path}usbip {_dtchq} {port}'


class USB(metaclass=config.Singleton):
    """ USB device recharging manager compatibility """
    def __init__(self, base, ip_addr):
        self._base = base
        self._ip_addr = ip_addr

        self._dmn_config = ini.Daemon(self._base, self._ip_addr)

        self._utl_type = namedtuple('utl_type', 'hubctrl uhubctl')

        self._loc = self._utl_type('-h', '-l')
        self._port = self._utl_type('-P', '-p')
        self._action = self._utl_type('-p', '-a')

        self.on = None
        self.off = None

        self._actions = {'on': 1, 'off': 0}
        for action in self._actions:
            setattr(self, action, self._get_action(action))

    def _get_action(self, action):
        """ Function template for compatibility instance """
        def _template(loc, port):
            """  """
            _utl = self._dmn_config.hub_cfg_utl
            _loc = getattr(self._loc, _utl)
            _port = getattr(self._port, _utl)
            _action = getattr(self._action, _utl)
            return f'sudo {_utl} {_loc} {loc} {_port} {port} {_action} {self._actions[action]}'
        return _template
