from library import bar, compatibility, config, ini, lang, log, queue

from os import path
from json import load
from threading import Thread, Event
from asyncio import get_event_loop, sleep
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import QLabel, QWidgetAction, QAction
from paramiko import SSHClient, AutoAddPolicy, ssh_exception


# noinspection PyPep8Naming, PyMethodMayBeStatic
class Base(metaclass=config.Singleton):
    """ Base class for periphery manager """
    def __init__(self, base, ip_addr):
        self._base = base
        self._ip_addr = ip_addr

        self._dmn_config = ini.Daemon(self._base, self._ip_addr)

        self._heading = ('Global', 'Local')
        self._lang = None
        for heading in self._heading:
            setattr(self, f'_get{heading}Heading', self._get_heading(heading))

    def _get_heading(self, heading):
        """ Function template for separator instance """
        def _template():
            """ Peripheral action separator - generator """
            _label = QLabel(getattr(self._lang, f'Action{heading}Heading'))
            _label.setStyleSheet('QLabel {color: gray;}')
            _label.setAlignment(Qt.AlignCenter)
            _action = QWidgetAction(None)
            _action.setDefaultWidget(_label)
            _action.setObjectName(f'{self._lang.__name__}{heading}')
            yield _action
        return _template

    def _getGlobalHeading(self):
        """ Global peripheral action separator - dummy function to resolve reference issue """
        yield from ()

    def _getLocalHeading(self):
        """ Local peripheral action separator - dummy function to resolve reference issue """
        yield from ()


# noinspection PyPep8Naming
class SSH(Base, metaclass=config.Singleton):
    """ SSH connection manager """
    def __init__(self, base, ip_addr):
        super().__init__(base, ip_addr)
        self._loop = get_event_loop()

        self._manager = queue.Manager(self._base)
        self._name = f'SSH connection : {self._ip_addr}'

        self._log = log.Manager(self._base)
        self._lang = lang.SSH
        self._ssh_param = f'{self._ip_addr}:{self._dmn_config.ssh_port}'

        self._connection = SSHClient()
        self._connection.set_missing_host_key_policy(AutoAddPolicy())

    def _action_param(self, param):
        """ Switch-case structure - get action type depending on the current connection state """
        return {
            False: self._open,
            True: self.close
        }.get(param)

    def _exec(self):
        """ Open the SSH connection - daemon thread """
        try:
            self._connection.connect(
                self._ip_addr,
                self._dmn_config.ssh_port,
                self._dmn_config.ssh_usr,
                self._dmn_config.ssh_pwd
            )
        except ssh_exception.NoValidConnectionsError:
            self._log.setError(f'{self._lang.LogSeparator} {self._ssh_param} : {self._lang.NoValidConnectionsError}')
        except ssh_exception.AuthenticationException:
            self._log.setError(f'{self._lang.LogSeparator} {self._ssh_param} : {self._lang.AuthenticationException}')
        else:
            self._log.setSuccess(f'{self._lang.LogSeparator} {self._ssh_param} : {self._lang.OpenSuccess}')
        return self._event.set()

    def __open(self):
        """ Open the SSH connection - inner function """
        self._event = Event()
        self._thread = Thread(target=self._exec, name=self._name)
        self._thread.start()
        self._event.wait()
        return self._connection.get_transport()

    def action(self):
        """ Global/Local daemon action over SSH - generator """
        for action in self._getGlobalHeading():
            yield action

        _trigger = self._action_param(self.isOpen())
        _name = _trigger.__name__.strip('_')
        _icon = QIcon(f'icon/ssh_{_name}.png')
        _lang = getattr(self._lang, f'ActionGlobal{_name.capitalize()}')
        _action = QAction(_icon, f'{_lang}')
        _action.setObjectName(f'{_name}')
        _action.triggered.connect(lambda __bool: _trigger())
        yield _action

        for action in self._getLocalHeading():
            yield action

        yield from ()

    def _open(self):
        """ Open the SSH connection - calling coroutine """
        self._manager.exec(self.open, self._name)

    async def open(self):
        """ Open the SSH connection - coroutine """
        if not self._dmn_config.ssh:
            return self._log.setError(f'{self._lang.LogSeparator} {self._ssh_param} : {self._lang.EnableRequired}')

        if self.isOpen():
            return self._log.setError(f'{self._lang.LogSeparator} {self._ssh_param} : {self._lang.AforeOpen}')

        return await self._loop.run_in_executor(None, self.__open)

    def close(self):
        """ Close the SSH connection """
        if not self._dmn_config.ssh:
            return self._log.setError(f'{self._lang.LogSeparator} {self._ssh_param} : {self._lang.EnableRequired}')

        if not self.isOpen():
            return self._log.setError(f'{self._lang.LogSeparator} {self._ssh_param} : {self._lang.AforeClose}')

        self._connection.close()
        if not self.isOpen():
            return self._log.setWarning(f'{self._lang.LogSeparator} {self._ssh_param} : {self._lang.CloseSuccess}')
        return self._log.setError(f'{self._lang.LogSeparator} {self._ssh_param} : {self._lang.CloseError}')

    def isOpen(self):
        """ Check if the SSH connection is open """
        return self._connection.get_transport() is not None

    async def establish(self, message):
        """ Check if the SSH connection is close / Establish connection """
        if not self.isOpen():
            self._log.setInformation(f'{message} {self._ip_addr} : {self._lang.ConnectionRequired}')
            await self.open()
        return self.isOpen()

    def exec(self, action):
        """ Execute a custom action over the SSH connection / Get the PID """
        if not self.isOpen():
            return None, None, None, None
        _stdin, _stdout, _stderr = self._connection.exec_command(f'echo $$; exec {action}')
        _pid = _stdout.readline().strip()
        return _pid, _stdin, _stdout, _stderr

    def kill(self, pid):
        """ Kill the long-running action over SSH connection """
        return self.exec(f'sudo kill {pid}')

    # noinspection PyMethodMayBeStatic
    def isError(self, channel):
        """ Get the exit status from the action on the daemon """
        # TODO Checking code for everything
        return channel.channel.recv_exit_status()


