#
from os import remove
#
from time import sleep
#
from datetime import datetime
#
from math import floor, log, pow
#
from ipaddress import ip_address
# Async threading interface
from asyncio import all_tasks
from threading import Event, Thread
# Interaction with the configuration *.ini files
from configparser import ConfigParser
#
from library.QtWaitingSpinner import QtWaitingSpinner
# PyQt5 modules
from PyQt5.QtGui import QIcon
from PyQt5.QtCore import QObject, pyqtSignal, Qt, QRegExp
from PyQt5.QtWidgets import QMessageBox
#
from subprocess import STARTUPINFO, STARTF_USESHOWWINDOW, Popen, PIPE


# ============================================================================ #
# QT SIGNALS
# ============================================================================ #

# Logging text browser
class LoggingResult(QObject):
    textAppended = pyqtSignal(object, str, bool, bool, bool)

    def append_text(self, _self, text, success=False, warn=False, err=False):
        self.textAppended.emit(_self, text, success, warn, err)


# Appending the text to text browser from an external thread
def append_text(_self, text, success=False, warn=False, err=False):
    # Success message type
    if success:
        _self.log.append(str(datetime.now().strftime("%Y-%m-%d %H:%M:%S")) + " : " +
                         "<font color='green'>Success: </font>" + text)
    # Warning message type
    elif warn:
        _self.log.append(str(datetime.now().strftime("%Y-%m-%d %H:%M:%S")) + " : " +
                         "<font color='orange'>Warning: </font>" + text)
    # Error message type
    elif err:
        _self.log.append(str(datetime.now().strftime("%Y-%m-%d %H:%M:%S")) + " : " +
                         "<font color='red'>An error has occurred: </font>" + text)
    # Default info message type
    else:
        _self.log.append(str(datetime.now().strftime("%Y-%m-%d %H:%M:%S")) + " : " + text)


# Applying signals
logging_result = LoggingResult()
logging_result.textAppended.connect(
    lambda _self, text, success, warn, err: append_text(_self, text, success, warn, err))


# Device tree
class DeviceTreeSignal(QObject):
    topLevelItemAppended = pyqtSignal(object, object)
    childTextSet = pyqtSignal(object, int, str)
    childIconSet = pyqtSignal(object, int, object)
    childToolTipSet = pyqtSignal(object, int, str)

    def append_item(self, _self, child):
        self.topLevelItemAppended.emit(_self, child)

    def set_text(self, child, col_id, text):
        self.childTextSet.emit(child, col_id, text)

    def set_tooltip(self, child, col_id, tooltip):
        self.childToolTipSet.emit(child, col_id, tooltip)

    def set_icon(self, child, col_id, icon):
        self.childIconSet.emit(child, col_id, icon)


# Appending the child to device tree from an external thread
def append_item(_self, child):
    _self.device_tree.addTopLevelItem(child)
    _self.device_tree.expandAll()


# Setting the device tree child column text from an external thread
def set_text(child, col_id, text):
    child.setText(col_id, text)


#
def set_tooltip(child, col_id, tooltip):
    child.setToolTip(col_id, tooltip)


#
def set_icon(child, col_id, icon):
    child.setIcon(col_id, icon)


# Applying signals
device_tree = DeviceTreeSignal()
device_tree.topLevelItemAppended.connect(lambda _self, child: append_item(_self, child))
device_tree.childTextSet.connect(lambda child, col_id, text: set_text(child, col_id, text))
device_tree.childToolTipSet.connect(lambda child, col_id, tooltip: set_tooltip(child, col_id, tooltip))
device_tree.childIconSet.connect(lambda child, col_id, icon: set_icon(child, col_id, icon))


# Server auto find progress bar
class ProgressBar(QObject):
    valueUpdated = pyqtSignal(object, float)

    def set_progress(self, _self, value):
        self.valueUpdated.emit(_self, value)


#
def set_progress(_self, value):
    _self.progress_bar.setValue(value)


# Applying signals
progress_bar = ProgressBar()
progress_bar.valueUpdated.connect(lambda _self, value: set_progress(_self, value))


# Server auto find search list result
class SearchResult(QObject):
    listCleared = pyqtSignal(object)
    itemAdded = pyqtSignal(object, object)

    def clear_list(self, _self):
        self.listCleared.emit(_self)

    def add_item(self, _self, item):
        self.itemAdded.emit(_self, item)


#
def clear_list(_self):
    _self.search_result.clear()


#
def add_item(_self, item):
    _self.search_result.addItem(item)


# Applying signals
search_result = SearchResult()
search_result.itemAdded.connect(lambda _self, item: add_item(_self, item))
search_result.listCleared.connect(lambda _self: clear_list(_self))


#
class SpinnerQueue(QObject):
    spinnerStarted = pyqtSignal(object)
    spinnerStopped = pyqtSignal(object)

    def start_spinner(self, spinner):
        self.spinnerStarted.emit(spinner)

    def stop_spinner(self, spinner):
        self.spinnerStopped.emit(spinner)


#
def start_spinner(spinner):
    spinner.start()


#
def stop_spinner(spinner):
    spinner.stop()


