# This file is a part of the USBIPManager software
# library/ini.py
# Implements an interface for managing the log area from any thread
#
# Copyright (c) 2018-2019 Mikhail Antonov
# Repository: https://github.com/lompal/USBIPManager
# Documentation: XXX

from library import config

from datetime import datetime
from PyQt5.QtCore import QObject, pyqtSignal

_message_type = ('Success', 'Warning', 'Error', 'Information', 'Debug')


def _color(param):
    """ Switch-case for determining the color of the message depending on its type """
    return {
        'Success': 'green',
        'Warning': 'orange',
        'Error': 'red',
        'Information': 'blue',
        'Debug': 'black'
    }.get(param, 'Debug')


class Signal(QObject):
    """ PyQt signals for correct logging area calls from a different thread """
    for param in _message_type:
        locals()[f'set{param}_'] = pyqtSignal(str)
    clear_ = pyqtSignal()

    def __init__(self):
        super(Signal, self).__init__()
        for param in _message_type:
            setattr(self, f'set{param}', lambda __message, __param=param: self._signal(__param)(__message))

    def _signal(self, param):
        """ Function template for emitting the signal """
        def _template(message):
            """ Set Success/Warning/Danger/Information/Regular message to the log area - emit the signal """
            _fn = getattr(self, f'set{param}_')
            _fn.emit(message)
        return _template

    def clear(self):
        """ Clear all messages in the log area - emit the signal """
        self.clear_.emit()


class Manager(metaclass=config.Singleton):
    """ Logging area manager """
    def __init__(self, base):
        self._base = base

        self._time_form = '%Y-%m-%d %H:%M:%S'

        self._signal = Signal()

        for param in _message_type:
            setattr(self, f'_set{param}', lambda __message, __param=param: self._inner(__param)(__message))
            setattr(self, f'set{param}', lambda __message, __param=param: self._instance(__param)(__message))
            _fn = getattr(self._signal, f'set{param}_')
            _fn.connect(lambda __message, __param=param: getattr(self, f'_set{__param}')(__message))

        self._signal.clear_.connect(lambda: self._clear())

    def _message_template(self, param, message):
        """ Log area message HTML template """
        _time = datetime.now().strftime(self._time_form)
        return f'{_time} : <font color=\'{_color(param)}\'>{param}</font> : {message}'

    def _inner(self, param):
        """ Function template for the log area inner function """
        def _template(message):
            """ Set Success/Warning/Danger/Information/Regular message to the log area - inner function """
            self._base.log.append(self._message_template(param, message))
        return _template

    def _instance(self, param):
        """ Function template for the log area instance """
        def _template(message):
            """ Set Success/Warning/Danger/Information/Regular message to the log area from a different thread """
            getattr(self._signal, f'set{param}')(message)
        return _template

    def _clear(self):
        """ Clear all messages in the log area - inner function """
        self._base.log.clear()

    def clear(self):
        """ Clear all messages in the log area from a different thread """
        self._signal.clear()
