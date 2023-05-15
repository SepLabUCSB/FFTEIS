# Standard lib
import time
from datetime import datetime
import os
import sys
import traceback
from functools import partial
from tkinter import *
from tkinter.ttk import *
import tkinter as tk

# Requirements
import psutil
import pandas as pd
import numpy as np
import matplotlib
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import pyvisa  # Install NI-VISA separately
               # pip install pyvisa instead of pyvisa-py


# Local modules
import modules
from modules.Arb import Arb
from modules.Buffer import ADCDataBuffer
from modules.DataProcessor import DataProcessor
from modules.DataStorage import Experiment, ImpedanceSpectrum
from modules.Oscilloscope import Oscilloscope
from modules.Waveform import Waveform
from modules.funcs import nearest, run
from modules.gui_utils import ask_duration_popup, message_popup, confirm_dialog

default_stdout = sys.stdout
default_stdin  = sys.stdin
default_stderr = sys.stderr

plt.style.use('ffteis.mplstyle')
colors = plt.rcParams['axes.prop_cycle'].by_key()['color']

this_dir = modules.__file__[:-20]
update_file = os.path.join(this_dir, 'update.txt')



'''  
TODO:
- save metadata
    
- make new waveform interface    
- record by duration
- titration multiplexing
- invivo multiplexing

- x vs t plot

Tk input prompts disappear behind main window??
'''



