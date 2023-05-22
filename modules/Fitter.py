import tkinter as tk
from tkinter import *
from tkinter.ttk import *
from PIL import Image
import os

import numpy as np
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

from .LEVM.LEVM import LEVM_fit


allowed_circuits = ('RRC', 'Sensor')

# Default parameter initial guesses/ free or not (bool)
circuit_params = {
    'RRC': {
        'R1': (100, 1),
        'R2': (1000, 1),
        'C1': (1e-6, 1),
        '_img': 'etc/RRC.png'     
        },
    'Sensor': {
        'Rs': (500, 1),
        'Rct': (30000, 1),
        'Cdl': (1e-7, 1),
        'n_dl': (1, 0),
        'Cads': (5e-7, 1),
        'n_ads': (0.84, 0),
        '_img': 'etc/Sensor.png'
        }
        
    }


def predict_circuit(circuit, frequencies, params):
    '''
    Return estimated Z(w) at the given frequencies for the chosen circuit.
    
    circuit: str, one of "RRC" or "Sensor"
    frequencies: list or array of frequencies
    params: dict of {circuit element: value}
    
    Returns: np array of shape (len(frequencies), 1)
    '''
    
    def CPE(f, params):
        '''
        Params:
            Q: CPE value
            n: CPE exponent (0 < n < 1)
        '''
        w = 2*np.pi*f
        Q = params['Q']
        n = params['n']
        return 1/(Q*(w*1j)**n)
    
    if circuit not in allowed_circuits:
        return
    
    if circuit == 'RRC':
        w = 2*np.pi*frequencies
        R1 = params['R1']
        R2 = params['R2']
        C = params['C1']
        Z_C = 1/(1j*w*C)
        return R1 + (R2*Z_C)/(Z_C + R2)
    
    if circuit == 'Sensor':
        R1 = params['Rs']
        R2 = params['Rct']
        Q1 = params['Cdl']
        n1 = params['ndl']
        Q2 = params['Cad']
        n2 = params['nad']
        Ca = CPE(frequencies, {'Q':Q2, 'n':n2})
        Cdl = CPE(frequencies, {'Q':Q1, 'n':n1})
        Z = R1 + 1/(1/Cdl + 1/(R2+Ca))
        return Z
        


class Fitter():
    def __init__(self, master):
        self.willStop = False
        self.master = master
        self.master.register(self)
        
        self.guesses = None # dict of element: (guess, free)
        self.circuit = None
    
    def parameter_window(self, selection=None):
        '''
        Make popup window, prompt for initial guesses/ free parameters
        '''
        if not selection:
            selection = self.master.GUI.fit_circuit.get()
            
        self.circuit = selection
        
        params = circuit_params[selection].copy()
        imgfile = params['_img']
        params.pop('_img')
        
        window = Toplevel()
        window.title('Fitting options')
        window.attributes('-topmost', 1)
        frame = Frame(window)
        frame.grid(row=0, column=0)
        
        imframe = Frame(window)
        imframe.grid(row=0, column=1)
        fig = plt.Figure(figsize=(3,2), dpi=80)
        ax = fig.add_subplot(111)
        canvas = FigureCanvasTkAgg(fig, master=imframe)
        canvas.get_tk_widget().grid(row=0, column=0)
        img = np.asarray(Image.open(imgfile))
        ax.imshow(img)
        ax.set_xticks([])
        ax.set_yticks([])
        ax.spines[['left', 'right', 'top', 'bottom']].set_visible(False)
        
        
        row = 0
        elems  = []
        values = []
        bools  = []
        for elem, (value, free) in params.items():
            
            Label(frame, text=elem).grid(row=row, column=0, sticky=(W,E))
            value_var = StringVar(value=str(value))
            Entry(frame, textvariable=value_var, width=6).grid(
                row=row, column=1, sticky=(W,E))
            bool_var = BooleanVar(value=free)
            Checkbutton(frame, text='', variable=bool_var).grid(
                row=row, column=2, sticky=(W,E))
            
            elems.append(elem)
            values.append(value_var)
            bools.append(bool_var)
            row += 1
            
        Button(frame, text='Done', command=window.destroy).grid(
            row=row, column=0, columnspan=3)
        
        window.wait_window()
        self.guesses = params.copy()
        self.bools = {}
        for (elem, value, boolean) in zip(elems, values, bools):
            try:
                self.guesses[elem] = (value.get(), 
                                      boolean.get()) 
                self.bools[elem]   = boolean.get()
            except:
                print(f'Invalid input for {elem}: {value}')
        
        return self.guesses
    
    
    def fit(self, spectrum, initial_guess=None):
        '''
        Fit spectrum to the chosen equivalent circuit. Use initial guess if
        give, otherwise uses previously-set initial guess by paramete_window().
        If we don't have any initial guess, prompt the user for it by calling
        parameter_window().
        
        spectrum: ImpedanceSpectrum object
        initial_guess: dictionary of {element: (value, free)} 
        '''
        
        # Get initial guess
        
        if not initial_guess:
            initial_guess = self.guesses if self.guesses else self.parameter_window()
        
        for elem, val in initial_guess.items():
            if not type(val) == tuple:
                initial_guess[elem] = (val, self.bools[elem])
        
        # print(initial_guess)
        circuit = self.circuit
        
        # Set values for fitting
        
        freqs = spectrum.freqs
        Z     = spectrum.Z
        guess = {elem: value for elem, (value, boolean) in initial_guess.items()}
        free  = {elem: boolean for elem, (value, boolean) in initial_guess.items()}
        
        # Run fitting subroutine
        fits = LEVM_fit(freqs, Z, guess, circuit, free)
        # print(f'fits: {fits}')
        return fits













