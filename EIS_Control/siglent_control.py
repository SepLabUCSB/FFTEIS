import pyvisa
from array import array
import numpy as np
import matplotlib.pyplot as plt
from time import sleep
import time
import pandas as pd
plt.style.use('Z:\Projects\Brian\scientific.mplstyle')


class FourierTransformData:
    
    def __init__(self, time, freqs, CH1data, CH2data, Z = None,
                 phase = None, waveform = None):
        self.time = time
        self.freqs = freqs
        self.CH1data = CH1data
        self.CH2data = CH2data
        
        self.Z = Z
        self.phase = phase
        self.waveform = waveform




def get_frame_time(ftim):
    ftim = ftim.replace(' ', '')
    hr, m, s = ftim.split(':')
    t = 3600*float(hr) + 60*float(m) + float(s)
    return t   
    
    
    
def record_signals(inst, total_time):
    inst.write('TRMD STOP')
    # inst.write('MSIZ 140K')
    # inst.write('TDIV 100MS')
    start_time = time.time()
    inst.write('ARM')
    sleep(1)
    inst.write('TRMD NORMAL')
    while time.time() - start_time < total_time:
        sleep(0.001)
    inst.write('STOP')
    


def record_single(inst, start_time, frame_time,
                  vdiv1, voffset1, vdiv2, voffset2,
                  sara, sample_time=1):
    # Determine t=0 for frame
    frame_start_time = time.time()
   
    # Record frame
    inst.write('TRMD AUTO')
    sleep(1.2*frame_time)
    
    # Get CH 1 data
    inst.write('C1:WF? DAT2')
    trace1 = inst.read_raw()
    wave1 = trace1[22:-2]
    adc1 = np.array(array('b', wave1))
    
    # Get CH 2 data
    inst.write('C2:WF? DAT2')
    trace2 = inst.read_raw()
    wave2 = trace2[22:-2]
    adc2 = np.array(array('b', wave2))
    
    # Convert to voltages
    volts1 = adc1*(vdiv1/25) - voffset1 
    volts2 = adc2*(vdiv2/25) - voffset2  
    
    # Get time array
    times = np.zeros(len(volts1))
    for i in range(len(volts1)):
        times[i] = frame_start_time + (1/sara)*i - start_time
           
    # Only Fourier transform first sample_time s
    if sample_time:
        end = np.where(times == times[0] + sample_time)[0][0]
    else:
        end = None
    
    freqs = sara*np.fft.rfftfreq(len(volts1[:end]))[1:]
    ft1   =      np.fft.rfft(volts1[:end])[1:]
    ft2   =      np.fft.rfft(volts2[:end])[1:]
    
    ft = FourierTransformData(time    = times[0],
                              freqs   = freqs,
                              CH1data = ft1,
                              CH2data = ft2,)
    
    return ft

    
    

if __name__ == '__main__':
    rm = pyvisa.ResourceManager()
    inst = rm.open_resource('USB0::0xF4ED::0xEE3A::SDS1EDEX5R5381::INSTR')

    print(inst.query('*IDN?'))
    
    ft = record_continuous(inst, 10)
    

