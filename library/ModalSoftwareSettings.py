# Software configuration
from library import config

#
from os import remove
#
from functools import partial
# PyQt5 modules
from PyQt5 import uic
from PyQt5.QtGui import QIntValidator, QDoubleValidator
from PyQt5.QtWidgets import QDialog


def text_changed(linedit):
    linedit.setStyleSheet("")


class SoftwareSettingUI(QDialog):
    def __init__(self, parent=None):
        # noinspection PyArgumentList
        super(SoftwareSettingUI, self).__init__(parent)
        uic.loadUi("ui/ModalSoftwareSettings.ui", self)

        # Getting the configuration from config.ini file
        self.config = config.get_config()
        # Interface
        self.language_index = int(self.config["SETTINGS"]["software_language"])
        self.language.setCurrentIndex(self.language_index)
        self.language.currentIndexChanged.connect(self.language_alert)
        #
        self.default_port.setText(self.config["SETTINGS"]["server_default_port"])
        self.socket_timeout.setText(self.config["SETTINGS"]["server_socket_timeout"].replace(".", ","))
        self.polling_time.setText(self.config["SETTINGS"]["server_polling_time"].replace(".", ","))
        self.connecting_timeout.setText(self.config["SETTINGS"]["connecting_timeout"].replace(".", ","))
        self.updating_time.setText(self.config["SETTINGS"]["device_updating_time"].replace(".", ","))

        # Obligatory line edit list
        self.linedit_list = [self.default_port, self.socket_timeout, self.polling_time, self.updating_time]
        #
        for linedit in self.linedit_list:
            linedit.textChanged.connect(partial(text_changed, linedit))

        # Setting input validation for line edits
        self.default_port.setValidator(QIntValidator())
        self.socket_timeout.setValidator(QDoubleValidator())
        self.polling_time.setValidator(QDoubleValidator())
        self.connecting_timeout.setValidator(QDoubleValidator())
        self.updating_time.setValidator(QDoubleValidator())

        #
        self.apply_button.clicked.connect(self.apply_action)
        self.cancel_button.clicked.connect(self.close)

    #
    def language_alert(self):
        if self.language.currentIndex() != self.language_index:
            config.alert_box("Warning", "Please restart the software to apply the language settings!", 1)

    def apply_action(self):
        # Checking for empty string in obligatory line edit list
        if config.is_empty(self.linedit_list):
            return

        # Updating config.ini
        remove("config.ini")
        self.config.set("SETTINGS", "software_language", str(self.language.currentIndex()))
        self.config.set("SETTINGS", "server_default_port", str(self.default_port.text()))
        self.config.set("SETTINGS", "server_socket_timeout", str(self.socket_timeout.text()).replace(",", "."))
        self.config.set("SETTINGS", "server_polling_time", str(self.polling_time.text()).replace(",", "."))
        self.config.set("SETTINGS", "connecting_timeout", str(self.connecting_timeout.text()).replace(",", "."))
        self.config.set("SETTINGS", "device_updating_time", str(self.updating_time.text()).replace(",", "."))
        with open("config.ini", "a", encoding="utf-8") as f:
            self.config.write(f)

        # Closing the modal window
        self.close()
