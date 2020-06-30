from library import config, ini, lang, log, performance, periphery, queue

from asyncio import get_event_loop
from threading import Thread, Event
from PyQt5.QtCore import QObject, pyqtSignal
from PyQt5.QtWidgets import QTreeWidgetItem


# noinspection PyPep8Naming
class Signal(QObject):
    """ PyQt signals for correct daemon device tree calls from a different thread """
    addTopLevelItem_ = pyqtSignal(object)
    setText_ = pyqtSignal(str, int, str)
    setToolTip_ = pyqtSignal(str, int, object)
    setIcon_ = pyqtSignal(str, int, object)

    def addTopLevelItem(self, daemon):
        """ Load daemon as a top-level item - emit the signal """
        self.addTopLevelItem_.emit(daemon)

    def setText(self, bid, col, baud):
        """ Set incoming/outgoing bandwidth - emit the signal """
        self.setText_.emit(bid, col, baud)

    def setToolTip(self, bid, col, html):
        """ Set tooltip for a daemon during capturing operation - emit the signal """
        self.setToolTip_.emit(bid, col, html)

    def setIcon(self, bid, col, icon):
        """ Set status icon for a daemon during capturing operation - emit the signal """
        self.setIcon_.emit(bid, col, icon)


# noinspection PyPep8Naming
class Tree(metaclass=config.Singleton):
    """ Daemon device bandwidth tree """
    def __init__(self, base, ip_addr):
        self._base = base
        self._ip_addr = ip_addr

        self._sw_config = ini.SWConfig(self._base)

        self._lang = lang.Tree

        self._signal = Signal()
        self._signal.addTopLevelItem_.connect(lambda __daemon: self._addTopLevelItem(__daemon))
        self._signal.setText_.connect(lambda __bid, __col, __baud: self._setText(__bid, __col, __baud))
        self._signal.setToolTip_.connect(lambda __bid, __col, __html: self._setToolTip(__bid, __col, __html))
        self._signal.setIcon_.connect(lambda __bid, __col, __icon: self._setIcon(__bid, __col, __icon))

    def _getDaemon(self):
        """  """
        _root = self._base.dev_tree.invisibleRootItem()
        for idx in range(_root.childCount()):
            _daemon = _root.child(idx)
            if _daemon.text(0) == self._ip_addr:
                return _daemon, idx
        return None, None

    def _takeDaemon(self, idx):
        """  """
        return self._base.dev_tree.takeTopLevelItem(idx)

    def _loadDaemon(self):
        """  """
        _daemon = QTreeWidgetItem([self._ip_addr])
        self.addTopLevelItem(_daemon)
        return _daemon, 0

    def _getDevice(self, bid):
        """  """
        _daemon, _idx = self._getDaemon()
        if not _daemon:
            return None, None
        for idx in range(_daemon.childCount()):
            _dev = _daemon.child(idx)
            if _dev.text(0) == bid:
                return _daemon, _dev
        return _daemon, None

    def _addTopLevelItem(self, daemon):
        """ Load daemon as a top-level item - inner function """
        self._base.dev_tree.addTopLevelItem(daemon)
        self._base.dev_tree.expandAll()

    def _setText(self, bid, col, baud):
        """ Set incoming/outgoing bandwidth - inner function """
        _daemon, _dev = self._getDevice(bid)
        if _dev:
            _baud = _dev.child(0)
            _baud.setText(col, baud)

    def _setToolTip(self, bid, col, html):
        """ Set tooltip for a daemon during capturing operation - inner function """
        _daemon, _dev = self._getDevice(bid)
        if _dev:
            _dev.setToolTip(col, html)

    def _setIcon(self, bid, col, icon):
        """ Set status icon for a daemon during capturing operation - inner function """
        _daemon, _dev = self._getDevice(bid)
        if _dev:
            _dev.setIcon(col, icon)

    def addTopLevelItem(self, daemon):
        """ Load daemon as a top-level item from a different thread """
        self._signal.addTopLevelItem(daemon)

    def setText(self, bid, col, baud):
        """ Set incoming/outgoing bandwidth from a different thread """
        self._signal.setText(bid, col, baud)

    def setToolTip(self, bid, col, html):
        """ Set status tooltip for a daemon during capturing operation from a different thread """
        self._signal.setToolTip(bid, col, html)

    def setIcon(self, bid, col, icon):
        """ Set status icon for a daemon during capturing operation from a different thread """
        self._signal.setIcon(bid, col, icon)

    def loadDevice(self, bid):
        """  """
        _device = QTreeWidgetItem([bid])
        _daemon, _idx = self._getDaemon()
        if not _daemon:
            _daemon, _idx = self._loadDaemon()
        _daemon, _dev = self._getDevice(bid)
        if _dev:
            return
        _daemon = self._takeDaemon(_idx)
        if self._sw_config.dev_perf:
            _baud = QTreeWidgetItem([self._lang.ParamBaud, self._lang.ParamNA, self._lang.ParamNA])
            _device.addChild(_baud)
        _daemon.addChild(_device)
        self.addTopLevelItem(_daemon)

    def unloadDevice(self, bid):
        """  """
        _daemon, _dev = self._getDevice(bid)
        if _dev:
            _daemon.removeChild(_dev)

    def setIncoming(self, bid, baud):
        """ Set incoming bandwidth """
        self.setText(bid, 1, baud)

    def setOutgoing(self, bid, baud):
        """ Set outgoing bandwidth """
        self.setText(bid, 2, baud)


