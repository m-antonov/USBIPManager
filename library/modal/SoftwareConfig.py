from library import ini
from library.validation import InterfaceManager

from PyQt5 import uic
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QDialog


class SoftwareConfigUI(QDialog):
    """  """
    def __init__(self, base):
        super(SoftwareConfigUI, self).__init__(parent=base)
        uic.loadUi('ui/modal/SoftwareConfig.ui', self)

        self.setAttribute(Qt.WA_DeleteOnClose)

        self._base = base

        self._interface_manager = InterfaceManager(self)

        self.config = ini.SWConfig(self._base)

        self.form_req = (
            self.lang,
            self.dmn_def_port,
            self.clt_ver,
            self.dev_atch_tmo,
            self.dev_dtch_tmo,
            self.queue_tmo,
            self.dmn_perf,
            self.dev_perf,
            self.sys_perf,
            self.net_perf
        )

        self.apply_btn.clicked.connect(self.apply_action)
        self.cancel_btn.clicked.connect(self.close)

        self._interface_manager.setup()

    def apply_action(self):
        """  """
        self._interface_manager.apply()
