from library import compatibility, config, device, ini, log, periphery, queue, usbip
from library.lang import LangDaemon
from library.modal.DaemonConfig import DaemonConfigUI

from collections import namedtuple
from PyQt5 import uic
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import QWidget, QMenu, QWidgetAction, QAction
from asyncio import create_subprocess_shell, subprocess, wait_for, open_connection, TimeoutError

#
_popup_action = ('poweroff', 'reload', 'unload')

# Maximum quantity of a USB device OUT/IN endpoints pairs
_maxlen = 16

#
_usbip_field = ['bid_0', 'name_0', 'location_0', 'descriptor_0'] + [f'ep_{idx}' for idx in range(_maxlen)]
_usbip_param = namedtuple('usbip_param', _usbip_field, defaults=(None,) * len(_usbip_field))


class USBIParam(_usbip_param):
    """ USBIP parser parameters printable class representation for queue manager modal window """
    # noinspection PyUnresolvedReferences
    def __repr__(self):
        return self.bid_0


#
_parser_param = namedtuple('parser_param', 'name idx maxlen')
_parser_config = (
    _parser_param(('bid', 'name'), (0, 1), 1),
    _parser_param(('location', ), (1, ), 1),
    _parser_param(('descriptor', ), (1, ), 1),
    _parser_param(('ep', ), (1, ), _maxlen)
)


