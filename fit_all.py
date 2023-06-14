'''
Re-fit all spectra in a given folder
'''

from tkinter import *
from tkinter.ttk import *
from tkinter import filedialog
import os
import sys
import numpy as np
import matplotlib.pyplot as plt
from functools import partial
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from modules.Fitter import predict_circuit, Fitter

plt.style.use('ffteis.mplstyle')
colors = plt.rcParams['axes.prop_cycle'].by_key()['color']


# Remove highest/ lowest points from the fitting
remove_high = 0
remove_low  = 0



def prompt(prompt, valid_answers):
    while True:
        var = input(prompt)
        if var in ['q', 'quit', 'exit']:
            import sys
            sys.exit()
        if var in valid_answers:
            return var
        print('Input not recognized. Input one of the following:')
        print(f'{valid_answers}')


class Spectrum():
    def __init__(self, freqs, Z):
        self.freqs = freqs
        self.Z = Z

def fit_all(ax, folder, sequential_fits:bool, plot_every:int, fitter):
    '''
    folder: folder of data files to fit
    sequential_fits: bool, use previous fit as initial guess for next fit
    plot_every: int, plots every nth fit to graph
    '''
    # Set up results file
    j = 0
    fits_file = os.path.join(folder, f'!fits{j:02}.csv')
    while os.path.exists(fits_file):
        j += 1
        fits_file = os.path.join(folder, f'!fits{j:02}.csv')
    
    # Set up plot
    # window = None
    if plot_every != 0:
        ax2 = ax.twinx()
        ax.set_xlabel('Frequency/ Hz')
        ax2.set_ylabel(r'|Z|/ $\Omega$')
        ax.set_ylabel(r'Phase/ $\degree$')
        plt.show()
    
    
    i = 0
    fits = None
    plt.pause(0.2)
    for file in os.listdir(folder):
        ln = open(os.path.join(folder, file), 'r').readline()
        if not ln.startswith('<Frequency>'):
            continue
        f, re, im = np.loadtxt(os.path.join(folder,file),
                               unpack=True, skiprows=1)
        Z = re +1j*im
        
        f = f[remove_low:len(f)-remove_high]
        Z = Z[remove_low:len(Z)-remove_high]
        
        spec = Spectrum(f, Z)
        initial_guess = None
        if (i != 0) and (sequential_fits):
            initial_guess = fits
        
        # Do fitting
        fits = fitter.fit(spec, initial_guess) 
        print(f'{file}: {fits}')
        
        # Save to file
        with open(fits_file, 'a') as f:
            if i == 0:
                header_line = ','.join(key for key in fits.keys())
                header_line = 'file,' + header_line
                f.write(header_line + '\n')
            line = ','.join(str(val) for val in fits.values())
            line = f'{file},' + line
            f.write(line + '\n')
            
        # Draw on plot
        if plot_every == 0:
            plt.close()
            i += 1
            continue
        
        if (i%plot_every != 0):
            i += 1
            continue
        
        fit_Z = predict_circuit('Sensor', spec.freqs, fits)
        ax.set_xscale('linear')
        ax.clear()
        ax2.clear()
        
        # Data
        ax.plot(spec.freqs, np.angle(spec.Z, deg=True), 'o', color='orange',
                alpha = 0.7)
        ax2.plot(spec.freqs, np.abs(spec.Z), 'o', color=colors[0])
        
        # Fit
        ax.plot(spec.freqs, np.angle(fit_Z, deg=True), '-', color='orange',
                alpha = 0.7)
        ax2.plot(spec.freqs, np.abs(fit_Z), '-', color=colors[0])
        
        ax.set_xlabel('Frequency/ Hz')
        ax2.set_ylabel(r'|Z|/ $\Omega$', color=colors[0])
        ax.set_ylabel(r'Phase/ $\degree$', color='orange')
        ax2.yaxis.set_label_position('right')
        ax.set_xscale('log')
        ax.set_xticks([1e-1,1e0,1e1,1e2,1e3,1e4,1e5,1e6])
        ax.set_xlim(0.7*min(spec.freqs), 1.5*max(spec.freqs))
        ax.set_title(file)
        fig.tight_layout()
        fig.canvas.draw_idle()
        plt.pause(0.1)
                
        i += 1
        
        





if __name__ == '__main__':
    class this_master:
        def __init__(self):
            self.register = lambda x:1
            self.GUI = self.fit_circuit = self
            self.get = lambda : 'Sensor'
            
    def end(root):
        root.after(1, root.destroy)
        root.mainloop()
        root.quit()
        
        
    
    master = this_master()
    fitter = Fitter(master)
    root = Tk()
    
    fitter.parameter_window()
    
    folder = filedialog.askdirectory()
    if not folder:
        end(root)
        sys.exit()
        
    # sequential_fits = prompt('Sequential fits: ', ['0', '1'])
    # if sequential_fits in {'q', 'quit', 'exit'}:
    #     end(root)
        
    # plot_every = prompt('Plot every: ', ['0', '1', '2', '5', '10',
    #                                      '25', '50', '100', '250',
    #                                      '500', '1000'])
    # if plot_every in {'q', 'quit', 'exit'}:
    #     end(root)
    
    end(root)    
    fig, ax = plt.subplots(figsize=(6,5), dpi=80)
    fit_all(ax, folder, 1, 1, fitter)
    # func = partial(fit_all, folder, 0, 1, fitter)
    
    # window = fit_all(folder, sequential_fits=0, plot_every=1,
    #         fitter=fitter)
    # if window:
    #     window.wait_window()
    # end(root)
    
    
    
