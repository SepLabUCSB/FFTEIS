# Standard lib
import time
import os
import sys
import traceback
from tkinter import *
from tkinter.ttk import *
import tkinter as tk

# Requirements
import pandas as pd
import numpy as np
import matplotlib
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import pyvisa

# Local modules
# from modules import *

default_stdout = sys.stdout
default_stdin  = sys.stdin
default_stderr = sys.stderr

matplotlib.use('TkAgg')


'''
Use oscilloscope but rewrite with threading

DataQ ADC has aliasing issues due to imprecise timing and sampling rates

Everything runs in main thread except:
    Oscilloscope.record_frame()
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
        
        
        ### TOP LEFT: Control buttons ###
        
        # Check if SDS1202X-E and DG812 are connected and on
        scope_connected = False
        arb_connected   = False
        if any(['SDS1' in rsc for rsc 
                in pyvisa.ResourceManager().list_resources()]):
            scope_connected = True
        if any(['DG8' in rsc for rsc 
                in pyvisa.ResourceManager().list_resources()]):
            arb_connected = True
        
        Label(topleft, text='Oscilloscope: ').grid(column=0, row=0, sticky=(E))
        Label(topleft, text='Connected' if scope_connected else 'NOT CONNECTED').grid(
            column=1, row=0)
        Label(topleft, text='Func. Gen: ').grid(column=0, row=1, sticky=(E))
        Label(topleft, text='Connected' if arb_connected else 'NOT CONNECTED').grid(
            column=1, row=1)
        
        # Waveform selection dropdown
        # !!!TODO: propagate default waveform options from waveforms/ 
        Label(topleft, text='Waveform: ').grid(column=0, row=2, sticky=(E))
        self.waveformselection = StringVar(topleft)
        OptionMenu(topleft, self.waveformselection, '', ['', 'waveform2']).grid(
            column=1, row=2, sticky=(E,W))
        Button(topleft, text='Apply Waveform', command=self.apply_waveform).grid(
            column=2, row=2, sticky=(W))
        
        
        # Record... Buttons
        Button(topleft, text='Record Reference', command=self.record_reference).grid(
            column=0, row=3, sticky=(E))
        Button(topleft, text='Record Spectrum', command=self.record_single).grid(
            column=1, row=3, sticky=(W,E))
        Button(topleft, text='Record for...', command=self.record_duration).grid(
            column=2, row=3, sticky=(W))
        
        
        # Multiplexing buttons
        Label(topleft, text='Multiplex: ').grid(
            column=0, row=4, sticky=(E))
        Button(topleft, text='Titration', command=self.multiplex_titration).grid(
            column=1, row=4, sticky=(W,E))
        Button(topleft, text='In-vivo', command=self.multiplex_invivo).grid(
            column=2, row=4, sticky=(W))
        
        
        
        ### TOP RIGHT: Input fields ###
        
        # mVpp input
        Label(topright, text='Amplitude (mV peak-peak): ').grid(
            column=0, row=0, sticky=(E))
        self.amplitude_input = Text(topright, height=1, width=3)
        self.amplitude_input.insert('1.0', '25')
        self.amplitude_input.grid(column=1, row=0, sticky=(W,E))
        
        # Current range selection
        current_ranges = ['1 A','100 mA','10 mA','1 mA','100 uA','10 uA','1 uA','100 nA', '10 nA']
        Label(topright, text='NOVA Current Range: ').grid(
            column=0, row=1, sticky=(E))
        self.current_range = StringVar(topright)
        OptionMenu(topright, self.current_range, current_ranges[6],
                   *current_ranges).grid(column=1, row=1, sticky=(W,E))
        
        
        # Reference spectrum correction
        Label(topright, text='Reference Correction: ').grid(
            column=0, row=2, sticky=(E))
        self.ref_correction_bool = BooleanVar(topright, value=TRUE)
        Checkbutton(topright, text='', variable=self.ref_correction_bool).grid(
            column=1, row=2, sticky=(W))
        
        
        # Generate optimize waveform button
        Button(topright, text='Create Optimized Waveform', command=
               self.create_optimized_waveform).grid(column=0, row=3,
                                                    columnspan=2, sticky=(W,E))
        
        
        
        
    def apply_waveform(self):
        return
    
    
    def record_reference(self):
        return
    
    
    def record_single(self):
        return
    
    
    def record_duration(self):
        return
    
    
    def multiplex_titration(self):
        return
    
    
    def multiplex_invivo(self):
        return
    
    
    def create_optimized_waveform(self):
        return
        
        
        
        
        
        
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
        
    except Exception as e:
        sys.stdout = default_stdout
        sys.stdin  = default_stdin
        sys.stderr = default_stderr
        print(traceback.format_exc())
    
    
    sys.stdout = default_stdout
    sys.stdin  = default_stdin
    sys.stderr = default_stderr
    
    
    











