# Software configuration
from library import config

#
from os import path, makedirs
#
from threading import Thread, Event
#
from logging import handlers, Formatter, DEBUG
# SSH interface
from paramiko import SSHClient, AutoAddPolicy, RSAKey, util


# ============================================================================ #
# SYNC FUNCTIONS
# ============================================================================ #

# Establishing ssh connection with server
def connection(_self, srv_addr):
    # Configuring and starting thread
    ssh_ready = Event()
    ssh_connection = EstablishSSHConnection(_self, ssh_ready, srv_addr)
    ssh_thread = Thread(target=ssh_connection.establish_connection, name="SSH: {0}".format(srv_addr), daemon=True)
    ssh_thread.start()
    # Blocking until ssh connection ready
    ssh_ready.wait()


#
def exec_query(srv_addr, query):
    return config.ssh_array[srv_addr].exec_command(query)


# ============================================================================ #
# CLASSES
# ============================================================================ #

# Establishing ssh connection with server
class EstablishSSHConnection(object):
    def __init__(self, _self, ready, srv_addr):
        self._self = _self
        self.ready = ready
        self.srv_addr = srv_addr
        # TODO Dynamic configuration update after changing software settings
        # TODO Getting configuration from the global source
        self.config = config.get_config()

        # Checking if server log path exists
        if not path.exists(path.join("log")):
            makedirs(path.join("log"))
        if not path.exists(path.join("log", srv_addr)):
            makedirs(path.join("log", srv_addr))
        # Setting ssh logging handler
        ssh_logger = util.logging.getLogger()
        hdlr = handlers.RotatingFileHandler(
            path.join("log", srv_addr, "ssh_{0}.log".format(srv_addr)), maxBytes=100000, backupCount=5)
        formatter = Formatter("%(asctime)s %(levelname)s %(message)s")
        hdlr.setFormatter(formatter)
        ssh_logger.addHandler(hdlr)
        ssh_logger.setLevel(DEBUG)

    def establish_connection(self):
        config.logging_result.append_text(self._self, "Establishing ssh connection with {0}".format(self.srv_addr))
        config.ssh_array[self.srv_addr] = SSHClient()
        config.ssh_array[self.srv_addr].set_missing_host_key_policy(AutoAddPolicy())
        # TODO Handle with ssh auth exceptions
        # Key auth type
        if self.config[self.srv_addr].getboolean("auth_type_key"):
            key = RSAKey.from_private_key_file(self.config[self.srv_addr]["key_path"])
            config.ssh_array[self.srv_addr].connect(
                self.srv_addr,
                port=self.config[self.srv_addr]["auth_ssh_port"],
                username=self.config[self.srv_addr]["auth_username"],
                pkey=key)
        # Password auth type
        elif self.config[self.srv_addr].getboolean("auth_type_password"):
            config.ssh_array[self.srv_addr].connect(
                self.srv_addr,
                port=self.config[self.srv_addr]["auth_ssh_port"],
                username=self.config[self.srv_addr]["auth_username"],
                password=self.config[self.srv_addr]["auth_password"])
        config.logging_result.append_text(
            self._self, "Connection with {0} established".format(self.srv_addr), success=True)
        # Setting connection completion flag
        self.ready.set()


# Reading and analyzing the server usb bus bit rate stdout
class USBTopSTDOUTProcessing(object):
    def __init__(self, srv_addr, stdout_array):
        self.srv_addr = srv_addr
        self.stdout_array = stdout_array

        # Setting up and starting the thread
        thread = Thread(target=self.run, name="USBTOP: {0}".format(self.srv_addr), daemon=True)
        thread.start()

    def run(self):
        # TODO SSH lost connection exception
        stdin, stdout, stderr = config.ssh_array[self.srv_addr].exec_command("sudo usbtop")
        self.stdout_processing(stdout)

    def stdout_processing(self, stdout):
        output = list()
        self.stdout_array[self.srv_addr] = dict()
        while True:
            line = stdout.readline(2048)
            if "\x1b[2J\x1b[1;1H" in line:
                self.stdout_analysis(output)
                output = list()
                output.append(line.lstrip().rstrip().replace("\x1b[2J\x1b[1;1H", ""))
            else:
                output.append(line.lstrip().rstrip())

    def stdout_analysis(self, output):
        bus_id = None
        for line in output:
            if "Bus ID" in line:
                bus_id = [int(s) for s in line.split() if s.isdigit()].pop()
                self.stdout_array[self.srv_addr][bus_id] = dict()
            if "Device ID" in line:
                dev_id = [int(s) for s in line.split() if s.isdigit()].pop()
                self.stdout_array[self.srv_addr][bus_id][dev_id] = [line.split()[4], line.split()[6]]


#
class PackSharkSTDOUTProcessing(object):
    def __init__(self, srv_addr, shark_req, queue, event):
        self.srv_addr = srv_addr
        self.shark_req = shark_req
        self.queue = queue
        self.event = event

        # Setting up and starting the thread
        thread = Thread(target=self.run, name="PackShark: {0}".format(self.srv_addr), daemon=True)
        thread.start()

    def run(self):
        # TODO SSH lost connection exception
        stdin, stdout, stderr = config.ssh_array[self.srv_addr].exec_command(self.shark_req)
        config.capture_array[self.srv_addr]["ssh_pid"] = int(stdout.readline())
        self.stdout_processing(stdout)

    #
    def line_buffered(self, data):
        line_buf = ""
        while not self.event.is_set():
            line_buf += data.read(1).decode()
            if line_buf.endswith("\n"):
                yield line_buf
                line_buf = ""

    #
    def stdout_processing(self, stdout):
        for line in self.line_buffered(stdout):
            dev_num, pack, ep = line.rstrip().split()
            self.queue.put([dev_num, pack, ep])
