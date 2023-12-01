import time
from datetime import datetime
import os

import numpy as np
import pandas as pd


class Experiment():
    
    def __init__(self, master, name=None):
        path = os.path.expanduser('~\Desktop\EIS Output')
        path = os.path.join(path, datetime.now().strftime('%Y-%m-%d'))
        if name:
            path = os.path.join(path, name)
        else:
            path = os.path.join(path, 'autosave')
            path = os.path.join(path, datetime.now().strftime('%H-%M-%S'))
        
        self.master    = master
        self.path      = path    # Save path
        self.time_file = os.path.join(path, '!times.txt')
        self.fits_file = os.path.join(path, '!fits.csv')
        self.meta_file = os.path.join(path, '!metadata.txt')
        self.spectra   = []
        self.i         = 0       # Counter for # of spectra
        
        self.waveform = None
        self.correction_factors = None
        
    
    def append_spectrum(self, spectrum):
        os.makedirs(self.path, exist_ok=True)
        self.spectra.append(spectrum)
        self.i = len(self.spectra)
        spectrum.save()
        self.write_time(spectrum)
        self.write_fits(spectrum)
        if not os.path.exists(self.meta_file):
            self.write_metadata()
        
    
    def write_time(self, spectrum):
        with open(self.time_file, 'a') as f:
            f.write(f'{spectrum.timestamp}\n')
            
            
    def write_fits(self, spectrum):
        if spectrum.fit == None:
            return
        if not os.path.exists(self.fits_file):
            with open(self.fits_file, 'w') as f:
                header_line = ','.join(key for key in spectrum.fit.keys())
                header_line = 'file,time,' + header_line
                f.write(header_line + '\n')
        with open(self.fits_file, 'a') as f:
            line = ','.join(str(val) for val in spectrum.fit.values())
            name = spectrum.name
            t    = spectrum.timestamp
            if not name:
                name = f'{self.i:06}.txt'
                
            line = f'{name},{t},' + line
            f.write(line + '\n')
            
    def write_metadata(self):
        with open(self.meta_file, 'w') as f:
            f.write(f"Meta file created on {datetime.now().strftime('%a %d %b %Y, %I:%M%p')}\n\n")
            f.write(f'Waveform: {self.waveform.name()}\n')
            f.write(f"Vpp: {self.master.GUI.amplitude_input.get('1.0', 'end')[:-1]} mV\n")
            f.write(f"User-set NOVA current range: {self.master.GUI.current_range.get()}\n\n")
            f.write(f"Filter correction: {self.master.GUI.ref_correction_bool.get()}\n")
            f.write(f"Frequencies: {self.waveform.freqs}\n\n")
            f.write(f"Z correction factors: {self.master.DataProcessor.Z_factors}\n\n")
            f.write(f"Phase corrections: {self.master.DataProcessor.phase_factors}\n\n")
            f.write(f'Fitting: {self.master.GUI.fit_bool.get()}\n')
            if (self.master.GUI.fit_bool.get() and
                hasattr(self.master.GUI, 'fitter')):
                f.write(f'Fit circuit: {self.master.GUI.fitter.circuit}\n')
                f.write(f'Initial guesses for fit: {self.master.GUI.fitter.guesses}\n')
            
        
        
    def set_waveform(self, Waveform):
        self.waveform = Waveform
        
    
    
class ImpedanceSpectrum():
    
    def __init__(self, freqs, Z, phase, experiment, timestamp, name=None):
        self.timestamp = time.time()
        self.freqs     = freqs
        self.Z         = Z
        self.phase     = phase
        self.experiment= experiment # Associated Experiment object
        self.timestamp = timestamp
        self.name      = name
        self.fit       = None
        
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
        
        if self.name:
            name = self.name
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
        # if 'autosave' not in save_path:
        #     print(f'Saved as {save_path}')
        
    
    def average(self, spectra:list):
        '''
        Average this spectrum with several others.
        
        Returns a new ImpedanceSpectrum object
        '''
        
        Zs = np.array([np.array(spec.Z) for spec in spectra])
        Z  = np.mean(Zs, axis=0)
        
        phases = np.array([np.array(spec.phase) for spec in spectra])
        phase  = np.mean(phases, axis=0)
        
        return ImpedanceSpectrum(self.freqs, Z, phase, self.experiment,
                                 self.timestamp, self.name)
        
