# Written by Samuel Lee 2019
from __future__ import print_function
from ctypes import c_void_p, cast, POINTER
from mbientlab.metawear import MetaWear, libmetawear, parse_value, cbindings
from mbientlab.metawear.cbindings import *
from time import sleep
from threading import Event, Thread
from sys import argv
import datetime
import os
import signal
import sys

# Color Text
RedText = '\033[41m'
DefaultColor = '\033[m'
GreenBack = '\033[30;42m'
YellowBack = '\033[30;43m'

# Setup ---------------------------------------------------------------------------
# set data collection to run for a given amount of time - can be hardcoded
sleep_time = input("set duration of data collection (in seconds):")

#signal handler
def handler(signum, frame):
    end_time = datetime.datetime.now()
    global running
    running = False
    print ('\n--------------------------------------\nProgram ended with signal %d \n--------------------------------------' % signum)
    print("Resetting devices")
    events = []
    for s in states:
        try:
            e = Event()
            events.append(e)
            s.device.on_disconnect = lambda s: e.set()
            libmetawear.mbl_mw_debug_reset(s.device.board)
        except:
            print(s.device.address + "Disconnected")
            pass
    for e in events:
        try:
            e.wait()
        except:
            pass
    for s in states:
        print ("Total Samples Received %s->%d" % (s.device.address, s.samples))
    time_data_collect = (end_time - data_start_time).total_seconds()
    print("Total Time of Data Collection %fs" %time_data_collect)
    sys.exit()

#gracefully exit if ctrl+c is pressed
signal.signal(signal.SIGINT, handler)

#initialize folder
now = datetime.datetime.now()
data_start_time = now
date = now.strftime("%m-%d-%Y")
time = now.strftime("%H:%M:%S")
path = ("/home/pi/Desktop/MetaWear-Program/results/%s-%s" %(date, time))
try:
    os.makedirs(path)
except OSError:
    pass
    
states = []
connected = {}
running = True
# Functions -------------------------------------------------------------------------------
def led_blue(mac):
    global states
    for s in states:
        if s.device.address == mac:
            pattern= LedPattern(repeat_count= Const.LED_REPEAT_INDEFINITELY)
            libmetawear.mbl_mw_led_load_preset_pattern(byref(pattern), LedPreset.PULSE)
            libmetawear.mbl_mw_led_write_pattern(s.device.board, byref(pattern), LedColor.BLUE)
            libmetawear.mbl_mw_led_play(s.device.board)
            sleep(2.0)
            libmetawear.mbl_mw_led_stop_and_clear(s.device.board)
    
def led_red(mac):
    global states
    for s in states:
        if s.device.address == mac:
            pattern= LedPattern(repeat_count= Const.LED_REPEAT_INDEFINITELY)
            libmetawear.mbl_mw_led_load_preset_pattern(byref(pattern), LedPreset.PULSE)
            libmetawear.mbl_mw_led_write_pattern(s.device.board, byref(pattern), LedColor.RED)
            libmetawear.mbl_mw_led_play(s.device.board)
            sleep(2.0)
            libmetawear.mbl_mw_led_stop_and_clear(s.device.board)
            
def still_connected():
    sleep(5.0)
    while running:
        print_now = datetime.datetime.now()
        print_time = print_now.strftime("%H:%M:%S")
        global connected
        line_one = "|"
        line_two = "|"
        line_three = "|"
        for i in connected:
            line_one += "-----------------|"
            line_two += i + "|"
            strength = connected[i]
            if strength >= 5:
                strength = 5
                #line_three += "connected |" + "o" * strength + " "*(5-strength) + "||"
                line_three += "connected |" + GreenBack + "|"*strength + DefaultColor + "||"
                blue_thread = Thread(target = led_blue, args = [i])
                blue_thread.start()

            elif strength > 0:
                line_three += "connected |" + YellowBack + "|"*strength + DefaultColor + "|"*(5-strength) + "||"
                red_thread = Thread(target = led_red, args = [i])
                red_thread.start()
                
            # or simply do
            # if strength > 0:
            #   line_three += "    connected    |"                                                           
            else:
                line_three += RedText + "  Disconnected   " + DefaultColor + "|"
        print(line_one + print_time)
        print(line_two)
        print(line_three)
        connected = {x:0 for x in connected}
        sleep(5.0)
                
