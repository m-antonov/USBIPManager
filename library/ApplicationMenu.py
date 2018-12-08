#
from library import config
#
from library import SRVMenu
#
from library.QtWaitingSpinner import QtWaitingSpinner
# Modal window interfaces
from library.ModalAutoFind import FindServerUI
from library.ModalAddServer import AddServerUI
from library.ModalSoftwareSettings import SoftwareSettingUI

# PyQt5 modules
from PyQt5.QtCore import Qt
# Suppress specified exception
from contextlib import suppress
# Async threading interface
from asyncio import sleep, all_tasks, CancelledError
#
from subprocess import STARTUPINFO, STARTF_USESHOWWINDOW, Popen, PIPE


# Displaying server auto find modal window
def auto_find(_self):
    auto_find_dialog = FindServerUI(_self)
    auto_find_dialog.show()


# Displaying server add modal window
def add_server(_self):
    add_server_dialog = AddServerUI(_self)
    add_server_dialog.show()


# Searching for devices on all servers
def search_all(_self):
    #
    addr_list = get_addr_list(_self)
    #
    _self.main_loop.create_task(async_search_all(_self, addr_list))


#
async def async_search_all(_self, addr_list):
    # Creating a searching task
    search_result = await _self.main_loop.create_task(SRVMenu.async_srv_search(_self, addr_list))
    #
    for srv_addr in search_result:
        if search_result[srv_addr]:
            _self.connect_all_button.setEnabled(True)
            break


# Connecting all devices
def connect_all(_self, addr_list=None):
    #
    if not addr_list:
        addr_list = get_addr_list(_self)
    #
    _self.main_loop.create_task(async_connect_all(_self, addr_list))


#
async def async_connect_all(_self, addr_list):
    #
    timeout = float(_self.config["SETTINGS"]["connecting_timeout"])

    #
    menu_box_spinner = QtWaitingSpinner(_self.menu_box, True, True, Qt.ApplicationModal)
    server_box_spinner = QtWaitingSpinner(_self.server_box, True, True, Qt.ApplicationModal)
    device_box_spinner = QtWaitingSpinner(_self.device_box, True, True, Qt.ApplicationModal)
    #
    config.spinner_queue.start_spinner([menu_box_spinner, server_box_spinner, device_box_spinner])
    _self.cancel_process.setParent(_self)
    _self.cancel_process.show()

    # Creating a searching task
    search_result = await _self.main_loop.create_task(SRVMenu.async_srv_search(_self, addr_list, echo=False))
    # Number of remaining devices
    array_length = config.get_array_length(search_result)
    #
    for srv_addr in search_result:
        if search_result[srv_addr]:
            #
            if srv_addr not in config.usbip_array:
                config.usbip_array[srv_addr] = dict()
            #
            for dev_bus in search_result[srv_addr]:
                #
                if dev_bus not in config.usbip_array[srv_addr]:
                    # Reducing the number of remaining devices
                    array_length -= 1
                    #
                    SRVMenu.srv_connect(_self, srv_addr, dev_bus)
                    config.logging_result.append_text(
                        _self, "The {0} device has connected from the {1} server, {2} left".format(
                            dev_bus, srv_addr, str(array_length)), success=True)
                    await sleep(timeout)

    #
    config.spinner_queue.stop_spinner([menu_box_spinner, server_box_spinner, device_box_spinner])
    _self.cancel_process.setParent(None)

    #
    _self.connect_all_button.setEnabled(False)
    _self.disconnect_all_button.setEnabled(True)
    _self.device_tree_menu["action"]["enable"].setEnabled(True)


# Disconnecting all devices and restoring default button state
def disconnect_all(_self, disconnect_array, sw_close=False):
    _self.main_loop.create_task(async_disconnect_all(_self, disconnect_array, sw_close))


#
async def async_disconnect_all(_self, disconnect_array, sw_close):
    #
    timeout = float(_self.config["SETTINGS"]["connecting_timeout"])

    #
    menu_box_spinner = QtWaitingSpinner(_self.menu_box, True, True, Qt.ApplicationModal)
    server_box_spinner = QtWaitingSpinner(_self.server_box, True, True, Qt.ApplicationModal)
    device_box_spinner = QtWaitingSpinner(_self.device_box, True, True, Qt.ApplicationModal)
    #
    config.spinner_queue.start_spinner([menu_box_spinner, server_box_spinner, device_box_spinner])
    _self.cancel_process.setParent(_self)
    _self.cancel_process.show()

    # Number of remaining devices
    array_length = config.get_array_length(disconnect_array)

    #
    for srv_addr in disconnect_array:
        for dev_bus in list(disconnect_array[srv_addr]):
            index = config.usbip_array[srv_addr][dev_bus]["d_index"]
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
            config.logging_result.append_text(
                _self, "The {0} device has disconnected from the {1} server, {2} left".format(
                    dev_bus, srv_addr, str(array_length)), warn=True)
            #
            await sleep(timeout)

    # Stopping all running processes and shutdown the program
    if sw_close:
        for queue in all_tasks(_self.main_loop):
            queue.cancel()
            with suppress(CancelledError):
                await queue
        _self.main_loop.stop()

    #
    config.spinner_queue.stop_spinner([menu_box_spinner, server_box_spinner, device_box_spinner])
    _self.cancel_process.setParent(None)


# Displaying software settings modal window
def settings(_self):
    settings_dialog = SoftwareSettingUI(_self)
    settings_dialog.show()


#
def get_addr_list(_self):
    addr_list = list()
    # Loop through all server addresses in the configuration
    for srv_addr in _self.config.sections():
        if srv_addr != "SETTINGS":
            addr_list.append(srv_addr)
    #
    return addr_list
