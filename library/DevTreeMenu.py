#
from library import config
#
from library import SSH

# De-serializing data
from json import loads
#
from queue import Queue
from threading import Event
# Calling functions with positional arguments
from functools import partial
# PyQt5 modules
from PyQt5.QtGui import QIcon


# ============================================================================ #
# CONTEXT MENU
# ============================================================================ #

# Device tree box right click context menu
def box_context_menu(_self, event):
    #
    _self.device_tree_menu["menu"].clear()

    #
    for action in _self.device_tree_menu["action"]:
        try:
            _self.device_tree_menu["action"][action].disconnect()
        except TypeError:
            pass
        _self.device_tree_menu["menu"].addAction(_self.device_tree_menu["action"][action])

    #
    _self.device_tree_menu["action"]["enable"].triggered.connect(partial(data_enable, _self))
    _self.device_tree_menu["action"]["reset"].triggered.connect(partial(data_reset, _self))
    _self.device_tree_menu["action"]["disable"].triggered.connect(partial(data_disable, _self))

    #
    _self.device_tree_menu["menu"].exec_(_self.device_box.mapToGlobal(event))


# Enabling data capture
def data_enable(_self):
    #
    _self.main_loop.create_task(async_data_enable(_self))
    #
    _self.device_tree_menu["action"]["enable"].setEnabled(False)
    _self.device_tree_menu["action"]["reset"].setEnabled(True)
    _self.device_tree_menu["action"]["disable"].setEnabled(True)


# Resetting data capture
def data_reset(_self):
    config.capturing_disable(_self)
    data_enable(_self)


# Disabling data capture
def data_disable(_self):
    #
    config.capturing_disable(_self)
    #
    _self.device_tree_menu["action"]["enable"].setEnabled(True)
    _self.device_tree_menu["action"]["reset"].setEnabled(False)
    _self.device_tree_menu["action"]["disable"].setEnabled(False)


#
async def async_data_enable(_self):
    #
    capturing_config = config.get_capturing_config()
    #
    config.ep_array = dict()
    config.capture_array = dict()
    #
    for srv_addr in config.usbip_array:
        config.ep_array[srv_addr] = dict()
        for dev_bus in config.usbip_array[srv_addr]:
            stdin, stdout, stderr = await _self.main_loop.run_in_executor(
                None, SSH.exec_query, srv_addr, "python get_data.py {0}".format(dev_bus))
            config.ep_array[srv_addr][dev_bus] = loads(stdout.readline(2048).rstrip())

    #
    for srv_addr in config.ep_array:
        display_filter = "usb.device_address eq {0}"
        shark_req = "echo $$ && exec sudo tshark -i usbmon1 -l -Y '("
        for dev_bus, has_more in lookahead(config.ep_array[srv_addr]):
            shark_req += display_filter.format(config.ep_array[srv_addr][dev_bus]["dev_num"])
            if has_more:
                shark_req += " or "
        shark_req += ") && usb.capdata && usb.endpoint_address && usb.dst eq host && usb.data_len gt 3' " \
                     "-T fields -e usb.device_address -e usb.capdata -e usb.endpoint_address"

        #
        config.capture_array[srv_addr] = dict()
        array = config.capture_array[srv_addr]
        array["event"] = Event()
        array["queue"] = Queue()
        array["future"] = _self.main_loop.run_in_executor(
            None, data_processing, _self, srv_addr, shark_req, array["queue"], array["event"], capturing_config)


#
def data_processing(_self, srv_addr, shark_req, queue, event, capturing_config):
    #
    SSH.PackSharkSTDOUTProcessing(srv_addr, shark_req, queue, event)

    #
    for dev in config.iter_dev(_self, srv_addr):
        # Getting device child quantity and generating default "0" enumeration based on the amount
        dev_child_qty = len(config.ep_array[srv_addr][dev.text(0)]) - 1
        dev_enum = [0] * dev_child_qty
        #
        update_dev(_self, dev, srv_addr, dev.text(0), dev_enum, capturing_config)

    # Data waiting loop until the "process stop" event set
    while not event.is_set():
        item = config.capture_array[srv_addr]["queue"].get()
        # None statement during the program window closing
        if not item:
            continue
        # Setting received device number, package and end point as variables
        dev_num, pack, ep = item
        # Checking package entry in specific filtering settings
        # TODO Custom filter conditions from GUI
        if pack.split(":")[2] != "aa":
            continue

        #
        ep_array = config.ep_array[srv_addr]
        for dev_bus in ep_array:
            # Empty current device child enumeration
            dev_enum = list()
            #
            if ep_array[dev_bus]["dev_num"] == dev_num:
                for index in ep_array[dev_bus]:
                    if isinstance(ep_array[dev_bus][index], dict):
                        # Appending default "0" enumeration statement
                        dev_enum.append(0)
                        #
                        for ep_type in ep_array[dev_bus][index]:
                            if ep_array[dev_bus][index][ep_type] == ep.lstrip("0x"):
                                # Rewriting default "0" enumeration statement with "1" flag by the child index
                                dev_enum[int(index)] = 1
                #
                for dev in config.iter_dev(_self, srv_addr):
                    if dev.text(0) == dev_bus:
                        update_dev(_self, dev, srv_addr, dev_bus, dev_enum, capturing_config)


#
def update_dev(_self, dev, srv_addr, dev_bus, dev_enum, capturing_config):
    # Generating tooltip HTML string based on the device child enumeration
    tooltip_string = tooltip_string_gen(_self, srv_addr, dev_bus, dev_enum, capturing_config)
    #
    if set(dev_enum).pop():
        config.device_tree.set_icon(dev, 0, QIcon("icon/got.png"))
    else:
        config.device_tree.set_icon(dev, 0, QIcon("icon/wait.png"))
    #
    config.device_tree.set_tooltip(dev, 0, tooltip_string)


# Generating tooltip HTML string based on the device child enumeration
def tooltip_string_gen(_self, srv_addr, dev_bus, dev_enum, capturing_config):
    # Default empty string
    tooltip_string = ""
    #
    for dev_child, has_more in lookahead(range(len(dev_enum))):
        #
        dev_place = "Config error"
        try:
            dev_place = loads(capturing_config[srv_addr].get(dev_bus + "[" + str(dev_child) + "]"))[0]
        except KeyError as err:
            config.logging_result.append_text(
                _self, "The {0} server device configuration for {1} port has not found in the capturing.ini".format(
                    srv_addr, err.args[0]), err=True)

        #
        if dev_enum[dev_child]:
            tooltip_string += "<b>{0}:</b> <font color='green'>MATCHED</font>".format(dev_place)
        else:
            tooltip_string += "<b>{0}:</b> <font color='red'>NONE</font>".format(dev_place)
        if has_more:
            tooltip_string += "<br>"

    return tooltip_string


# Detecting the last element in a loop
def lookahead(iterable):
    it = iter(iterable)
    last = next(it)
    for val in it:
        yield last, True
        last = val
    yield last, False
