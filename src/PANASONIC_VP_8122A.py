import pyvisa # PyVisa info @ http://PyVisa.readthedocs.io/en/stable/
#import serial.tools.list_ports
#import serial
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
INSTRUMENT_VISA_ADDRESS = 'USB0::0x03EB::0x2065::GPIB_02_55137303031351900211::INSTR' # Get this from Keysight IO Libraries Connection Expert
    ## Note: sockets are not supported in this revision of the script (though it is possible), and PyVisa 1.8 does not support HiSlip, nor do these scopes.
    ## Note: USB transfers are generally fastest.
    ## Video: Connecting to Instruments Over LAN, USB, and GPIB in Keysight Connection Expert: https://youtu.be/sZz8bNHX5u4

# any read rerun the status string divided by space
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
            if INSTRUMENT_VISA_ADDRESS in item:
                self.res_name = item
        self.inst = self.rm.open_resource(self.res_name)
        # self.inst.set_visa_attribute(pyvisa.constants.VI_ATTR_SEND_END_EN, 1)
        # self.inst.write_termination = ""
        # self.inst.timeout = 2000 # timeout in ms
        print("Connected to: ", self.inst.query("*IDN?"))



    def send(self, txt):
        # will put sending command here
        # print(f'Sending: {txt}')
        self.inst.write(txt)
        delay()

    # def read(self, txt):
    #     # will put sending command here
    #     # print(f'Sending: {txt}')
    #     self.inst.write(txt)
    #     delay()

    def query(self, cmd_str):
        # delay and retry in case of old device with slow processing time
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
    
    def init_measurement(self):
        pass
        # Turn on AM modulation at 30%
        self.send(self.cmd.am.set.val(30))
        self.send(self.cmd.am.on())

        # Set amplitude to 20 dBuV
        #output_level = "AP20.0DB"
        self.send(self.cmd.output.set_dBuV.val(20.0))

        # Set modulation mode to mono
        #modulation_mode = "MS01"
        self.send(self.cmd.main_and_sub_ch.MONO_INT())


        # Turn on internal modulator at 1 kHz
        # Could also use external
        self.send(self.cmd.am.set1kHz())

        # Set Frequency to 531 Hz (according to the specific measurement)
        #frequency = "FR0.531MZ"
        self.send(self.cmd.freq.MHz.val(0.531))
        # Set output impedance to 50 ohm
        #output_impendace = "AP50"
        self.send(self.cmd.output.set_imp_50R())


    def disconnect(self):
        self.send(self.cmd.go_to_local.str())


##################################################################
# *******  service classes to reduce coding  *********************
##################################################################

class str3:
    def __init__(self, prefix):
        self.prefix = prefix
        self.cmd = self.prefix

    def str(self):
        return self.cmd


class dig_param3:
    def __init__(self, prefix, min, max, ending=""):
        self.prefix = prefix
        self.cmd = self.prefix
        self.max = max
        self.min = min
        self.ending = ending

    def val(self, count=0):
        count = range_check(count, self.min, self.max, "MAX count")
        return f'{self.cmd} {count}{self.ending}'


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

##################################################################
# *******  main class with high level key function list  *********
##################################################################


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
        self.output = output("AP")
        self.freq = frequency("FR")
        self.main_and_sub_ch = main_and_sub_ch()
        self.neg_peak_clipper = on_off("NP")
        self.fm_stereo_pre_emphasis = fm_stereo_pre_emphasis()


##################################################################
# *******                   hierarchical classes         *********
##################################################################


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


class output(on_off):
    def __init__(self, prefix):
        self.prefix = prefix
        self.cmd = self.prefix
        self.prefix = self.cmd
        self.set_dBm = dig_param3(self.prefix, -133.0, 19.0, "DM")
        self.set_dBuV = dig_param3(self.prefix, -26.0, 126.0, "DB")
        self.set_mV = dig_param3(self.prefix, 0.000050, 2000, "MV")
        self.set_uV = dig_param3(self.prefix, 0.050, 2000000, "UV")

    def set_imp_50R(self):
        return self.prefix + " 50"

    def set_imp_75R(self):
        return self.prefix + " 75"

    # def set_level_dBm(self, value):
    #     value = range_check(value, -133.0, 19.0, "dBm value")
    #     return f'{self.cmd} {value}DM'
    #
    # def set_level_dBuV(self, value):
    #     value = range_check(value, -26.0, 126.0, "dBuV value")
    #     return f'{self.cmd} {value}DB'
    #
    # def set_level_mV(self, value):
    #     value = range_check(value, 0.000050, 2000, "mV value")
    #     return f'{self.cmd} {value}MV'
    #
    # def set_level_uV(self, value):
    #     value = range_check(value, 0.050, 2000000, "uV value")
    #     return f'{self.cmd} {value}UV'


class frequency:
    def __init__(self, prefix):
        self.prefix = prefix
        self.cmd = self.prefix
        self.prefix = self.cmd
        self.MHz = dig_param3(self.prefix, 0.01000, 280.00000, "MZ")
        self.kHz = dig_param3(self.prefix, 10.00000, 280000.00, "KZ")

    # def set_MHz(self, value):
    #     value = range_check(value, 0.01000, 280.00000, "freq in MHz value")
    #     return f'{self.cmd} {value}MZ'
    #
    # def set_kHz(self, value):
    #     value = range_check(value, 10.00000, 280000.00, "dBuV value")
    #     return f'{self.cmd} {value}KZ'


class main_and_sub_ch:
    def __init__(self):
        pass

    def OFF(self):
        return "MS 00"

    def MONO_INT(self):
        return "MS 01"

    def L_eq_R_INT(self):
        return "MS 02"

    def L_INT(self):
        return "MS 03"

    def R_INT(self):
        return "MS 04"

    def L_eq_minusR_INT(self):
        return "MS 05"

    def MONO_EXT(self):
        return "MS 11"

    def L_eq_R_EXT(self):
        return "MS 12"

    def L_EXT(self):
        return "MS 13"

    def R_EXT(self):
        return "MS 14"

    def L_eq_minusR_EXT(self):
        return "MS 15"

    def L_R_EXT(self):
        return "MS 17"


class fm_stereo_pre_emphasis:
    def __init__(self):
        pass

    def OFF(self):
        return "PR 0"

    def set_25uS(self):
        return "PR 1"

    def set_50uS(self):
        return "PR 2"

    def set_75uS(self):
        return "PR 3"

if __name__ == '__main__':

    cmd = storage()
    print("")
    print("TOP LEVEL")
    print("*" * 150)
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
    print(cmd.am.set.val(30))
    print(cmd.output.off())
    print(cmd.output.on())
    print(cmd.output.set_imp_50R())
    print(cmd.output.set_imp_75R())
    print(cmd.output.set_dBm.val(20))
    print(cmd.freq.kHz.val(1500))
    print(cmd.freq.MHz.val(150))
    print(cmd.main_and_sub_ch.OFF())
    print(cmd.main_and_sub_ch.MONO_INT())
    print(cmd.neg_peak_clipper.on())
    print(cmd.neg_peak_clipper.off())
    print(cmd.fm_stereo_pre_emphasis.OFF())
    print(cmd.fm_stereo_pre_emphasis.set_50uS())
    print(cmd.output.set_dBm.val(10))

    # inst = com_interface()
    # inst.init()

