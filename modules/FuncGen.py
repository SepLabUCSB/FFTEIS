



class ArbitraryWaveformGenerator():
    '''
    Sends commands to the arbitrary waveform generator
    '''
    def __init__(self, master):
        self.willStop = False
        self.master = master
        self.master.register(self)
        
    def initialize(self):
        # open port, set settings
        return
    
    def set_waveform(self, waveform):
        # send waveform data to arb and turn it on
        return

