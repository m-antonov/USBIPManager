from library import config

from threading import Thread


# ============================================================================ #
# SYNC FUNCTIONS
# ============================================================================ #

#
def exec_query(srv_addr, query):
    return config.ssh_array[srv_addr].exec_command(query)


# ============================================================================ #
# CLASSES
# ============================================================================ #

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
