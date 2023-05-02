import time
from datetime import datetime
import os

import numpy as np
import pandas as pd


class Experiment():
    
    def __init__(self, name=None):
        path = os.path.expanduser('~\Desktop\EIS Output')
        path = os.path.join(path, datetime.now().strftime('%Y-%m-%d'))
        if name:
            path = os.path.join(path, name)
        else:
            path = os.path.join(path, 'autosave')
            path = os.path.join(path, datetime.now().strftime('%H-%M-%S'))
            
        self.path     = path    # Save path
        self.spectra  = []
        self.i        = 0       # Counter for # of spectra
        
        self.waveform = None
        self.correction_factors = None
        
    
    def append_spectrum(self, spectrum):
        self.spectra.append(spectrum)
        self.i = len(self.spectra)
        spectrum.save()
        
        
    def set_waveform(self, Waveform):
        self.waveform = Waveform
        
    
    
class ImpedanceSpectrum():
    
    def __init__(self, freqs, Z, phase, experiment):
        self.timestamp = time.time()
        self.freqs     = freqs
        self.Z         = Z
        self.phase     = phase
        self.experiment= experiment # Associated Experiment object
        
    def correct_Z(self, Z_factors, phase_factors):
        
        # |Z| correction is multiplicative
        Z = np.absolute(self.Z)
        Z /= Z_factors
        
        # Phase correction is additive
        self.phase -= phase_factors
        self.Z = Z * np.exp(1j*self.phase*np.pi/180)
        return
    
    def save(self, name=None):
        '''
        Save this spectrum to its Experiment's save path
        '''
        path = self.experiment.path
        os.makedirs(path, exist_ok=True)
        i    = self.experiment.i
        
        if not name:
            name = f'{i:06}.txt'
        
        save_path = os.path.join(path, name)
        
        d = pd.DataFrame(
            {'f': self.freqs,
             're': np.real(self.Z),
             'im': np.imag(self.Z)}
            )
        d.to_csv(save_path, columns = ['f', 're', 'im'],
                 header = ['<Frequency>', '<Re(Z)>', '<Im(Z)>'], 
                 sep = '\t', index = False, encoding='ascii')
        
    
    def average(self, spectra:list):
        '''
        Average this spectrum with several others.
        
        Returns a new ImpedanceSpectrum object
        '''
        
        Zs = np.array([np.array(spec.Z) for spec in spectra])
        Z  = np.mean(Zs, axis=0)
        
        phases = np.array([np.array(spec.phase) for spec in spectra])
        phase  = np.mean(phases, axis=0)
        
        return ImpedanceSpectrum(self.freqs, Z, phase, self.experiment)
        
