# usage: python led.py [mac]
from __future__ import print_function
from mbientlab.metawear import MetaWear, libmetawear, parse_value
from mbientlab.metawear.cbindings import *
from time import sleep
from threading import Event
import platform
import sys

if sys.version_info[0] == 2:
    range = xrange

class State:
    def __init__(self, device):
        self.device = device
        self.samples = 0
        self.callback = FnVoid_VoidP_DataP(self.data_handler)

    def data_handler(self, ctx, data):
        print("%s -> %s" % (self.device.address, parse_value(data)))
        
device = MetaWear(sys.argv[1])
device.connect()
print("Connected")
s = State(device)

signal = libmetawear.mbl_mw_settings_get_battery_state_data_signal(device.board)
libmetawear.mbl_mw_datasignal_subscribe(signal, None, s.callback)
libmetawear.mbl_mw_datasignal_read(signal)

sleep(1.0)

device.disconnect()
libmetawear.mbl_mw_datasignal_unsubscribe(signal)
