# Software configuration
from library import config

#
from os import remove
#
from functools import partial
# Manipulating with IP addresses
from ipaddress import IPv4Address
# Async threading interface
from threading import Event
from asyncio import get_running_loop
#
from socket import socket, AF_INET, SOCK_STREAM, timeout
# PyQt5 modules
from PyQt5 import uic
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QRegExpValidator, QIcon
from PyQt5.QtWidgets import QDialog, QListWidgetItem, QMenu, QAction


# ============================================================================ #
# GUI
# ============================================================================ #

class FindServerUI(QDialog):
    def __init__(self, parent=None):
        # noinspection PyArgumentList
        super(FindServerUI, self).__init__(parent)
        self.setAttribute(Qt.WA_DeleteOnClose)
        uic.loadUi("ui/ModalAutoFind.ui", self)

        # Getting the configuration from config.ini file
        self.config = config.get_config()
        #
        self.from_ip = self.config["SETTINGS"]["find_from_range"]
        self.range_from.setText(self.from_ip)
        self.to_ip = self.config["SETTINGS"]["find_to_range"]
        self.range_to.setText(self.to_ip)

        # Obligatory line edit list
        self.linedit_list = [self.range_from, self.range_to]
        #
        for linedit in self.linedit_list:
            linedit.textChanged.connect(partial(self.text_changed, linedit))

        # Setting IP validation for the search range
        ip_validator = QRegExpValidator(config.ip_regex, self)
        for linedit in self.linedit_list:
            linedit.setValidator(ip_validator)

        # Getting the running event loop
        self.main_loop = get_running_loop()
        # Setting event for interrupting the task running in thread
        self.find_event = Event()

        # Setting buttons clicked actions
        self.find_button.clicked.connect(self.call_auto_find)
        self.stop_button.clicked.connect(self.call_stop_find)
        self.append_button.clicked.connect(self.call_append)
        self.cancel_button.clicked.connect(self.close)

        # Setting right-click context menu to check/uncheck all found servers
        self.search_result.setContextMenuPolicy(Qt.CustomContextMenu)
        self.search_result.customContextMenuRequested.connect(self.search_result_context_menu)

    # ============================================================================ #
    # SYNC FUNCTIONS
    # ============================================================================ #

    #
    def text_changed(self, linedit):
        # Updating config.ini
        remove("config.ini")
        self.config.set("SETTINGS", "find_from_range", str(self.range_from.text()))
        self.config.set("SETTINGS", "find_to_range", str(self.range_to.text()))
        # Saving configuration to the ini file
        with open("config.ini", "a", encoding="utf-8") as f:
            self.config.write(f)
        # Restoring default linedit stylesheet
        linedit.setStyleSheet("")

    #
    def call_auto_find(self):
        # Checking for empty string in obligatory line edit list
        if config.is_empty(self.linedit_list):
            return

        # Checking for the valid IPv4 address in obligatory line edit list
        if not config.is_valid(self.linedit_list):
            return

        # Restoring default linedit stylesheet
        self.range_from.setStyleSheet("")
        self.range_to.setStyleSheet("")
        # Switching modal buttons to search state
        self.find_button.setEnabled(False)
        self.stop_button.setEnabled(True)
        self.append_button.setEnabled(False)
        #
        self.main_loop.create_task(self.async_auto_find())

    #
    def auto_find(self, event):
        #
        from_range = int(IPv4Address(self.range_from.text()))
        to_range = int(IPv4Address(self.range_to.text()))
        # Resetting progress and result text browser
        current_progress = 0
        config.progress_bar.set_progress(self, round(current_progress))
        config.search_result.clear_list(self)
        #
        iteration_qty = to_range - from_range + 1
        if iteration_qty < 1:
            self.range_from.setStyleSheet(config.linedit_stylesheet)
            self.range_to.setStyleSheet(config.linedit_stylesheet)
            return
        progress_chunk = 100 / iteration_qty

        srv_list = list()

        # Searching servers through the IP range
        for ip_address in range(from_range, to_range + 1):
            if not event.is_set():
                try:
                    # Checking TCP connection to the server
                    conn = socket(AF_INET, SOCK_STREAM)
                    conn.settimeout(float(self.config["SETTINGS"]["server_socket_timeout"]))
                    conn.connect((str(IPv4Address(ip_address)), int(self.config["SETTINGS"]["server_default_port"])))
                    conn.close()
                    # Appending result with IP address
                    item = QListWidgetItem()
                    item.setText(str(IPv4Address(ip_address)))
                    item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
                    item.setCheckState(Qt.Unchecked)
                    config.search_result.add_item(self, item)
                    srv_list.append([str(IPv4Address(ip_address)), self.config["SETTINGS"]["server_default_port"]])
                    # Counting progress and moving progress bar
                    current_progress += progress_chunk
                    config.progress_bar.set_progress(self, round(current_progress))
                except (ConnectionRefusedError, timeout):
                    # Counting progress and moving progress bar
                    current_progress += progress_chunk
                    config.progress_bar.set_progress(self, round(current_progress))
            else:
                return srv_list
        return srv_list

    #
    def call_stop_find(self):
        self.find_event.set()

    #
    def call_append(self):
        #
        found_list = list()
        for index in range(self.search_result.count()):
            item = self.search_result.item(index)
            if item.checkState():
                found_list.append(item.text())

        #
        collision_list = list()
        for srv_addr in found_list:
            if srv_addr in config.srv_array:
                collision_list.append(srv_addr)

        #
        if collision_list:
            detail = "\n".join(collision_list)
            config.alert_box("Warning", "Some addresses have already been added! Please uncheck them first!", 1, detail)
        else:
            params = {
                "server_port": self.config["SETTINGS"]["server_default_port"],
                "search_filter": "*",
                "server_name": ""
            }
            for srv_addr in found_list:
                config.config_add(srv_addr, params)
            self.close()

    #
    def search_result_context_menu(self, event):
        menu = QMenu()
        check_all = QAction(QIcon("icon/check.png"), "Check all", self)
        check_all.triggered.connect(partial(self.context_menu_action, state=Qt.Checked))
        uncheck_all = QAction(QIcon("icon/uncheck.png"), "Uncheck all", self)
        uncheck_all.triggered.connect(partial(self.context_menu_action, state=Qt.Unchecked))
        menu.addAction(check_all)
        menu.addAction(uncheck_all)
        menu.exec_(self.search_result.mapToGlobal(event))

    #
    def context_menu_action(self, state):
        for index in range(self.search_result.count()):
            item = self.search_result.item(index)
            item.setCheckState(state)

    # ============================================================================ #
    # ASYNC FUNCTIONS
    # ============================================================================ #

    async def async_auto_find(self):
        #
        find_result = await self.main_loop.run_in_executor(None, self.auto_find, self.find_event)
        #
        self.find_event.clear()
        # Switching modal buttons to default state
        self.find_button.setEnabled(True)
        self.stop_button.setEnabled(False)
        #
        if find_result:
            self.append_button.setEnabled(True)
