from library import config, lang, log

from PyQt5 import uic
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QWidget
from asyncio import get_event_loop, all_tasks
from concurrent.futures import ThreadPoolExecutor


class Manager(metaclass=config.Singleton):
    """ Executor queue manager """
    def __init__(self, base):
        self._base = base

        self._loop = get_event_loop()

        self._pool = list()

        self._log = log.Manager(self._base)
        self._lang = lang.QueueManager

    def _done(self, name, **kwargs):
        """ Task completion callback """
        # TODO Check for debug option
        self._log.setDebug(f'{self._lang.DebugCallback} : {name}')
        self._pool.remove(name)

        _parent = kwargs.get('parent', None)
        if _parent is not None:
            _cancel = UIObj(_parent, self)
            _cancel.hide()

    def exec(self, coro, name, *args, **kwargs):
        """ Execute the task and load it to the pool """
        # TODO Check for debug option
        self._log.setDebug(f'{self._lang.DebugExec} : {name}')
        self._pool.append(name)
        _coro = self._loop.create_task(coro(*args), name=name)
        _coro.add_done_callback(lambda __coro: self._done(name, **kwargs))

        _parent = kwargs.get('parent', None)
        if _parent is not None:
            _cancel = UIObj(_parent, self)
            _cancel.show()

        return _coro

    async def pool(self, func, name, *args):
        """ Arrange for the synchronous function to be called in the separate executor """
        with ThreadPoolExecutor(thread_name_prefix=name) as pool:
            await self._loop.run_in_executor(pool, func, *args)

    def cancel(self, name=None):
        """ Cancel a task execution by a name / last running task """
        _name = name
        if not _name:
            try:
                _name = self._pool[-1]
            except IndexError:
                return None
        for coro in all_tasks():
            if coro.get_name() == _name:
                return coro.cancel()
        return None


class UIObj(QWidget, metaclass=config.WSingleton):
    """ Executor termination widget """
    def __init__(self, parent, manager):
        super(UIObj, self).__init__(parent)
        uic.loadUi('ui/widget/cancel.ui', self)

        self.setAttribute(Qt.WA_DeleteOnClose)

        _lft = (self.parent().frameGeometry().width() - self.width()) / 2
        _top = (self.parent().frameGeometry().height() - self.height()) / 2
        self.setGeometry(_lft, _top, self.width(), self.height())

        self._manager = manager

        self.cancel_btn.clicked.connect(self._cancel)

    def _cancel(self):
        """ Cancel the last running task from the pool """
        self._manager.cancel()
