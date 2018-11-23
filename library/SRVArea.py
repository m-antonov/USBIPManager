# Software configuration
from library import config
#
from library import SRVMenu
#
from library import ApplicationMenu

# Async threading interface
from asyncio import sleep
# Calling functions with positional arguments
from functools import partial
#
from socket import socket, AF_INET, SOCK_STREAM, timeout
# PyQt5 modules
from PyQt5.QtGui import QIcon
from PyQt5.QtCore import QSize, Qt
from PyQt5.QtWidgets import QGroupBox, QHBoxLayout, QPushButton, QMenu, QAction


# ============================================================================ #
# ASYNC FUNCTIONS
# ============================================================================ #

# Checking servers availability
async def async_srv_check(_self):
    #
    socket_timeout = float(_self.config["SETTINGS"]["server_socket_timeout"])
    polling_time = float(_self.config["SETTINGS"]["server_polling_time"])
    #
    while True:
        if _self.config.sections():
            for srv_addr in _self.config.sections():
                if srv_addr != "SETTINGS":
                    try:
                        conn = socket(AF_INET, SOCK_STREAM)
                        conn.settimeout(socket_timeout)
                        conn.connect((srv_addr, int(_self.config[srv_addr]["server_port"])))
                        conn.close()
                        config.srv_array[srv_addr]["search_btn"].setEnabled(True)
                        config.srv_array[srv_addr]["box"].setStyleSheet('QGroupBox {color: green;}')
                    except (ConnectionRefusedError, timeout):
                        config.srv_array[srv_addr]["search_btn"].setEnabled(False)
                        config.srv_array[srv_addr]["box"].setStyleSheet('QGroupBox {color: red;}')
                await sleep(polling_time)
        else:
            await sleep(polling_time)


# ============================================================================ #
# SYNC FUNCTIONS
# ============================================================================ #

# Getting the configuration and filling the server list with the found servers
def srv_get(_self):
    # Getting the configuration from config.ini file
    _self.config = config.get_config()
    #
    config.srv_array = dict()
    # Removing previous widgets from the content layout
    for i in reversed(range(_self.scroll_content_layout.count())):
        _self.scroll_content_layout.itemAt(i).widget().deleteLater()

    # Updating the GUI
    for srv_addr in _self.config.sections():
        if srv_addr != "SETTINGS":
            # Server box title
            title = srv_addr + ":" + _self.config[srv_addr]["server_port"]
            if _self.config[srv_addr]["server_name"]:
                title += " [" + _self.config[srv_addr]["server_name"] + "]"
            #
            config.srv_array[srv_addr] = dict()
            # Single server box
            config.srv_array[srv_addr]["box"] = QGroupBox(title, _self.scroll_content)
            config.srv_array[srv_addr]["box"].setMinimumSize(QSize(0, 66))
            config.srv_array[srv_addr]["box"].setMaximumSize(QSize(16777215, 66))
            config.srv_array[srv_addr]["box"].setContextMenuPolicy(Qt.CustomContextMenu)
            config.srv_array[srv_addr]["box"].customContextMenuRequested.connect(partial(
                SRVMenu.srv_context_menu, _self, srv_addr=srv_addr, srv_box=config.srv_array[srv_addr]["box"]))
            # Server layout
            config.srv_array[srv_addr]["layout"] = QHBoxLayout(config.srv_array[srv_addr]["box"])
            # Server buttons
            config.srv_array[srv_addr]["search_btn"] = QPushButton("Search", config.srv_array[srv_addr]["box"])
            config.srv_array[srv_addr]["search_btn"].clicked.connect(partial(SRVMenu.srv_search, _self, [srv_addr]))
            config.srv_array[srv_addr]["action_btn"] = QPushButton("Actions", config.srv_array[srv_addr]["box"])
            config.srv_array[srv_addr]["action_btn"].setEnabled(False)
            config.srv_array[srv_addr]["settings_btn"] = QPushButton("Settings", config.srv_array[srv_addr]["box"])
            config.srv_array[srv_addr]["settings_btn"].clicked.connect(partial(SRVMenu.srv_settings, _self, srv_addr))
            # Adding server buttons to server layout
            config.srv_array[srv_addr]["layout"].addWidget(config.srv_array[srv_addr]["search_btn"])
            config.srv_array[srv_addr]["layout"].addWidget(config.srv_array[srv_addr]["action_btn"])
            config.srv_array[srv_addr]["layout"].addWidget(config.srv_array[srv_addr]["settings_btn"])

            # Adding single server box to scroll layout
            _self.scroll_content_layout.addWidget(config.srv_array[srv_addr]["box"])


# ============================================================================ #
# CONTEXT MENU
# ============================================================================ #

# Server box right click context menu
def box_context_menu(_self, event):
    menu = QMenu()
    #
    # TODO Shut down all action
    shutdown_action = QAction(QIcon("icon/shutdown.png"), "Shut down all", _self)
    shutdown_action.triggered.connect(box_pwr_off)
    #
    add_action = QAction(QIcon("icon/add.png"), "Add server", _self)
    add_action.triggered.connect(partial(ApplicationMenu.add_server, _self))
    #
    # TODO Clear list action
    clear_list = QAction(QIcon("icon/clear.png"), "Clear server list", _self)
    #
    menu.addAction(shutdown_action)
    menu.addAction(add_action)
    menu.addAction(clear_list)
    menu.exec_(_self.server_box.mapToGlobal(event))


#
def box_pwr_off():
    print(config.srv_array.keys())
