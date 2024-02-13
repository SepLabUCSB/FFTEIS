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
import matplotlib
from modules.Fitter import predict_circuit, Fitter

plt.style.use('ffteis.mplstyle')
# matplotlib.use('Qt5Agg')
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
    
    
    # Initialize times list
    times_list = []
    if os.path.exists(os.path.join(folder, f'!times.txt')):
        with open(os.path.join(folder, f'!times.txt'), 'r') as f:
            for line in f:
                times_list.append(float(line))
        t0 = times_list[0]
    
    
    # Get number of sensors in this experiment
    sensors = list()
    for file in os.listdir(folder):
        if file.endswith('.xlsx'):
            continue
        ln = open(os.path.join(folder, file), 'r').readline()
        if not ln.startswith('<Frequency>'):
            continue
        if '_' in file:
            sensor, _ = file.split('_')
            if sensor not in sensors:
                sensors.append(sensor)
    n_sensors = len(sensors)
        
    
    i = 0
    fits = None
    plt.pause(0.2)
    for file in os.listdir(folder):
        if file.endswith('.xlsx'):
            continue
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
        
        # Find the correct time
        if '_' in file:
            sensor, idx = file[:-4].split('_')
            sensor_idx = [j for j, sens in enumerate(sensors) if sens==sensor][0]
            idx = int(idx)
            
            idx = idx*n_sensors + int(sensor_idx)
        else:
            idx = i
        
        if times_list:
            t = times_list[idx] - times_list[0]
        else:
            t = idx
            
        
        # Save to file
        with open(fits_file, 'a') as f:
            if i == 0:
                header_line = ','.join(key for key in fits.keys())
                header_line = 'file,time,' + header_line
                f.write(header_line + '\n')
            line = ','.join(str(val) for val in fits.values())
            line = f'{file},{t},' + line
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
        # plt.show()
        plt.pause(0.1)
                
        i += 1
    return
        
        





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
        
    sequential_fits = prompt('Sequential fits (0/1): ', ['0', '1'])
    if sequential_fits in {'q', 'quit', 'exit'}:
        end(root)
        sys.exit()
        
    plot_every = prompt('Plot every (0 for no plotting): ', 
                        ['0', '1', '2', '5', '10',
                        '25', '50', '100', '250',
                        '500', '1000'])
    if plot_every in {'q', 'quit', 'exit'}:
        end(root)
        sys.exit()
    
    end(root)    
    fig, ax = plt.subplots(figsize=(6,5), dpi=80)
    fit_all(ax, folder, bool(int(sequential_fits)), 
            int(plot_every), fitter)

    
    
    
