# Software configuration
from library import config
#
from library import SRVArea
#
from library import DevTreeMenu
#
from library import ApplicationMenu
#
from library import NetworkActivity

#
import builtins
#
from os import path
# System-specific parameters and functions
from sys import argv, exit
# Calling functions with positional arguments
from functools import partial
#
from psutil import process_iter, cpu_count
# Plotting charts modules
from pyqtgraph import setConfigOption, PlotWidget
# Async threading interface
from asyncio import sleep, ProactorEventLoop, set_event_loop, CancelledError
# PyQt5 modules
from PyQt5 import uic
from PyQt5.QtGui import QIcon
from PyQt5.QtCore import QObject, pyqtSignal, Qt, QTranslator
from PyQt5.QtWidgets import QWidget, QPushButton, QMainWindow, QMenu, QAction, QGridLayout, QMessageBox, QApplication

# Watchdog utilities for monitoring file system events
if config.watchdog_enable:
    from watchdog.observers import Observer
    from watchdog.events import FileSystemEventHandler

#
if "_" not in dir(builtins):
    from gettext import gettext as _


# ============================================================================ #
# CLASSES
# ============================================================================ #

#
if config.watchdog_enable:
    class ConfigWatchdog(FileSystemEventHandler, QObject):
        fileUpdated = pyqtSignal()

        def __init__(self):
            super(ConfigWatchdog, self).__init__()

        def file_updated(self):
            self.fileUpdated.emit()

        def on_modified(self, event):
            if event.src_path == path.abspath("config.ini"):
                self.file_updated()


# ============================================================================ #
# ASYNC FUNCTIONS
# ============================================================================ #

# Main processing events loop
async def async_process_subprocess(qapp):
    while True:
        await sleep(0)
        qapp.processEvents()


#
async def async_sw_usage(_self):
    #
    timeout = float(_self.config["SETTINGS"]["status_updating_time"])
    for proc in process_iter():
        if config.program_title in proc.name():
            while True:
                # Getting and counting process cpu and memory usage
                cpu_usage = str(proc.cpu_percent() / cpu_count())
                memory_usage = str(config.convert_size(proc.memory_info().rss))
                # Updating status bar
                _self.statusBar().showMessage(_("CPU: ") + cpu_usage + _("% MEMORY: ") + memory_usage)

                await sleep(timeout)


# ============================================================================ #
# GUI
# ============================================================================ #

class CancelProcessButton(QWidget):
    def __init__(self, main_width, main_height):
        # noinspection PyArgumentList
        super(CancelProcessButton, self).__init__()

        self.main_width = main_width
        self.main_height = main_height
        self.cancel_button = QPushButton(_("Cancel"), self)

    def paintEvent(self, event):
        # w = self.cancel_button.width()
        # h = self.cancel_button.height()
        w = 131
        h = 31

        x = (self.main_width - w) / 2.0
        y = (self.main_height - h) / 2.0
        self.cancel_button.setGeometry(x, y, w, h)


