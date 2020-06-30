from library import ini
from library.validation import InterfaceManager

from json import load
from os import listdir, path
from PyQt5 import uic
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QWidget, QDialog, QHeaderView, QTableWidgetItem


class UIObj(QWidget):
    """  """
    def __init__(self, hub_id):
        super(UIObj, self).__init__()
        uic.loadUi('ui/widget/hub.ui', self)

        self.setAttribute(Qt.WA_DeleteOnClose)

        self._hub_id = hub_id

        for idx, param in enumerate(self._hub_id, 1):
            _checkbox = getattr(self, f'port_{idx}')
            _checkbox.setChecked(self._hub_id[param][0])
            _name = getattr(self, f'port_{idx}_name')
            _name.setText(self._hub_id[param][1])


class DaemonConfigUI(QDialog):
    """  """
    def __init__(self, base, ip_addr):
        super(DaemonConfigUI, self).__init__(parent=base)
        uic.loadUi('ui/modal/DaemonConfig.ui', self)

        self.setAttribute(Qt.WA_DeleteOnClose)

        self._base = base
        self._ip_addr = ip_addr
        self.setWindowTitle(f'{self.windowTitle()} {self._ip_addr}')

        self._interface_manager = InterfaceManager(self)

        self.config = ini.Daemon(self._base, self._ip_addr)

        self.form_req = (
            self.dmn_name,
            self.dmn_port,
            self.ssh,
            self.hub,
            self.sniffer
        )

        _header = self.hub_cfg_param.horizontalHeader()
        _header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        _header.setSectionResizeMode(1, QHeaderView.Stretch)

        _header = self.hub_cfg_param.verticalHeader()
        _header.setSectionResizeMode(QHeaderView.ResizeToContents)

        _hub_cfg = listdir('hub')
        if _hub_cfg:
            self.hub_cfg.addItems([path.splitext(_cfg)[0] for _cfg in _hub_cfg if _cfg.endswith('.json')])
            self.hub_cfg.currentTextChanged.connect(self._hub_cfg_update)

        self.apply_btn.clicked.connect(self.apply_action)
        self.cancel_btn.clicked.connect(self.close)

        self._interface_manager.setup()

    def _hub_cfg_update(self):
        """  """
        try:
            with open(path.join('hub', f'{self.hub_cfg.currentText()}.json')) as fp:
                _hub_cfg = load(fp)
        except FileNotFoundError:
            return self.hub_cfg_param.setRowCount(0)

        self.hub_cfg_param.setRowCount(len(_hub_cfg))
        for idx, hub_id in enumerate(_hub_cfg):
            _row = QTableWidgetItem(hub_id)
            _row.setTextAlignment(Qt.AlignCenter)
            self.hub_cfg_param.setItem(idx, 0, _row)
            self.hub_cfg_param.setCellWidget(idx, 1, UIObj(_hub_cfg[hub_id]))

    def apply_action(self):
        """  """
        self._interface_manager.apply()