class State:
    def __init__(self, device, file):
        self.device = device
        self.callback = cbindings.FnVoid_VoidP_DataP(self.data_handler)
        self.processor = None
        self.file = file
        self.samples = 0
        self.count = 100
    
    def data_handler(self, ctx, data):
        values = parse_value(data, n_elem = 3)
        if self.count == 100:
            #print("%s -> acc: (%.4f,%.4f,%.4f), gyro: (%.4f,%.4f,%.4f), mag:(%.4f, %.4f, %.4f)" % (self.device.address, values[0].x, values[0].y, values[0].z, values[1].x, values[1].y, values[1].z, values[2].x, values[2].y, values[2].z)) 
            self.count = 0
            connected[self.device.address] += 1
        acc = values[0]
        gyro = values[1]
        mag = values[2]
        current = datetime.datetime.now()
        time_diff = (current - data_start_time).total_seconds()
        time_stamp = current.strftime("%H:%M:%S.%f")
        self.count += 1
        self.samples += 1
        self.file.write("%s,%f,%f,%f,%f,%f,%f,%f,%f,%f,%f \n" %(time_stamp, time_diff, acc.x, acc.y, acc.z, gyro.x, gyro.y, gyro.z, mag.x, mag.y, mag.z))
        
    def setup(self):
        #Set up file
        self.file.write("Time, Time from start (s), Acc x, Acc y, Acc z, Gyro x, Gyro y, Gyro z, Mag x, Mag y, Mag z \n")
        
        #Set up board
        libmetawear.mbl_mw_settings_set_connection_parameters(self.device.board, 7.5, 7.5, 0, 6000)

        #Acceleration sampling frequency
        libmetawear.mbl_mw_acc_set_odr(s.device.board, 100.0) #fastest frequency is 400 Hz
        #range of acceleration
        libmetawear.mbl_mw_acc_set_range(s.device.board, 16.0)
        #write acceleration config
        libmetawear.mbl_mw_acc_write_acceleration_config(s.device.board)
        
        #Gyro sampling frequency
        libmetawear.mbl_mw_gyro_bmi160_set_odr(self.device.board, 8) #9 = 200Hz, 8 = 100Hz
        #Gyro range
        libmetawear.mbl_mw_gyro_bmi160_set_range(self.device.board, 0) #0 = 2000 dps, 1 = 1000 dps
        #Write gyro config
        libmetawear.mbl_mw_gyro_bmi160_write_config(self.device.board)
        
        libmetawear.mbl_mw_mag_bmm150_set_preset(self.device.board, 3)
        
        sleep(1.5)

        e = Event()

        def processor_created(context, pointer):
            self.processor = pointer
            e.set()
        fn_wrapper = cbindings.FnVoid_VoidP_VoidP(processor_created)
        
        acc = libmetawear.mbl_mw_acc_get_acceleration_data_signal(self.device.board)
        gyro = libmetawear.mbl_mw_gyro_bmi160_get_rotation_data_signal(self.device.board)
        mag = libmetawear.mbl_mw_mag_bmm150_get_b_field_data_signal(self.device.board)
        signals = (c_void_p * 2)()
        signals[0] = gyro
        signals[1] = mag
        libmetawear.mbl_mw_dataprocessor_fuser_create(acc, signals, 2, None, fn_wrapper)
        e.wait()

        libmetawear.mbl_mw_datasignal_subscribe(self.processor, None, self.callback)

    def start(self):
    
        libmetawear.mbl_mw_gyro_bmi160_enable_rotation_sampling(self.device.board)
        libmetawear.mbl_mw_acc_enable_acceleration_sampling(self.device.board)
        libmetawear.mbl_mw_mag_bmm150_enable_b_field_sampling(self.device.board)

        libmetawear.mbl_mw_gyro_bmi160_start(self.device.board)
        libmetawear.mbl_mw_acc_start(self.device.board)
        libmetawear.mbl_mw_mag_bmm150_start(self.device.board)
        

#Start of Script --------------------------------------------------------------------------------------
hciList = ["hci0", "hci1", "hci2", "hci3", "hci4", "hci5"]        
for i in range(len(argv) - 1):
    d = MetaWear(argv[i + 1], hci_mac=hciList[i%3])
    try:
        d.connect()
    except:
        d.connect()
    print("Connected to " + d.address)
    name = ("%s" %(d.address))
    file = open("%s/%s.csv" %(path, name), "w", buffering = 4096)
    states.append(State(d, file))
    connected[argv[i+1]] = 0

for s in states:
    print("Configuring %s" % (s.device.address))
    s.setup()
    pattern= LedPattern(repeat_count= Const.LED_REPEAT_INDEFINITELY)
    libmetawear.mbl_mw_led_load_preset_pattern(byref(pattern), LedPreset.SOLID)
    libmetawear.mbl_mw_led_write_pattern(s.device.board, byref(pattern), LedColor.GREEN)
    libmetawear.mbl_mw_led_play(s.device.board)

raw_input("press enter when ready to collect")
for s in states:
    libmetawear.mbl_mw_led_stop_and_clear(s.device.board)
print("--------------------------------------\nCollecting Data\n--------------------------------------")
print("Press Ctrl + c to end program ")


data_start_time = datetime.datetime.now()
for s in states:
    s.start()    

thread_connected = Thread(target = still_connected)
thread_connected.start()

sleep(sleep_time)
running = False

print("--------------------------------------\nResetting devices")
events = []
for s in states:
    e = Event()
    events.append(e)

    s.device.on_disconnect = lambda s: e.set()
    libmetawear.mbl_mw_debug_reset(s.device.board)

for e in events:
    e.wait()

for s in states:
    print ("Total Samples Received %s->%d" % (s.device.address, s.samples))
