from library import ini, log
from library.lang import LangConfig, LangFormValidation
from library.validation import ip_validator, form_empty, form_valid

from functools import partial
from PyQt5 import uic
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QDialog


def _update_form(form):
    """ Set the default form stylesheet """
    form.setStyleSheet('')


class LoadDaemonUI(QDialog):
    """ Modal window with a form for loading a daemon """
    def __init__(self, base):
        super(LoadDaemonUI, self).__init__(parent=base)
        uic.loadUi('ui/modal/LoadDaemon.ui', self)

        self.setAttribute(Qt.WA_DeleteOnClose)

        self._base = base

        self._sw_config = ini.SWConfig(self._base)

        self._dmn_manage = ini.DaemonManage(self._base)

        self._log = log.Manager(self._base)

        self._form_req = (self.dmn_addr, self.dmn_port)
        self._form_ip = (self.dmn_addr, )

        for form in self._form_req:
            form.textEdited.connect(partial(_update_form, form))

        self.dmn_port.setText(str(self._sw_config.dmn_def_port))
        self.dmn_addr.setValidator(ip_validator)
        self.dmn_addr.textEdited.connect(partial(_update_form, self.dmn_addr))

        self._form_setter = (self.dmn_port, self.dmn_name, self.dmn_filter)
        self._setter_param = {}
        for form in self._form_setter:
            self._setter_param[form] = form.text()

        self.apply_btn.clicked.connect(self.load_action)
        self.cancel_btn.clicked.connect(self.close)

    def load_action(self):
        """ Load the daemon to the main configuration """
        if form_empty(self._form_req):
            return self._log.setError(LangFormValidation.FormEmptyError)

        if form_valid(self._form_ip):
            return self._log.setError(LangFormValidation.FormValidError)

        _ip_addr = self.dmn_addr.text()
        try:
            self._dmn_manage.load(_ip_addr)
        except ini.InsertError:
            return self._log.setError(f'{_ip_addr} {LangConfig.InsertError}')
        _dmn_config = ini.Daemon(self._base, _ip_addr)
        for form in self._setter_param:
            if self._setter_param[form] != form.text():
                setattr(_dmn_config, form.objectName(), form.text())
        _dmn_config.write()
        self.close()
