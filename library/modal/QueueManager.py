from library import config

import threading
from PyQt5 import uic
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QDialog, QHeaderView, QTableWidgetItem


class QueueManagerUI(QDialog):
    """ Modal window with a queue manager to control active processes and interfaces """
    def __init__(self, parent):
        super(QueueManagerUI, self).__init__(parent)
        uic.loadUi('ui/modal/QueueManager.ui', self)

        self.setAttribute(Qt.WA_DeleteOnClose)

        _header = self.thread_table.horizontalHeader()
        _header.setSectionResizeMode(0, QHeaderView.Stretch)

        self.thread_table.setRowCount(len(threading.enumerate()))
        for idx, thread in enumerate(threading.enumerate()):
            __name = QTableWidgetItem(thread.name)

            self.thread_table.setItem(idx, 0, __name)

        _header = self.interface_table.horizontalHeader()
        _header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        _header.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        _header.setSectionResizeMode(2, QHeaderView.Stretch)

        _instance = config.Singleton.instances
        self.interface_table.setRowCount(len(_instance))
        for idx, interface in enumerate(_instance):
            _cls, _param = interface

            __name = QTableWidgetItem(repr(_cls))
            __param = QTableWidgetItem(repr(_param))
            __doc = QTableWidgetItem(_cls.__doc__)

            self.interface_table.setItem(idx, 0, __name)
            self.interface_table.setItem(idx, 1, __param)
            self.interface_table.setItem(idx, 2, __doc)

        self.cancel_btn.clicked.connect(self.close)
