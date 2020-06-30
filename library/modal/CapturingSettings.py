# Software configuration
from library import config

# PyQt5 modules
from PyQt5 import uic
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QDialog, QHeaderView, QTableWidgetItem


# ============================================================================ #
# GUI
# ============================================================================ #

class CapturingSettingUI(QDialog):
    def __init__(self, parent=None, srv_addr=None):
        # noinspection PyArgumentList
        super(CapturingSettingUI, self).__init__(parent)
        self.setAttribute(Qt.WA_DeleteOnClose)
        uic.loadUi("ui/modal/CapturingSettings.ui", self)
        self.srv_addr = srv_addr

        # Window title
        self.setWindowTitle(self.windowTitle() + " {0}".format(self.srv_addr))

        # Stretching table to fit the widget
        self.children_conf.horizontalHeader().setResizeMode(QHeaderView.Stretch)

        #
        self.children_gen.clicked.connect(self.children_gen_action)

        # Setting up children configuration menu click actions
        self.children_conf_save.clicked.connect(self.save_action)
        self.children_conf_insert.clicked.connect(self.insert_action)
        self.children_conf_delete.clicked.connect(self.delete_action)
        self.children_conf_cancel.clicked.connect(self.cancel_action)

    def insert_item(self, row_position):
        port_id = QTableWidgetItem("0")
        custom_name = QTableWidgetItem("Port #0")
        if self.children_conf.item(row_position - 1, 0):
            port_id.setText(str(row_position))
            custom_name.setText("Port #" + str(row_position))
        port_id.setTextAlignment(Qt.AlignCenter)
        custom_name.setTextAlignment(Qt.AlignCenter)
        return port_id, custom_name

    def children_gen_action(self):
        for child_id in range(int(self.children_qty.currentText())):
            row_position = self.children_conf.rowCount()
            self.children_conf.insertRow(row_position)
            self.children_conf.setItem(row_position, 0, self.insert_item(row_position)[0])
            self.children_conf.setItem(row_position, 1, self.insert_item(row_position)[1])

    def save_action(self):
        self.close()

    def insert_action(self):
        row_position = self.children_conf.rowCount()
        self.children_conf.insertRow(row_position)
        self.children_conf.setItem(row_position, 0, self.insert_item(row_position)[0])
        self.children_conf.setItem(row_position, 1, self.insert_item(row_position)[1])

    def delete_action(self):
        config.table_row_delete(self.children_conf)

    def cancel_action(self):
        self.close()
