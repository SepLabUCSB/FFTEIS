import time
from array import array

import numpy as np
import pyvisa

if __name__ == '__main__':
    from Buffer import ADCDataBuffer
    from DataProcessor import DataProcessor
    from funcs import run
else:
    from .Buffer import ADCDataBuffer
    from .DataProcessor import DataProcessor
    from .funcs import run    


class Oscilloscope():
    '''
    Class for communicating with an SDS1202X-E oscilloscope
    '''
    def __init__(self, master, ADCDataBuffer):
        
        self.willStop = False
        self.master = master
        self.master.register(self)
        
        self.buffer = ADCDataBuffer
        
        self.inst = None
        self._name = 'USB0::0xF4ED::0xEE3A::SDS1EDED5R0471::INSTR'
        self._is_recording = False
        
        run(self.initialize)
        
    
    
    def write(self, cmd):
        # Send command to scope and wait for 
        if not self.inst:
            return
        self.inst.write(cmd)
        time.sleep(0.2)
    
    
    
    def initialize(self):
        if self._name in pyvisa.ResourceManager().list_resources():
            self.inst = pyvisa.ResourceManager().open_resource(self._name)
        
        self._is_recording = True
        # Write default settings
        # self.inst.write('*RST')                 # Reset
        # time.sleep(4)
        self.write('TRMD AUTO')
        self.write('C1:TRA ON')                 # Turn on CH 1
        self.write('C2:TRA ON')                 # Turn on CH 2
        self.write('MEMORY_SIZE 70K')           # Set memory depth
        self.write('TDIV 100MS')
        
        self.write('TRSE EDGE,SR,EX,HT,OFF')    # Set up triggering
        
        # self.write('TRMD STOP')
        self._is_recording = False
        
    
    def get_i_range(self):
        # Read current range from GUI
        i_range = self.master.GUI.current_range.get()
        val, unit = i_range.split(' ')
        
        factor = {'nA': 1e-9,
                  'uA': 1e-6,
                  'mA': 1e-3,
                  'A' : 1,}
        
        val = int(val)
        val *= factor[unit]
        return val
    
    
    def get_recording_params(self):
        i_range     = self.get_i_range()
        vdiv1       = float(self.inst.query('C1:VDIV?')[8:-2])
        voffset1    = float(self.inst.query('C1:OFST?')[8:-2])
        vdiv2       = float(self.inst.query('C2:VDIV?')[8:-2])
        voffset2    = float(self.inst.query('C2:OFST?')[8:-2])
        sara        = float(self.inst.query('SARA?')[5:-5])
        tdiv        = float(self.inst.query('TDIV?')[5:-2])
        self.recording_params = {
            'vdiv1':vdiv1,
            'vdiv2':vdiv2,
            'voffset1':voffset1,
            'voffset2':voffset2,
            'sara':sara,
            'tdiv':round(tdiv, 6),
            'frame_time':14*round(tdiv, 6),
            'i_range': i_range,
            }      
        return self.recording_params.copy()
        
    
    
    def record_frame(self, timeout = 10, add_to_buffer=True):
        # Record one frame of data.
        # Returns raw voltages
        
        if self._is_recording:
            return
        self._is_recording = True
        
        recording_params = self.get_recording_params()
                
        vdiv1    = recording_params['vdiv1']
        vdiv2    = recording_params['vdiv2']
        voffset1 = recording_params['voffset1']
        voffset2 = recording_params['voffset2']
        
        self.inst.write('TRMD AUTO')
        st = time.time()
        while time.time() - st < timeout:
            # Check status
            inr = int(self.inst.query('INR?').strip('\n').split(' ')[1])
            if inr==1:
                break
        self.inst.write('TRMD STOP')
        
        # Read the data back
        self.inst.write('C1:WF? DAT2')
        trace1 = self.inst.read_raw()
        wave1  = trace1[22:-2]
        adc1   = np.array(array('b', wave1))
        
        self.inst.write('C2:WF? DAT2')
        trace2 = self.inst.read_raw()
        wave2  = trace2[22:-2]
        adc2   = np.array(array('b', wave2))
        
        volts1 = adc1*(vdiv1/25) - voffset1
        volts2 = adc2*(vdiv2/25) - voffset2
        if add_to_buffer:
            self.buffer.append( (time.time(), 
                                 recording_params, 
                                 volts1, volts2) )
        self._is_recording = False
        self.inst.write('TRMD AUTO')
        return volts1, volts2
    
    
    def record_duration(self, t):
        '''
        Record continuously for a given duration t
        '''
        st = time.time()
        while time.time() - st < t:
            if self.master.ABORT:
                return
            self.record_frame()
        return
    
    
    def autocenter_frames(self):
        # Automatically adjust vertical divisions and vertical offset
        # so that each trace is centered and fills the screen
        
        # Go to starting settings
        self.inst.write('BUZZ OFF')     # Turns sound off
        self.inst.write('TDIV 20MS')    # Faster scans for this
        self.inst.write('C1:VDIV 10V')  # Start as zoomed out as possible
        self.inst.write('C2:VDIV 10V')
        self.inst.write('C1:OFST 0')    # Centered at 0V
        self.inst.write('C2:OFST 0')
        self.get_recording_params()
        
        vdivs = [5e-4,              # 500uV/div
                 1e-3, 2e-3, 5e-3,  # 1, 2, 5 mV/div
                 1e-2, 2e-2, 5e-2,  # ...
                 1e-1, 2e-1, 5e-1,
                 1, 2, 5, 10]
        
        v1_idx  = v2_idx  = 13
        V1_DONE = V2_DONE = False
        
        # Iteratively zoom in
        i = 0
        while i < 13:
            
            # Record a frame
            v1, v2 = self.record_frame(add_to_buffer = False)
            
            self.get_recording_params()
            vdiv1 = self.recording_params['vdiv1']
            vdiv2 = self.recording_params['vdiv2']
            voffset1 = self.recording_params['voffset1']
            voffset2 = self.recording_params['voffset2']
            
            # Determine if we should zoom in more
            if not (max(v1) > (-voffset1 + 1.5*vdiv1) or
                    min(v1) < (-voffset1 - 1.5*vdiv1) or
                    V1_DONE):
                v1_idx -= 1
            else:
                V1_DONE = True
            
                
            if not (max(v2) > (-voffset2 + 1.5*vdiv2) or
                    min(v2) < (-voffset2 - 1.5*vdiv2) or
                    V2_DONE):
                v2_idx -= 1
            else:
                V2_DONE = True
                
                
            # Step down faster if we're far off
            if (max(v1) < (-voffset1 + 0.2*vdiv1) and
                min(v1) > (-voffset1 - 0.2*vdiv1)):
                v1_idx -= 1
            if (max(v2) < (-voffset2 + 0.2*vdiv2) and
                min(v2) > (-voffset2 - 0.2*vdiv2)):
                v1_idx -= 1
            
            
            if (V1_DONE and V2_DONE):
                break
            
            # Zoom in and re-center
            self.inst.write(f'C1:VDIV {vdivs[v1_idx]}')
            self.inst.write(f'C2:VDIV {vdivs[v2_idx]}')
            self.inst.write(f'C1:OFST {-np.mean(v1)}')
            self.inst.write(f'C2:OFST {-np.mean(v2)}')
            
            self.get_recording_params() #update self.recording_params
            i += 1
            
        self.inst.write('BUZZ ON')                  # Turn beep back on
        self.inst.write(f'C1:VDIV {vdivs[v1_idx]}') # Makes it beep
        self.inst.write('TDIV 100MS')               # Reset
        self.inst.write('TRMD AUTO')                # So user can view waveform
        return
        
        
        




if __name__ == '__main__':
    class thisMaster:
        def __init__(self):
            self.STOP = False
            self.register = lambda x:0
    
    buffer = ADCDataBuffer()
    master = thisMaster()
    scope  = Oscilloscope(master, buffer)
    dataProcessor = DataProcessor(master, buffer)
    scope.initialize()
    scope.autocenter_frames()
    run(dataProcessor.run)
    scope.record_frame()
    
    
        


