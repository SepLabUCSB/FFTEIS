from tkinter import *
from tkinter.ttk import *
import tkinter as tk
import numpy as np
import time
from functools import partial

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
    def __init__(self, master, root, sensor_names=list):
        self.master = master
        self.root   = root
        self._closed = False
        
        self.expt = self.master.experiment
        self.last_spectrum = None
        self.last_selection= None
        self.xdata = {sensor_name:[] for sensor_name in sensor_names}
        self.ydata = {sensor_name:[] for sensor_name in sensor_names}
        
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
        
        Label(toprow, text='     ').grid(row=0, column=3, sticky=(W,E))
        
        self.ax_selection_option = StringVar()
        self.ax_selection_option_menu = OptionMenu(toprow, self.ax_selection_option,
                                                   '', *[''])
        self.ax_selection_option_menu.grid(row=0, column=4, sticky=(W,E))
        
        
        Button(toprow, text='Zoom in', command=self.zoom_in).grid(
            row=0, column=5, sticky=(W,E))
        Button(toprow, text='Zoom out', command=self.zoom_out).grid(
            row=0, column=6, sticky=(W,E))
        
        
        figframe = Frame(self.window)
        figframe.grid(row=1, column=0, sticky=(W,E))
        
        self.fig = plt.Figure(figsize=(5,4), dpi=80)
        self.generate_axes()
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
    
    
    def generate_axes(self):
        self.axes = {}
        self.lns  = {}
        keys = list(self.xdata.keys())
        n_axes = len(keys)
        if n_axes == 1:
            n_rows = n_cols = 1
        else:
            n_cols = -(-n_axes//2)
            n_rows = 2
        
        fig_width  = 5*n_cols
        fig_height = 3*n_rows
        self.fig.set_size_inches(fig_width, fig_height)
        
        # Generate the axes
        for i, key in enumerate(keys):
            ax = self.fig.add_subplot(n_rows, n_cols, i+1)
            self.axes[key] = ax
        
        self.fig.supxlabel('Time/ s')
        self.fig.supylabel('{selection} @ {option}')
        self.fig.tight_layout()
        
        self.ax_selection_option_menu.set_menu(keys[0], *keys)
        
            
                
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
        ax_key = [key for key in self.xdata.keys() if spec.name.startswith(key)][0]
        self.process_spectrum(ax_key, spec, selection, option)
        self.update_axlim(ax_key) # Check if we need to adjust the axis limits
        self._draw_blit(ax_key)
        self.last_spectrum = spec
    
    
    def process_spectrum(self, ax_key, spectrum, selection, option):
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
        self.xdata[ax_key].append(t - self.expt.spectra[0].timestamp)
                
        if selection in ('|Z|', 'Phase'):
            idx, _ = nearest(spectrum.freqs, float(option))
            if selection == '|Z|':
                self.ydata[ax_key].append(np.absolute(spectrum.Z[idx]))
            elif selection == 'Phase':
                self.ydata[ax_key].append(spectrum.phase[idx])
            return
        
        if selection == 'Parameter':
            try:
                val = spectrum.fit[option]
            except:
                val = 0
            self.ydata[ax_key].append(val)
            return
        
        if selection == 'k':
            if ('Rct' in spectrum.fit) and ('Cads' in spectrum.fit):
                val = 1/(2*spectrum.fit['Rct']*spectrum.fit['Cads'])
            else:
                val= 0
            self.ydata[ax_key].append(val)
        
        else:
            # TODO: implement once fitting is working
            self.ydata[ax_key].append(1)
        return
            
    
    def zoom_in(self):
        '''
        Zoom in y axis on given axes
        '''
        ax_key = self.ax_selection_option.get()
        self.axes[ax_key].y_lim_forced = True
        ymin, ymax = self.axes[ax_key].get_ylim()
        
        delta = ymax - ymin
        
        self.axes[ax_key].set_ylim(ymin + 0.1*delta,
                                   ymax - 0.1*delta)
        self._draw_blit(ax_key)
        return
        
    
    def zoom_out(self):
        '''
        Zoom out y axis on given axes
        '''
        ax_key = self.ax_selection_option.get()
        self.axes[ax_key].y_lim_forced = True
        ymin, ymax = self.axes[ax_key].get_ylim()
        
        delta = ymax - ymin
        
        self.axes[ax_key].set_ylim(ymin - 0.1*delta,
                                   ymax + 0.1*delta)
        self._draw_blit(ax_key)
        return
        
        
    def update_axlim(self, ax_key):
        '''
        Check if we need to expand the axis limits. If so, redraw the figure
        and save the new background for blitting
        '''
        updated = False
        
        xlim = self.axes[ax_key].get_xlim()
        ylim = self.axes[ax_key].get_ylim()
        
        # Check if we need to extend x axis
        xmax = xlim[1]
        xmax_idx, _ = nearest(xmaxes, xmax)
        
        if self.xdata[ax_key][-1] > 0.9*xmax:
            while self.xdata[ax_key][-1] > 0.9*xmax:
                xmax_idx += 1
                xmax = xmaxes[xmax_idx]
            self.axes[ax_key].set_xlim(0,xmaxes[xmax_idx])
            updated = True
        
        # Check if we need to zoom out of y axis
        if (not self.axes[ax_key].y_lim_forced) and ( 
                (min(self.ydata[ax_key]) <= ylim[0]) or 
                (max(self.ydata[ax_key]) >= ylim[1]) 
                ):
            yrange = max(self.ydata[ax_key]) - min(self.ydata[ax_key])
            if yrange == 0:
                yrange = self.ydata[ax_key][0]
            
            ymax = max(self.ydata[ax_key]) + 0.3*yrange
            ymin = min(self.ydata[ax_key]) - 0.3*yrange
            
            self.axes[ax_key].set_ylim(ymin, ymax)
            updated = True
        
        # Save new background
        if updated:   
            self._draw_blit(ax_key)
    
        
    def _draw_blit(self, ax_key):
        '''
        Draw figure and save its background
        '''
        self.fig.tight_layout()
        self.fig.canvas.draw()
        if ax_key not in self.lns:
            ln, = self.axes[ax_key].plot(self.xdata[ax_key], 
                                      self.ydata[ax_key], 'ko-', 
                                      animated=True)
            self.lns[ax_key] = ln
        else:
            self.lns[ax_key].set_data(self.xdata[ax_key], 
                                      self.ydata[ax_key])
        
        for key, ln in self.lns.items():
            self.axes[ax_key].draw_artist(ln)
        self.bg = self.canvas.copy_from_bbox(self.fig.bbox)
        self.canvas.blit(self.fig.bbox)
        self.canvas.flush_events()
    
    
    def redraw_plot(self):
        '''
        Called in case of option change (i.e., plot something different)
        
        Also used to initialize plot. Redraw everything.
        '''
        
        selection = self.display_selection.get()
        option    = self.display_option.get()
        
        for key in self.xdata.keys():
            self.redraw_axes(key, selection, option)
    
    
    def redraw_axes(self, ax_key, selection, option):
        
        self.xdata[ax_key] = []
        self.ydata[ax_key] = []
        
        self.axes[ax_key].clear()
        self.axes[ax_key].set_title(ax_key)
        self.axes[ax_key].y_lim_forced = False
        
        for spectrum in self.expt.spectra:
            if not ax_key in spectrum.name:
                continue
            self.process_spectrum(ax_key, spectrum, selection, option)
            self.last_spectrum = spectrum
        
        # self.axes[ax_key].set_xlabel('Time/ s')
        # self.axes[ax_key].set_ylabel(f'{selection} @ {option}')
        self.fig.supxlabel('Time/ s')
        self.fig.supylabel(f'{selection} @ {option}')
        
        if len(self.xdata[ax_key]) == 0:
            self._draw_blit(ax_key)
            return
        self.update_axlim(ax_key)
    

    def update_option_menu(self):
        '''
        Update the frequency or parameter selection dropdown menu
        '''
        
        # Don't update if the selection hasn't changed
        if self.display_selection.get() == self.last_selection:
            return
        self.last_selection = self.display_selection.get()
        
        if self.display_selection.get() in ('|Z|', 'Phase'):
            freqs = list(self.master.waveform.freqs)
            if freqs is None:
                return
            self.display_option_menu.set_menu(freqs[0], *freqs)
            return
        
        if self.display_selection.get() == 'Parameter':
            circuit = self.master.GUI.fit_circuit.get()
            params = list(circuit_params[circuit].keys())
            params.remove('_img')
            self.display_option_menu.set_menu(params[0], *params)
            return
        
        if self.display_selection.get() == 'k':
            self.display_option_menu.set_menu('-', *['-',])
            return
            
        
    def _display_menu_changed(self, option):
        self.update_option_menu()
        self.redraw_plot()
    
    
    def _display_option_changed(self, value):
        # self.update_option_menu()
        self.redraw_plot()
        
        
        


if __name__ == '__main__':
    root = Tk()
    win = MonitorWindow(None, root)
    root.mainloop()
    root.quit()    












