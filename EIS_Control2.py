import time
import os

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt






class Experiment():
    
    def __init__(self, path):
        self.path     = path    # Save path
        self.spectra  = []
        self.i        = 0       # Counter for # of spectra
        
    
    def append_spectrum(self, spectrum):
        self.spectra.append(spectrum)
        self.i = len(self.spectra)
        
    
    
class ImpedanceSpectrum():
    
    def __init__(self, freqs, Z, phase, experiment):
        self.timestamp = time.time()
        self.freqs     = freqs
        self.Z         = Z
        self.phase     = phase
        self.expt      = experiment # Associated Experiment object
        
    def correct_Z(self, Z_factors, phase_factors):
        
        # |Z| correction is multiplicative
        Z = np.absolute(self.Z)
        Z /= Z_factors
        
        # Phase correction is additive
        self.phase -= phase_factors
        self.Z = Z * np.exp(1j*Z*np.pi/180)
        return
    
    def save(self, name=None):
        '''
        Save this spectrum to its Experiment's save path
        '''
        path = self.experiment.path
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
        


class MasterModule():
    
    def __init__(self):
        self.STOP = False
        self.modules = [self]
        
    def register(self, module):
        '''
        Register a submodule to master
        '''
        setattr(self, module.__class__.__name__, module)
        self.modules.append(getattr(self, module.__class__.__name__))
        
    def run(self):
        '''
        Master main loop
        !! Runs in its own thread !!
        Checks if any module has issued a global stop command.
        If so, stops all other modules.
        '''
        while True:
            for module in self.modules:
                if module.willStop:
                    self.STOP = True
                    self.endState()
                    return
            time.sleep(0.1)
        
    def endState(self):
        '''
        Close ports for modules which need it and stop others nicely
        '''
        for module in self.modules:
            if hasattr(module, 'stop'):
                module.stop()



class ArbitraryWaveformGenerator():
    '''
    Sends commands to the arbitrary waveform generator
    '''
    def __init__(self, master):
        self.willStop = False
        self.master = master
        self.master.register(self)
        
    def initialize(self):
        # open port, set settings
        return
    
    def set_waveform(self, waveform):
        # send waveform data to arb and turn it on
        return
 
    
    
class ADC():
    '''
    Communicates with the ADC. Sets data recording settings and
    reads data back via serial port.
    '''
    def __init__(self, master):
        self.willStop = False
        self.master = master
        self.master.register(self)
    
    def initialize(self):
        # open port, set recording settings
        return
    
    def record(self, duration):
        # record for a certain duration
        # turn off/ on in between spectra? Probably should
        return


class DataTransformer():
    '''
    Monitors data stream from ADC (in a separate thread). When enough data
    points have been collected for a complete spectrum, Fourier transforms
    the data and sends the FourierTransformData object to the current
    Experiment.
    '''
    def __init__(self, master):
        self.willStop = False
        self.master = master
        self.master.register(self)
        
    def run(self):
        # get Z and phase correction factors        
        # ... check size of ADC buffer
        # ... generate ImpedanceSpectrum
        # ... save spectrum
        return
    
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
        
        
    
    
class GUI():
    
    def __init__(self, master):
        self.willStop = False
        self.master = master
        self.master.register(self)
        
        # Make all GUI windows
        
    # Spectrum/ waveform display window
    
    # Real time plot display window
        
    # Save/ update config
    
    # apply waveform
    
    # Record reference spectrum
    
    # record single spectrum
    
    # record continuously
    
    # multiplex - titration
    
    # multiplex - invivo
    
    # Create new waveform (csv template)
    
    # Create new waveform from last measurement
    
    # Adjust waveform Vpp
    
    














