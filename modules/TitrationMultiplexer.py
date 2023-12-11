import os
import time
from tkinter import simpledialog
from functools import partial

from .DataStorage import Experiment
from .funcs import run




class TitrationMultiplexer:
    
    def __init__(self, master, root, update_file):
        self.master      = master
        self.root        = root
        self.update_file = update_file
        self.expt        = None
        
        self.n_sensors = int()
        self.sensors   = list()
        self.nframes   = int()
        self.name      = str()
        
        self.conc      = ''
        self.i         = 0
        
        self.saved_names = []
        self.saved_specs = []
        
        
        
    def prompts(self):
        # prompt user for parameters
        n_sensors = simpledialog.askinteger('Sensors to multiplex', 'Input number of sensors to toggle between: ')
        if not n_sensors > 0:
            return False
        
        sensors = simpledialog.askstring('Sensor names', 'Input labels for each sensor (comma separated): ',
                                            initialvalue= ','.join([f's{i}' for i in range(n_sensors)]))
        sensors = sensors.split(',')
        if len(sensors) != n_sensors:
            print(f'Could not identify {n_sensors} names in input string: {sensors}')
            return False
        
        # Ask for recording frames per sensor
        nframes = simpledialog.askinteger('Averaging', 'Average over frames: ',
                                              initialvalue=5)
        if nframes < 1:
            return False
        
        # Ask for save name
        name = simpledialog.askstring('Save As', 'Input save name: ')
        if not name:
            return False
        
        
        self.n_sensors = n_sensors
        self.sensors   = sensors
        self.nframes   = nframes
        self.name      = name
        
        self.make_experiment()
        return True
    
    
    def make_experiment(self):
        # Creates a local Experiment which will save averaged spectra
        self.expt = Experiment(self.master, name = self.name)
        self.expt.set_waveform(self.master.waveform)
    
    def check_action(self):
        
        if self.master.ABORT:
            run(self.master.make_ready)
            self.master.GUI.idle()
            return
        
        if self.needs_new_conc():
            r = self.prompt_conc()
            if not r:
                self.master.GUI.idle()
                return
            
        if self.recording_finished():
            self.save_last_recording()
            
        
        if self.autolab_ready():
            self.start_recording()
        
        
        self.root.after(100, self.check_action)
    
    
    def trigger_point(self):
        # Trigger actions when we've recorded nframes of data
        return (len(self.master.experiment.spectra)%self.nframes == 0)
    
    
    def needs_new_conc(self):
        # Check that we're at a trigger point
        if not self.trigger_point():
            return False
        
        if self.conc == '':
            return True
        
        # Check if we've recorded all spectra for all sensors at the
        # previous concentration
        fnames = [f'{sensor}_{self.conc}.txt' for sensor in self.sensors]
        if not all([s in self.saved_names for s in fnames]):
            return False
        print(f'Finished all recording for {self.conc}\n')
        return True
        
    
    def prompt_conc(self):
        self.conc = simpledialog.askstring('Next concentration', 'Input next concentration (cancel ends experiment): ')
        return self.conc
            
    
    def recording_finished(self):
        # Check if previous sensor's recording has finished
        if (len(self.master.experiment.spectra) != 0 and 
            self.trigger_point()):
            return True
        return False
    
    
    def save_last_recording(self):
        spectra = self.master.experiment.spectra[-self.nframes:]
        if any([s in self.saved_specs for s in spectra]):
            return
        
        sensor = self.sensors[self.i%len(self.sensors)]
        fname = f'{sensor}_{self.conc}.txt'
        
        avg            = spectra[0].average(spectra[1:])
        avg.name       = fname
        avg.experiment = self.expt
        avg.fit = self.master.GUI.fitter.fit(avg)
        self.expt.append_spectrum(avg)
        self.saved_specs.extend(spectra)
        self.saved_names.append(fname)
        self.i += 1
        print(f'Finished {sensor}, {self.conc}')
        return
    
    
    def autolab_ready(self):
        return os.path.exists(self.update_file)
    
    
    def start_recording(self):
        # Trigger scope recording and delete the trigger file
        run( partial(self.master.Oscilloscope.record_n, self.nframes) )
        time.sleep(0.1)
        os.remove(self.update_file)
        pass
    
        

