import tkinter as tk
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import os
import sys
import time
from datetime import date, datetime
from array import array
import pyvisa
from EIS_Control import rigol_control, siglent_control, create_waveform
from EIS_Fit import EIS_fit
default_stdout = sys.stdout
default_stdin  = sys.stdin
default_stderr = sys.stderr


this_dir = rigol_control.__file__[:-16]


# Find dir with waveforms
rigol_waves = os.path.join(this_dir, 'waveforms')


# Get matplotlib style sheet and color cycle
plt.style.use(os.path.join(this_dir[:-13], 'scientific.mplstyle'))
colors = plt.rcParams['axes.prop_cycle'].by_key()['color']


'''
To add:

Real time fitting

'''



##### Create log file #####

LOGGING = False

log_file = 'C:/Users/BRoehrich/Desktop/log.txt'

def log(file, text):
    if text != '\n' and text != '' and LOGGING:
        with open(file, 'a') as f:
            t = str(datetime.now().time())
            f.write(t + '\t' + text + '\n')
            f.close()

            
            
##### PrintLogger class #####

class PrintLogger(): 
    # Class to print console output into Tkinter window
    def __init__(self, textbox): # pass reference to text widget
        self.textbox = textbox # keep ref

    def write(self, text):
        log(log_file, text)
        self.textbox.insert(tk.END, text) # write text to textbox
        self.textbox.see('end') # scroll to end

    def flush(self): # needed for file like object
        pass



##### MainWindow class #####

