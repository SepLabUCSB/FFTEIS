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
                
        self.data  = []
        
        
    
    
    def run(self):
        st = time.time()
        while True:
            if time.time() - st > 10:
                return
            if self.master.STOP:
                return
            
            
            
            if self.buffer.buffer:
                data = self.buffer.get(1)
                self.process(*data)
    
                    
    
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

                
               
    def process(self, timestamp, recording_params, volts1, volts2):
        '''
        timestamp: time.time() output when frame was recorded
        recording_params: dict, importantly includes sampling rate and tdiv
        volts1: np.array of raw voltage output from CH 1 (voltage)
        volts2: np.array of raw voltage output from CH 2 (current)
        
        We need to use the current range (set in NOVA) to convert volts2 back
        into current. Then Fourier transform both and filter to only keep
        the frequencies we applied.      
        '''
        
        
        sample_rate = recording_params['sara']
        total_time  = recording_params['frame_time']
        i_range     = recording_params['i_range']
        
        
        t = np.linspace(0, total_time, int(sample_rate*total_time))
        v = volts1
        i = volts2/i_range
        
        
        # TODO: adapt for spectra that don't end at 1Hz
        cutoff_time = 1
        cutoff_id   = max([i for i, ti in enumerate(t) if ti <= cutoff_time])
        
        t = t[:cutoff_id]
        v = v[:cutoff_id]
        i = i[:cutoff_id]
        
        
        freqs = sample_rate*np.fft.rfftfreq(len(v))[1:]
        ft_v  =             np.fft.rfft(v)[1:]
        ft_i  =             np.fft.rfft(i)[1:]
                
        
        self.data.append( (freqs, ft_v, ft_i) )
