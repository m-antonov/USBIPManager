from library import bar, compatibility, config, daemon, ini, lang, log, performance, queue
from library.modal import LoadDaemon, SelfSearch, SoftwareConfig, QueueManager

from sys import argv
from asyncio import sleep, CancelledError
from PyQt5 import uic
from PyQt5.QtGui import QIcon
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QMainWindow, QMenu, QAction, QMessageBox, QApplication


async def _processing(application):
    """ Process all pending events - keep interface alive """
    while True:
        application.processEvents()
        await sleep(0)


class USBIPManagerUI(QMainWindow):
    """ Main window """
    def __init__(self):
        super(USBIPManagerUI, self).__init__()
        uic.loadUi('ui/USBIPManager.ui', self)

        self.setWindowIcon(QIcon('icon/logo.png'))

        self._center()

        self._sw_config = ini.SWConfig(self)

        self._dmn_manager = ini.DaemonManage(self)

        self._manager = queue.Manager(self)
        self._atch_name = 'USBIP attach all'
        self._dtch_name = 'USBIP detach all'

        _repr = config.ProgressRepr(self.progress, self.__class__.__name__)
        self._bar = bar.Manager(_repr.replace())

        self._perf = performance.Manager(self)
        self._perf.load()

        self._log = log.Manager(self)
        self._lang = lang.USBIPManagerUI

        self.self_search_btn.clicked.connect(self._self_search)
        self.search_btn.clicked.connect(self._search_all)
        self.atch_btn.clicked.connect(self._atch_all)
        self.dtch_btn.clicked.connect(self._dtch_all)
        self.load_btn.clicked.connect(self._scroll_load)
        self.queue_btn.clicked.connect(self._queue_manager)
        self.config_btn.clicked.connect(self._configuration)
        self.doc_btn.clicked.connect(self._documentation)

        self._popup_param = ('scroll', 'log')
        self._scroll_param = ('poweroff', 'load', 'clear')
        self._log_param = ('clear', )

        for action in self._popup_param:
            setattr(self, f'_popup_{action}', self._popup_action(action))
            _popup = getattr(self, f'_popup_{action}')
            _obj = getattr(self, action)
            _obj.setContextMenuPolicy(Qt.CustomContextMenu)
            _obj.customContextMenuRequested.connect(_popup)
            setattr(self, f'_menu_{action}', QMenu())
            _menu = getattr(self, f'_menu_{action}')
            _action_param = getattr(self, f'_{action}_param')
            for param in _action_param:
                _icon = QIcon(f'icon/{param}.png')
                _lang = getattr(self._lang, f'Popup{action.capitalize()}{param.capitalize()}')
                setattr(self, f'_action_{action}_{param}', QAction(_icon, _lang, _obj))
                _action = getattr(self, f'_action_{action}_{param}')
                _action.triggered.connect(getattr(self, f'_{action}_{param}'))
                _menu.addAction(_action)

        for _daemon in self.__all():
            _daemon.load()

    def __repr__(self):
        """ Printable class representation for queue manager modal window """
        return f'{self.__class__.__name__}'

    def __all(self):
        """ Daemon manager generator to get all from the configuration """
        for ip_addr in self._dmn_manager.get_all():
            yield daemon.Manager(self, ip_addr)

    def _popup_action(self, action):
        """ Function template for context menu instance """
        def _template(coordinate):
            """ Show the right-click popup menu in the action area """
            _menu = getattr(self, f'_menu_{action}')
            _obj = getattr(self, action)
            _menu.exec_(_obj.mapToGlobal(coordinate))
        return _template

    async def _atch_dtch_all(self, action):
        """ Attach/Detach all action with global progress bar processing """
        _global_pool = list()
        for _daemon in self.__all():
            _global_pool += _daemon.usbip_pool()
        if not _global_pool:
            _lang = getattr(self._lang, f'{action.capitalize()}Separator')
            self._log.setWarning(f'{_lang} : {self._lang.PoolEmpty}')
            return getattr(self, f'{action}_btn').setEnabled(True)
        _ep = 100 / len(_global_pool)
        _span = getattr(self._sw_config, f'dev_{action}_tmo')
        for _daemon in self.__all():
            _local_pool = _daemon.usbip_pool()
            for device in _local_pool:
                self._bar.setRange(_span, _ep)
                getattr(device, action)(100 / len(_local_pool))
                await sleep(_span + 0.25)
        return getattr(self, f'{action}_btn').setEnabled(True)

    def _center(self):
        """ Center main application window based on the cursor position for multiple displays """
        _frame = self.frameGeometry()
        # noinspection PyArgumentList
        _root = QApplication.desktop()
        _active_screen = _root.screenNumber(_root.cursor().pos())
        _center = _root.screenGeometry(_active_screen).center()
        _frame.moveCenter(_center)
        self.move(_frame.topLeft())

    def _self_search(self):
        """ Self search application menu button action """
        _dialog = SelfSearch.SelfSearchUI(self)
        _dialog.show()

    def _search_all(self):
        """ Search all application menu button action """
        for _daemon in self.__all():
            _daemon.search()

    def _atch_all(self):
        """ Attach all application menu button action """
        self.atch_btn.setEnabled(False)
        self._manager.exec(self._atch_dtch_all, self._atch_name, 'atch')

    def _dtch_all(self):
        """ Detach all application menu button action """
        self.dtch_btn.setEnabled(False)
        self._manager.exec(self._atch_dtch_all, self._dtch_name, 'dtch')

    def _queue_manager(self):
        """ Queue manager application menu button action """
        _dialog = QueueManager.QueueManagerUI(self)
        _dialog.show()

    def _configuration(self):
        """ Configuration application menu button action """
        _dialog = SoftwareConfig.SoftwareConfigUI(self)
        _dialog.show()

    def _documentation(self):
        """ Documentation application menu button action """
        pass

    def _scroll_poweroff(self):
        """ Scroll area right-click popup menu poweroff action """
        pass

    def _scroll_load(self):
        """ Load daemon application menu button action """
        _dialog = LoadDaemon.LoadDaemonUI(self)
        _dialog.show()

    def _scroll_clear(self):
        """ Scroll area right-click popup menu clear action """
        pass

    def _log_clear(self):
        """ Log area right-click popup menu clear action """
        self.log.clear()

    def closeEvent(self, event):
        """ Main window closing action - detach all devices """
        # TODO Message API
        warning = QMessageBox()
        warning.setWindowTitle(self._lang.MessageCloseTitle)
        warning.setText(self._lang.MessageCloseText)
        warning.setIcon(1)
        ok_button = warning.addButton(self._lang.MessageCloseOK, QMessageBox.YesRole)
        cancel_button = warning.addButton(self._lang.MessageCloseCancel, QMessageBox.NoRole)
        warning.exec_()
        if warning.clickedButton() == ok_button:
            event.ignore()
        elif warning.clickedButton() == cancel_button:
            event.ignore()


if __name__ == '__main__':
    _application = QApplication(argv)
    _comp = compatibility.System()
    _loop = _comp.loop()
    _ui = USBIPManagerUI()
    _ui.show()
    try:
        _loop.run_until_complete(_processing(_application))
    except CancelledError:
        pass
