import time

import numpy as np
import pyvisa

if __name__ == '__main__':
    from Waveform import Waveform
else:
    from .Waveform import Waveform


def to_int16(signal):
    signal = np.array(signal)
    if signal.max() > abs(signal.min()):
        # signal = signal - signal.min()
        signal = np.int16(((signal/signal.max()) * int("3fff", 16)))
    elif abs(signal.min()) > signal.max():
        signal = np.int16(((signal/abs(signal.min())) * int("3fff", 16)))
    return signal



def get_bytes(val):
    # Unused but saving just in case...
    bit = int(8191.5*val + 8191.5)
    
    bigbyte = int(bit/2**8)
    littlebyte = bit-(bigbyte*2**8)
    return '%c%c'%(littlebyte, bigbyte)
    


def send_bytes(inst, signal, channel):
    # Break signal up into 16kpts chunks (32 kB)
    number_of_blocks = int(np.floor(len(signal)/16000))
    blocks = {}
    
    string = ':SOURCE%s:TRACe:DATA:DAC16 VOLATILE,CON,'%channel
    end_string = ':SOURCE%s:TRACe:DATA:DAC16 VOLATILE,END,'%channel
    
    for i in range(number_of_blocks+1):
        blocks[i] = signal[16000*i:16000*(i+1)]

    wait(inst)
    for i in range(number_of_blocks):
        inst.write_binary_values(string, blocks[i], datatype='h')
        wait(inst)
    
    wait(inst)
    inst.write_binary_values(end_string, blocks[number_of_blocks], datatype='h')
    wait(inst)
    return blocks


def wait(inst):
    r = False
    while r is False:
        try:
            r = inst.query('*OPC?')
        except:
            time.sleep(0.05)


def apply_waveform(inst, s, Vpp=1, srate=100000):
    '''
    Apply arbitrary waveform s to Rigol DG812 AWG
    
    https://rigol.force.com/support/s/article/methods-for-programmatically-creating-arbitrary-waves1

    Parameters
    ----------
    inst : pyvisa Instrument
        Handle for DG812.
        USB0::0x1AB1::0x0643::DG8A232302748::INSTR
    s : array of int16
        Arbitrary waveform to apply.
    '''
    
    if not s.dtype == 'int16':
        s = to_int16(s)    
    
    inst.timeout = 1000
    inst.write(':SOURCE1:APPL:SEQ')
    inst.write(':SOURCE1:FUNC:SEQ:FILT INSERT')
    send_bytes(inst, s, channel=1)
    # inst.write(':SOURCE1:VOLTAGE %sVPP'%(Vpp))
    inst.write(f':SOURCE1:FUNC:SEQ:SRAT {int(srate)}')
    inst.write(':SOURCE1:FUNC:SEQ:EDGETime 0.000005')
    inst.write(':SOURCE1:FUNC:')
    wait(inst)
    print('Waveform loaded!\n')
    inst.clear()
    

class Arb():
    '''
    Class to communicate with Rigol DG812 arbitrary waveform generator
    '''
    def __init__(self, master, ARB_ADDRESS):
        self.willStop = False
        self.master = master
        self.master.register(self)
        
        self._name = ARB_ADDRESS
        self.initialize()
        
    
    def initialize(self):
        if self._name in pyvisa.ResourceManager().list_resources():
            self.inst = pyvisa.ResourceManager().open_resource(self._name)
        
    
    def send_waveform(self, Waveform, Vpp):
        max_freq = max(Waveform.freqs)
        sample_freq = min(100000, 10*max_freq)
        sample_freq = int(sample_freq)
        v = Waveform.time_domain(srate=sample_freq)
        self.turn_off()
        apply_waveform(self.inst, v, srate=sample_freq)
        self.set_amplitude(Vpp)
        self.turn_on()
        
        
    def set_amplitude(self, Vpp):
        # Sets peak-to-peak amplitude of waveform
        self.inst.write(f':SOURCE1:VOLTAGE {Vpp}VPP')
        wait(self.inst)
        
        
    def turn_on(self):
        self.inst.write(':OUTPUT1 ON;')
        wait(self.inst)
    
    
    def turn_off(self):
        self.inst.write(':OUTPUT1 OFF;')
        wait(self.inst)




if __name__ == '__main__':
    import matplotlib.pyplot as plt
    class thisMaster:
        def __init__(self):
            self.STOP = False
            self.register = lambda x:0
            
    master = thisMaster()
    arb = Arb(master)
    wf = Waveform()
    wf.generate(1, 1000, 15)
    # fig, ax = plt.subplots()
    arb.send_waveform(wf, 0.1)
    






