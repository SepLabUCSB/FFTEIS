from tkinter import *
from tkinter.ttk import *
import tkinter as tk
import numpy as np

import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

from .funcs import nearest




plot_options = ['|Z|', 'Phase', 'Parameter', 'k']

# TODO: set initial xlim as 0, 15 min
# every 15 minutes, update xlim and re-acquire background
# Set generous ylim, and only redo background if y goes very close

class MonitorWindow:
    '''
    Popup window when recording. Allows user to choose what to plot
    as a function of time: 
        |Z| at freq. f
        phase at freq. f
        EEC parameter
        k_et
    '''
    def __init__(self, master, root):
        self.master = master
        self.root   = root
        self._closed = False
        
        self.last_spectrum = None
        self.saved_freqs   = []
        self.xdata = []
        self.ydata = []
        
        self.window = Toplevel()
        self.window.protocol('WM_DELETE_WINDOW', self._on_closing)
        
        self.window.title('Real-time monitor')
        self.window.attributes('-topmost', 1)
        self.window.attributes('-topmost', 0)
        
        toprow = Frame(self.window)
        toprow.grid(row=0, column=0, sticky=(W,E))
        
        Label(toprow, text='Plot: ').grid(row=0, column=0, sticky=(W,E))
        
        self.display_selection = StringVar()
        display_menu = OptionMenu(toprow, self.display_selection,
                                  plot_options[0], *plot_options, 
                                  command=self._display_menu_changed)
        display_menu.grid(row=0, column=1, sticky=(W,E))
        
        self.display_option = StringVar()
        self.display_option_menu = OptionMenu(toprow, self.display_option,
                                    '', *['',], 
                                    command=self._display_option_changed)
        self.display_option_menu.grid(row=0, column=2, sticky=(W,E))
        
        figframe = Frame(self.window)
        figframe.grid(row=1, column=0, sticky=(W,E))
        
        self.fig = plt.Figure(figsize=(5,4), dpi=100)
        self.ax = self.fig.add_subplot(111)
        self.canvas = FigureCanvasTkAgg(self.fig, master=figframe)
        self.canvas.get_tk_widget().grid(row=0, column=0)
        
        # Initialize background for blitting
        self.redraw_plot()
    
    
    def _on_closing(self):
        '''
        Called when user closes this window. Don't check for updates anymore
        '''
        self._closed = True
        self.window.destroy()
    
    
    def update(self):
        if self._closed:
            return
        self.update_option_menu()
        if len(self.master.experiment.spectra) == 0:
            self.root.after(100, self.update)
            return
        
        if self.master.experiment.spectra[-1] != self.last_spectrum:
            self.update_plot()
        
        self.root.after(100, self.update)
     
        
    def update_plot(self):
        spec      = self.master.experiment.spectra[-1]
        selection = self.display_selection.get()
        option    = self.display_option.get()
        self.process_spectrum(spec, selection, option)
        self.redraw()
        self.last_spectrum = spec
    
    
    def reset_axlim(self):
        if (len(self.xdata) == 0 or 
            len(self.ydata) == 0):
            return
        self.ax.set_xlim(min(self.xdata)-0.5,
                         max(self.xdata)+2)
        
        if min(self.ydata) < 0:
            miny = 1.05*min(self.ydata)
        else:
            miny = 0.95*min(self.ydata)
            
        if max(self.ydata) < 0:
            maxy = 0.95*max(self.ydata)
        else:
            maxy = 1.05*max(self.ydata)
        
        self.ax.set_ylim(miny, maxy)
        return
    
    
    def redraw(self):
        '''
        Redraw figure with blitting
        '''
        # self.canvas.restore_region(self.bg)
        self.ln.set_data(self.xdata, self.ydata)
        self.ax.draw_artist(self.ln)
        # # self.ax.relim()
        # # self.ax.reset_ticks()
        # # self.canvas.blit(self.fig.bbox)
        self.canvas.draw_idle()
        # self.canvas.flush_events()
        
    
    
    def redraw_plot(self):
        '''
        Called in case of option change (i.e., plot something different)
        
        Redraw everything
        '''
        
        selection = self.display_selection.get()
        option    = self.display_option.get()
        
        self.xdata = []
        self.ydata = []
        self.ax.clear()
        
        for spectrum in self.master.experiment.spectra:
            
            self.process_spectrum(spectrum, selection, option)
            self.last_spectrum = spectrum
        
        self.ax.set_xlabel('Time/ s')
        self.ax.set_ylabel(f'{selection} @ {option}')
        
        self.fig.canvas.draw()
        self.ln, = self.ax.plot(self.xdata, self.ydata, animated=False)
        self.fig.tight_layout()
        
        # self.bg = self.canvas.copy_from_bbox(self.fig.bbox)
        self.ax.draw_artist(self.ln)
        # self.canvas.blit(self.fig.bbox)
        self.canvas.draw()
        
        
    def process_spectrum(self, spectrum, selection, option):
        '''
        Spectrum: ImpedanceSpectrum
        selection: one of '|Z|', 'Phase', 'Parameter', 'k'.
        option: a number (meaning a frequency) or string (corresponding
                to an EEC parameter)
        I.e. selection = '|Z|', option = 100.0: plot |Z|(100Hz) vs t
        '''
        
        # append time to xdata
        t = spectrum.timestamp
        self.xdata.append(t - self.master.experiment.spectra[0].timestamp)
        
        if selection in ('|Z|', 'phase'):
            idx, _ = nearest(spectrum.freqs, float(option))
            if selection == '|Z|':
                self.ydata.append(np.absolute(spectrum.Z[idx]))
            elif selection == 'phase':
                self.ydata.append(spectrum.phase[idx])
        else:
            print(f'{selection} not yet implemented')
            self.ydata.append(1)
        return
     

    def update_option_menu(self):
        freqs = list(self.master.waveform.freqs)
        if freqs is None:
            return
        if freqs == self.saved_freqs:
            return
        self.saved_freqs = list(freqs)
        self.display_option_menu.set_menu(freqs[0], *freqs)
        return
            
        
        
    def _display_menu_changed(self, option):
        self.redraw_plot()
    
    
    def _display_option_changed(self, value):
        self.redraw_plot()
        
        
        


if __name__ == '__main__':
    root = Tk()
    win = MonitorWindow(None, root)
    root.mainloop()
    root.quit()    












