import subprocess
import os

print("Program Starting ... ")
select = "-1"
while select == "-1":
    sensor = subprocess.check_output("sudo btmgmt find | grep MetaWear -B 2 | grep rssi", shell = True)
    print sensor
    sensor_list = []
    for line in sensor.split("\n"):
        sensor_dict = {}
        if line != "":
            mac = line[16:33]
            rssi = line[54:57]
            sensor_dict["mac"] = mac
            sensor_dict["rssi"] = rssi
            sensor_list.append(sensor_dict)
    #print(sensor_list)

    for d in sensor_list:
        #print(d["mac"])
        try: 
            terminal_string = ("sudo python get_battery.py %s | grep voltage" % d["mac"])
            battery = subprocess.check_output(terminal_string, shell = True)
            d["charge"] = battery[-5:-2]
        except:
            raise IOError("Connection Failed to %s, please try again" %d["mac"])

    count = 0
    print("\n---------------------------------------------------\n Metawear Device Information \n---------------------------------------------------")
    for d in sensor_list:
        count += 1
        print ("%d. %s | rssi:%s, battery life:%s%% " % (count, d["mac"], d["rssi"], d["charge"]))
    print("---------------------------------------------------")
    select = raw_input("To continue press Enter, else type 0 to exit or -1 to rescan: ")
    if select == "0":
        exit(0)
    if select == "-1":
        print("Rescanning ... ")

mac_input = raw_input("To automatically connect to all devices press Enter otherwise list the mac addresses for specific device:")
if mac_input == "":
    macs = ""
    for d in sensor_list:
        macs = macs + d["mac"] + " " 
    os.system("sudo python data_collection.py %s" % macs)
else:
    os.system("sudo python data_collection.py %s" %mac_input)
