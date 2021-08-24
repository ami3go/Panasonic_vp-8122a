# import pyvisa # PyVisa info @ http://PyVisa.readthedocs.io/en/stable/
import serial.tools.list_ports
import serial
import time


#It is recommended to use a minimum delay of 250ms between two commands
def delay(time_in_sec=0.25):
    time.sleep(time_in_sec)

## Number of Points to request
USER_REQUESTED_POINTS = 1000
    ## None of these scopes offer more than 8,000,000 points
    ## Setting this to 8000000 or more will ensure that the maximum number of available points is retrieved, though often less will come back.
    ## Average and High Resolution acquisition types have shallow memory depth, and thus acquiring waveforms in Normal acq. type and post processing for High Res. or repeated acqs. for Average is suggested if more points are desired.
    ## Asking for zero (0) points, a negative number of points, fewer than 100 points, or a non-integer number of points (100.1 -> error, but 100. or 100.0 is ok) will result in an error, specifically -222,"Data out of range"

## Initialization constants
INSTRUMENT_VISA_ADDRESS = 'USB0::0x03EB::0x2065::HP0.87300MZ_AP20.0DB_EMOF_COOF_CO0_AP50_MS01_AM30.::INSTR' # Get this from Keysight IO Libraries Connection Expert
    ## Note: sockets are not supported in this revision of the script (though it is possible), and PyVisa 1.8 does not support HiSlip, nor do these scopes.
    ## Note: USB transfers are generally fastest.
    ## Video: Connecting to Instruments Over LAN, USB, and GPIB in Keysight Connection Expert: https://youtu.be/sZz8bNHX5u4

# any read retrun the status string devided by space 
# FR0.87300MZ 
# AP20.0DB 
# EMOF 
# COON 
# CO0.0 
# AP50 
# MS01 
# AM40.0 
# AMON 
# AMT1 
# FM40.0 
# FMOF 
# FMT1 
# MS46PC 
# PR0 
# PL0.0 
# PLOF 
# SCOF 
# NPOF 
# DR30 
# AS0 
# NT0.20 
# P1D0 
# P2D0



GLOBAL_TOUT =  10 # IO time out in milliseconds



def range_check(val, min, max, val_name):
    if val > max:
        print(f"Wrong {val_name}: {val}. Max value should be less then {max}")
        val = max
    if val < min:
        print(f"Wrong {val_name}: {val}. Should be >= {min}")
        val = min
    return val



class com_interface:
    def __init__(self):
        # Commands Subsystem
        # this is the list of Subsystem commands
        # super(communicator, self).__init__(port="COM10",baudrate=115200, timeout=0.1)
        self.rm = pyvisa.ResourceManager()
        self.res_name = None
        print(self.rm)
        self.inst = None

        self.cmd = storage()

    def init(self):
        rm_list = self.rm.list_resources()
        i = 0
        for item in rm_list:
            if "AutoWave" in item:
                self.res_name = item
        self.inst = self.rm.open_resource(self.res_name)
        self.inst.set_visa_attribute(pyvisa.constants.VI_ATTR_SEND_END_EN, 1)
        # self.inst.write_termination = ""
        # self.inst.timeout = 2000 # timeout in ms
        print("Connected to: ", self.inst.query("*IDN?"))
        print("Protocol OFF: ", self.inst.query("*PRCL:OFF"))
        print(self.inst.query("*ECHO:ON"))


    def send(self, txt):
        # will put sending command here
        # print(f'Sending: {txt}')
        self.inst.write(txt)
        delay()

    def query(self, cmd_str):
        # delay and retry in cause of old device with slow processing time
        # cycle will make 10 attempts before everything will get crashed.
        for i in range(10):
            try:
                # debug print to check how may tries
                #print("trying",i)
                return_val = self.inst.query(cmd_str)
                delay() # regular delay according to datasheet before next command
                return return_val

            except:
                print("VI_ERROR_TMO, retry:", i)
                delay(5)


    def disconnect(self):
        self.send(self.cmd.go_to_local.str())

    def reboot(self):
        self.send(self.cmd.reboot.str())





class str3:
    def __init__(self, prefix):
        self.prefix = prefix
        self.cmd = self.prefix

    def str(self):
        return self.cmd


class dig_param3:
    def __init__(self, prefix, min, max):
        self.prefix = prefix
        self.cmd = self.prefix
        self.max = max
        self.min = min

    def val(self, count=0):
        count = range_check(count, self.min, self.max, "MAX count")
        txt = f'{self.cmd} {count}'
        return txt


# class on_off:
#     def __init__(self, prefix):
#         self.prefix = prefix
#         self.cmd = self.prefix
#         self.on = str3(self.prefix + " ON")
#         self.off = str3(self.prefix + " OF")
#         self.value = dig_param3(self.prefix)

class on_off:
    def __init__(self, prefix):
        self.prefix = prefix
        self.cmd = self.prefix

    def on(self):
        return self.prefix + " ON"

    def off(self):
        return self.prefix + " OF"

class up_down:
    def __init__(self, prefix):
        self.prefix = prefix
        self.cmd = self.prefix

    def up(self):
        return self.prefix + " UP"

    def down(self):
        return self.prefix + " DN"


class t1_t4_ext:
    def __init__(self, prefix):
        self.prefix = prefix
        self.cmd = self.prefix

    def set400Hz(self):
        return self.prefix + " T4"

    def set1kHz(self):
        return self.prefix + " T1"

    def setExternal(self):
        return self.prefix + " XD"


class on_off_set:
    def __init__(self, prefix, min, max):
        self.prefix = prefix
        self.cmd = self.prefix
        self.set = dig_param3(self.prefix, min, max)

    def on(self):
        return self.prefix + " ON"

    def off(self):
        return self.prefix + " OF"



class storage:
    def __init__(self):
        self.cmd = None
        self.prefix = None
        self.go_to_local = str3("GTL")
        self.control_out = control_output("CO")
        self.fm = modulation("FM", 0, 300)
        self.am = modulation("AM", 0, 125)
        self.pilot_signal = on_off_set("PL", 0, 19.9)
        self.total_fm_deviation = dig_param3("FT", 0, 402)
        self.composite_sign_out_level = dig_param3("LV", 0, 9990)





class control_output(on_off, up_down):
    def __init__(self, prefix):
        self.prefix = prefix
        self.cmd = self.prefix
        self.prefix = self.cmd
        self.set = dig_param3(self.prefix, 0, 10)

class modulation(on_off, t1_t4_ext):
    def __init__(self, prefix, min, max):
        self.prefix = prefix
        self.cmd = self.prefix
        self.prefix = self.cmd
        self.set = dig_param3(self.prefix, min, max)


if __name__ == '__main__':

    cmd = storage()
    print("")
    print("TOP LEVEL")
    print("*" * 150)
    # print(cmd.control_out.on.str())
    # print(cmd.control_out.off.str())
    print(cmd.control_out.up())
    print(cmd.control_out.down())
    print(cmd.control_out.set.val(8.2))
    print(cmd.control_out.off())
    print(cmd.am.set1kHz())
    print(cmd.am.set400Hz())
    print(cmd.fm.set1kHz())
    print(cmd.fm.set400Hz())
    print(cmd.pilot_signal.on())
    print(cmd.pilot_signal.set.val(10))
    print(cmd.total_fm_deviation.val(100))
    print(cmd.composite_sign_out_level.val(500))