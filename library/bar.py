from library import config

from time import sleep
from asyncio import get_event_loop
from PyQt5.QtCore import QObject, pyqtSignal


# noinspection PyPep8Naming
class Signal(QObject):
    """ PyQt signals for correct progress bar calls from a different thread """
    setProgress_ = pyqtSignal(float)

    def setProgress(self, value):
        """ Set a progress bar value - emit the signal """
        self.setProgress_.emit(value)


# noinspection PyPep8Naming
class Manager(metaclass=config.Singleton):
    """ Progress bar manager """
    def __init__(self, obj):
        self._obj = obj

        self._loop = get_event_loop()

        self._signal = Signal()
        self._signal.setProgress_.connect(lambda __value: self._setProgress(__value))

        self._refresh_freq = 20

    def __setRange(self, tmo, offset):
        """ Set a progress bar value during the execution of an action - inner function """
        _exec = self.value()
        _range = offset + _exec + 0.25
        _sleep = 1 / self._refresh_freq
        _value = offset / tmo / self._refresh_freq
        while _exec <= _range:
            _exec += _value
            self.setProgress(_exec)
            sleep(_sleep)

    def _setProgress(self, value):
        """ Set a progress bar value - inner function """
        self._obj.setValue(round(value))

    async def _setRange(self, tmo, offset, widget=None):
        """ Set a progress bar value during the execution of an action - coroutine """
        if widget is not None:
            widget.setEnabled(False)
        await self._loop.run_in_executor(None, self.__setRange, tmo, offset)
        if widget is not None:
            widget.setEnabled(True)

    def value(self):
        """ Get a progress bar current value """
        return self._obj.value()

    def isFull(self):
        """ Check if a progress bar is 100 % """
        return self.value() == 100

    def clear(self):
        """ Clear a progress bar and show no progress """
        self.setProgress(0)

    def setProgress(self, value):
        """ Set a progress bar value from a different thread """
        self._signal.setProgress(value)

    def setRange(self, tmo, offset=None, widget=None):
        """ Set a progress bar value during the execution of an action - calling coroutine """
        _offset = offset
        if _offset is None:
            _offset = 100
        if self.isFull():
            self.clear()
        self._loop.create_task(self._setRange(tmo, _offset, widget))
