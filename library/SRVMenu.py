# Software configuration
from library import config
#
from library import SSH
#
from library import DevTreeArea
#
from library import ApplicationMenu
#
from library.ModalServerSettings import ServerSettingUI

#
from os import path
#
from json import load
#
from time import sleep
# Calling functions with positional arguments
from functools import partial
# PyQt5 modules
from PyQt5.QtGui import QIcon
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QMenu, QAction
#
from library.QtWaitingSpinner import QtWaitingSpinner
# Async threading interface
from threading import Event
from concurrent.futures import ThreadPoolExecutor
from asyncio import create_subprocess_shell, subprocess


# Searching for devices on the server
def srv_search(_self, addr_list):
    # Creating the searching task
    _self.main_loop.create_task(async_srv_search(_self, addr_list))


# Searching for devices on servers
async def async_srv_search(_self, addr_list, echo=True):
    #
    search_result = dict()
    #
    for srv_addr in addr_list:
        #
        search_result[srv_addr] = list()
        # Resetting server action menu to default state
        config.srv_array[srv_addr]["action_menu"] = QMenu()
        # Switching server action button to default state
        config.srv_array[srv_addr]["action_btn"].setEnabled(False)
        # Connect all devices action
        connect_all = QAction(QIcon("icon/server_disconnect.png"), "Connect all devices", _self)
        # Reset all hub ports action
        reset_all = QAction(QIcon("icon/reset.png"), "Reset all hub ports", _self)

        #
        try:
            with open(path.join("hub", "{0}.json".format(_self.config[srv_addr]["hub_json"]))) as fp:
                hub_conf = load(fp)
        #
        except FileNotFoundError:
            config.logging_result.append_text(_self, "Hub configuration file not found", err=True)
            return

        reset_all.triggered.connect(partial(hub_reset, _self, srv_addr, hub_conf))

        #
        if _self.config[srv_addr]["hub_json"] != "None":
            config.srv_array[srv_addr]["action_btn"].setEnabled(True)
            config.srv_array[srv_addr]["action_menu"].addAction(reset_all)

            for hub_id in hub_conf:
                for idx, port in enumerate(hub_conf[hub_id], 1):
                    if port:
                        # TODO Custom name for Hub/Port ID from the settings
                        action = QAction(
                            QIcon("icon/port.png"), "Reset : Hub ID {0} : Port {1}".format(hub_id, idx), _self)
                        #
                        idx_list = [0] * 7
                        idx_list[idx - 1] = 1
                        action.triggered.connect(partial(hub_reset, _self, srv_addr, {hub_id: idx_list}))
                        config.srv_array[srv_addr]["action_menu"].addAction(action)

            #
            config.srv_array[srv_addr]["action_menu"].addSeparator()
        #
        search_proc = await create_subprocess_shell(
            "usbip.exe -l {0}".format(srv_addr), stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        await search_proc.wait()
        data = await search_proc.stderr.read()
        output = data.decode("utf-8")
        if echo:
            config.logging_result.append_text(_self, "Searching for devices")
            config.logging_result.append_text(_self, output)

        for section in output.split("\r\n \r\n"):
            section_list = section.split("\r\n")
            if "- " + srv_addr in section_list:
                section_list.remove("- " + srv_addr)
            if "" in section_list:
                continue
            dev_bus, dev_name, *rest = [item.lstrip().rstrip() for item in section_list.pop(0).split(":")]

            #
            if connect_all not in config.srv_array[srv_addr]["action_menu"].actions():
                connect_all.triggered.connect(partial(ApplicationMenu.connect_all, _self, [srv_addr]))
                config.srv_array[srv_addr]["action_menu"].addAction(connect_all)

            #
            search_result[srv_addr].append(dev_bus)

            # Switching server action button to connect state
            config.srv_array[srv_addr]["action_btn"].setEnabled(True)
            # Adding found devices to server action menu
            #
            if srv_addr not in config.usbip_array:
                action = QAction(QIcon("icon/device_disconnect.png"),
                                 "Connect : {0} : {1}".format(dev_bus, dev_name), _self)
                action.triggered.connect(partial(srv_connect, _self, srv_addr, dev_bus))
                config.srv_array[srv_addr]["action_menu"].addAction(action)
            #
            else:
                #
                if dev_bus not in config.usbip_array[srv_addr]:
                    action = QAction(QIcon("icon/device_disconnect.png"),
                                     "Connect : {0} : {1}".format(dev_bus, dev_name), _self)
                    action.triggered.connect(partial(srv_connect, _self, srv_addr, dev_bus))
                    config.srv_array[srv_addr]["action_menu"].addAction(action)
                #
                else:
                    action = QAction(QIcon("icon/device_connect.png"),
                                     "Disconnect : {0} : {1}".format(dev_bus, dev_name), _self)
                    action.triggered.connect(partial(srv_disconnect, _self, srv_addr, dev_bus))
                    config.srv_array[srv_addr]["action_menu"].addAction(action)
        #
        config.srv_array[srv_addr]["action_btn"].setMenu(config.srv_array[srv_addr]["action_menu"])
    #
    return search_result


#
def hub_reset(_self, srv_addr, hub_conf):
    # Initializing spinner
    spinner = QtWaitingSpinner(config.srv_array[srv_addr]["box"], True, True, Qt.ApplicationModal)
    #
    _self.main_loop.create_task(async_hub_reset(_self, srv_addr, spinner, hub_conf))


#
async def async_hub_reset(_self, srv_addr, spinner, hub_conf):
    #
    _self.main_loop.run_in_executor(None, hub_reset_action, _self, srv_addr, spinner, hub_conf)


#
def hub_reset_action(_self, srv_addr, spinner, hub_conf):
    # Starting spinner
    config.spinner_queue.start_spinner([spinner])

    # Checking if ssh connection not present and establishing ssh connection with server
    if srv_addr not in config.ssh_array:
        config.logging_result.append_text(
            _self, "An active ssh connection with the {0} server not found".format(srv_addr))
        # Establishing ssh connection with server
        SSH.connection(_self, srv_addr)
        # Reading and analyzing the server bit rate stdout
        SSH.USBTopSTDOUTProcessing(srv_addr, config.usbtop_array)

    #
    timeout = float(_self.config[srv_addr]["hub_timeout"])

    #
    for hub_id in hub_conf:
        for idx, port in enumerate(hub_conf[hub_id], 1):
            if port:
                config.logging_result.append_text(
                    _self, "Rebooting the {0} server hub #{1} port #{2}".format(srv_addr, hub_id, idx))

                # Powering off the hub port
                stdin, stdout, stderr = config.ssh_array[srv_addr].exec_command(
                    "sudo ./hub-ctrl -h {0} -P {1} -p 0".format(hub_id, idx))
                exit_status = stdout.channel.recv_exit_status()
                # Successful completion
                if not exit_status:
                    config.logging_result.append_text(
                        _self, "The {0} server hub #{1} port #{2} has been powering off".format(
                            srv_addr, hub_id, idx), success=True)
                # Error
                else:
                    config.logging_result.append_text(
                        _self, "The {0} server hub #{1} port #{2} has not been powering off".format(
                            srv_addr, hub_id, idx), err=True)
                    #
                    continue

                # Powering on the hub port
                stdin, stdout, stderr = config.ssh_array[srv_addr].exec_command(
                    "sudo ./hub-ctrl -h {0} -P {1} -p 1".format(hub_id, idx))
                exit_status = stdout.channel.recv_exit_status()
                # Successful completion
                if not exit_status:
                    config.logging_result.append_text(
                        _self, "The {0} server hub #{1} port #{2} has been powering on".format(
                            srv_addr, hub_id, idx), success=True)
                # Error
                else:
                    config.logging_result.append_text(
                        _self, "The {0} server hub #{1} port #{2} has not been powering on".format(
                            srv_addr, hub_id, idx), err=True)

                # Waiting for server udev process completion
                sleep(timeout)
    # Stopping spinner
    config.spinner_queue.stop_spinner([spinner])


# Actions with the server device action menu item
def srv_connect(_self, srv_addr, dev_bus):
    # Creating the server device connection task
    _self.main_loop.create_task(async_srv_connect(_self, srv_addr, dev_bus))

    # Inverting state of the server device action menu item
    action = config.get_action(srv_addr, dev_bus)
    if action:
        # Disconnect all previous signals
        action.disconnect()
        # Updates during the device connection procedure
        action.setText(action.text().replace("Connect", "Disconnect"))
        action.setIcon(QIcon("icon/device_connect.png"))
        # Setting up new signal
        action.triggered.connect(partial(srv_disconnect, _self, srv_addr, dev_bus))


#
async def async_srv_connect(_self, srv_addr, dev_bus):
    #
    if srv_addr not in config.usbip_array:
        config.usbip_array[srv_addr] = dict()
    #
    config.usbip_array[srv_addr][dev_bus] = dict()
    array = config.usbip_array[srv_addr][dev_bus]

    # Default device connection port index
    array["d_index"] = 0

    #
    port_list = list()
    for srv in config.usbip_array:
        for dev in config.usbip_array[srv]:
            port_list.append(config.usbip_array[srv][dev]["d_index"])

    #
    missing_ports = get_missing_ports(sorted(port_list))
    if missing_ports:
        array["d_index"] = min(missing_ports)
    else:
        array["d_index"] = max(port_list) + 1

    #
    action = config.get_action(srv_addr, "Connect all")
    if action:
        action.disconnect()
        action.setText(action.text().replace("Connect", "Disconnect"))
        action.setIcon(QIcon("icon/server_connect.png"))
        disconnect_array = {srv_addr: config.usbip_array[srv_addr].keys()}
        action.triggered.connect(partial(ApplicationMenu.disconnect_all, _self, disconnect_array))
    #
    array["event"] = Event()
    with ThreadPoolExecutor(max_workers=1, thread_name_prefix="USBIP: {0} {1}".format(srv_addr, dev_bus)) as pool:
        array["future"] = await _self.main_loop.run_in_executor(
            pool, DevTreeArea.srv_connection_process, _self, srv_addr, dev_bus, array["event"])

    #
    srv_disconnect(_self, srv_addr, dev_bus)


# Actions during the server device disconnection procedure
def srv_disconnect(_self, srv_addr, dev_bus):
    #
    try:
        d_index = config.usbip_array[srv_addr][dev_bus]["d_index"]
    except KeyError:
        return
    _self.main_loop.create_task(async_srv_disconnect(d_index))

    # Marking the future as canceled and interrupting inside blocking functions
    # config.usbip_array[srv_addr][dev_bus]["future"].cancel()
    config.usbip_array[srv_addr][dev_bus]["event"].set()

    # Inverting state of the server device action menu item
    action = config.get_action(srv_addr, dev_bus)
    if action:
        # Disconnect all previous signals
        action.disconnect()
        # Updates during the device disconnection procedure
        action.setText(action.text().replace("Disconnect", "Connect"))
        action.setIcon(QIcon("icon/device_disconnect.png"))
        # Setting up new signal
        action.triggered.connect(partial(srv_connect, _self, srv_addr, dev_bus))

    #
    menu_action = config.srv_array[srv_addr]["action_menu"].actions()
    if not [action.text() for action in menu_action if "Disconnect : " in action.text()]:
        action = config.get_action(srv_addr, "Disconnect all")
        if action:
            action.setText(action.text().replace("Disconnect", "Connect"))
            action.setIcon(QIcon("icon/server_disconnect.png"))
            action.triggered.connect(partial(ApplicationMenu.connect_all, _self, [srv_addr]))

    #
    del config.usbip_array[srv_addr][dev_bus]
    rm_dev_child(_self, srv_addr, dev_bus)


#
async def async_srv_disconnect(d_index):
    connection_shutdown = await create_subprocess_shell(
        "usbip.exe -d {0}".format(d_index), stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    await connection_shutdown.wait()


# Displaying server settings modal window
def srv_settings(_self, srv_addr):
    srv_settings_dialog = ServerSettingUI(_self, srv_addr)
    srv_settings_dialog.show()


# Finding missing elements in an integer sequence
def get_missing_ports(port_list):
    start, end = port_list[0], port_list[-1]
    # noinspection PyUnresolvedReferences
    return sorted(set(range(start, end + 1)).difference(port_list))


# Deleting server device tree widget by the server address and device bus
def rm_dev_child(_self, srv_addr, dev_bus):
    # Getting the device tree root and counting children
    root = _self.device_tree.invisibleRootItem()
    child_count = root.childCount()
    # Looping through children range and getting certain server address
    for child in range(child_count):
        item = root.child(child)
        if item.text(0) == srv_addr:
            # Counting server children
            sub_child_count = item.childCount()
            # Looping through server children range and getting certain device
            for sub_child in range(sub_child_count):
                dev = item.child(sub_child)
                if dev.text(0) == dev_bus:
                    # Removing server device tree widget
                    return item.removeChild(dev)


# ============================================================================ #
# CONTEXT MENU
# ============================================================================ #

# Single server right click context menu
def srv_context_menu(_self, event, srv_addr, srv_box):
    menu = QMenu()
    #
    shutdown_action = QAction(QIcon("icon/shutdown.png"), "Shut down {0}".format(srv_addr), _self)
    shutdown_action.triggered.connect(partial(srv_pwr_off, _self, [srv_addr]))
    #
    rm_action = QAction(QIcon("icon/delete.png"), "Remove {0}".format(srv_addr), _self)
    rm_action.triggered.connect(partial(srv_rm, _self, srv_addr))
    #
    menu.addAction(shutdown_action)
    menu.addAction(rm_action)
    menu.exec_(srv_box.mapToGlobal(event))


# Powering off the servers
def srv_pwr_off(_self, addr_list):
    _self.main_loop.create_task(async_srv_pwr_off(_self, addr_list))


# Powering off the servers
async def async_srv_pwr_off(_self, addr_list):
    _self.main_loop.run_in_executor(None, srv_pwr_off_action, _self, addr_list)


#
def srv_pwr_off_action(_self, addr_list):
    for srv_addr in addr_list:
        if srv_addr not in config.ssh_array:
            config.logging_result.append_text(
                _self, "An active ssh connection with the {0} server not found".format(srv_addr))
            # Establishing ssh connection with server
            SSH.connection(_self, srv_addr)
        #
        config.ssh_array[srv_addr].exec_command("sudo poweroff")
        del config.ssh_array[srv_addr]
        config.logging_result.append_text(_self, "The {0} server has been shutting down".format(srv_addr))


#
def srv_rm(_self, srv_addr):
    config.config_rm(_self.config, srv_addr)
