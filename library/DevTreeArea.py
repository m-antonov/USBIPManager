# Software configuration
from library import config
#
from library import SSH

#
from time import sleep
#
from threading import Thread
# PyQt5 modules
from PyQt5.QtWidgets import QTreeWidgetItem
#
from subprocess import STARTUPINFO, STARTF_USESHOWWINDOW, Popen, PIPE


# ============================================================================ #
# SYNC FUNCTIONS
# ============================================================================ #

# Mounting selected device to the system
def srv_connection_process(_self, srv_addr, dev_bus, event):
    # Getting the list with all device tree children
    child_list = list()
    root = _self.device_tree.invisibleRootItem()
    child_count = root.childCount()
    for child in range(child_count):
        item = root.child(child)
        child_list.append(item.text(0))

    # Adding connected device to device tree
    DeviceTreeAddChild(_self, srv_addr, dev_bus, srv_addr not in child_list)

    # Checking if ssh connection not present and establishing ssh connection with server
    if srv_addr not in config.ssh_array:
        config.logging_result.append_text(
            _self, "An active ssh connection with the {0} server not found".format(srv_addr))
        # Establishing ssh connection with server
        SSH.connection(_self, srv_addr)
        # Reading and analyzing the server bit rate stdout
        SSH.USBTopSTDOUTProcessing(srv_addr, config.usbtop_array)

    # Starting device bit rate update thread
    DeviceTreeUpdate(_self, srv_addr, dev_bus, event)

    # Eliminating windows console during process execution
    startupinfo = STARTUPINFO()
    startupinfo.dwFlags |= STARTF_USESHOWWINDOW
    # Mounting device to the system
    connection = Popen(
        "usbip.exe -a {0} {1}".format(
            srv_addr, dev_bus), stdin=PIPE, stdout=PIPE, stderr=PIPE, startupinfo=startupinfo, bufsize=0)
    connection.communicate()


# ============================================================================ #
# CLASSES
# ============================================================================ #

# Adding connected device to device tree
class DeviceTreeAddChild(object):
    def __init__(self, _self, srv_addr, dev_bus, add_srv):
        self._self = _self
        self.srv_addr = srv_addr
        self.dev_bus = dev_bus
        self.add_srv = add_srv

        # Adding connected device to the device tree
        self.add_child()

    # Getting server tree widget by the server address
    def get_srv_child(self):
        root = self._self.device_tree.invisibleRootItem()
        child_count = root.childCount()
        for child in range(child_count):
            item = root.child(child)
            if item.text(0) == self.srv_addr:
                return child

    # Adding connected device to the device tree
    def add_child(self):
        # The server is not present in the device tree
        if self.add_srv:
            srv_child = QTreeWidgetItem([self.srv_addr])
        # The server is present in the device tree
        else:
            srv_child_id = self.get_srv_child()
            srv_child = self._self.device_tree.takeTopLevelItem(srv_child_id)

        # Setting up default bit rate activity values and adding server device child to the device tree
        dev_child = QTreeWidgetItem([self.dev_bus])
        child_activity = QTreeWidgetItem(["Activity", "N/A", "N/A"])
        dev_child.addChild(child_activity)
        srv_child.addChild(dev_child)
        config.device_tree.append_item(self._self, srv_child)


# Device bit rate update thread
class DeviceTreeUpdate(object):
    def __init__(self, _self, srv_addr, dev_bus, event):
        self._self = _self
        self.srv_addr = srv_addr
        self.dev_bus = dev_bus
        self.event = event
        # TODO Dynamic configuration update after changing software settings
        # TODO Getting configuration from the global source
        self.config = config.get_config()

        # Setting up and starting the thread
        thread = Thread(target=self.run, name="DeviceTree: {0} {1}".format(self.srv_addr, self.dev_bus), daemon=True)
        thread.start()

    # Getting server device number by the device bus
    def get_dev_num(self):
        # TODO SSH lost connection exception
        ssh_connection = config.ssh_array[self.srv_addr]
        if ssh_connection.get_transport().is_active():
            stdin, stdout, stderr = ssh_connection.exec_command(
                "sudo cat /sys/bus/usb/devices/{0}/devnum".format(self.dev_bus))
            return stdout.readline(2048).rstrip()

    # Bit rate update thread
    def run(self):
        # Getting server device number and device bus id
        # TODO SSH lost connection exception
        dev_num = int(self.get_dev_num())
        bus_id = int(self.dev_bus[0])
        # Getting device child from the device tree
        # TODO Device child not found exception
        dev_child = self.get_dev_child()
        activity = dev_child.child(0)
        # Updating until the event is set
        while not self.event.is_set():
            # Updating bit rate "to" device value
            try:
                config.device_tree.set_text(
                    activity, 1, config.usbtop_array[self.srv_addr][bus_id][dev_num][0] + " kb/s")
            except KeyError:
                config.device_tree.set_text(activity, 1, "N/A")
            # Updating bit rate "from" device value
            try:
                config.device_tree.set_text(
                    activity, 2, config.usbtop_array[self.srv_addr][bus_id][dev_num][1] + " kb/s")
            except KeyError:
                config.device_tree.set_text(activity, 2, "N/A")
            # Activity updating polling time
            sleep(float(self.config["SETTINGS"]["device_updating_time"]))

    # Getting server device tree widget by the server address and device bus
    def get_dev_child(self):
        # Getting the device tree root and counting children
        root = self._self.device_tree.invisibleRootItem()
        child_count = root.childCount()
        # Looping through children range and getting certain server address
        for child in range(child_count):
            item = root.child(child)
            if item.text(0) == self.srv_addr:
                # Counting server children
                sub_child_count = item.childCount()
                # Looping through server children range and getting certain device
                for sub_child in range(sub_child_count):
                    dev = item.child(sub_child)
                    if dev.text(0) == self.dev_bus:
                        # Returning server device tree widget
                        return dev
