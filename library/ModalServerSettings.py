# Software configuration
from library import config

#
from json import dump, load
#
from os import listdir, path, remove
# PyQt5 modules
from PyQt5 import uic
from PyQt5.QtCore import Qt, QPersistentModelIndex
from PyQt5.QtWidgets import QWidget, QHBoxLayout, QCheckBox, QDialog, QLineEdit, QHeaderView, QTableWidgetItem, \
    QFileDialog


class HubPortSelection(QWidget):
    def __init__(self, data, parent=None):
        # noinspection PyArgumentList
        QWidget.__init__(self, parent)

        layout = QHBoxLayout()
        for idx, port in enumerate(data, 1):
            checkbox = QCheckBox()
            checkbox.setText("{0}".format(idx))
            if port:
                checkbox.setChecked(True)
            # noinspection PyArgumentList
            layout.addWidget(checkbox)
            layout.setAlignment(Qt.AlignCenter)
        self.setLayout(layout)


class ServerSettingUI(QDialog):
    def __init__(self, parent=None, srv_addr=None):
        # noinspection PyArgumentList
        super(ServerSettingUI, self).__init__(parent)
        uic.loadUi("ui/ModalServerSettings.ui", self)
        self.srv_addr = srv_addr

        # Window title
        self.setWindowTitle(self.windowTitle() + " {0}".format(self.srv_addr))

        # Getting the configuration from config.ini file
        self.config = config.get_config()
        #
        self.server_name.setText(self.config[self.srv_addr]["server_name"])
        self.search_filter.setText(self.config[self.srv_addr]["search_filter"])
        #
        self.auth_ssh_port.setText(self.config[self.srv_addr]["auth_ssh_port"])
        self.auth_username.setText(self.config[self.srv_addr]["auth_username"])
        self.auth_password.setText(self.config[self.srv_addr]["auth_password"])
        self.auth_password.setEchoMode(QLineEdit.Password)
        self.key_path.setText(self.config[self.srv_addr]["key_path"])
        self.key_passphrase.setText(self.config[self.srv_addr]["key_passphrase"])
        self.key_passphrase.setEchoMode(QLineEdit.Password)
        #
        self.auth_type_key.setChecked(self.config[self.srv_addr].getboolean("auth_type_key"))
        self.auth_type_password.setChecked(self.config[self.srv_addr].getboolean("auth_type_password"))
        self.auth_type_none.setChecked(self.config[self.srv_addr].getboolean("auth_type_none"))

        # Reading the hub configuration directory and filling the combobox
        for file in listdir("hub"):
            if file.endswith(".json"):
                filename, _ = path.splitext(file)
                self.hub_json.addItem(filename)

        #
        self.hub_json.currentIndexChanged.connect(self.checking_hub_json)
        self.hub_json.setCurrentIndex(
            self.hub_json.findText(self.config[self.srv_addr]["hub_json"], Qt.MatchFixedString))

        # Save hub configuration button action
        self.hub_conf_save.clicked.connect(self.save_hub_json)
        # Insert hub configuration row button action
        self.hub_conf_insert.clicked.connect(self.insert_row_hub_json)
        # Delete hub configuration row button action
        self.hub_conf_delete.clicked.connect(self.delete_row_hub_json)

        #
        self.hub_timeout.setText(self.config[self.srv_addr]["hub_timeout"])

        # Server logging settings
        # Remote logging
        self.remote_daemon.setChecked(self.config[self.srv_addr].getboolean("log_daemon"))
        self.remote_kernel.setChecked(self.config[self.srv_addr].getboolean("log_kernel"))
        self.remote_syslog.setChecked(self.config[self.srv_addr].getboolean("log_syslog"))
        self.remote_user.setChecked(self.config[self.srv_addr].getboolean("log_user"))
        self.logging_time.setText(self.config[self.srv_addr]["logging_time"])
        # Local logging
        self.local_sftp.setChecked(self.config[self.srv_addr].getboolean("log_sftp"))
        self.local_ssh.setChecked(self.config[self.srv_addr].getboolean("log_ssh"))

        #
        self.search_filter.textChanged.connect(self.text_changed)

        #
        self.auth_type_key.clicked.connect(self.checking_auth_type)
        self.auth_type_password.clicked.connect(self.checking_auth_type)
        self.auth_type_none.clicked.connect(self.checking_auth_type)

        #
        self.apply_button.clicked.connect(self.apply_action)
        self.cancel_button.clicked.connect(self.close)
        self.select_button.clicked.connect(self.file_dialog)

        #
        self.checking_auth_type()

    #
    def text_changed(self):
        self.search_filter.setStyleSheet("")

    #
    def checking_auth_type(self):
        if self.auth_type_key.isChecked():
            self.auth_ssh_port.setEnabled(True)
            self.auth_username.setEnabled(True)
            self.auth_password.setEnabled(False)
            self.key_path.setEnabled(True)
            self.key_passphrase.setEnabled(True)
            self.select_button.setEnabled(True)
        elif self.auth_type_password.isChecked():
            self.auth_ssh_port.setEnabled(True)
            self.auth_username.setEnabled(True)
            self.auth_password.setEnabled(True)
            self.key_path.setEnabled(False)
            self.key_passphrase.setEnabled(False)
            self.select_button.setEnabled(False)
        elif self.auth_type_none.isChecked():
            self.auth_ssh_port.setEnabled(False)
            self.auth_username.setEnabled(False)
            self.auth_password.setEnabled(False)
            self.key_path.setEnabled(False)
            self.key_passphrase.setEnabled(False)
            self.select_button.setEnabled(False)

    #
    def checking_hub_json(self):
        # Reading current selected configuration
        try:
            with open(path.join("hub", "{0}.json".format(self.hub_json.currentText()))) as fp:
                conf = load(fp)
        # Disabling hub configuration objects in the absence of the configuration file
        except FileNotFoundError:
            self.hub_conf.setRowCount(0)
            self.hub_conf.setEnabled(False)
            self.hub_timeout.setEnabled(False)
            self.hub_conf_save.setEnabled(False)
            self.hub_conf_insert.setEnabled(False)
            self.hub_conf_delete.setEnabled(False)
            return

        # Enabling hub configuration objects in the presence of the configuration file
        self.hub_conf.setEnabled(True)
        self.hub_timeout.setEnabled(True)
        self.hub_conf_save.setEnabled(True)
        self.hub_conf_insert.setEnabled(True)
        self.hub_conf_delete.setEnabled(True)
        #
        self.hub_conf.setRowCount(len(conf))
        header = self.hub_conf.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.Stretch)
        for idx, hub_id in enumerate(conf):
            item = QTableWidgetItem(hub_id)
            item.setTextAlignment(Qt.AlignCenter)
            self.hub_conf.setItem(idx, 0, item)
            self.hub_conf.setCellWidget(idx, 1, HubPortSelection(conf[hub_id]))

    #
    def save_hub_json(self):
        # Default empty configuration array
        conf = dict()

        # Reading configuration parameters and filling array
        for row in range(self.hub_conf.rowCount()):
            #
            hub_id = self.hub_conf.item(row, 0).text()
            conf[hub_id] = list()
            #
            layout = self.hub_conf.cellWidget(row, 1).layout()
            ports = (layout.itemAt(i).widget() for i in range(layout.count()))
            for port in ports:
                conf[hub_id].append(port.isChecked() * 1)

        # Saving configuration to the json file
        # TODO File selection dialog
        with open(path.join("hub", "{0}.json".format(self.hub_json.currentText())), "w") as fp:
            dump(conf, fp)

        # Setting up the alert message
        config.alert_box("Success", "Configuration successfully saved!", 1)

    #
    def insert_row_hub_json(self):
        row_position = self.hub_conf.rowCount()
        self.hub_conf.insertRow(row_position)
        item = QTableWidgetItem()
        item.setTextAlignment(Qt.AlignCenter)
        self.hub_conf.setItem(row_position, 0, item)
        self.hub_conf.setCellWidget(row_position, 1, HubPortSelection([0] * 7))

    #
    def delete_row_hub_json(self):
        if self.hub_conf.selectionModel().hasSelection():
            index = [QPersistentModelIndex(index) for index in self.hub_conf.selectionModel().selectedRows()]
            if not index:
                config.alert_box("Warning", "Please select entire row!", 2)
                return
            for row in index:
                self.hub_conf.removeRow(row.row())
        else:
            # Setting up the alert message
            config.alert_box("Warning", "No configuration row selected!", 2)

    #
    def apply_action(self):
        # Checking for empty string in obligatory line edit list
        if config.is_empty([self.search_filter]):
            return

        # Updating config.ini
        remove("config.ini")
        #
        self.config.set(self.srv_addr, "search_filter", str(self.search_filter.text()))
        self.config.set(self.srv_addr, "server_name", str(self.server_name.text()))
        #
        self.config.set(self.srv_addr, "auth_ssh_port", str(self.auth_ssh_port.text()))
        self.config.set(self.srv_addr, "auth_username", str(self.auth_username.text()))
        self.config.set(self.srv_addr, "auth_password", str(self.auth_password.text()))
        self.config.set(self.srv_addr, "key_path", str(self.key_path.text()))
        self.config.set(self.srv_addr, "key_passphrase", str(self.key_passphrase.text()))
        #
        # TODO USB hub configuration
        #
        self.config.set(self.srv_addr, "auth_type_key", str(self.auth_type_key.isChecked()))
        self.config.set(self.srv_addr, "auth_type_password", str(self.auth_type_password.isChecked()))
        self.config.set(self.srv_addr, "auth_type_none", str(self.auth_type_none.isChecked()))
        # Server logging settings
        # Remote logging
        # Local logging
        # Saving configuration to the ini file
        with open("config.ini", "a", encoding="utf-8") as f:
            self.config.write(f)

        # Closing the modal window
        self.close()

    def file_dialog(self):
        options = QFileDialog.Options()
        # noinspection PyCallByClass
        filename, _ = QFileDialog.getOpenFileName(self, "Selecting key", "", "All Files (*)", options=options)
        if filename:
            self.key_path.setText(filename)
