# Software configuration
from library import config

#
from functools import partial
# PyQt5 modules
from PyQt5 import uic
from PyQt5.QtGui import QRegExpValidator
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QDialog


def text_changed(linedit):
    linedit.setStyleSheet("")


class AddServerUI(QDialog):
    def __init__(self, parent=None):
        # noinspection PyArgumentList
        super(AddServerUI, self).__init__(parent)
        self.setAttribute(Qt.WA_DeleteOnClose)
        uic.loadUi("ui/ModalAddServer.ui", self)

        # Getting the configuration from config.ini file
        self.config = config.get_config()
        #
        self.server_port.setText(self.config["SETTINGS"]["server_default_port"])
        self.search_filter.setText("*")

        # Obligatory line edit list
        self.linedit_list = [self.server_address, self.server_port, self.search_filter]
        #
        for linedit in self.linedit_list:
            linedit.textChanged.connect(partial(text_changed, linedit))

        # Setting IP validation for server address line edit
        ip_validator = QRegExpValidator(config.ip_regex, self)
        self.server_address.setValidator(ip_validator)

        #
        self.apply_button.clicked.connect(self.apply_action)
        self.cancel_button.clicked.connect(self.close)

    def apply_action(self):
        # Checking for empty string in obligatory line edit list
        if config.is_empty(self.linedit_list):
            return

        # Checking for the valid IPv4 address in server address line edit
        if not config.is_valid([self.server_address]):
            return

        # Inserting a server to the configuration file
        params = {
            "server_port": self.server_port.text(),
            "search_filter": self.search_filter.text(),
            "server_name": self.server_name.text()
        }
        config.config_add(self.server_address.text(), params)

        # Closing the modal window
        self.close()
