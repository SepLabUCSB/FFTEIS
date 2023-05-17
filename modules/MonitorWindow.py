from tkinter import *
from tkinter.ttk import *
import tkinter as tk

import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg




plot_options = ['|Z|', 'Phase', 'Parameter', 'k']



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
        
        self.last_spectrum = None
        self.xdata = []
        self.ydata = []
        
        self.window = Toplevel()
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
        
    
    def update(self):
        print('called Monitor.update()')
        if len(self.master.experiment.spectra) == 0:
            self.root.after(100, self.update)
            return
        
        if self.master.experiment.spectra[-1] != self.last_spectrum:
            self.update_plot()
        
        self.root.after(100, self.update)
     
    def update_plot(self):
        # Get newest spectrum from master
        
        
    def _display_menu_changed(self, option):
        pass
    
    
    def _display_option_changed(self, value):
        pass
        
        
        


if __name__ == '__main__':
    root = Tk()
    win = MonitorWindow(None, root)
    root.mainloop()
    root.quit()    












