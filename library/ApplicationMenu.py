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

# Async threading interface
from asyncio import sleep
# PyQt5 modules
from PyQt5.QtCore import Qt
#
from threading import Thread


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
def connect_all(_self):
    #
    addr_list = get_addr_list(_self)
    #
    _self.main_loop.create_task(async_connect_all(_self, addr_list))


#
async def async_connect_all(_self, addr_list):
    #
    timeout = float(_self.config["SETTINGS"]["connecting_timeout"])
    #
    spinner = QtWaitingSpinner(_self.connect_all_button, True, True, Qt.ApplicationModal)
    config.spinner_queue.start_spinner(spinner)
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
    config.spinner_queue.stop_spinner(spinner)
    _self.connect_all_button.setEnabled(False)
    _self.disconnect_all_button.setEnabled(True)
    _self.device_tree_menu["action"]["enable"].setEnabled(True)


# Disconnecting all devices and restoring default button state
def disconnect_all(_self):
    _self.main_loop.create_task(async_disconnect_all(_self))


#
async def async_disconnect_all(_self):
    #
    close_query = config.KillProc(_self, _self.disconnect_all_button)
    close_thread = Thread(target=close_query.processing, name="DisconnectAll", daemon=True)
    close_thread.start()
    while close_thread.is_alive():
        await sleep(0)
    #
    _self.disconnect_all_button.setEnabled(False)
    _self.connect_all_button.setEnabled(True)
    _self.device_tree_menu["action"]["enable"].setEnabled(False)


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
