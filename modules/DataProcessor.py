import time
import os

import numpy as np
import pandas as pd

if __name__ == '__main__':
    from DataStorage import ImpedanceSpectrum
else:
    from .DataStorage import ImpedanceSpectrum



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
                
        self.wf    = None
        

    
    def run(self):
        st = time.time()
        while True:
            # if time.time() - st > 10:
            #     return
            if self.master.STOP:
                return
            if self.master.waveform:
                if self.wf != self.master.waveform:
                    self.wf = self.master.waveform
                    self.load_correction_factors()
            if self.buffer.buffer:
                data = self.buffer.get(1)
                self.process(*data)
            time.sleep(0.05)
    
                    
    
    def make_spectrum(self, timestamp, freqs, Z, name):
        spectrum = ImpedanceSpectrum(
            freqs       = freqs,
            Z           = Z,
            phase       = np.angle(Z, deg=True),
            experiment  = self.master.experiment,
            timestamp   = timestamp,
            name        = name
            )
        if self.master.GUI.ref_correction_bool.get():
            spectrum.correct_Z(self.Z_factors, self.phase_factors)
            
        if (self.master.GUI.fit_bool.get() and
            hasattr(self.master.GUI, 'fitter')):
            initial_guess = None
            if len(self.master.experiment.spectra) > 0:
                initial_guess = self.master.experiment.spectra[-1].fit
            fit = self.master.GUI.fitter.fit(spectrum, initial_guess)
            spectrum.fit = fit
            
            
        self.master.experiment.append_spectrum(spectrum)

                
               
    def process(self, timestamp, recording_params, volts1, volts2, name):
        '''
        timestamp: time.time() output when frame was recorded
        recording_params: dict, importantly includes sampling rate and tdiv
        volts1: np.array of raw voltage output from CH 1 (voltage)
        volts2: np.array of raw voltage output from CH 2 (current)
        name: string or None
        
        We need to use the current range (set in NOVA) to convert volts2 back
        into current. Then Fourier transform both and filter to only keep
        the frequencies we applied.      
        '''
        
        
        sample_rate = recording_params['sara']
        total_time  = recording_params['frame_time']
        i_range     = recording_params['i_range']
                
        t = np.linspace(0, total_time, int(sample_rate*total_time))
        v = volts1
        i = volts2*i_range
        
        
        cutoff_time = 1/self.applied_freqs[0]
        cutoff_id   = max([i for i, ti in enumerate(t) if ti <= cutoff_time])
        cutoff_id  += 1
        
        t = t[:cutoff_id]
        v = v[:cutoff_id]
        i = i[:cutoff_id]
        
        
        freqs = sample_rate*np.fft.rfftfreq(len(v))[1:]
        ft_v  =             np.fft.rfft(v)[1:]
        ft_i  =            -np.fft.rfft(i)[1:]
        
        
        freqs = freqs.round(3)
        
        # Only keep applied frequencies
        idxs = [i for i, freq in enumerate(freqs) 
                if freq in self.applied_freqs]
                
        freqs = freqs[idxs]
        ft_v  = ft_v[idxs]
        ft_i  = ft_i[idxs]
                
        self.make_spectrum(timestamp, freqs, ft_v/ft_i, name)
        
        
    
    
    def load_correction_factors(self):
        # Get applied frequencies and correction factors
        wf = self.master.waveform
        self.applied_freqs = wf.freqs
        
        wf_name = wf.name()
        wf_name = wf_name.replace('_opt', '')
        correction_files = [f for f in os.listdir('waveforms/reference')
                            if wf_name in f]
        if len(correction_files) == 0:
            print(f'Error: Will not correct spectra: no reference spectrum found for waveform {wf.name()}!')
            self.Z_factors     = np.ones(len(self.applied_freqs))
            self.phase_factors = np.zeros(len(self.applied_freqs))
            return
        
        file = correction_files[-1] # Most recent date
        file = os.path.join('waveforms/reference', file)
        df = pd.read_csv(file)
        self.Z_factors     = df['Z_factor'].to_numpy()
        self.phase_factors = df['phase_factor'].to_numpy()
        return
        
        
        
        
        
        
        