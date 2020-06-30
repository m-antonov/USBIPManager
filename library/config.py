#
import builtins
#
from os import path, chdir
# Interaction with the configuration *.ini files
from configparser import ConfigParser
# PyQt5 modules
from PyQt5.QtGui import QIcon
from PyQt5.QtCore import QPersistentModelIndex
from PyQt5.QtWidgets import QMessageBox, QWidget, QProgressBar


# ============================================================================ #
# SYNC FUNCTIONS
# ============================================================================ #

# Reading the configuration file
def get_config():
    config = ConfigParser()
    config.read(["config.ini"], encoding="utf-8")
    return config


# Checking if one of the line edit is empty
def is_empty(linedit_list):
    for linedit in linedit_list:
        if not linedit.text():
            linedit.setStyleSheet(linedit_stylesheet)
            return True
    return False


#
def iter_dev(_self, srv_addr):
    #
    root = _self.device_tree.invisibleRootItem()
    child_count = root.childCount()
    # Looping through children range and getting certain server address
    for child in range(child_count):
        item = root.child(child)
        if item.text(0) == srv_addr:
            # Counting server children
            sub_child_count = item.childCount()
            # Looping through server children range and yielding certain device
            for sub_child in range(sub_child_count):
                dev = item.child(sub_child)
                yield dev


#
def capturing_disable(_self):
    for srv_addr in capture_array:
        #
        capture_array[srv_addr]["event"].set()
        capture_array[srv_addr]["queue"].put(None)
        # Killing data capturing process on the server
        ssh_pid = capture_array[srv_addr]["ssh_pid"]
        ssh_array[srv_addr].exec_command("sudo kill {0}".format(ssh_pid))
        # Deleting icons and tooltips from device tree
        for dev in iter_dev(_self, srv_addr):
            device_tree.set_icon(dev, 0, QIcon())
            device_tree.set_tooltip(dev, 0, "")


#
def alert_box(title, message, icon, detail=False):
    alert = QMessageBox()
    alert.setWindowTitle(title)
    alert.setText(message)
    alert.setIcon(icon)
    if detail:
        alert.setDetailedText(detail)
    alert.exec_()


# Reading the capture configuration file
def get_capturing_config():
    capturing_config = ConfigParser()
    capturing_config.read(["capturing.ini"], encoding="utf-8")
    return capturing_config


#
def table_row_delete(table_widget):
    if table_widget.selectionModel().hasSelection():
        index = [QPersistentModelIndex(index) for index in table_widget.selectionModel().selectedRows()]
        if not index:
            alert_box(_("Warning"), _("Please select entire row!"), 2)
            return
        for row in index:
            table_widget.removeRow(row.row())
    else:
        # Setting up the alert message
        alert_box(_("Warning"), _("No configuration row selected!"), 2)


# ============================================================================ #
# PARAMS AND VARIABLES
# ============================================================================ #

# Software title
program_title = "USBIPManager"

#
# TODO Documenting
linedit_stylesheet = "background-color: rgb(244, 125, 85); border: 0.5px solid rgb(63, 63, 63);"

# Default key / value parameters for server configuration
default_srv_ini = {
    'server_port': '',
    'search_filter': '*',
    'server_name': '',
    'auth_ssh_port': '10050',
    'auth_username': 'usbip',
    'auth_password': 'usbip',
    'key_path': '',
    'key_passphrase': '',
    'auth_type_key': 'False',
    'auth_type_password': 'False',
    'auth_type_none': 'True',
    'hub_json': 'None',
    'hub_timeout': '3',
    'remote_daemon': 'False',
    'remote_kernel': 'False',
    'remote_syslog': 'False',
    'remote_user': 'False',
    'local_sftp': 'False',
    'local_ssh': 'False',
    'logging_time': '30',
    'capturing_box': 'False',
}

#
# TODO Documenting
ssh_array = dict()
#
# TODO Documenting
usbip_array = dict()
#
# TODO Documenting
ep_array = dict()
#
# TODO Documenting
capture_array = dict()

# Setting the working directory
BASE_DIR = path.dirname(path.dirname(path.abspath(__file__)))
chdir(BASE_DIR)

#
if "_" not in dir(builtins):
    from gettext import gettext as _


class Singleton(type):
    """ Class single design pattern with arguments """
    instances = {}

    def __call__(cls, *args):
        _key = (cls, args)
        if _key not in cls.instances:
            cls.instances[_key] = super(Singleton, cls).__call__(*args)
        return cls.instances[_key]

    def __repr__(cls):
        return f'{cls.__name__}'


class WSingleton(Singleton, type(QWidget)):
    """ Class single design pattern with arguments and QWidget type to resolve metaclass conflict """
    pass


class ProgressBar(QProgressBar):
    """ Progress bar with custom printable class representation for queue manager modal window """
    def __init__(self, base, name):
        super(ProgressBar, self).__init__(parent=base)

        self._name = name
        self._value = 0

        self.setValue(self._value)

    def __repr__(self):
        """ Printable class representation for queue manager modal window """
        return f'{self._name} QProgressBar'


class ProgressRepr:
    """ Custom printable QProgressBar class representation interface """
    def __init__(self, obj, name):
        super(ProgressRepr, self).__init__()

        self._obj = obj
        self._name = name

    def replace(self):
        """ Remove / Replace an object with custom representation """
        _base = self._obj.parent()
        _lyt = _base.layout()
        _position = _lyt.getItemPosition(_lyt.indexOf(self._obj))

        _lyt.removeWidget(self._obj)
        self._obj.deleteLater()
        self._obj.setParent(None)

        _obj = ProgressBar(_base, self._name)
        _lyt.addWidget(_obj, *_position)
        _lyt.update()

        return _obj
