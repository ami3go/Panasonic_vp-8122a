import sys
sys.path.append('../')
import src.PANASONIC_VP_8122A as panasonic


def rf_init():
    rf = panasonic.com_interface()
    rf.init()

def rf_init_measurements():


if __name__  == '__main__':
    pass