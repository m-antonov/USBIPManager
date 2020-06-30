# This file is a part of the USBIPManager software
# library/performance.py
# Implements interfaces for measuring the performance of software and its modules
#
# Copyright (c) 2018-2019 Mikhail Antonov
# Repository: https://github.com/lompal/USBIPManager
# TODO Change documentation URL
# Documentation: https://gthb.in/blog/post/2019/10/1/38-usbip-manager-system-and-network-activities-api-reference

from library import config, daemon, device, ini, lang, log, queue

import math
from threading import Event
from collections import deque
from asyncio import get_event_loop, sleep
from PyQt5.QtGui import QIcon, QColor
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QMenu, QAction
from psutil import process_iter, cpu_count, net_io_counters
from pyqtgraph import setConfigOption, PlotWidget, LegendItem, mkPen


class LoadError(Exception):
    """ Error starting a measure """
    pass


class UnloadError(Exception):
    """ Error stopping a measure """
    pass


class Manager(metaclass=config.Singleton):
    """ Performance measure manager """
    def __init__(self, base):
        self._base = base

        self._pool = (System(self._base), Network(self._base), Daemon(self._base), Device(self._base))

    def load(self):
        """ Load each performance from the pool """
        for perf in self._pool:
            perf.load()

    def unload(self):
        """ Unload each performance from the pool """
        for perf in self._pool:
            perf.unload()

    def reload(self):
        """ Reload each performance from the pool """
        for perf in self._pool:
            perf.reload()


# noinspection PyPep8Naming
class Base(metaclass=config.Singleton):
    """ Base class for a performance measure """
    def __init__(self, base):
        self._base = base

        self._loop = get_event_loop()

        self._sw_config = ini.SWConfig(self._base)

        self._manager = queue.Manager(self._base)
        self._proc_name = self.__doc__
        self._event = Event()
        self._event.set()

        # TODO Log messaging for load/unload action
        self._log = log.Manager(self._base)
        self._lang = lang.Performance

    async def _load(self):
        """ Load a performance measure - coroutine """
        pass

    def _clear(self):
        """ Clear an object or area """
        pass

    def load(self):
        """ Load a performance measure - calling coroutine """
        if self.isRunning():
            raise LoadError
        self._event.clear()
        self._manager.exec(self._load, self._proc_name)

    def unload(self):
        """ Unload a performance measure - cancelling coroutine """
        if not self.isRunning():
            raise UnloadError
        if self._manager.cancel(self._proc_name):
            self._event.set()
            self._clear()

    def reload(self):
        """ Reload a performance measure - cancelling/calling coroutine """
        try:
            self.unload()
        except UnloadError:
            pass
        self.load()

    def isRunning(self):
        """ Check if a performance measure is running """
        return not self._event.is_set()


class System(Base, metaclass=config.Singleton):
    """ System performance measure """
    def __init__(self, base):
        super(System, self).__init__(base)
        self._cpu_usage = None
        self._mem_usage = None

    def _mem_transform(self):
        """ Formatting the value of the RAM usage """
        if self._mem_usage == 0:
            return '0 B'
        size_name = ('B', 'KB', 'MB', 'GB', 'TB', 'PB', 'EB', 'ZB', 'YB')
        index = int(math.floor(math.log(self._mem_usage, 1024)))
        exp = pow(1024, index)
        size = round(self._mem_usage / exp, 2)
        return '{0:.2f} {1}'.format(size, size_name[index])

    def _cpu_transform(self):
        """ Formatting the value of the CPU usage """
        return '{0:.2f} % '.format(self._cpu_usage)

    async def _load(self):
        """ Load the system performance measure - coroutine """
        if not self._sw_config.sys_perf:
            return self._event.set()
        for proc in process_iter():
            if config.program_title in proc.name() or 'python' in proc.name():
                while not self._event.is_set():
                    self._cpu_usage = proc.cpu_percent() / cpu_count()
                    self._mem_usage = proc.memory_info().rss
                    self._base.statusBar().showMessage(
                        f'{self._lang.SystemCPU}: {self._cpu_transform()}' +
                        f'{self._lang.SystemMEM}: {self._mem_transform()}'
                    )
                    await sleep(self._sw_config.sys_perf_tmo)


