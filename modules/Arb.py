import time

import numpy as np
import pyvisa


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


def apply_waveform(inst, s, Vpp=1):
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
    inst.write(':SOURCE1:VOLTAGE %sVPP'%(Vpp))
    inst.write(':SOURCE1:FUNC:SEQ:SRAT 100000')
    inst.write(':SOURCE1:FUNC:SEQ:EDGETime 0.000005')
    inst.write(':SOURC1s:FUNC:')
    wait(inst)
    inst.write(':OUTPUT1 ON;')
    wait(inst)
    print('Waveform loaded!\n')
    inst.clear()
    

class Arb():
    def __init__(self, master):
        self.willStop = True
        self.master = master
        self.master.register(self)
        
        self._name = 'USB0::'  # !!!TODO 
        
    
    def initialize(self):
        self.inst = pyvisa.ResourceManager().open_resource(self._name)
        
    
    def send_waveform(self, Waveform):
        v = Waveform.time_domain()
        if v:
            apply_waveform(self.inst, v)