# noinspection PyPep8Naming
class USB(Base, metaclass=config.Singleton):
    """ USB device recharging manager """
    def __init__(self, base, obj, ip_addr):
        super().__init__(base, ip_addr)
        self._obj = obj

        self._loop = get_event_loop()

        self._manager = queue.Manager(self._base)
        self._rchrg_name = f'USB recharge : {self._ip_addr}'
        self._glob_rchrg_name = f'USB global recharge : {self._ip_addr}'

        self._bar = bar.Manager(self._obj.progress)

        self._usb_comp = compatibility.USB(self._base, self._ip_addr)

        self._ssh = SSH(self._base, self._ip_addr)

        self._log = log.Manager(self._base)
        self._lang = lang.USB

        self._rchrg = list()

    async def __actionGlobal(self):
        """ Recharge the entire USB hub - coroutine """
        if not await self._ssh.establish(self._lang.LogSeparator):
            return self._log.setInformation(f'{self._lang.LogSeparator} {self._ip_addr} : {self._lang.RechargeCancel}')

        _ep = 100 / len(self._rchrg)
        _span = self._dmn_config.hub_cfg_tmo
        for device in self._rchrg:
            _location, _hole = device
            self.recharge(_location, _hole, _ep, False)
            await sleep(_span + 0.25)

    def __recharge(self, location, hole):
        """ Recharge the USB device - inner function """
        self._ssh.exec(self._usb_comp.off(location, hole))
        _query = self._usb_comp.on(location, hole)
        _echo = self._ssh.exec(_query)
        if not all(_echo):
            return self._log.setError(
                f'{self._lang.LogSeparator} {self._ip_addr} : {self._lang.RechargeQuery} : {_query}')
        _pid, _stdin, _stdout, _stderr = _echo
        _param = self._ssh.isError(_stdout)
        _log, _message = self._action_param(_param)
        return _log(f'{self._lang.LogSeparator} {self._ip_addr} : {_message} : ID {location} #{hole}')

    def _action_param(self, param):
        """ Switch-case structure - get message type depending on the SSH received exit status """
        return {
            0: (self._log.setSuccess, self._lang.RechargeSuccess),
            1: (self._log.setError, self._lang.RechargeError)
        }.get(param, 0)

    def _actionGlobal(self):
        """ Recharge the entire USB hub - calling coroutine """
        self._manager.exec(self.__actionGlobal, self._glob_rchrg_name)

    async def _recharge(self, location, hole, ep=None, hang=True):
        """ Recharge the USB device - coroutine """
        if not await self._ssh.establish(self._lang.LogSeparator):
            return self._log.setInformation(f'{self._lang.LogSeparator} {self._ip_addr} : {self._lang.RechargeCancel}')

        _span = self._dmn_config.hub_cfg_tmo
        self._bar.setRange(_span, ep, self._obj.menu)
        await self._loop.run_in_executor(None, self.__recharge, location, hole)
        if hang:
            await sleep(_span)

    def action(self):
        """ Global/Local USB device recharge action - generator """
        for action in self._getGlobalHeading():
            yield action

        _action = QAction(QIcon('icon/reload.png'), f'{self._lang.ActionGlobalRecharge}')
        _action.setEnabled(self._dmn_config.ssh)
        _action.setObjectName(f'{self._lang.__name__}')
        _action.triggered.connect(lambda __bool: self._actionGlobal())
        yield _action

        for action in self._getLocalHeading():
            yield action

        try:
            with open(path.join('hub', f'{self._dmn_config.hub_cfg}.json')) as fp:
                _hub_cfg = load(fp)
        except FileNotFoundError:
            return

        self._rchrg = list()
        for location in _hub_cfg:
            _hub_param = _hub_cfg[location]
            for hole in _hub_param:
                _active, _name = _hub_param[hole]
                if not _active:
                    continue
                _icon = QIcon('icon/reload_single.png')
                _action = QAction(_icon, f'{self._lang.ActionLocalRecharge} : ID {location} #{hole}')
                if _name:
                    _action.setText(f'{_action.text()} : [{_name}]')
                _action.setEnabled(self._dmn_config.ssh)
                _action.setObjectName(f'{location}{hole}')
                _action.triggered.connect(
                    lambda __bool, __location=location, __hole=hole: self.recharge(__location, __hole))
                self._rchrg.append((location, hole))
                yield _action

    def recharge(self, location, hole, ep=None, hang=True):
        """ Recharge the USB device - calling coroutine """
        self._manager.exec(self._recharge, self._rchrg_name, location, hole, ep, hang)