class Network(Base, metaclass=config.Singleton):
    """ Network performance measure """
    def __init__(self, base):
        super(Network, self).__init__(base)
        self._out_val = None
        self._inc_val = None

        self._plot()
        self._clear()

    def _plot(self):
        """ Network performance graph """
        setConfigOption('background', '#FF000000')
        _graph = PlotWidget()
        _graph.setMenuEnabled(enableMenu=False)
        _graph.setMouseEnabled(x=False, y=False)
        _graph.hideButtons()

        self._out_curve = _graph.getPlotItem().plot()
        self._inc_curve = _graph.getPlotItem().plot()

        self._legend = LegendItem(offset=(50, 10))
        self._legend.setParentItem(_graph.getPlotItem())
        self._legend.addItem(self._out_curve, self._lang.NetworkGraphOutgoing)
        self._legend.addItem(self._inc_curve, self._lang.NetworkGraphIncoming)

        self._base.net_perf_lyt.addWidget(_graph)

        self._menu_popup = QMenu()
        _action = QAction(QIcon('icon/reload.png'), self._lang.PopupReload, self._base.net_perf_box)
        _action.triggered.connect(self.reload)
        self._menu_popup.addAction(_action)

        self._base.net_perf_box.setContextMenuPolicy(Qt.CustomContextMenu)
        self._base.net_perf_box.customContextMenuRequested.connect(self._popup_show)

    def _set_value(self):
        """ Set send and receive value for the network performance curves """
        self._out_curve.setData(self._out_val, pen=mkPen(
            width=self._sw_config.net_perf_out_wd, color=QColor(self._sw_config.net_perf_out_cl)))
        self._inc_curve.setData(self._inc_val, pen=mkPen(
            width=self._sw_config.net_perf_inc_wd, color=QColor(self._sw_config.net_perf_inc_cl)))

    async def _load(self):
        """ Load the network performance measure - coroutine """
        if not self._sw_config.net_perf:
            return self._event.set()
        _old_out = 0
        _old_inc = 0
        while not self._event.is_set():
            _rev_out = net_io_counters().bytes_sent
            _rev_int = net_io_counters().bytes_recv
            if _old_out and _old_inc:
                self._out_val.append(_rev_out - _old_out)
                self._inc_val.append(_rev_int - _old_inc)
            self._set_value()
            _old_out = _rev_out
            _old_inc = _rev_int
            await sleep(self._sw_config.net_perf_tmo)

    def _popup_show(self, coordinate):
        """ Right-click popup menu in the graph area """
        self._menu_popup.exec_(self._base.net_perf_box.mapToGlobal(coordinate))

    def _clear(self):
        """ Clear the entire graph """
        self._out_val = deque([0] * self._sw_config.net_perf_len, maxlen=self._sw_config.net_perf_len)
        self._inc_val = deque([0] * self._sw_config.net_perf_len, maxlen=self._sw_config.net_perf_len)
        self._set_value()


class Daemon(Base, metaclass=config.Singleton):
    """ USBIP daemon availability checking """
    def __init__(self, base):
        super(Daemon, self).__init__(base)

        self._dmn_manage = ini.DaemonManage(self._base)

    async def _load(self):
        """ Load a daemon availability checking - coroutine """
        if not self._sw_config.dmn_perf:
            return self._event.set()
        _all = self._dmn_manage.get_all()
        while not self._event.is_set():
            for ip_addr in _all:
                _device = daemon.Manager(self._base, ip_addr)
                if not _device.isExisting():
                    _device.load()
                # TODO Timeout
                self._loop.create_task(_device.check())
                await sleep(self._sw_config.dmn_perf_tmo)

    def _clear(self):
        """ Clear the entire daemon manager """
        for idx in reversed(range(self._base.scroll_lyt.count())):
            _obj = self._base.scroll_lyt.itemAt(idx).widget()
            _obj.deleteLater()
            _obj.setParent(None)


# noinspection PyPep8Naming
class Device(Base, metaclass=config.Singleton):
    """ Daemon device bandwidth measure """
    def __init__(self, base):
        super(Device, self).__init__(base)
        self._pool = dict()

    def _isDaemon(self, ip_addr):
        """ Check if a daemon is in the processing pool """
        _daemon = self._pool.get(ip_addr, None)
        if not _daemon:
            self._pool[ip_addr] = dict()
            return self._pool[ip_addr]
        return _daemon

    def _isbID(self, ip_addr, bnum):
        """ Check if a daemon device bus number is in the processing pool """
        _daemon = self._isDaemon(ip_addr)
        _bnum = _daemon.get(bnum, None)
        if not _bnum:
            _daemon[bnum] = dict()
            return _daemon[bnum]
        return _bnum

    async def _load(self):
        """ Load a daemon device bandwidth measure - coroutine """
        if not self._sw_config.dev_perf:
            return self._event.set()
        while not self._event.is_set():
            for ip_addr in self._pool:
                _device = daemon.Manager(self._base, ip_addr)
                _tree = device.Tree(self._base, ip_addr)
                for usbip in _device.usbip_pool():
                    if not usbip.isBound():
                        continue
                    _bid = usbip.bID()
                    _bnum = usbip.bNum()
                    _dnum = usbip.dNum()
                    if not all((_bnum, _dnum)):
                        continue
                    _incoming, _outgoing = self._pool[ip_addr][_bnum][_dnum]
                    _tree.setIncoming(_bid, _incoming)
                    _tree.setOutgoing(_bid, _outgoing)
            await sleep(self._sw_config.dev_perf_tmo)

    def _clear(self):
        """ Clear the device bandwidth processing pool """
        self._pool = dict()

    def setProcessing(self, ip_addr, bnum, dnum, value):
        """ Set an incoming/outgoing bandwidth value to the processing pool """
        _bnum = self._isbID(ip_addr, bnum)
        _bnum[dnum] = value

    def delProcessing(self, ip_addr, bnum, dnum):
        """ Remove an incoming/outgoing bandwidth value from the processing pool """
        try:
            del self._pool[ip_addr][bnum][dnum]
        except KeyError:
            pass
