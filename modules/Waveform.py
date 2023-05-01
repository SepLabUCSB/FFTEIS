import numpy as np
import matplotlib.pyplot as plt
import pandas as pd

if __name__ == '__main__':
    from funcs import nearest
else:
    from .funcs import nearest


# !!! TODO: change this

waveform_dir = r'C:/Users/BRoehrich/Desktop/git/FFTEIS/waveforms'


def generate_waveform(f0, f1, n_pts):
    '''
    f0: float, starting frequency (Hz)
    f1: float, ending frequency (Hz)
    n_pts: int, number of frequencies to measure
    '''

    # Validate inputs
    assert(f1 > f0 > 0),    'EIS input error: must have f1 > f0 > 0.'
    assert(f1 > n_pts*f0), f'EIS input error: cannot fit {n_pts} points between {f0} and {f1} Hz because for FFT-EIS, all frequencies must be integer multiples of the lowest frequency ({f0} Hz).'
    
    # Generate array of frequencies
    freqs = np.logspace(np.log10(f0), np.log10(f1), n_pts)
    
    # All frequencies must be interger multiples of the lowest frequency,
    # and should not be 2nd harmonics of each other
    # Avoid harmonics of 60 Hz as well (US mains power frequencies)
    
    base_freq = f0
    valid_freqs = [n*base_freq for n in range(1, 1 + int(f1//base_freq))]
    
    for i in range(n_pts):
        f = freqs[i]
        idx, f = nearest(valid_freqs, f) # Find closest interger multiple
        
        while ( (f in freqs[:i]) 
               or (f%60 == 0)                       # 60 Hz harmonics
               or any([f/set_freq == 2 for set_freq in freqs[:i]]) # 2nd harmonic of lower freq
              ):
            idx += 1
            try:
                f = valid_freqs[idx]
            except:
                break   
        freqs[i] = f
    
    phases = [np.random.randint(-180, 180) for _ in freqs]
    
    # Make sure no two sine waves have the same phase
    while len(set(phases)) != len(phases):
        phases = [np.random.randint(-180, 180) for _ in freqs]
        
    return freqs, phases
        

def make_time_domain(freqs, phases, mVpp):
    '''
    Total measurement duration is 1/min(freqs): 1 cycle at the lowest
    requested frequency.
    
    Number of points needd it duration*sample rate. For now, sample rate is 
    fixed at 100 kHz. In the future the sample rate will be chosen based
    on the maximum requested frequency (srate >= 10* max(freqs) )
    '''
    
    
    if type(mVpp) not in (list, np.ndarray):
        mVpp = [mVpp for _ in freqs]
    
    sample_rate = 100000 # TODO: set this dynamically, choose between i.e. 10, 25, 100kHz
    
    N = (1/min(freqs)) * sample_rate
    N = int(np.ceil(N)) # collect 1 extra point if N is not an integer
    v = np.zeros(N)
    t = np.linspace(0, 1/min(freqs), N)
    for freq, phase, amp in zip(freqs, phases, mVpp):
        v += amp*np.sin(2*np.pi*freq*t + phase)
    
    v *= max(mVpp)/max(v) # rescale to set max Vpp
    
    return v
        




class Waveform():
    def __init__(self, freqs=None, phases=None, amps=None):
        self.freqs  = freqs
        self.phases = phases
        self.amps   = amps


    def generate(self, f_min, f_max, n_pts):
        self.freqs, self.phases = generate_waveform(f_min, f_max, n_pts)
        
    
    def from_csv(self, file):
        df = pd.read_csv(file)
        self.freqs  = df['freqs']
        self.phases = df['phases']
        self.amps   = df['amps']
        return
    
    
    def to_csv(self):
        
        assert type(self.freqs) in (list, np.ndarray), 'Invalid frequencies'
        assert type(self.phases) in (list, np.ndarray), 'Invalid phases'
        opt = '_opt'
        if type(self.amps) not in (list, np.ndarray):
            opt = ''
            self.amps = np.ones(len(self.freqs))
            
        path = waveform_dir
        
        high = max(self.freqs)
        low  = min(self.freqs)
        n    = len(self.freqs)
        
        name = f'{high}_{low}_{n}{opt}.csv'    
        file = os.path.join(path, name)
        
        df = pd.DataFrame({'freqs': self.freqs,
                           'phases': self.phases,
                           'amps': self.amps})
        df.to_csv(file, index=False)
    

    def optimize_from_spectrum(self, ImpedanceSpectrum):
        assert self.freqs == ImpedanceSpectrum.freqs, 'Correction input frequencies do not match Waveform frequencies'
        Z = np.asarray(ImpedanceSpectrum.Z)
        amp_factor = 1/np.absolute(Z)
        
        self.amps = amp_factor/max(amp_factor)
      
        
    def time_domain(self):
        if not (len(self.freqs) == len(self.phases) > 0):
            print('frequencies or phases invalid')
            return
        
        if type(self.amps) not in (list, np.ndarray):
            self.amps = np.ones(len(self.freqs))
        
        v = make_time_domain(self.freqs, self.phases, self.amps)
        return v
    
    
    def plot_to_ax(self, ax):
        x = np.arange(min(self.freqs)/5, 
                      5*(max(self.freqs) + min(self.freqs)), 
                      min(self.freqs)/10)
        y = np.zeros(len(x))
        
        for i, freq in enumerate(self.freqs):
            idx, _ = nearest(x, freq)
            y[idx] = self.amps[i]
        
        ax.plot(x, y)
        ax.set_xscale('log')
        ax.set_xticks([1,10,100,1000,10000])
        ax.set_xlim(min(x), max(x))
        ax.set_xlabel('Frequency/ Hz')
        ax.set_ylabel('Amplitude')
 
       
 

if __name__ == '__main__':
    import os
    csv_dir = r'C:/Users/BRoehrich/Desktop/git/FFTEIS/waveforms'
    wf = Waveform()
    wf.generate(10, 1000, 14)
    out_csv = os.path.join(csv_dir, 'test.csv')
    wf.to_csv()
    # wf.from_csv(out_csv)
    # fig, ax = plt.subplots()
    # wf.plot_to_ax(ax)











