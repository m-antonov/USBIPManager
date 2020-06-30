# This file is a part of the USBIPManager software
# library/modal/SelfSearch.py
# Implements procedures for automatic search of USBIP servers in a network by a given IP range
#
# Copyright (c) 2018-2019 Mikhail Antonov
# Repository: https://github.com/lompal/USBIPManager
# Documentation: XXX

from library import bar, ini, log, queue
from library.lang import LangSelfSearchUI, LangConfig, LangFormValidation
from library.validation import ip_validator, error_css, form_empty, form_valid

from threading import Event
from functools import partial
from ipaddress import IPv4Address
from socket import socket, AF_INET, SOCK_STREAM, timeout
from PyQt5 import uic
from PyQt5.QtCore import QObject, pyqtSignal, Qt
from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import QDialog, QListWidgetItem, QMenu, QAction

#
_popup_action = ('check', 'uncheck')


# noinspection PyPep8Naming
class Signal(QObject):
    """ PyQt signals for correct dialog calls from a different thread """
    clearSearch_ = pyqtSignal()
    setSearch_ = pyqtSignal(str)

    def clearSearch(self):
        """ Clear the search area - emit the signal """
        self.clearSearch_.emit()

    def setSearch(self, ip_addr):
        """ Load the daemon to the search area - emit the signal """
        self.setSearch_.emit(ip_addr)


# noinspection PyPep8Naming
class SelfSearchUI(QDialog):
    """ Modal window with automatic look for a USBIP daemon in a network by a given IP range """
    def __init__(self, base):
        super(SelfSearchUI, self).__init__(parent=base)
        uic.loadUi('ui/modal/SelfSearch.ui', self)

        self.setAttribute(Qt.WA_DeleteOnClose)

        self._base = base

        self._sw_config = ini.SWConfig(self._base)

        self._dmn_manage = ini.DaemonManage(self._base)

        self._bar = bar.Manager(self.bar)

        self._log = log.Manager(self._base)
        self._lang = LangSelfSearchUI

        self._signal = Signal()
        self._signal.clearSearch_.connect(lambda: self._clearSearch())
        self._signal.setSearch_.connect(lambda __ip_addr: self._setSearch(__ip_addr))

        self._is_found = False

        self._manager = queue.Manager(self._base)
        self._name = 'SelfSearch'

        self._event = Event()

        self._form_req = (self.find_ip_ini, self.find_ip_end)

        for form in self._form_req:
            form.setText(getattr(self._sw_config, form.objectName()))
            form.setValidator(ip_validator)
            form.textEdited.connect(partial(self._update_form, form))

        self.search_btn.clicked.connect(self.search_action)
        self.finish_btn.clicked.connect(self.finish_action)
        self.load_btn.clicked.connect(self.load_action)
        self.cancel_btn.clicked.connect(self.close)

        self._menu_popup = QMenu()
        for param in _popup_action:
            _icon = QIcon(f'icon/{param}.png')
            _lang = getattr(self._lang, f'Popup{param.capitalize()}')
            _condition = getattr(Qt, f'{param.capitalize()}ed')
            _action = QAction(_icon, _lang, self)
            _action.triggered.connect(lambda __bool, __condition=_condition: self._condition(__condition))
            self._menu_popup.addAction(_action)

        self.search.setContextMenuPolicy(Qt.CustomContextMenu)
        self.search.customContextMenuRequested.connect(self._popup_show)

    def _clearSearch(self):
        """ Clear the search area - inner function """
        self.search.clear()

    def _setSearch(self, ip_addr):
        """ Load the daemon to the search area - inner function """
        _item = QListWidgetItem()
        _item.setText(ip_addr)
        _item.setFlags(_item.flags() | Qt.ItemIsUserCheckable)
        _item.setCheckState(Qt.Checked)
        self.search.addItem(_item)

    def _update_form(self, form):
        """ Update the default value of the form field in the configuration and set the default stylesheet """
        setattr(self._sw_config, form.objectName(), form.text())
        form.setStyleSheet('')

    def __search_action(self):
        """ Look for a USBIP daemon - inner function """
        _find_ip_ini = int(IPv4Address(self.find_ip_ini.text()))
        _find_ip_end = int(IPv4Address(self.find_ip_end.text()))

        _bar = 0
        self._is_found = False
        self._bar.setProgress(_bar)
        self.clearSearch()

        _iter_qty = _find_ip_end - _find_ip_ini + 1
        if _iter_qty < 1:
            self.find_ip_ini.setStyleSheet(error_css)
            self.find_ip_end.setStyleSheet(error_css)
            return self._log.setError(LangFormValidation.FormGTError)

        _chunk = 100 / _iter_qty

        for ip_addr in range(_find_ip_ini, _find_ip_end + 1):
            _ip_addr = str(IPv4Address(ip_addr))
            if not self._event.is_set():
                _bar += _chunk
                self._bar.setProgress(_bar)
                _connection = socket(AF_INET, SOCK_STREAM)
                _connection.settimeout(self._sw_config.dmn_perf_sock_tmo)
                try:
                    _connection.connect((_ip_addr, self._sw_config.dmn_def_port))
                except (ConnectionRefusedError, OSError, timeout):
                    continue
                _connection.close()
                self.setSearch(_ip_addr)
                self._is_found = True

    async def _search_action(self):
        """ Look for a USBIP daemon - coroutine """
        await self._manager.pool(self.__search_action, self._name)
        self._event.clear()
        self.search_btn.setEnabled(True)
        self.finish_btn.setEnabled(False)
        if self._is_found:
            self.load_btn.setEnabled(True)

    def _popup_show(self, coordinate):
        """ Right-click popup menu in the search area """
        self._menu_popup.exec_(self.search.mapToGlobal(coordinate))

    def _condition(self, condition):
        """ Set check/uncheck condition for a daemon in the search area """
        for index in range(self.search.count()):
            _item = self.search.item(index)
            _item.setCheckState(condition)

    def clearSearch(self):
        """ Clear the search area from a different thread """
        self._signal.clearSearch()

    def setSearch(self, ip_addr):
        """ Load the daemon to the search area from a different thread """
        self._signal.setSearch(ip_addr)

    def search_action(self):
        """ Look for a USBIP daemon - calling coroutine """
        if form_empty(self._form_req):
            return self._log.setError(LangFormValidation.FormEmptyError)

        if form_valid(self._form_req):
            return self._log.setError(LangFormValidation.FormValidError)

        self.find_ip_ini.setStyleSheet('')
        self.find_ip_end.setStyleSheet('')
        self.search_btn.setEnabled(False)
        self.finish_btn.setEnabled(True)
        self.load_btn.setEnabled(False)

        self._manager.exec(self._search_action, self._name)

    def finish_action(self):
        """ Finish the look for a USBIP daemon """
        self._event.set()

    def load_action(self):
        """ Load a daemon to the configuration """
        for idx in range(self.search.count()):
            _item = self.search.item(idx)
            if _item.checkState():
                _ip_addr = _item.text()
                try:
                    self._dmn_manage.load(_ip_addr)
                except ini.InsertError:
                    self._log.setError(f'{_ip_addr} {LangConfig.InsertError}')
        self.close()

    def closeEvent(self, event):
        """ Modal window closing action """
        if self._manager.cancel(self._name):
            self.finish_action()
