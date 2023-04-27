import traceback
import time
from collections import deque
import threading
import struct
import serial

import numpy as np
import matplotlib.pyplot as plt


def run(func, args=()):
    t = threading.Thread(target=func, args=args)
    t.start()
    return t



class Master():
    def __init__(self):
        self.willStop = False
        self.STOP = False
        self.modules = [self]
        
    def register(self, module):
        '''
        Register a submodule to master
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



class DataTransformer():
    
    def __init__(self, master, ADCDataBuffer):
        self.willStop = False
        self.master = master
        self.master.register(self)
        self.buffer = ADCDataBuffer
        
        self.block_size = 10000
        
        self.data  = []
        
        self.last_spec_count = 0
        self.spec_time = 5
        
    
    def run(self):
        st = time.perf_counter()
        while True:
            if time.perf_counter() - st > 10:
                return
            if self.master.STOP:
                return
            
            if type(self.master.ADC.last_timepoint) != int:
                continue
            
            
            if self.buffer.buffer:
                first_timepoint = self.buffer.buffer[0][0]
                last_timepoint  = self.buffer.buffer[-1][0]
                
                if abs(last_timepoint - first_timepoint)*1e-9 > self.spec_time:
                    data = self.buffer.get(self.buffer.size())
                    self.process(data)
            
            
            # if (self.master.ADC.spec_count != self.last_spec_count) and (self.master.ADC.spec_count != 0):
            #     self.last_spec_count += 1
            #     print(self.buffer.size())
            #     data = self.buffer.get(self.buffer.size())
            #     self.process(data)
                
            
            # if self.buffer.size() >= self.block_size:
            #     start_time = self.master.ADC.start_time
            #     data = self.buffer.get(self.block_size)
            #     self.process(data)
                
                
    def process(self, data):
        
        processed_data = [ [], [] ]
        
        first_timestamp = data[0][0]
        last_timestamp  = data[-1][0]
        
        prev_timestamp = first_timestamp
        t = []
        for timestamp, count, response in data[1:]:
            bResponse = bytearray(response)
            Channel = struct.unpack("<"+"h"*count, bResponse)
            times = np.linspace(prev_timestamp, timestamp, count)
            
            for j in range(count):
                ch_idx = (count - j)%2
                processed_data[ch_idx].append(Channel[j]*10/2**15)
                
                if j%2 == 0:
                    t.append(times[j])
        
        v, i = processed_data
        # t = np.linspace(first_timestamp, last_timestamp, len(v))
        
        # t, v, i = zip(*data)
        t = np.array(t)
        t -= t[0]
        t *= 1e-9
        
        cutoff_id = max([i for i, time in enumerate(t) if time <= 1])
        v = v[:cutoff_id]
        i = i[:cutoff_id]
        
        
        
        sample_rate = (t[-1] - t[0])/len(t)
        print(1/sample_rate, len(t))
        
        # sample_rate = 10000
        freqs = sample_rate*np.fft.rfftfreq(len(v))[1:]
        ft_v  = np.fft.rfft(v)[1:]
        ft_i  = np.fft.rfft(i)[1:]
        
        
        # Correct frequencies due to variable ADC sample time
        # peaks = np.where(abs(ft_v) > 2*np.mean(abs(ft_v)))[0]
        # max_freq = freqs[max(peaks)]
        # print(f'Max measured frequency: {max_freq}')
        
        # correction_factor = 1000/max_freq
        # freqs *= correction_factor
        
        
        self.data.append((freqs, ft_v))
        
        
        
        
    
        

class ADCDataBuffer():
    '''
    Buffer to facilitate data transfer between ADC and data processing
    modules. Essentially just an extension of collections.deque 
    '''
    
    def __init__(self):
        self.buffer = deque()
        
    def size(self):
        return len(self.buffer)
        
    def append(self, i):
        self.buffer.append(i)
        
    def extend(self, vals):
        self.buffer.extend(vals)
    
    def get(self, n):
        # Return first n points in buffer
        return [self.buffer.popleft() for _ in range(n)]
    
    def clear(self):
        self.buffer.clear()
    
    
    



class ADC():
    '''
    Communicates with the ADC. Sets data recording settings and
    reads data back via serial port.
    '''
    def __init__(self, master, ADCDataBuffer, SER_PORT = 'COM6'):
        self.willStop = False
        self.master   = master
        self.master.register(self)
        
        self.port = serial.Serial(port=SER_PORT, timeout=0.5)
        
        self._is_setup = False
        self._is_polling = False
        
        self.buffer = ADCDataBuffer
        self.last_timepoint = None
        
        # Default ADC parameters, refer to DI-2108 manual for definitions
        self.params = {
            'n_channels': 2,
            'srate'     : 800,
            'dec'       : 1,
            'deca'      : 1,
            'ps'        : 1, # packet size = 2**(ps + 4) bytes, min = 2**(1 + 4) = 32
                             # !!! Min ps = 1 or else buffer overflows !!!
            }
        
        self.setup()
        self.set_sample_rate(10000)
        
    
    # Stop recording and close serial port
    def stop(self):
        try:
            self.port.write(b"stop\r")
        except Exception as e: # port is already closed
            return
        time.sleep(0.5)
        self.port.close()
        self.willStop = True
        return    
    
    
    def setup(self, params=None):
        
        if not params:
            params = {}
        
        new_params = {
            'n_channels': params.get('n_channels', self.params['n_channels']),
            'srate'     : params.get('srate', self.params['srate']),
            'dec'       : params.get('dec', self.params['dec']),
            'deca'      : params.get('deca', self.params['deca']),
            'ps'        : params.get('ps', self.params['ps']),
            }
        
        if (new_params == self.params) and self._is_setup:
            return
        
        self.params = new_params
                
        
        self.port.write(b"stop\r")        #stop in case device was left scanning
        self.port.write(b"encode 0\r")    #set up the device for binary mode
        self.port.write(b"slist 0 0\r")   #scan list position 0 channel 0
        if self.params['n_channels'] == 2:
            self.port.write(b"slist 1 1\r")
        
        #write scanning params
        self.port.write(f"srate {self.params['srate']}\r".encode('utf-8')) 
        self.port.write(f"dec {self.params['dec']}\r".encode('utf-8'))
        self.port.write(f"deca {self.params['deca']}\r".encode('utf-8'))
        self.port.write(f"ps {self.params['ps']}\r".encode('utf-8')) # packet size
        time.sleep(0.5)
        while True:
            i = self.port.in_waiting
            if i > 0:
                response = self.port.read(i)
                # print(response)
                break
        self._is_setup = True
        return
    
    
    def set_sample_rate(self, freq):
        # Adjust sampling parameters to match desired sample rate
        # with maximal filtering
        
        srate = 400*self.params['n_channels'] # minimum srate = fastest base freq
        
        # Maximum sample rate is ~70 kHz for 2 channels
        
        dec = 70000//freq
        deca = 1
        while dec > 512:
            dec //= 10
            deca *= 10
            
        self.setup(params={'srate': srate,
                           'dec'  : dec,
                           'deca' : deca})                
        return
    
    
    
    def record(self, duration=10):
        # record for a certain duration
        # turn off/ on in between spectra? Probably should
        
        n_ch = self.params['n_channels']
        numofbyteperscan = 2*n_ch
        
        self.buffer.clear()
        self.port.reset_input_buffer()
        self.port.write(b"start\r")
        
        st = time.perf_counter_ns()
        self.start_time = st
        self.last_timepoint = st
        self.last_spectime  = st
        self.spec_count = 0
        while True:
            if (time.perf_counter_ns() - st)*1e-9 > duration:
                break
            
            if (time.perf_counter_ns() - self.last_spectime)*1e-9 >= 1:
                self.last_spectime = time.perf_counter_ns()
                self.spec_count += 1
                
            
            i = self.port.in_waiting
            if (i//numofbyteperscan) > 0:
                # https://github.com/dataq-instruments/Simple-Python-Examples/blob/master/simpletest_binary2.py
                
                data = [ [] for _ in range(n_ch)]
                response = self.port.read(i - i%numofbyteperscan)
                
                count = (i - i%numofbyteperscan)//2
                
                self.buffer.append( (time.perf_counter_ns(),
                                     count,
                                     response) )
                
                
                # count = (i - i%numofbyteperscan)//2
                # bResponse = bytearray(response)
                # Channel = struct.unpack("<"+"h"*count, bResponse)
                
                # for j in range(count):
                #     ch_idx = (count - j)%2 # ! Only accomodates 2 channels
                #     data[ch_idx].append(Channel[j]*10/2**15)
                
                # this_timepoint = time.perf_counter_ns()
                # dt = (this_timepoint - self.last_timepoint) / len(data[0])
                
                # ts = list(1e-9*np.arange(self.last_timepoint,
                #                           this_timepoint,
                #                           dt))
                
                            
                # for t, ch1, ch2 in zip(ts, data[0], data[1]):
                #     # print(t, ch1, ch2)
                #     self.buffer.append( (t, ch1, ch2) )
                    
                # self.last_timepoint = this_timepoint
                    
                
        print('done recording')
        # time.sleep(0.1)
        # self.last_timepoint = None
        return




if __name__ == '__main__':
    master = Master()
    buffer = ADCDataBuffer()
    adc = ADC(master, buffer)
    transformer = DataTransformer(master, buffer)
    run(master.run)
    run(transformer.run)
    
    adc.record()
     
    adc.stop()
    
    fig, ax = plt.subplots(figsize=(5,5), dpi=150)
    data = transformer.data
    for (freqs, ft_v) in data:
        # peaks = np.where(abs(ft_v) > 20*np.mean(abs(ft_v)))[0]
        # max_freq = freqs[max(peaks)]
        # factor = 1000/max_freq
        # freqs *= factor
        # freqs /= freqs[0]
        # ax.plot(freqs, abs(ft_v))
        ax.plot(abs(ft_v))
        # ax.axhline(20*np.mean(abs(ft_v)))
        # ax.axvline(max_freq)
    ax.set_xscale('log')
    plt.show()
        


