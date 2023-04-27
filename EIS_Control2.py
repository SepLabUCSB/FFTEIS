import time
import os

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt


'''
Use oscilloscope but rewrite with threading

DataQ ADC has aliasing issues due to imprecise timing and sampling rates
'''



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
    
    














