from library import bar, compatibility, config, device, ini, lang, log, performance, periphery, queue

from subprocess import Popen, PIPE
from concurrent.futures import ThreadPoolExecutor
from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import QAction
from asyncio import get_event_loop, sleep, create_subprocess_shell, subprocess

#
_usbip_action = ('atch', 'dtch')
_extra_param = ('busnum', 'devnum')


# noinspection PyPep8Naming
class Device(periphery.Base, metaclass=config.Singleton):
    """  """
    def __init__(self, base, obj, ip_addr, usbip_param):
        super().__init__(base, ip_addr)
        self._obj = obj
        self._ip_addr = ip_addr
        self._usbip_param = usbip_param

        self._loop = get_event_loop()

        self._sw_config = ini.SWConfig(self._base)

        self._manager = queue.Manager(self._base)
        self._atch_name = f'USBIP attach : {self._ip_addr} : {self.bID()}'
        self._dtch_name = f'USBIP detach : {self._ip_addr} : {self.bID()}'
        self._glob_atch_name = f'USBIP global attach : {self._ip_addr}'
        self._glob_dtch_name = f'USBIP global detach : {self._ip_addr}'
        self._num_name = f'Extra configuration : {self._ip_addr} : {self.bID()}'

        self._bar = bar.Manager(self._obj.progress)

        self._ssh = periphery.SSH(self._base, self._ip_addr)

        self._system_comp = compatibility.System()
        self._usbip_comp = compatibility.USBIP(self._base)

        self._enumeration = Enumerator()

        self._tree = device.Tree(self._base, self._ip_addr)
        self._top = device.USBTop(self._base, self._ip_addr)

        self._dmn_perf = performance.Device(self._base)

        self._log = log.Manager(self._base)
        self._lang = lang.USBIP

        self._is_bound = False

        self._idx = 1

        self._busnum = None
        self._devnum = None

    def _action_param(self, param):
        """  """
        return {
            False: self.atch,
            True: self.dtch
        }.get(param)

    def __atch(self):
        """ Attach device - inner function """
        _proc = Popen(
            self._usbip_comp.attach(self._ip_addr, self.bID()),
            stdin=PIPE,
            stdout=PIPE,
            stderr=PIPE,
            startupinfo=self._system_comp.startupinfo(),
            bufsize=0
        )
        _proc.communicate()

    async def __actionGlobal(self, action):
        """  """
        _offset = 100 / len(self._obj.usbip_interface)
        _tmo = getattr(self._sw_config, f'dev_{action}_tmo')
        for usbip in self._obj.usbip_interface:
            getattr(usbip, action)(_offset)
            await sleep(_tmo + 0.25)

    def _actionGlobal(self, action):
        """  """
        _name = getattr(self, f'_glob_{action}_name')
        self._manager.exec(self.__actionGlobal, _name, action)

    async def _atch(self, offset=None):
        """ Attach device - coroutine """
        self._bar.setRange(self._sw_config.dev_atch_tmo, offset, self._obj.menu)
        if self.isBound():
            return self._log.setWarning(
                f'{self._lang.LogSeparator} {self._ip_addr} : {self._lang.AforeAtch} : {self.bID()}')
        self._idx = self._enumeration.assign()
        self._is_bound = True
        with ThreadPoolExecutor(max_workers=1, thread_name_prefix=f'USBIP: {self._ip_addr} {self.bID()}') as pool:
            await self._loop.run_in_executor(pool, self.__atch)
        # TODO Hang after detach
        if self.isBound():
            self.dtch()

    async def _dtch(self, offset=None):
        """ Detach device - coroutine """
        self._bar.setRange(self._sw_config.dev_dtch_tmo, offset, self._obj.menu)
        if not self.isBound():
            return self._log.setWarning(
                f'{self._lang.LogSeparator} {self._ip_addr} : {self._lang.AforeDtch} : {self.bID()}')
        self._enumeration.displace(self._idx)
        self._is_bound = False
        _proc = await create_subprocess_shell(
            self._usbip_comp.detach(self._idx),
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        await _proc.wait()
        # TODO Hang after detach

    def __num(self):
        """ Get an extra device configuration from the daemon - inner function """
        for param in _extra_param:
            _query = f'sudo cat {self.dLocation()}/{param}'
            _echo = self._ssh.exec(_query)
            if not all(_echo):
                return self._log.setError(
                    f'{self._lang.LogSeparator} {self._ip_addr} : {self._lang.ExtraQuery} : {_query}')
            _pid, _stdin, _stdout, _stderr = _echo
            if self._ssh.isError(_stdout):
                self._log.setError(f'{self._lang.LogSeparator} {self._ip_addr} : {self._lang.ExtraError} : {param}')
                continue
            setattr(self, f'_{param}', _stdout.readline().strip())
            self._log.setSuccess(f'{self._lang.LogSeparator} {self._ip_addr} : {self._lang.ExtraSuccess} : {param}')

    async def _num(self):
        """ Get an extra device configuration from the daemon - coroutine """
        self._log.setInformation(f'{self._lang.LogSeparator} {self._ip_addr} : {self._lang.ExtraInformation}')

        if not await self._ssh.establish(self._lang.LogSeparator):
            return self._log.setInformation(f'{self._lang.LogSeparator} {self._ip_addr} : {self._lang.ExtraCancel}')

        await self._manager.pool(self.__num, self._num_name)

        if not self._top.isRunning():
            self._top.run()

    def action(self):
        """ Device attach/detach action - generator """
        for action in self._getGlobalHeading():
            yield action

        for action in _usbip_action:
            _icon = QIcon(f'icon/{action}.png')
            _lang = getattr(self._lang, f'ActionGlobal{action.capitalize()}')
            _action = QAction(_icon, f'{_lang}')
            _action.setObjectName(f'{action}')
            _action.triggered.connect(lambda __bool, __action=action: self._actionGlobal(__action))
            yield _action

        for action in self._getLocalHeading():
            yield action

        _trigger = self._action_param(self.isBound())
        _name = _trigger.__name__
        _icon = QIcon(f'icon/{_name}.png')
        _lang = getattr(self._lang, f'ActionLocal{_name.capitalize()}')
        _action = QAction(_icon, f'{_lang} : {self.bID()} : {self.dName()}')
        _action.setObjectName(f'{self.bID()}')
        _action.triggered.connect(lambda __bool: _trigger())
        yield _action

    def isBound(self):
        """  """
        return self._is_bound

    def atch(self, offset=None):
        """ Attach device - calling coroutine """
        self._manager.exec(self._atch, self._atch_name, offset)
        if self._sw_config.dev_perf:
            self._manager.exec(self._num, self._num_name)
        self._tree.loadDevice(self.bID())

    def dtch(self, offset=None):
        """ Detach device - calling coroutine """
        self._manager.exec(self._dtch, self._dtch_name, offset)
        self._tree.unloadDevice(self.bID())
        self._dmn_perf.delProcessing(self._ip_addr, self.bNum(), self.dNum())

    def bID(self):
        """ [Client] Device bus ID """
        return self._usbip_param.bid_0

    def dName(self):
        """ [Client] Device name """
        return self._usbip_param.name_0

    def dLocation(self):
        """ [Client] Device path in the daemon """
        return self._usbip_param.location_0

    def bNum(self):
        """ [Daemon] Device bus number """
        return self._busnum

    def dNum(self):
        """ [Daemon] Device number """
        return self._devnum


class Enumerator(metaclass=config.Singleton):
    """ USBIP device enumerator interface for accounting and calculating ID of attaching/detaching devices """
    def __init__(self):
        self._device = list()

    def _get_missing(self):
        """ Discover missing elements in the device port sequence """
        _begin, _end = None, None
        try:
            _begin, _end = self._device[0], self._device[-1]
        except IndexError:
            return
        return sorted(set(range(_begin, _end + 1)).difference(self._device))

    def assign(self):
        """ Assign a port number to a newly attached device """
        _missing = self._get_missing()
        if _missing:
            _value = min(_missing)
            self._device.append(_value)
            return _value
        _value = max(self._device, default=0) + 1
        self._device.append(_value)
        return _value

    def displace(self, idx):
        """ Remove the port number of the just detached device from the sequence """
        return self._device.remove(idx)