class MainWindow:
    
    global this_dir, rigol_waves
    
    def __init__(self, root):
        self.root = root
        root.title("Arb/ Scope control")
        root.attributes('-topmost', 1)
        root.attributes('-topmost', 0)    

        self.rm = pyvisa.ResourceManager()
        self.ft = None
            
        
        # Initialize frames and canvas
        
        # frame: upper left
        self.frame = tk.Frame(self.root)
        self.frame.grid(row=0, column = 0)
        
        # frame2: upper right
        self.frame2 = tk.Frame(self.root)
        self.frame2.grid(row=0, column = 1)
        
        # frame3: lower right (console output)
        self.frame3 = tk.Frame(self.root)
        self.frame3.grid(row=1, column=1)
        self.frame3.pack_propagate(0)
        
        # console printout to frame3
        self.console = tk.Text(self.frame3, width=50, height=25)
        self.console.grid(row=0, column=0)
        pl = PrintLogger(self.console)
        sys.stdout = pl
       
        # fig: lower left
        self.fig = plt.Figure(figsize=(5,4), dpi=100)
        self.ax  = self.fig.add_subplot(111)
        self.ax2 = self.ax.twinx()
        self.ax2.set_yticks([])
                
        self.canvas = FigureCanvasTkAgg(self.fig, master=root)
        self.canvas.get_tk_widget().grid(row=1, column=0)
        
        # Other vars to initialize
        self.last_file_name = ''
        self.test_mode = False
        
        
        
        #################################################
        ### FRAME 1: Instrument selection and control ###
        #################################################
        
        # Potentiostat selection
        text = tk.Label(self.frame, text='Potentiostat:')
        text.grid(row=1, column=1)
        self.potentiostat = tk.StringVar(self.frame)
        self.potentiostat.set('Autolab')
        self.potentiostat_selector = tk.OptionMenu(self.frame, self.potentiostat,
                                                   *['Gamry', 'Autolab'])
        self.potentiostat_selector.grid(row=1, column=2)
        
        
        
        # Waveform selection dropdown menu
        text = tk.Label(self.frame, text='Waveform:')
        text.grid(row=2, column=1)
        self.file_list = [file for file in os.listdir(rigol_waves) 
                          if file.endswith('freqs.csv')
                          if file.startswith('Rigol')]
        
        self.waveform = tk.StringVar(self.frame)
        self.waveform.set(self.file_list[4])
        self.waveform_selector = tk.OptionMenu(self.frame, self.waveform, 
                                               *self.file_list, command=self.show_waveform)
        self.waveform_selector.grid(row=2, column=2)

                
        
        # VISA selection menu: Arb
        try:
            text = tk.Label(self.frame, text='Arb:')
            text.grid(row=3, column=1)
            self.arb = tk.StringVar(self.frame)
            
            try:
                # Look for Rigol arb, i.e.
                # 'USB0::0x1AB1::0x0643::DG8A232302748::INSTR'
                default_arb = [inst for inst in self.rm.list_resources() 
                                if len(inst.split('::')) > 3 
                                and inst.split('::')[3].startswith('DG')][0]
            
            except:
                default_arb = ''
            
            self.arb.set(default_arb)
            self.arb_selector = tk.OptionMenu(self.frame, self.arb, 
                                                   *self.rm.list_resources())
            self.arb_selector.grid(row=3, column=2)
            self.apply_waveform_button = tk.Button(self.frame, text='Apply Wave', 
                                                   command=self.apply_waveform)
            self.apply_waveform_button.grid(row=3, column=3)
            
        except:
            # If no instrument connected, no button
            self.test_mode = True
            pass
        
        
        
        # VISA selection menus: Scope
        try:
            text = tk.Label(self.frame, text='Scope:')
            text.grid(row=4, column=1)
            self.scope = tk.StringVar(self.frame)
            
            try:
                default_scope = [inst for inst in self.rm.list_resources() 
                                if len(inst.split('::')) > 3 
                                and inst.split('::')[3].startswith('SDS')][0]
            
            except:
                default_scope = ''
            
            self.scope.set(default_scope)
            self.scope_selector = tk.OptionMenu(self.frame, self.scope, 
                                                   *self.rm.list_resources())
            self.scope_selector.grid(row=4, column=2)
        except:
            pass
        
        
        
        # Record, save buttons
        self.record_signals_button = tk.Button(self.frame, text='Record Signals', 
                                               command=self.record_signals)
        self.record_signals_button.grid(row=4, column=3)
        
        
        self.record_reference_button = tk.Button(self.frame, text='Record Reference', 
                                               command=self.record_reference)
        self.record_reference_button.grid(row=5, column=1)
        
        
        self.save_button = tk.Button(self.frame, text='Save last measurement', 
                                                   command=self.save_last)
        self.save_button.grid(row=5, column=2, columnspan=1)
        

        self.record_save_button = tk.Button(self.frame, text='Record and save', 
                                                   command=self.record_and_save)
        self.record_save_button.grid(row=5, column=3, columnspan=2)
        
        
        
        # Plot Z, phase toggles
        self.plot_Z = tk.IntVar(value=1)
        self.plot_Z_option = tk.Checkbutton(self.frame, text='|Z|', 
                                                variable=self.plot_Z)
        self.plot_Z_option.grid(row=6, column=1)
        
        
        self.plot_phase = tk.IntVar(value=1)
        self.plot_phase_option = tk.Checkbutton(self.frame, text='Phase', 
                                                variable=self.plot_phase)
        self.plot_phase_option.grid(row=6, column=2)
        
        
        
        
        
        ########################################
        ### FRAME 2: User-adjustable options ###
        ########################################
        

        # Applied waveform amplitude
        text = tk.Label(self.frame2, text='Waveform Vpp (mV):')
        text.grid(row=0, column = 0)
        self.waveform_vpp = tk.Text(self.frame2, height=1, width=7)
        self.waveform_vpp.insert('1.0', '20')
        self.waveform_vpp.grid(row=0, column=1)
        
        
        
        # Recording duration
        text = tk.Label(self.frame2, text='Recording time (s):')
        text.grid(row=1, column = 0)
        self.recording_time = tk.Text(self.frame2, height=1, width=7)
        self.recording_time.insert('1.0', '10')
        self.recording_time.grid(row=1, column=1)
        
        
        
        # Potentiostat current range
        text = tk.Label(self.frame2, text='Current range:')
        text.grid(row=2, column = 0)
        self.current_range = tk.Text(self.frame2, height=1, width=7)
        self.current_range.insert('1.0', '1e-6')
        self.current_range.grid(row=2, column=1)
        
        
        
        # DC Voltage offset
        text = tk.Label(self.frame2, text='DC Voltage (V):')
        text.grid(row=3, column = 0)
        self.DC_offset = tk.Text(self.frame2, height=1, width=7)
        self.DC_offset.insert('1.0', '0.0')
        self.DC_offset.grid(row=3, column=1)
        
        self.DC_offset_button = tk.Button(self.frame2, 
                                              text='Apply offset', 
                                              command=self.apply_offset)
        self.DC_offset_button.grid(row=3, column=2)
        
        
        
        # Apply calibration correction
        text = tk.Label(self.frame2, text='Apply reference correction:')
        text.grid(row=4, column = 0)
        self.ref_corr_val = tk.Text(self.frame2, height=1, width=7)
        self.ref_corr_val.insert('1.0', '10k')
        self.ref_corr_val.grid(row=4, column=1)
        
        self.ref_corr_var = tk.IntVar(value=1)
        self.ref_corr_option = tk.Checkbutton(self.frame2, 
                                              variable=self.ref_corr_var)
        self.ref_corr_option.grid(row=4, column=2)
        
        
        
        # Create waveform from result
        self.make_waveform_button = tk.Button(self.frame2, 
                                              text='Create waveform from last measurement', 
                                              command=self.make_waveform)
        self.make_waveform_button.grid(row=5, column=0, columnspan=2)
        
        
        
        
        # Save options
        
        self.fit = tk.IntVar(value=0)
        self.fit_option = tk.Checkbutton(self.frame2, text='Fit', 
                                                variable=self.fit)
        self.fit_option.grid(row=6, column=0)
        
        
        
        
        self.circuit = tk.StringVar(self.frame2)
        self.circuit.set('RRC')
        self.circuit_selector = tk.OptionMenu(self.frame2, self.circuit,
                                                   *['RRC', 'Randles_adsorption'])
        self.circuit_selector.grid(row=6, column=1, columnspan=2)
                
            
    def get_units(self, n):    
        if n >= 1e-6 and n < 1e-3:
            return ('u', 1e-6)
        
        if n >= 1e-3 and n < 0:
            return ('m', 1e-3)
        
        if n >= 0 and n <= 1000:
            return ('', 1)
        
        if n > 1e3 and n <= 1e6:
            return ('k', 1e3)
        
        if n > 1e6:
            return ('M', 1e6)    
    
    
    
    def make_waveform(self):
        if not self.ft:
            print('No previous scan. Record data then try again')
            return
        
        # Get current waveform's phases from f_.csv file
        waveform = self.ft[0].waveform
        phase_file = 'f' + waveform[10:]
        phase_file = os.path.join(rigol_waves, phase_file)
        
        df = pd.read_csv(phase_file, skiprows=1, names=('index', 'f', 'phase'))
        phases = df['phase'].to_numpy()
        
        # Get |Z| and f from previous data set
        Z     = self.ft[0].Z
        freqs = self.ft[0].freqs
        
        # Average Z over all frames
        for i in self.ft:
            Z = np.mean(np.array([Z, self.ft[i].Z]), axis=0)
            
        amps = np.sqrt(np.absolute(Z))
        
        # Create new waveform
        S, fname = create_waveform.Rigol_waveform(freqs, phases, 
                                    sample_freq=100000, total_time=1, 
                                    amax = 1, amps= amps, save_path = rigol_waves)
        
        # Display the new waveform
        self.show_waveform(new_waveform = S)
        
        
        # Reinitialize file selection list to incude new file
        self.file_list = [file for file in os.listdir(rigol_waves) 
                          if file.endswith('freqs.csv')
                          if file.startswith('Rigol')]
        
        del self.waveform_selector
        self.waveform_selector = tk.OptionMenu(self.frame, self.waveform, 
                                               *self.file_list, command=self.show_waveform)
        self.waveform_selector.grid(row=2, column=2)
        print('\n')
    
    
    
    def show_waveform(self, selection=None, new_waveform=None):
        # Plot currently selected waveform
        try:
            if len(new_waveform) > 0:
                s = new_waveform
        
        except:
            file = os.path.join(rigol_waves, self.waveform.get())
            df = pd.read_csv(file, skiprows=9, names=('x', 'V'))
            s = df['V'].to_numpy()
        
        self.ax.set_xscale('linear')
        self.ax.clear()
        self.ax2.clear()
        self.ax2.set_yticks([])
        self.ax.plot(100000*np.fft.rfftfreq(len(s)), 
                     np.abs(np.fft.rfft(s)))
        self.ax.set_xlabel('Frequency/ Hz')
        self.ax.set_ylabel('Amplitude')
        self.ax.set_xscale('log')
        self.fig.tight_layout()
        self.canvas.draw_idle()
        
        
    
    
    def apply_waveform(self):
        # Send currently selected waveform to Arb
        file = os.path.join(rigol_waves, self.waveform.get())    
        df = pd.read_csv(file, skiprows=9, names=('x', 'V'))    
        signal = df['V'].to_numpy()
        
        inst = self.rm.open_resource(self.arb.get())
        
        Vpp = self.waveform_vpp.get('1.0', 'end')
        Vpp = str(float(Vpp)/1000)
        
        try:
            inst.write('*RST')
            rigol_control.apply_waveform(inst, 1, signal, Vpp)
        except:
            print('Could not connect')
            pass
    
    
    
    def apply_offset(self):
        
        try:
            # Connect to scope
            inst = self.rm.open_resource(self.scope.get())
                 
            # Set scope parameters
            # inst.write('C1:VDIV 5mV')
            # inst.write('C1:OFST %s' %self.DC_offset.get('1.0', 'end'))
            
            inst.write('TRMD AUTO')
            
        
        except:
            # No instrument connected
            pass
        


    def record_signals(self, save=False):
        
        plot_Z     = self.plot_Z.get()
        plot_phase = self.plot_phase.get()
        
        self.ax.set_xscale('linear')
        self.ax.clear()
        self.ax.set_xscale('linear')
        self.ax2.clear()
        
        # line1: Z data
        # line2: phase data
        # line3: Z fit
        # line4: phase fit
        line1, = self.ax.plot([],[], 'o', color=colors[0])
        line2, = self.ax2.plot([],[], 'x', color=colors[1])
        line3, = self.ax.plot([],[], '-', color=colors[0])
        line4, = self.ax2.plot([],[], '-', color=colors[1])
               
        
        self.ax.set_xscale('log')
        self.ax.set_xlabel('Frequency/ Hz')
        self.fig.tight_layout()
        self.canvas.draw_idle()
        
        
        
        # Get waveform correction factors
        if self.ref_corr_var.get():
            # Path
            ref_dir = os.path.join(this_dir, 'reference waveforms\\')
            
            # Resistance
            R = self.ref_corr_val.get('1.0', 'end')
            R = R[:-1]
            
            # Waveform
            waveform = self.waveform.get()
            
            if waveform.split('_')[1] == 'opt':
                # Use same correction factors for optimized waveform as
                # for unoptimized
                waveform = waveform.split('_')
                del waveform[1]
                waveform = '_'.join(waveform)
            
            
            # Put it all together and get corrections
            fname = 'REF_%s_%s'%(R, waveform)
            file = os.path.join(ref_dir, fname)
            
            try:
                corr_df = pd.read_csv(file, skiprows=1, names=('freqs', 
                                                               'Z_corr', 
                                                               'phase_corr')
                                      )
                
                Z_corr = corr_df['Z_corr'].to_numpy()
                phase_corr = corr_df['phase_corr'].to_numpy()
            
            except:
                print('Invalid reference file: ')
                print(file)
                print('Uncheck "Apply reference correction" or record a')
                print('reference spectrum of a resistor.\n')
                return
                
            
            
        # Get recording time
        t = self.recording_time.get('1.0', 'end')
        current_range = self.current_range.get('1.0', 'end')
        current_range = float(current_range)
             
        
        try:
            t = float(t)
            t > 0
        except:
            print('Invalid time. Must be a real number > 0.')
            return
        
        
        
        # Connect to scope
        inst = self.rm.open_resource(self.scope.get())
             
        
        # Set and record some scope parameters
        inst.write('TRMD AUTO')
        inst.write('MSIZ 70K')
        inst.write('TDIV 100MS')
        inst.write('TRMD STOP')
        inst.write('C1:OFST %sV' %self.DC_offset)
        
        vdiv1       = float(inst.query('C1:VDIV?')[8:-2])
        voffset1    = float(inst.query('C1:OFST?')[8:-2])
        vdiv2       = float(inst.query('C2:VDIV?')[8:-2])
        voffset2    = float(inst.query('C2:OFST?')[8:-2])
        sara        = float(inst.query('SARA?')[5:-5])
        tdiv        = float(inst.query('TDIV?')[5:-2])
        frame_time  = 14*tdiv
        
        
        # Get applied frequencies
        file  = os.path.join(rigol_waves, self.waveform.get())    
        df    = pd.read_csv(file, skiprows=9, names=('x', 'V'))    
        
        freqs = 100000*np.fft.rfftfreq(len(df))
        V     = np.fft.rfft(df['V'])
        ftdf  = pd.DataFrame({
                'freqs': freqs,
                'V': V})
        
        ftdf  = ftdf[np.abs(ftdf['V']) > 100]
        applied_freqs = ftdf['freqs'].to_numpy()
            
        
        # Initialize save files
        if save:
            
            # Make save folder
            try:
                name = tk.simpledialog.askstring('Save name', 'Input save name:',
                                             initialvalue = self.last_file_name)
                today = str(date.today())
                save_path = os.path.join(os.path.expanduser('~\Desktop\EIS Output'), 
                                       today, name)
            
            except:
                # User hits cancel
                return
            
            # Reinitialize last file name
            self.last_file_name = name
                        
            createFolder(save_path)
            
            # Create metadata file
            meta_file = os.path.join(save_path, '0000_Metadata.txt')
                
            with open(meta_file, 'w') as f:
                f.write('Waveform Vpp (mV): '+ str(self.waveform_vpp.get('1.0', 'end')))
                f.write('Waveform: '+ str(self.waveform.get()))    
            f.close()
            
            # Start time list file
            time_file = os.path.join(save_path, '0000_time_list.txt')
            
            # Start fits file
            fits_file = os.path.join(save_path, '0000_fits.txt')
        
        
        
        def siglent_record_single(inst, start_time, frame_time, vdiv1, 
                                  voffset1, vdiv2, voffset2, sara, 
                                  frame, sample_time=1):
            # Determine t=0 for frame
            frame_start_time = time.time()
           
            # Record frame
            inst.write('TRMD AUTO')
            
            
            # Process last frame while waiting
            if frame != 0:
                process_frame(frame-1)
                # print(time.time() - frame_start_time)
            while time.time() - frame_start_time < 1.2*frame_time:
                time.sleep(0.01)              
                            
            
            # Get CH 1 data
            inst.write('C1:WF? DAT2')
            trace1 = inst.read_raw()
            wave1 = trace1[22:-2]
            adc1 = np.array(array('b', wave1))
            
            # Get CH 2 data
            inst.write('C2:WF? DAT2')
            trace2 = inst.read_raw()
            wave2 = trace2[22:-2]
            adc2 = np.array(array('b', wave2))
            
            # Convert to voltages
            volts1 = adc1*(vdiv1/25) - voffset1 
            volts2 = adc2*(vdiv2/25) - voffset2  
            
            # Get time array
            times = np.zeros(len(volts1))
            for i in range(len(volts1)):
                times[i] = frame_start_time + (1/sara)*i - start_time
                   
            # Only Fourier transform first sample_time s
            if sample_time:
                end = np.where(times == times[0] + sample_time)[0][0]
            else:
                end = None
            
            freqs = sara*np.fft.rfftfreq(len(volts1[:end]))[1:]
            ft1   =      np.fft.rfft(volts1[:end])[1:]
            ft2   =      np.fft.rfft(volts2[:end])[1:]
            
            ft = siglent_control.FourierTransformData(time    = times[0],
                                      freqs   = freqs,
                                      CH1data = ft1,
                                      CH2data = ft2,)
            
            return ft
        
        
        
        
        def record_frame(frame):
            d = siglent_record_single(inst, start_time, frame_time, vdiv1, 
                                      voffset1, vdiv2, voffset2, sara, 
                                      frame, sample_time=1)
            
            print(f'Frame %s: {d.time:.2f} s'%frame)
            
            V = d.CH1data
            
            if self.potentiostat.get() == 'Autolab':
                # Autolab BNC out inverts current signal
                I = -d.CH2data * current_range
            elif self.potentiostat.get() == 'Gamry':
                I = d.CH2data * current_range
            
            Z = V/I
            phase = np.angle(V/I, deg=True)
            
            
            df = pd.DataFrame(
                    {
                    'freqs': d.freqs,
                    'Z': Z,
                    'phase': phase
                    }
            )
            
            df = df[df['freqs'].isin(applied_freqs)]
            
            # Apply calibration correction
            if self.ref_corr_var.get():
                df['Z'] = df['Z'] / Z_corr
                df['phase'] = df['phase'] - phase_corr
            
            
            d.freqs = df['freqs'].to_numpy()
            d.Z = df['Z'].to_numpy()
            d.phase = df['phase'].to_numpy()
            d.waveform = self.waveform.get()
            
            self.ft[frame] = d
            
            
        
        def process_frame(frame):
            
            # Fit, if the option is checked
            if self.fit.get():
                fit_frame(frame)
                if self.circuit.get() == 'Randles_adsorption':
                    Rct = self.ft[frame].params["R2"]
                    Cad = self.ft[frame].params["Q2"]
                    ket = 1/(2*Rct*Cad)
                    print(f'Rct: {Rct}, Cad: {Cad}, ket: {ket}')
                
                
            # Plot this result to figure canvas
            d = self.ft[frame]
            Z = np.abs(d.Z)
            phase = d.phase
            
            # Determine which plot to make
            if plot_Z:
                if not plot_phase:
                    line1.set_xdata(d.freqs)          
                    line1.set_ydata(Z)
                    if hasattr(self.ft[frame], 'fits'):
                        line3.set_xdata(d.freqs)
                        line3.set_ydata(np.abs(self.ft[frame].fits))
                    self.ax.set_ylim(min(Z)-1.05*min(Z), 1.05*max(Z))
                    self.ax.set_ylabel('|Z|/ $\Omega$')
                    self.ax2.set_yticks([])
            
            if plot_phase:
                if not plot_Z:
                    line2.set_xdata(d.freqs)
                    line2.set_ydata(phase)
                    if hasattr(self.ft[frame], 'fits'):
                        line4.set_xdata(d.freqs)
                        line4.set_ydata(np.angle(self.ft[frame].fits))
                    self.ax2.set_ylim(min(phase)-10, max(phase)+10)
                    self.ax2.set_ylabel('Phase/ $\degree$')
                    self.ax2.set_yticks([])
                
            if plot_Z and plot_phase:
                line1.set_xdata(d.freqs)
                line2.set_xdata(d.freqs)
                line1.set_ydata(Z)
                line2.set_ydata(phase)
                if hasattr(self.ft[frame], 'fits'):
                    line3.set_xdata(d.freqs)
                    line4.set_xdata(d.freqs)
                    line3.set_ydata(np.abs(self.ft[frame].fits))
                    line4.set_ydata(np.angle(self.ft[frame].fits, deg=True))
                self.ax.set_ylim(min(Z)-1.05*min(Z), 1.05*max(Z))
                self.ax2.set_ylim(min(phase)-10, max(phase)+10)
                self.ax.set_ylabel('|Z|/ $\Omega$')
                self.ax2.set_ylabel('Phase/ $\degree$')
                
                
            # Draw the plot
            self.fig.tight_layout()
            self.ax.set_xticks([1e-1,1e0,1e1,1e2,1e3,1e4,1e5,1e6])
            self.ax.set_xlim(0.7*min(d.freqs), 1.5*max(d.freqs))
            self.fig.canvas.draw()
            self.fig.canvas.flush_events()
            
                            
            if save:
                # Add frame time to time list
                with open(time_file, 'a') as f:
                    f.write(str(d.time) + '\n')
                    f.close()
                # Save frame as tab separated .txt
                self.save_frame(frame, d.freqs, np.real(d.Z),
                                np.imag(d.Z), save_path)
            
            
        
        def fit_frame(frame, n_iter = 25, starting_guess = None,
                      **kwargs):
            
            # initialize bounds, give starting guess for frame 0
            if self.circuit.get() == 'Randles_adsorption':
                bounds = {
                        'R1': [1e-1, 1e9],
                        'R2': [1e-1, 1e9],
                        'Q1': [1e-15, 1],
                        'n1': [0.9,1.1],
                        'Q2': [1e-15, 1],
                        'n2': [0.8,1.1]
                        }
                if frame == 0:
                    starting_guess = {
                        'R1': 284, 
                        'R2': 62000, 
                        'Q1': 1.8e-07, 
                        'n1': 1, 
                        'Q2': 3.2e-07, 
                        'n2': 0.9
                        }
            
                    
            if self.circuit.get() == 'RRC':
                bounds = {
                        'R1': [1e-1, 1e9],
                        'R2': [1e-1, 1e9],
                        'C': [1e-15, 1]
                        }
            
            if frame > 0:
                starting_guess = self.ft[frame-1].params
            
            Z     = self.ft[frame].Z
            freqs = self.ft[frame].freqs
            
            
            # Perform fit
            DataFile = EIS_fit.DataFile(file='', circuit=self.circuit.get(), 
                                Z=Z, freqs=freqs, bounds=bounds)
    
            DataFile.ga_fit(n_iter = n_iter, starting_guess = starting_guess, **kwargs)
            DataFile.LEVM_fit(timeout = 0.4) # Needs short timeout
                                             # to not interfere with data
                                             # collection
            
            # Save fit parameters, if fit was successful
            try:
                self.ft[frame].params = DataFile.params # R, C parameters
                self.ft[frame].fits   = DataFile.fits   # Fitted Z vs freq
                
                if save:
                    with open(fits_file, 'a') as f:
                        if frame == 0:
                            f.write('time,')
                            for key, _ in self.ft[frame].params.items():
                                f.write(key + ',')
                            f.write('\n')
                        
                        f.write(str(self.ft[frame].time) + ',')
                        for key, val in self.ft[frame].params.items():
                            f.write(str(val) + ',')
                        f.write('\n')
                        f.close()
            
            except:
                pass
            
            
            
        
        
        # Record starting time
        start_time = time.time()
        self.ft = {}
        
        # Record frames
        print('')
        print('Recording for ~%d s' %t)
        frame = 0
        while time.time() - start_time < t:
            record_frame(frame)   
            print(f'Frame {frame}: {self.ft[frame].time:.2f} s')                
            frame += 1
        
        # Process the last frame
        process_frame(frame-1)
        try:
            print(self.ft[frame-1].params)
        except:
            pass
        
        print(f'Measurement complete. Total time {time.time()-start_time:.2f} s\n')
        
        if save:
            print('Saved as ASCII:', save_path, '\n')
        
        
        
            
            
        
    def record_reference(self):
        # Record impedance spectrum of a resistor to calibrate
        # Save with resistance and waveform labelled
        
        # Check that reference correction is unchecked
        if self.ref_corr_var.get():
            print('Uncheck "Apply Reference Correction" before\n'+
                  'recording a reference spectrum!\n')  
                  
            return
        
        
        # Prompt for resistance value
        R = tk.simpledialog.askstring('Calibration', 'Resistance:')
        
        # Break on "cancel" button
        if not R:
            return
        
        
        # Record spectra
        self.record_signals()
        

        # Determine reference file path/ name
        ref_dir = os.path.join(this_dir, 'reference waveforms\\')
        
        waveform = self.waveform.get()
        
        name = 'REF_%s_%s'%(R, waveform)
        
        out_file = os.path.join(ref_dir, name)
        
        # Average spectra
        freqs = self.ft[1].freqs
        Z = np.mean([np.abs(self.ft[i].Z) for i in self.ft], axis=0)
        phase = np.mean([self.ft[i].phase for i in self.ft], axis=0)
        
        
        if R.endswith('k'):
            R = 1e3*float(R[:-1])
        
        elif R.endswith('M'):
            R = 1e6*float(R[:-1])
        
        else:
            R = float(R)
        
        
        # Determine corrections
        Z_corr      = Z / R
        phase_corr  = phase
                
        df = pd.DataFrame(
            {'freq': freqs,
            'Z_corr': Z_corr,
            'phase_corr': phase_corr}
            )
        
        # Save to csv
        df.to_csv(out_file, index=False)
        
        print('Saved correction file to:')
        print(out_file, '\n')
        
        
        
    def save_frame(self, num, freqs, re, im, save_path):
        d = pd.DataFrame(
            {'f': freqs,
            're': re,
            'im': im}
            )
        
        fname = save_path + f'\\{num:04}s.txt'
    
        d.to_csv(fname, columns = ['f', 're', 'im'],
                     header = ['<Frequency>', '<Re(Z)>', '<Im(Z)>'], 
                     sep = '\t', index = False, encoding='ascii')
        
        
        
    def save_last(self):
                
        if self.ft:
            try:
                name = tk.simpledialog.askstring('Save name', 'Input save name:',
                                                 initialvalue = self.last_file_name)
                
                self.last_file_name = name
                
                today = str(date.today())
                                    
                folder_path = os.path.join(os.path.expanduser('~\Desktop\EIS Output'), 
                                           today, name)
                
                createFolder(folder_path)
                
                time_file = os.path.join(folder_path, '0000_time_list.txt')
                
                with open(time_file, 'w') as f:
                    for i, _ in self.ft.items():
                        time = str(self.ft[i].time)
                        f.write(time + '\n')
                    
                f.close()
                    
                for i, _ in self.ft.items():
                    re = np.real(self.ft[i].Z)
                    im = np.imag(self.ft[i].Z)
                    freqs = self.ft[i].freqs
                    
                    self.save_frame(i, freqs, re, im, folder_path)
                    
                                    
                meta_file = os.path.join(folder_path, '0000_Metadata.txt')
                
                with open(meta_file, 'w') as f:
                    f.write('Waveform Vpp (mV): '+ str(self.waveform_vpp.get('1.0', 'end')))
                    f.write('Waveform: '+ str(self.waveform.get()))
                    
                f.close()
                
                    
                self.fig.savefig(folder_path+'\\0000_fig', dpi=100)
                
                print('Saved as ASCII:', folder_path, '\n')
                 
            
            except:
                # User hits cancel
                # Still option to save previous run
                pass
                

        else:
            print('No previous measurement to export\n')


    

    def record_and_save(self):
        self.record_signals(save=True)
     
        
         
        
        
    ########################################
    ###     END OF MAINWINDOW CLASS      ###
    ########################################


def createFolder(directory):
    try:
        if not os.path.exists(directory):
            os.makedirs(directory)
    except OSError:
        print ('Error: Creating directory. ' +  directory)


root = tk.Tk()
gui = MainWindow(root)
root.mainloop()
sys.stdout = default_stdout
sys.stdin = default_stdin
sys.stderr = default_stderr
