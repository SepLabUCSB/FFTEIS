# Standard lib
import time
import os
import sys
import traceback
from tkinter import *
from tkinter.ttk import *

# Requirements
import pandas as pd
import numpy as np
import matplotlib
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

# Local modules
# from modules import *

default_stdout = sys.stdout
default_stdin  = sys.stdin
default_stderr = sys.stderr

matplotlib.use('TkAgg')


'''
Use oscilloscope but rewrite with threading

DataQ ADC has aliasing issues due to imprecise timing and sampling rates
'''



class MasterModule():
    
    def __init__(self):
        self.STOP = False
        self.modules = [self]
        
        self.experiment = None
      
        
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
    
    
    def set_experiment(self, Experiment):
        self.experiment = Experiment
        
    
    def endState(self):
        '''
        Close ports for modules which need it and stop others nicely
        '''
        for module in self.modules:
            if hasattr(module, 'stop'):
                module.stop()

 
class PrintLogger(): 
    '''
    File like object to print console output into Tkinter window
    set sys.stdout = PrintLogger, then print() will print to
    PrintLogger.textbox
    '''
    def __init__(self, textbox): 
        self.textbox = textbox # tk.Text object

    def write(self, text):
        self.textbox.insert(END, text) # write text to textbox
        self.textbox.see('end') # scroll to end

    def flush(self): # needed for file like object
        pass
       
    
    
class GUI():
    
    def __init__(self, root, master):
        self.willStop = False
        self.master = master
        self.master.register(self)
        
        self.root = root
        self.params = {}
        
        root.title('FFT-EIS Controller')
        root.attributes('-topmost', 1)
        root.attributes('-topmost', 0)
        root.option_add('*tearOff', FALSE)
        
        
        # Top left: Control
        topleft     = Frame(self.root)
        topleft.grid(row=0, column=0, sticky=(N,S))
        
        # Top right: input fields
        topright    = Frame(self.root)
        topright.grid(row=0, column=1, sticky=(N,S))
        
        # Bottom left: figure
        botleft     = Frame(self.root)
        botleft.grid(row=1, column=0, sticky=(N,S))
        self.fig = plt.Figure(figsize=(5,4), dpi=100)
        self.ax = self.fig.add_subplot(111)
        self.canvas = FigureCanvasTkAgg(self.fig, master=botleft)
        self.canvas.get_tk_widget().grid(row=0, column=0)

        # Bottom right: console
        botright    = Frame(self.root)
        botright.grid(row=1, column=1, sticky=(N,S))
        console = Text(botright, width=50, height=25)
        console.grid(row=0, column=0, sticky=(N,S,E,W))
        pl = PrintLogger(console)
        sys.stdout = pl
        
        
        
        
        
        
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
    
    



if __name__ == '__main__':
    
    master = MasterModule()
    
    root = Tk()
    try:
        gui = GUI(root, master)
        
        root.mainloop()
        root.quit()
        gui.willStop = True
        
    except Exception:
        print(traceback.format_exc())
    
    sys.stdout = default_stdout
    sys.stdin  = default_stdin
    sys.stderr = default_stderr
    
    
    











