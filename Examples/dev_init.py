import sys
sys.path.append('../')
import src.PANASONIC_VP_8122A as panasonic

rf = panasonic.com_interface()
rf.init()
rf.init_measurement()