# noinspection PyPep8Naming
class USBTop(metaclass=config.Singleton):
    """ Daemon device bandwidth processing """
    def __init__(self, base, ip_addr):
        self._base = base
        self._ip_addr = ip_addr

        self._loop = get_event_loop()

        self._sw_config = ini.SWConfig(self._base)

        self._manager = queue.Manager(self._base)
        self._name_running = f'USBTOP processing running : {self._ip_addr}'
        self._name_cancelling = f'USBTOP processing cancelling : {self._ip_addr}'

        self._ssh = periphery.SSH(self._base, self._ip_addr)

        self._log = log.Manager(self._base)
        self._lang = lang.USBTop

        self._tree = Tree(self._base, self._ip_addr)

        self._dmn_perf = performance.Device(self._base)

        self._thread = Thread()
        self._event = Event()
        self._pid = None

    # noinspection PyMethodMayBeStatic
    def _idx(self, row):
        """  """
        return [param for param in row.split() if param.isdigit()].pop()

    def _processing(self, buf):
        """  """
        _bid = None
        for row in buf:
            if 'Bus ID' in row:
                _bid = self._idx(row)
                continue
            if 'Device ID' in row:
                _did = self._idx(row)
                _value = row.split()
                self._dmn_perf.setProcessing(self._ip_addr, _bid, _did, (_value[4], _value[6]))

    def _exec(self):
        """ Run the USBTOP processing - daemon thread """
        _query = 'sudo usbtop'
        _echo = self._ssh.exec(_query)
        if not all(_echo):
            return self._log.setError(f'{self._lang.LogSeparator} {self._ip_addr} : {self._lang.RunQuery} : {_query}')
        self._pid, _stdin, _stdout, _stderr = _echo
        _buf = list()
        while not self._event.is_set():
            _line = _stdout.readline(2048)
            if not _line:
                return self._event.set()
            if '\x1b[2J\x1b[1;1H' in _line:
                self._processing(_buf)
                _buf = list()
                _buf.append(_line.strip().replace('\x1b[2J\x1b[1;1H', ''))
                continue
            _buf.append(_line.strip())

    def __run(self):
        """ Run the USBTOP processing - inner function """
        self._event = Event()
        self._thread = Thread(target=self._exec, name=self._name_running)
        self._thread.start()

        self._log.setSuccess(f'{self._lang.LogSeparator} {self._ip_addr} : {self._lang.RunSuccess}')

        self._event.wait()
        return self._event.is_set()

    async def _run(self):
        """ Run the USBTOP processing - coroutine """
        if not self._sw_config.dev_perf:
            return self._log.setError(f'{self._lang.LogSeparator} {self._ip_addr} : {self._lang.EnableRequired}')

        if self.isRunning():
            return self._log.setError(f'{self._lang.LogSeparator} {self._ip_addr} : {self._lang.AforeRun}')

        if not await self._ssh.establish(self._lang.LogSeparator):
            return self._log.setInformation(f'{self._lang.LogSeparator} {self._ip_addr} : {self._lang.CancelSuccess}')

        await self._loop.run_in_executor(None, self.__run)
        if self.isRunning():
            self.cancel()

    async def _cancel(self):
        """ Cancel the USBTOP processing - coroutine """
        if not self._sw_config.dev_perf:
            return self._log.setError(f'{self._lang.LogSeparator} {self._ip_addr} : {self._lang.EnableRequired}')

        if not self.isRunning():
            return self._log.setError(f'{self._lang.LogSeparator} {self._ip_addr} : {self._lang.AforeCancel}')

        self._event.set()
        self._thread.join()
        if not self.isRunning():
            self._ssh.kill(self._pid)
            return self._log.setWarning(f'{self._lang.LogSeparator} {self._ip_addr} : {self._lang.CancelSuccess}')
        return self._log.setError(f'{self._lang.LogSeparator} {self._ip_addr} : {self._lang.CancelError}')

    def run(self):
        """ Run the USBTOP processing - calling coroutine """
        self._manager.exec(self._run, self._name_running)

    def cancel(self):
        """ Cancel the USBTOP processing - calling coroutine """
        self._manager.exec(self._cancel, self._name_cancelling)

    def isRunning(self):
        """ Check if the USBTOP processing is running """
        return self._thread.is_alive()