class ProgramUI(QMainWindow):
    def __init__(self, main_loop):
        # noinspection PyArgumentList
        super(ProgramUI, self).__init__()
        uic.loadUi("ui/USBIPManager.ui", self)
        self.show()
        # Setting application icon
        self.setWindowIcon(QIcon("icon/logo.png"))
        # Application main loop
        self.main_loop = main_loop
        # Getting the configuration from config.ini file
        self.config = config.get_config()

        self.cancel_process = CancelProcessButton(self.frameGeometry().width(), self.frameGeometry().height())
        self.cancel_process.setParent(None)

        # Setting actions for main menu buttons
        self.auto_find_button.clicked.connect(partial(ApplicationMenu.auto_find, self))
        self.add_server_button.clicked.connect(partial(ApplicationMenu.add_server, self))
        self.search_all_button.clicked.connect(partial(ApplicationMenu.search_all, self))
        self.connect_all_button.clicked.connect(partial(ApplicationMenu.connect_all, self))
        self.disconnect_all_button.clicked.connect(partial(ApplicationMenu.disconnect_all, self, config.usbip_array))
        self.settings_button.clicked.connect(partial(ApplicationMenu.settings, self))

        #
        self.log.setContextMenuPolicy(Qt.CustomContextMenu)
        self.log.customContextMenuRequested.connect(self.log_context_menu)

        # Setting context menu for the server list box
        self.server_box.setContextMenuPolicy(Qt.CustomContextMenu)
        self.server_box.customContextMenuRequested.connect(partial(SRVArea.box_context_menu, self))

        # Setting default context menu for the connected device tree box
        self.device_tree_menu = dict()
        self.device_tree_menu["menu"] = QMenu()
        self.device_tree_menu["action"] = dict()

        # Enabling data capture context action
        self.device_tree_menu["action"]["enable"] = \
            QAction(QIcon("icon/enable.png"), _("Enable data capturing"), self)
        self.device_tree_menu["action"]["enable"].setEnabled(False)

        # Resetting data capture context action
        self.device_tree_menu["action"]["reset"] = \
            QAction(QIcon("icon/reset.png"), _("Reset data capturing"), self)
        self.device_tree_menu["action"]["reset"].setEnabled(False)

        # Disabling data capture context action
        self.device_tree_menu["action"]["disable"] = \
            QAction(QIcon("icon/disable.png"), _("Disable data capturing"), self)
        self.device_tree_menu["action"]["disable"].setEnabled(False)

        #
        self.device_box.setContextMenuPolicy(Qt.CustomContextMenu)
        self.device_box.customContextMenuRequested.connect(partial(DevTreeMenu.box_context_menu, self))

        # Setting activity plot
        setConfigOption("background", "#FF000000")
        activity_graph = PlotWidget()
        activity_graph.setMenuEnabled(enableMenu=False)
        activity_graph.setMouseEnabled(x=False, y=False)
        activity_graph.showGrid(x=True, y=True)
        activity_graph.hideButtons()
        # Defining sent and received activity curves
        self.sent_curve = activity_graph.getPlotItem().plot()
        self.recv_curve = activity_graph.getPlotItem().plot()
        # Setting activity box layout and adding activity plot to the program window
        activity_layout = QGridLayout()
        self.activity_box.setLayout(activity_layout)
        activity_layout.addWidget(activity_graph)
        self.activity_box.setContextMenuPolicy(Qt.CustomContextMenu)
        self.activity_box.customContextMenuRequested.connect(partial(NetworkActivity.box_context_menu, self))

        # Getting the configuration and filling the server list with the found servers
        SRVArea.srv_get(self)
        # Starting checking servers availability process
        self.srv_checking = self.main_loop.create_task(SRVArea.async_srv_check(self))
        # Starting checking software cpu and memory usage process
        self.usage_checking = self.main_loop.create_task(async_sw_usage(self))
        # Starting checking network activity process
        self.activity_checking = self.main_loop.create_task(NetworkActivity.async_get_activity(self))

        if config.watchdog_enable:
            # Setting watchdog event handler as PyQt Object signal
            event_handler = ConfigWatchdog()
            event_handler.fileUpdated.connect(self.config_change_action)
            # Starting observer thread that schedules file watching and dispatches calls to event handler
            observer = Observer()
            observer.schedule(event_handler, path=path.dirname(path.abspath(__file__)), recursive=False)
            observer.start()

    # Log right click context menu
    def log_context_menu(self, event):
        menu = QMenu()
        #
        clear_log = QAction(QIcon("icon/clear.png"), _("Clear"), self)
        clear_log.triggered.connect(self.log.clear)
        #
        menu.addAction(clear_log)
        menu.exec_(self.log.mapToGlobal(event))

    # Watchdog event handler actions
    def config_change_action(self):
        # Cancelling current checking servers availability process
        self.srv_checking.cancel()
        # Getting the configuration and filling the server list with the found servers
        SRVArea.srv_get(self)
        # Starting checking servers availability process
        self.srv_checking = self.main_loop.create_task(SRVArea.async_srv_check(self))

    # Actions during the program window closed
    def closeEvent(self, event):
        # Setting up the alert message
        warning = QMessageBox()
        warning.setWindowTitle(_("Warning"))
        warning.setText(_("Are you sure want to exit? All current connections will be terminated!"))
        warning.setIcon(1)
        ok_button = warning.addButton(_("OK"), QMessageBox.YesRole)
        cancel_button = warning.addButton(_("Cancel"), QMessageBox.NoRole)
        warning.exec_()
        #
        if warning.clickedButton() == ok_button:
            #
            ApplicationMenu.disconnect_all(self, config.usbip_array, sw_close=True)
            event.ignore()
        #
        elif warning.clickedButton() == cancel_button:
            event.ignore()


if __name__ == "__main__":
    app = QApplication(argv)

    #
    if len(list([proc.info for proc in process_iter(attrs=["name"]) if config.program_title in proc.info["name"]])) > 1:
        # Setting up the alert message
        config.alert_box(_("Warning"), _("Another instance is already running!"), 1)
        # Closing the program
        exit()

    # Installing translator
    ini = config.get_config()
    if ini["SETTINGS"].getboolean("software_language"):
        translator = QTranslator()
        translator.load("lang/ru/interface.qm")
        app.installTranslator(translator)

    # Preparing the main loop
    loop = ProactorEventLoop()
    set_event_loop(loop)

    # Preparing and displaying the GUI
    ProgramUI(loop)
    try:
        loop.run_until_complete(async_process_subprocess(app))
    except CancelledError:
        pass