class MasterModule():
    
    def __init__(self):
        self.willStop = False
        self.STOP = False
        self.ABORT = False
        self.modules = [self]
        
        self.experiment = Experiment() # Tracks current Experiment object
        self.waveform   = Waveform()   # Tracks waveform currently on Arb.
      
        
    def register(self, module):
        '''
        Register a submodule to master
        
        i.e. ADC --> master.ADC
             master.modules = [ADC, ...]
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
                
                
    def set_experiment(self, Experiment):
        self.experiment = Experiment
        return
    
    
    def check_connections(self):
        # Check that scope and arb are connected and turned on,
        # and that NOVA is running
        self.scope_connected = False
        self.arb_connected   = False
        if any(['SDS1' in rsc for rsc 
                in pyvisa.ResourceManager().list_resources()]):
            self.scope_connected = True
        if any(['DG8' in rsc for rsc 
                in pyvisa.ResourceManager().list_resources()]):
            self.arb_connected = True
        self.NOVA_connected = False
        for p in psutil.process_iter():
            if 'Nova.exe' in p.name():
                self.NOVA_connected = True
                break
        
        if not self.scope_connected:
            print('Oscilloscope not found! Make sure SDS1202X-E is powered on and connected to PC.')
        if not self.arb_connected:
            print('Waveform generator not found! Make sure Rigol DG812 is powered on and connected to PC.')
        if not self.NOVA_connected:
            print('NOVA not detected! Make sure Nova is running.')
        
        if (self.scope_connected and self.arb_connected and self.NOVA_connected):
            return True
        return False    
        
                
    
    

 
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
        self.last_spectrum = None
        
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
        self.ax2 = self.ax.twinx()
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
        self.master.check_connections()
        Label(topleft, text='Oscilloscope: ').grid(column=0, row=0, sticky=(E))
        Label(topleft, text='Connected' if self.master.scope_connected else 'NOT CONNECTED').grid(
            column=1, row=0)
        Button(topleft, text='STOP', command=self.stop_button).grid(
            column=2, row=0, sticky=(W,E))
        Label(topleft, text='Func. Gen: ').grid(column=0, row=1, sticky=(E))
        Label(topleft, text='Connected' if self.master.arb_connected else 'NOT CONNECTED').grid(
            column=1, row=1)
        Button(topleft, text='Setup Oscilloscope', command=self.setup_scope).grid(
            column=2, row=1, sticky=(E))
        
        # Waveform selection dropdown
        waveforms = [f.replace('.csv', '') for f in os.listdir('waveforms')
                     if f != 'reference']
        waveforms.sort(key=lambda s: [float(x) for x in s.split('_')[:-1]])
        Label(topleft, text='Waveform: ').grid(column=0, row=2, sticky=(E))
        self.waveform_selection = StringVar(topleft)
        self.waveformMenu = OptionMenu(topleft, self.waveform_selection, 
            waveforms[0], *waveforms, command=self.show_waveform)
        self.waveformMenu.grid(column=1, row=2, sticky=(E,W))
        Button(topleft, text='Apply Waveform', command=self.apply_waveform).grid(
            column=2, row=2, sticky=(E,W))
        
        
        # Record... Buttons
        Button(topleft, text='Record Reference', command=self.record_reference).grid(
            column=0, row=3, sticky=(E))
        Button(topleft, text='Record Spectrum', command=self.record_single).grid(
            column=1, row=3, sticky=(W,E))
        Button(topleft, text='Record for...', command=self.record_duration).grid(
            column=2, row=3, sticky=(E,W))
        
        
        # Save as button
        Button(topleft, text='Save last...', command=self.save_last_as).grid(
            column=0, row=4, sticky=(W,E))
        # Multiplex buttons
        Button(topleft, text='Multiplex titration', command=self.multiplex_titration).grid(
            column=1, row=4, sticky=(W,E))
        Button(topleft, text='Multiplex in-vivo', command=self.multiplex_invivo).grid(
            column=2, row=4, sticky=(E,W))
        
        
        
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
        
                                                    
        Button(topright, text='Create New Waveform', command=
               self.create_new_waveform).grid(column=0, row=4,
                                              columnspan=2, sticky=(W,E))
                              
        
        ###############################
        #####     END __INIT__    #####  
        ###############################
        
    def stop_button(self):    
        self.master.ABORT = True
        return
    
                                                    
    def update_plot(self):
        '''
        Called periodically (every 50 ms) by Tk GUI. Checks if a new
        spectrum has been recorded, and if so, plots it to the figure.
        '''
        if self.master.experiment.spectra:
            if self.master.experiment.spectra[-1] != self.last_spectrum:
                self.last_spectrum = self.master.experiment.spectra[-1]
                freqs = self.last_spectrum.freqs
                Z     = self.last_spectrum.Z
                phase = self.last_spectrum.phase
                
                Z = abs(Z)
                
                # Plot |Z| and phase
                self.ax.set_xscale('linear')
                self.ax.clear()
                self.ax2.clear()
                self.ax2.plot(freqs, phase, 'o-', color='orange')
                self.ax.plot(freqs, Z, 'o-', color=colors[0])
                
                # Set axis labels
                self.ax.set_xlabel('Frequency/ Hz')
                self.ax.set_ylabel(r'|Z|/ $\Omega$', color=colors[0])
                self.ax2.set_ylabel(r'Phase/ $\degree$', color='orange')
                self.ax2.yaxis.set_label_position('right')
                
                # Set ticks and axis limits
                self.ax.set_ylim(min(Z)-1.05*min(Z), 1.05*max(Z))
                self.ax.set_xscale('log')
                self.ax2.set_ylim(min(phase)-5, max(phase)+5)
                self.ax2.set_yticks([-180, -150, -120, -90, -60, -30, 0,
                                     30, 60, 90, 120, 150, 180])
                self.ax2.set_ylim(min(phase)-10, max(phase)+10)
                self.ax.set_xticks([1e-1,1e0,1e1,1e2,1e3,1e4,1e5,1e6])
                self.ax.set_xlim(0.7*min(freqs), 1.5*max(freqs))
                
                # Draw it
                self.fig.tight_layout()
                self.canvas.draw_idle()
        
        # Schedule next check
        self.root.after(10, self.update_plot)
        return
    
    
    def update_waveform_dropdown(self):
        '''
        Update list of waveforms in dropdown menu
        '''
        waveforms = [f.replace('.csv', '') for f in os.listdir('waveforms')
                     if f != 'reference']
        waveforms.sort(key=lambda s: [float(x) for x in s.split('_')[:-1]])
        
        self.waveformMenu.set_menu(waveforms[0], *waveforms)
        return
    
                                                    
    def show_waveform(self, waveform):
        '''
        Triggered by selecting a new waveform from the dropdown. Show its
        frequency domain representation in the display
        '''
        waveform_file = f'waveforms/{waveform}.csv'
        wf = Waveform()
        wf.from_csv(waveform_file)
        self.ax.set_xscale('linear')
        self.ax.clear()
        self.ax2.clear()
        wf.plot_to_ax(self.ax)
        self.fig.tight_layout()
        self.canvas.draw_idle()
        return
    
        
    def apply_waveform(self):
        '''
        Send waveform data to arbitrary waveform generator. 
        '''
        waveform = self.waveform_selection.get()
        mVpp     = self.amplitude_input.get('1.0', 'end')
        
        try:
            Vpp = 2*float(mVpp)/1000 # Arb output gets divided by 2 on Autolab input
        except:
            print('Invalid amplitude input! Check for erronous letters or spaces')
        
        waveform_file = f'waveforms/{waveform}.csv'
        wf = Waveform()
        wf.from_csv(waveform_file)
        
        self.master.Arb.send_waveform(wf, Vpp)
        self.master.waveform = wf
        self.master.DataProcessor.load_correction_factors()
        return
    
    
    def setup_scope(self):
        '''
        Do oscilloscope autocentering
        '''
        self.master.Oscilloscope.autocenter_frames()
        return
    
    
    def record_reference(self):
        '''
        Record and save a "reference" spectrum of a resistor with
        a known resistance. This can be used to correct for filtering
        artefacts in subsequent experiments.
        '''
        if self.ref_correction_bool.get():
            print('Uncheck "Apply Reference Correction" before\n'+
                  'recording a reference spectrum!\n')  
            return
        
        R = tk.simpledialog.askstring('Calibration', 'Resistance:')
        if not R:
            return
        
        # Do it in another thread
        run( partial(self._record_reference, R) )
        return
    
    def _record_reference(self, R):
        R = R.replace('k', '000')
        R = R.replace('M', '000000')
        try:
            R = float(R)
        except:
            print('Invalid resistance entry!')
            return
        
        self.master.set_experiment(Experiment(name='reference'))
        self.master.experiment.set_waveform(self.master.waveform)
        
        # Record 5 spectra
        for _ in range(5):
            self.master.Oscilloscope.record_frame()
        spectra = self.master.experiment.spectra
        
        # Average them together
        avg_spectrum = spectra[0].average(spectra[1:])
        Z     = np.absolute(avg_spectrum.Z)
        phase = avg_spectrum.phase
        
        # Calculate correction factors and save locally
        Z_correction     = Z/R
        phase_correction = phase
        
        df = pd.DataFrame({'freqs': spectra[0].freqs,
                           'Z_factor': Z_correction,
                           'phase_factor': phase_correction})
        
        date = datetime.now().strftime('%Y-%m-%d')
        name = self.master.experiment.waveform.name()
        out_file = f'waveforms/reference/{date}-{name}-{R}Ohm.csv'
        df.to_csv(out_file, index=False)        
        
        # Update DataProcessor with new reference
        self.master.DataProcessor.load_correction_factors()        
        return
    
    
    def record_single(self):
        '''
        Record a single impedance spectrum
        '''
        self.master.set_experiment(Experiment())
        self.master.experiment.set_waveform(self.master.waveform)
        run(self.master.Oscilloscope.record_frame)
        return
    
    
    def record_duration(self):
        '''
        Record for a user-inputted duration
        '''
        t = ask_duration_popup()
        if t <= 0:
            return
        
        name = tk.simpledialog.askstring('Save As', 'Input save name: ')
        if not name:
            return
        
        self.master.set_experiment(Experiment(name=name))
        self.master.experiment.set_waveform(self.master.waveform)
        run(partial(self.master.Oscilloscope.record_duration, t) )
        return
    
    
    def save_last_as(self):
        name = tk.simpledialog.askstring('Save As', 'Input save name: ')
        if not name:
            return
        temp_expt = Experiment(name)
        temp_expt.set_waveform(self.master.experiment.waveform)
        for spectrum in self.master.experiment.spectra:
            spectrum.experiment = temp_expt
            temp_expt.append_spectrum(spectrum)
        return
    
    
    def multiplex_titration(self):
        '''
        Do a titration-type experiment. Cycle between several sensors then wait,
        prompt user to adjust the solution concentration and input the new value
        '''
        
        # Get number of sensors
        self.root.attributes('-topmost', 0)
        n_sensors = tk.simpledialog.askinteger('Sensors to multiplex', 'Input number of sensors to toggle between: ')
        if not n_sensors > 0:
            return
        
        sensors = tk.simpledialog.askstring('Sensor names', 'Input labels for each sensor (comma separated): ',
                                            initialvalue= ','.join([str(i) for i in range(n_sensors)]))
        sensors = sensors.split(',')
        if len(sensors) != n_sensors:
            print(f'Could not identify {n_sensors} names in input string: {sensors}')
            return
        # Ask for recording frames per sensor
        nframes = tk.simpledialog.askinteger('Averaging', 'Average over frames: ',
                                              initialvalue=5)
        if nframes < 1:
            return
        
        # Ask for save name
        name = tk.simpledialog.askstring('Save As', 'Input save name: ')
        if not name:
            return
        
        if os.path.exists(update_file):
            os.remove(update_file)
        
        # TODO: prompt user to set up NOVA protocol correctly. calculate frame time
        
        # Setup autosave experiment
        self.master.set_experiment(Experiment())
        self.master.experiment.set_waveform(self.master.waveform)
        
        # Setup Experiment with averaged results
        expt = Experiment(name=name)
        expt.set_waveform(self.master.waveform)
        
        # iterate through 
        self.multiplex_done = False
        i = 0
        
        def _multiplex(i, conc):
            # Wait for Autolab trigger
            while not os.path.exists(update_file):
                if self.master.ABORT:
                    self.master.ABORT = False
                    return
                time.sleep(0.01)
            
            
            # Record n frames
            for _ in range(nframes):
                if self.master.ABORT:
                    self.master.ABORT = False
                    return
                self.master.Oscilloscope.record_frame()
            
            sensor = sensors[i%len(sensors)]
            fname = f'{sensor}_{conc}.txt'
            
            spectra  = self.master.experiment.spectra[-nframes:]
            avg      = spectra[0].average(spectra[1:])
            avg.name = fname 
            expt.append_spectrum(avg)
            self.multiplex_done = True
        
        while True:
            # User inputs concentration. Cancel ends experiment
            if not self.multiplex_done:
                continue
            self.multiplex_done = False
            
            conc = tk.simpledialog.askstring('Next concentration', 'Input next concentration (cancel ends experiment): ')
            if not conc:
                break
            
            run(partial(_multiplex, i, conc))
            
            i += 1
            
        return
    
    
    def multiplex_invivo(self):
        '''
        Continuously cycle between several sensors for a user-defined duration.
        
        Timing is dictated by Autolab creating designated update file,
        which triggers scope recording here
        '''
        
        # Ask user for time, # of sensors, sensor labels
        t = ask_duration_popup()
        if not t > 0:
            return
        
        n_sensors = tk.simpledialog.askinteger('Sensors to multiplex', 'Input number of sensors to toggle between: ')
        if not n_sensors > 0:
            return
        
        sensors = tk.simpledialog.askstring('Sensor names', 'Input labels for each sensor (comma separated): ',
                                            initialvalue= ','.join([str(i) for i in range(n_sensors)]))
        sensors = sensors.split(',')
        if len(sensors) != n_sensors:
            print(f'Could not identify {n_sensors} names in input string: {sensors}')
            return
        
        name = tk.simpledialog.askstring('Save As', 'Input save name: ')
        if not name:
            return
        
        if os.path.exists(update_file):
            os.remove(update_file)
        message_popup('Ready to go.\nMake sure NOVA multiplexing protocol is configured for the correct number of sensors.\nClick "OK" before running NOVA program.')
        
        self.master.set_experiment(Experiment(name=name))
        self.master.experiment.set_waveform(self.master.waveform)
        

        def _multiplex():
            st = time.time()
            i = 0
            while time.time() - st < t:
                if self.master.ABORT:
                    print('Stopping multiplex experiment')
                    self.master.ABORT = False
                    return
                
                # Wait for NOVA to create trigger file indicating new electrode
                # has been selected
                while not os.path.exists(update_file):
                    continue
                
                
                # Find correct label
                this_sensor = sensors[i%len(sensors)]
                idx = i//len(sensors)
                
                # Do recording
                fname = f'{this_sensor}_{idx:06}.txt'
                self.master.Oscilloscope.record_frame(name=fname)   
                
                os.remove(update_file)
                
                i += 1
        
        run(_multiplex)

        return
    
    
    def create_optimized_waveform(self):
        '''
        Use the previous spectrum/ spectra to generate a
        new waveform with "optimized" amplitudes
        '''
        spectra = self.master.experiment.spectra
        if len(spectra) == 0:
            print('No previous spectra to create optimized waveform from!')
            return
        
        if len(spectra) > 1:
            #Average them all together
            avg_spectrum = spectra[0].average(spectra[1:]) 
        else:
            avg_spectrum = spectra[0]
        
        
        # Normalized, optimized amplitudes
        # Proportional to sqrt(Z)
        Z = np.sqrt(np.absolute(avg_spectrum.Z))       
        amps = Z/max(Z)
        
        base_wf = self.master.experiment.waveform
        opt_wf  = Waveform(freqs  = base_wf.freqs,
                           phases = base_wf.phases,
                           amps   = amps)
        opt_wf.to_csv()        
        self.update_waveform_dropdown()        
        return
    
    
    def create_new_waveform(self):
        '''
        Make popup that prompts user for starting frequency,
        ending frequency, and number of frequencies. Then generate
        a new waveform and save it to the waveforms directory
        '''
        popup = Toplevel()
        popup.title('Make New Waveform')
        popup.attributes('-topmost', 1)
        
        frame = Frame(popup)
        frame.grid(row=0, column=0)
        
        f_0 = 10
        f_1 = 1000
        n_freqs = 14        
        
        Label(frame, text='Starting frequency (Hz): ').grid(
            column=0, row=0, sticky=(E))
        self._f_0 = Text(frame, height=1, width=6)
        self._f_0.insert('1.0', f_0)
        self._f_0.grid(column=1, row=0, sticky=(W,E))
        
        Label(frame, text='Ending frequency (Hz): ').grid(
            column=0, row=1, sticky=(E))
        self._f_1 = Text(frame, height=1, width=6)
        self._f_1.insert('1.0', f_1)
        self._f_1.grid(column=1, row=1, sticky=(W,E))
        
        Label(frame, text='Number of frequencies: ').grid(
            column=0, row=2, sticky=(E))
        self._n_freqs = Text(frame, height=1, width=6)
        self._n_freqs.insert('1.0', n_freqs)
        self._n_freqs.grid(column=1, row=2, sticky=(W,E))
        
        def _generate():
            f_0 = self._f_0.get('1.0', 'end')
            f_1 = self._f_1.get('1.0', 'end')
            n_freqs = self._n_freqs.get('1.0', 'end')
            try:
                f_0 = float(f_0)
                f_1 = float(f_1)
                n_freqs = int(n_freqs)
            except:
                print('Invalid inputs')
                return
            wf = Waveform()
            wf.generate(f_0, f_1, n_freqs)
            wf.to_csv()
            print(f'Generated {wf.name()}')
            self.update_waveform_dropdown()
            popup.destroy()
            return
        
        Button(frame, text='Generate', command=_generate).grid(
            column=0, row=3, columnspan=2, sticky=(W,E))
        
        popup.mainloop()
        popup.quit()
        
        return
        
                

    
    



if __name__ == '__main__':
    
    master = MasterModule()
    
    # if not master.check_connections():
    #     input('Press enter to exit')
    #     sys.exit()
    
    # Load submodules
    arb             = Arb(master)
    buffer          = ADCDataBuffer()
    dataProcessor   = DataProcessor(master, buffer)
    oscilloscope    = Oscilloscope(master, buffer)
    
    run(master.run)
    run(dataProcessor.run)
    
    root = Tk()
    try:
        gui = GUI(root, master)
        
        root.after(1000, gui.update_plot)
        root.mainloop()
        root.quit()
        gui.willStop = True
        
    except Exception as e:
        sys.stdout = default_stdout
        sys.stdin  = default_stdin
        sys.stderr = default_stderr
        print(traceback.format_exc())
    
    gui.willStop = True
    sys.stdout = default_stdout
    sys.stdin  = default_stdin
    sys.stderr = default_stderr
    
    
    