# Applying signals
spinner_queue = SpinnerQueue()
spinner_queue.spinnerStarted.connect(lambda spinner: start_spinner(spinner))
spinner_queue.spinnerStopped.connect(lambda spinner: stop_spinner(spinner))


# ============================================================================ #
# CLASSES
# ============================================================================ #

#
class KillProc(object):
    def __init__(self, _self, spinner_obj, sw=False):
        self._self = _self
        self.sw = sw

        # Initializing and starting spinner
        self.spinner = QtWaitingSpinner(spinner_obj, True, True, Qt.ApplicationModal)
        spinner_queue.start_spinner(self.spinner)

        #
        self.ready = Event()

    def processing(self):
        # Shutting down all usbip connections
        shutdown = ConnectionShutdown(self._self, self.ready)
        shutdown_thread = Thread(target=shutdown.processing, name="KillProc SW: {0}".format(self.sw), daemon=True)
        shutdown_thread.start()
        self.ready.wait()
        #
        capturing_disable(self._self)
        # Stopping waiting spinner
        spinner_queue.stop_spinner(self.spinner)

        # Stopping all running processes
        if self.sw:
            for queue in all_tasks(self._self.main_loop):
                queue.cancel()


#
class ConnectionShutdown(object):
    def __init__(self, _self, ready):
        self._self = _self
        self.ready = ready

        #
        self.timeout = float(self._self.config["SETTINGS"]["connecting_timeout"])

    def processing(self):
        # Number of remaining devices
        array_length = get_array_length(usbip_array)

        #
        for srv_addr in usbip_array:
            # Copying of the keys to avoiding RuntimeError after query finished
            for dev_bus in list(usbip_array[srv_addr]):
                index = usbip_array[srv_addr][dev_bus]["d_index"]
                # Reducing the number of remaining devices
                array_length -= 1

                # Eliminating windows console during process execution
                startupinfo = STARTUPINFO()
                startupinfo.dwFlags |= STARTF_USESHOWWINDOW
                #
                query = Popen(
                    "usbip.exe -d {0}".format(index), stdin=PIPE, stdout=PIPE, stderr=PIPE, startupinfo=startupinfo)
                query.wait()

                #
                logging_result.append_text(
                    self._self, "The {0} device has disconnected from the {1} server, {2} left".format(
                        dev_bus, srv_addr, str(array_length)), warn=True)
                #
                sleep(self.timeout)
        #
        self.ready.set()


# ============================================================================ #
# SYNC FUNCTIONS
# ============================================================================ #

# Reading the configuration file
def get_config():
    config = ConfigParser()
    config.read(["config.ini"], encoding="utf-8")
    return config


# Adding a server to the configuration file
def config_add(linedit_list):
    config = ConfigParser()
    section = linedit_list.pop(0).text()
    config.add_section(section)
    for linedit in linedit_list:
        config.set(section, linedit.objectName(), linedit.text())
    with open("config.ini", "a", encoding="utf-8") as f:
        config.write(f)


# Removing a server from the configuration file
def config_rm(config, srv_addr):
    remove("config.ini")
    with open("config.ini", "a", encoding="utf-8") as f:
        config.remove_section(srv_addr)
        config.write(f)


# Checking if one of the line edit is empty
def is_empty(linedit_list):
    for linedit in linedit_list:
        if not linedit.text():
            linedit.setStyleSheet(linedit_stylesheet)
            return True
    return False


# Checking if one of the line edit IPv4 address is valid
def is_valid(linedit_list):
    for linedit in linedit_list:
        try:
            ip_address(linedit.text())
        except ValueError:
            linedit.setStyleSheet(linedit_stylesheet)
            return False
    return True


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
def get_array_length(array):
    return sum(len(value) for value in array.values())


#
def convert_size(size_bytes):
    if size_bytes == 0:
        return "0 B"
    size_name = ("B", "KB", "MB", "GB", "TB", "PB", "EB", "ZB", "YB")
    i = int(floor(log(size_bytes, 1024)))
    p = pow(1024, i)
    s = round(size_bytes / p, 2)
    return "%s %s" % (s, size_name[i])


#
def alert_box(title, message, icon, detail=False):
    alert = QMessageBox()
    alert.setWindowTitle(title)
    alert.setText(message)
    alert.setIcon(icon)
    if detail:
        alert.setDetailedText(detail)
    alert.exec_()


# ============================================================================ #
# PARAMS AND VARIABLES
# ============================================================================ #

#
watchdog_enable = True

# Software title
program_title = "USBIPManager"

# Regex IP address linedit validation
ip_range = "(?:[0-1]?[0-9]?[0-9]|2[0-4][0-9]|25[0-5])"
ip_regex = QRegExp("^" + ip_range + "\\." + ip_range + "\\." + ip_range + "\\." + ip_range + "$")

#
# TODO Documenting
linedit_stylesheet = "background-color: rgb(244, 125, 85); border: 0.5px solid rgb(63, 63, 63);"

#
# TODO Documenting
ssh_array = dict()
#
# TODO Documenting
usbtop_array = dict()
#
# TODO Documenting
srv_array = dict()
#
# TODO Documenting
usbip_array = dict()
#
# TODO Documenting
ep_array = dict()
#
# TODO Documenting
capture_array = dict()
