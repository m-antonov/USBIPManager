# Async threading interface
from asyncio import sleep
# Plotting charts modules
from pyqtgraph import mkPen
#
from collections import deque
#
from psutil import net_io_counters
# PyQt5 modules
from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import QMenu, QAction


# ============================================================================ #
# ASYNC FUNCTIONS
# ============================================================================ #

async def async_get_activity(_self):
    # Default empty deque list with 101 length
    sent_list = deque([0] * 101, maxlen=101)
    recv_list = deque([0] * 101, maxlen=101)
    # Default previous values for sent and received activity
    sent_prev = 0
    recv_prev = 0
    # Chart updating interval
    timeout = float(_self.config["SETTINGS"]["activity_updating_time"])

    while True:
        # Getting sent and received bytes values
        sent_val = net_io_counters().bytes_sent
        recv_val = net_io_counters().bytes_recv
        # Appending deque lists
        if sent_prev and recv_prev:
            sent_list.append(sent_val - sent_prev)
            recv_list.append(recv_val - recv_prev)

        # Updating chart
        _self.sent_curve.setData(list(sent_list), pen=mkPen(width=2, color="g"))
        _self.recv_curve.setData(list(recv_list), pen=mkPen(width=2, color="r"))
        # Updating previous sent and received values with new data
        sent_prev = sent_val
        recv_prev = recv_val

        await sleep(timeout)


# ============================================================================ #
# CONTEXT MENU
# ============================================================================ #

# Network activity box right click context menu
def box_context_menu(_self, event):
    menu = QMenu()
    #
    reset_action = QAction(QIcon("icon/reset.png"), "Reset activity", _self)
    #
    menu.addAction(reset_action)
    menu.exec_(_self.activity_box.mapToGlobal(event))
