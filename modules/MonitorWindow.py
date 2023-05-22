from tkinter import *
from tkinter.ttk import *
import tkinter as tk
import numpy as np
import time

import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

from .funcs import nearest
from .Fitter import circuit_params


plot_options = ['|Z|', 'Phase', 'Parameter', 'k']
xmaxes = [30, 60, 120, 300, 600, 1200] + [1800*i for i in range(1,200)]


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
        
        self.expt = self.master.experiment
        self.last_spectrum = None
        self.saved_freqs   = []
        self.saved_params  = {}
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
        self.update_option_menu()
        
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
        '''
        Called periodically by Tk root. Check if new data should be plotted
        '''
        if self._closed:
            return
        
        if self.expt != self.master.experiment:
            # In case user starts another time-series experiment
            # before closing this window, don't plot to this one
            return
        
        self.update_option_menu()
        if len(self.expt.spectra) == 0:
            # Recording hasn't started
            self.root.after(100, self.update)
            return
        
        if self.expt.spectra[-1] != self.last_spectrum:
            st = time.time()
            self.update_plot()
            t = time.time() - st
            # print(f'plot time: {t:0.3f} s')
        
        # Reschedule
        self.root.after(100, self.update)
     
        
    def update_plot(self):
        '''
        Append newest data point to plot. 
        '''
        spec      = self.expt.spectra[-1]
        selection = self.display_selection.get()
        option    = self.display_option.get()
        self.process_spectrum(spec, selection, option)
        self.redraw()
        self.last_spectrum = spec
    
    
    def process_spectrum(self, spectrum, selection, option):
        '''
        Extract the requested piece of information out of the spectrum
        
        Spectrum: ImpedanceSpectrum
        selection: one of '|Z|', 'Phase', 'Parameter', 'k'.
        option: a number (meaning a frequency) or string (corresponding
                to an EEC parameter)
        I.e. selection = '|Z|', option = 100.0: plot |Z|(100Hz) vs t
        '''
        
        # append time to xdata
        t = spectrum.timestamp
        self.xdata.append(t - self.expt.spectra[0].timestamp)
                
        if selection in ('|Z|', 'Phase'):
            idx, _ = nearest(spectrum.freqs, float(option))
            if selection == '|Z|':
                self.ydata.append(np.absolute(spectrum.Z[idx]))
            elif selection == 'Phase':
                self.ydata.append(spectrum.phase[idx])
            return
        
        if selection == 'Parameter':
            val = spectrum.fit[option]
            self.ydata.append(val)
            return
        
        else:
            # TODO: implement once fitting is working
            self.ydata.append(1)
        return
    
    
    def redraw(self):
        '''
        Redraw figure with blitting
        '''
        self.update_axlim() # Check if we need to adjust the axis limits
        
        self.canvas.restore_region(self.bg)
        self.ln.set_data(self.xdata, self.ydata)
        self.ax.draw_artist(self.ln)
        self.canvas.blit(self.fig.bbox)
        self.canvas.flush_events()
        
        
    def update_axlim(self):
        '''
        Check if we need to expand the axis limits. If so, redraw the figure
        and save the new background for blitting
        '''
        updated = False
        
        xlim = self.ax.get_xlim()
        ylim = self.ax.get_ylim()
        
        # Check if we need to extend x axis
        xmax = xlim[1]
        xmax_idx, _ = nearest(xmaxes, xmax)
        
        if self.xdata[-1] > 0.9*xmax:
            while self.xdata[-1] > 0.9*xmax:
                xmax_idx += 1
                xmax = xmaxes[xmax_idx]
            self.ax.set_xlim(0,xmaxes[xmax_idx])
            updated = True
        
        # Check if we need to zoom out of y axis
        if ( (min(self.ydata) <= ylim[0]) or 
             (max(self.ydata) >= ylim[1]) ):
            yrange = max(self.ydata) - min(self.ydata)
            if yrange == 0:
                yrange = self.ydata[0]
            
            ymax = max(self.ydata) + 0.3*yrange
            ymin = min(self.ydata) - 0.3*yrange
            
            self.ax.set_ylim(ymin, ymax)
            updated = True
        
        # Save new background
        if updated:   
            self._draw_blit()
    
        
    def _draw_blit(self):
        '''
        Draw figure and save its background
        '''
        self.fig.tight_layout()
        self.fig.canvas.draw()
        self.ln, = self.ax.plot(self.xdata, self.ydata, 'ko-', 
                                animated=True)
        self.bg = self.canvas.copy_from_bbox(self.fig.bbox)
        self.ax.draw_artist(self.ln)
        self.canvas.blit(self.fig.bbox)
        self.canvas.flush_events()
    
    
    def redraw_plot(self):
        '''
        Called in case of option change (i.e., plot something different)
        
        Also used to initialize plot. Redraw everything.
        '''
        
        selection = self.display_selection.get()
        option    = self.display_option.get()
        
        self.xdata = []
        self.ydata = []
        self.ax.clear()
        
        for spectrum in self.expt.spectra:
            
            self.process_spectrum(spectrum, selection, option)
            self.last_spectrum = spectrum
        
        self.ax.set_xlabel('Time/ s')
        self.ax.set_ylabel(f'{selection} @ {option}')
        
        if len(self.xdata) == 0:
            self._draw_blit()
            return
        self.update_axlim()
    

    def update_option_menu(self):
        '''
        Update the frequency or parameter selection dropdown menu
        '''
        if self.display_selection.get() in ('|Z|', 'Phase'):
            freqs = list(self.master.waveform.freqs)
            if freqs is None:
                return
            if freqs == self.saved_freqs:
                return
            self.saved_freqs = list(freqs)
            self.display_option_menu.set_menu(freqs[0], *freqs)
            return
        
        if self.display_selection.get() == 'Parameter':
            circuit = self.master.GUI.fit_circuit.get()
            params = list(circuit_params[circuit].keys())
            params.remove('_img')
            if params == self.saved_params:
                return
            self.saved_params = params
            self.display_option_menu.set_menu(params[0], *params)
            return
        
        if self.display_selection.get() == 'k':
            self.display_option_menu.set_menu('', *[''])
            return
            
        
    def _display_menu_changed(self, option):
        self.update_option_menu()
        self.redraw_plot()
    
    
    def _display_option_changed(self, value):
        self.redraw_plot()
        
        
        


if __name__ == '__main__':
    root = Tk()
    win = MonitorWindow(None, root)
    root.mainloop()
    root.quit()    












