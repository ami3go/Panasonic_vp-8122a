import sys
sys.path.append('../')
from src.PANASONIC_VP_8122A import com_interface, storage


def rf_init():
    rf = com_interface()
    cmd = storage()

    # Turn on AM modulation at 30%
    rf.send(cmd.am.set.val(30))
    rf.send(cmd.am.on())

    # Set amplitude to 20 dBuV
    # output_level = "AP20.0DB"
    rf.send(cmd.output.set_dBuV.val(20.0))

    # Set modulation mode to mono
    # modulation_mode = "MS01"
    rf.send(cmd.main_and_sub_ch.MONO_INT())

    # Turn on internal modulator at 1 kHz
    # Could also use external
    rf.send(cmd.am.set1kHz())

    # Set Frequency to 531 Hz (according to the specific measurement)
    # frequency = "FR0.531MZ"
    rf.send(cmd.freq.MHz.val(0.531))

    # Set output impedance to 50 ohm
    # output_impendace = "AP50"
    rf.send(cmd.output.set_imp_50R())
    rf.send(cmd.control_out.on())

def set_freq_MHz(frq_Mhz):
    rf.send(cmd.control_out.off())

    rf.send(cmd.freq.MHz.val(frq_Mhz))

    rf.send(cmd.control_out.on())



# def rf_init_measurements():


if __name__  == '__main__':
    pass