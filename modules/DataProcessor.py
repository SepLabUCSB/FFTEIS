import time

import numpy as np

from DataStorage import ImpedanceSpectrum

class DataProcessor():
    '''
    Monitors data stream from oscilloscope (in a separate thread). When a 
    frame is recorded, Fourier transforms the data and sends the 
    FourierTransformData object to the current Experiment.
    '''
    def __init__(self, master, ADCDataBuffer):
        self.willStop = False
        self.master = master
        self.master.register(self)
        self.buffer = ADCDataBuffer
        
        self.block_size = 10000
        
        self.data  = []
        
        self.last_spec_count = 0
        self.spec_time = 5
        
    
    
    def run(self):
        st = time.perf_counter()
        while True:
            if time.perf_counter() - st > 10:
                return
            if self.master.STOP:
                return
            
            if type(self.master.ADC.last_timepoint) != int:
                continue
            
            
            if self.buffer.buffer:
                first_timepoint = self.buffer.buffer[0][0]
                last_timepoint  = self.buffer.buffer[-1][0]
                
                if abs(last_timepoint - first_timepoint)*1e-9 > self.spec_time:
                    data = self.buffer.get(self.buffer.size())
                    self.process(data)
    
                    
    
    def make_spectrum(self, freqs, Z):
        spectrum = ImpedanceSpectrum(
            freqs = freqs,
            Z     = Z,
            phase = np.angle(Z, deg=True),
            expt  = self.master.experiment
            )
        spectrum.correct_Z(self.Z_factors, self.phase_factors)
        spectrum.save()
        self.master.experiment.append_spectrum(spectrum)

                
               
    def process(self, data):
        
        processed_data = [ [], [] ]
        
        first_timestamp = data[0][0]
        last_timestamp  = data[-1][0]
        
        prev_timestamp = first_timestamp
        t = []
        for timestamp, count, response in data[1:]:
            bResponse = bytearray(response)
            Channel = struct.unpack("<"+"h"*count, bResponse)
            times = np.linspace(prev_timestamp, timestamp, count)
            
            for j in range(count):
                ch_idx = (count - j)%2
                processed_data[ch_idx].append(Channel[j]*10/2**15)
                
                if j%2 == 0:
                    t.append(times[j])
        
        v, i = processed_data
        # t = np.linspace(first_timestamp, last_timestamp, len(v))
        
        # t, v, i = zip(*data)
        t = np.array(t)
        t -= t[0]
        t *= 1e-9
        
        cutoff_id = max([i for i, time in enumerate(t) if time <= 1])
        v = v[:cutoff_id]
        i = i[:cutoff_id]
        
        
        
        sample_rate = (t[-1] - t[0])/len(t)
        print(1/sample_rate, len(t))
        
        # sample_rate = 10000
        freqs = sample_rate*np.fft.rfftfreq(len(v))[1:]
        ft_v  = np.fft.rfft(v)[1:]
        ft_i  = np.fft.rfft(i)[1:]
                
        
        self.data.append((freqs, ft_v))