# noinspection PyPep8Naming
class UIObj(QWidget):
    """ USBIP daemon object """
    def __init__(self, base, ip_addr):
        super(UIObj, self).__init__(parent=base)
        uic.loadUi('ui/widget/daemon.ui', self)

        self.setAttribute(Qt.WA_DeleteOnClose)

        self._base = base
        self._ip_addr = ip_addr

        self.setObjectName(self._ip_addr)

        self._is_online = False

        self._matching = ('Exportable USB devices', '======================', f'- {self._ip_addr}')

        self._sw_config = ini.SWConfig(self._base)

        self._manager = queue.Manager(self._base)
        self._search_name = f'Daemon search : {self._ip_addr}'
        self._attach_name = f'Daemon attach : {self._ip_addr}'
        self._detach_name = f'Daemon detach : {self._ip_addr}'

        self._log = log.Manager(self._base)
        self._lang = LangDaemon

        self._ssh = periphery.SSH(self._base, self._ip_addr)
        self._usb = periphery.USB(self._base, self, self._ip_addr)
        self.phy_interface = (self._ssh, self._usb)
        self.usbip_interface = list()

        self._usbip_comp = compatibility.USBIP(self._base)

        self._menu_popup = QMenu()
        for param in _popup_action:
            _icon = QIcon(f'icon/{param}.png')
            _lang = getattr(self._lang, f'Popup{param.capitalize()}')
            setattr(self, f'_action_{param}', QAction(_icon, f'{_lang} {self._ip_addr}', self.frame))
            _action = getattr(self, f'_action_{param}')
            _action.triggered.connect(getattr(self, f'_{param}'))
            self._menu_popup.addAction(_action)

        self._menu_phy = QMenu()
        self._menu_phy.aboutToShow.connect(lambda: self._interface_reload('phy'))
        self.phy_btn.setMenu(self._menu_phy)

        self.frame.setContextMenuPolicy(Qt.CustomContextMenu)
        self.frame.customContextMenuRequested.connect(self._popup_show)

        self.search_btn.clicked.connect(self.search)
        self.config_btn.clicked.connect(self.config)

    def __repr__(self):
        """ Printable class representation for queue manager modal window """
        return f'{self.__class__.__name__}'

    def _popup_reload(self):
        """ Get the current status of global/local action and reload the right-click popup menu """
        # TODO Checking for SSH configuration
        pass

    def _interface_reload(self, name):
        """ Get the current status of global/local action and reload the dropdown periphery/usbip menu """
        _seq = getattr(self, f'{name}_interface')
        _btn = getattr(self, f'{name}_btn')
        _menu = getattr(self, f'_menu_{name}')

        for action in _btn.findChildren(QAction):
            action.deleteLater()
            action.setParent(None)

        for interface in _seq:
            for action in interface.action():
                if _btn.findChildren(QWidgetAction, action.objectName()):
                    continue
                if _btn.findChildren(QAction, action.objectName()):
                    continue
                action.setParent(_btn)
                _menu.addAction(action)

    def _iterator(self, clean):
        """ Yield a found device from the decoded stdout/stderr output """
        for section in clean.split(self._usbip_comp.section()):
            row = list(map(str.strip, section.split(self._usbip_comp.row())))
            matching = [idx for idx, value in enumerate(self._matching) if value in row]
            if matching:
                for idx in matching:
                    row.remove(self._matching[idx])
            yield list(filter(None, row))

    async def _search(self):
        """ Search for available for attaching device - coroutine """
        self._log.setInformation(f'{self._lang.LogSeparator} {self._ip_addr} : {self._lang.SearchExec}')
        if not self.isOnline():
            return self._log.setWarning(f'{self._lang.LogSeparator} {self._ip_addr} : {self._lang.SearchOffline}')

        self.menu.setEnabled(False)
        self.usbip_btn.setMenu(None)
        self.usbip_btn.setEnabled(False)

        _proc = await create_subprocess_shell(
            self._usbip_comp.search(self._ip_addr),
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        await _proc.wait()

        raw = await self._usbip_comp.pipe(_proc).read()
        clean = raw.decode('utf-8')

        self._menu_usbip = QMenu()
        self._menu_usbip.aboutToShow.connect(lambda: self._interface_reload('usbip'))

        for idx, usbip_device in enumerate(self.usbip_interface):
            if not usbip_device.isBound():
                del self.usbip_interface[idx]

        for row in self._iterator(clean):
            if not row:
                break
            _usbip_value = {}
            for param in _parser_config:
                for idx in range(param.maxlen):
                    try:
                        _config = row.pop(0).split(':')
                    except IndexError:
                        break
                    for name, index in zip(param.name, param.idx):
                        _usbip_value[f'{name}_{idx}'] = _config[index].strip()

            _usbip = usbip.Device(self._base, self, self._ip_addr, USBIParam(**_usbip_value))
            self.usbip_interface.append(_usbip)

        if self.usbip_interface:
            self.usbip_btn.setMenu(self._menu_usbip)
            self.usbip_btn.setEnabled(True)

        self.menu.setEnabled(True)

    def _popup_show(self, coordinate):
        """ Show the right-click popup menu in the object box """
        self._popup_reload()
        self._menu_popup.exec_(self.frame.mapToGlobal(coordinate))

    def _poweroff(self):
        """ Poweroff the daemon """
        pass

    def _reload(self):
        """ Reload the daemon """
        pass

    def _unload(self):
        """ Unload the USBIP daemon object from the layout and from the configuration """
        pass

    def setTitle(self, title):
        """ Set the object group box title """
        self.menu.setTitle(title)

    def setOnline(self):
        """ Set online status - green highlighting """
        self.menu.setStyleSheet('QGroupBox {color: green;}')
        self.search_btn.setEnabled(True)
        self.phy_btn.setEnabled(True)
        self._action_poweroff.setEnabled(True)
        self._action_reload.setEnabled(True)
        self._is_online = True

    def setOffline(self):
        """ Set offline status - red highlighting """
        self.menu.setStyleSheet('QGroupBox {color: red;}')
        self.search_btn.setEnabled(False)
        self.phy_btn.setEnabled(False)
        self.usbip_btn.setEnabled(False)
        self.usbip_btn.setMenu(None)
        self._action_poweroff.setEnabled(False)
        self._action_reload.setEnabled(False)
        self._is_online = False

    def setPending(self):
        """ Set pending status - orange highlighting """
        self.menu.setStyleSheet('QGroupBox {color: orange;}')

    def isOnline(self):
        """ Check if the daemon is available """
        return self._is_online

    def search(self):
        """ Search for available for attaching device - calling coroutine """
        self._manager.exec(self._search, self._search_name)

    def config(self):
        """ Open the USBIP daemon configuration modal window """
        _dialog = DaemonConfigUI(self._base, self._ip_addr)
        _dialog.show()


# noinspection PyPep8Naming
class Manager(metaclass=config.Singleton):
    """ USBIP daemon manager """
    def __init__(self, base, ip_addr):
        self._base = base
        self._ip_addr = ip_addr

        self._sw_config = ini.SWConfig(self._base)

        self._dmn_config = ini.Daemon(self._base, self._ip_addr)
        self._dmn_ui = None

        self._ssh = periphery.SSH(self._base, self._ip_addr)
        self._top = device.USBTop(self._base, self._ip_addr)
        self._interface = {
            self._ssh: (self._ssh.isOpen, self._ssh.close),
            self._top: (self._top.isRunning, self._top.cancel)
        }

        self._log = log.Manager(self._base)
        self._lang = LangDaemon

    def load(self):
        """ Load the USBIP daemon object into the layout """
        _title = f'{self._ip_addr}:{self._dmn_config.dmn_port}'
        if self._dmn_config.dmn_name:
            _title += f' [{self._dmn_config.dmn_name}]'

        self._dmn_ui = UIObj(self._base, self._ip_addr)
        self._dmn_ui.setTitle(_title)
        self._base.scroll_lyt.addWidget(self._dmn_ui)

    async def check(self):
        """ Check USBIP daemon availability """
        self._dmn_ui.setPending()
        try:
            reader, writer = await wait_for(open_connection(
                self._ip_addr, self._dmn_config.dmn_port), timeout=self._sw_config.dmn_perf_sock_tmo)
            writer.close()
            await writer.wait_closed()
            self._dmn_ui.setOnline()
        except (TimeoutError, OSError):
            self._dmn_ui.setOffline()
            # TODO Disconnect devices
            for interface in self._interface:
                _running, _cancel = self._interface[interface]
                if not _running():
                    continue
                self._log.setWarning(f'{self._lang.LogSeparator} {self._ip_addr} : {self._lang.CheckUnstable}')
                _cancel()

    def isExisting(self):
        """ Check if the USBIP daemon is existing """
        for obj in self._base.findChildren(UIObj):
            if self._ip_addr != obj.objectName():
                continue
            return obj
        return None

    def search(self):
        """ Search for available for attaching devices """
        if self.isExisting():
            self._dmn_ui.search()

    def config(self):
        """ Open the USBIP daemon configuration modal window """
        self._dmn_ui.config()

    def usbip_pool(self):
        """  """
        return self._dmn_ui.usbip_interface
