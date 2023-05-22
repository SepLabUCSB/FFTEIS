import sys
import os
import subprocess
import numpy as np
import math
'''

Main function to call for LEVM fitting:

LEVM_fit(freqs, Z, guess, circuit, free_params):
    returns fits: dict of best-fit parameters

'''


def assign_params(circuit, guess, free):
        # Write initial guesses to select parameters
        # Check LEVM manual pp. 114-150 to choose an appropriate
        # function ('A'-'F' most appropriate for solution phase 
        # echem) and map circuit elements to the correct parameter (0-40) 
    
    if circuit == 'Randles_adsorption':
        d = {
             'Rs':   (1, guess['Rs'], free['Rs']),
             'Rct':  (4, guess['Rct'], free['Rct']),
             'Cdl':  (3, guess['Cdl'], free['Cdl']),
             'Cad':  (7, guess['Cad'], free['Cad']),
             'phi':  (9, guess['phi'], free['phi']),
             '_Cad': (10, 2, 0),
             'func': 'C'
             }
        
    elif circuit == 'Randles_uelec':
        d = {
            'R1'  : (1, guess['R1'], free['R1']),
            'R2'  : (4, guess['R2'], free['R2']),
            'R3'  : (21, guess['R3'], free['R3']),
            'Q1'  : (3, guess['Q1'], free['Q1']),
            'Q2'  : (7, guess['Q2'], free['Q2']),
            'n2'  : (9, guess['n2'], free['n2']),
            '_Q2' : (10, 2, 0),
            'func': 'C'            
            }
    
    elif circuit == 'RRC':
        d = {
            'R1'  : (1, guess['R1'], free['R1']),
            'R2'  : (4, guess['R2'], free['R2']),
            'C1'   : (3, guess['C1'], free['C1']),
            'func': 'C'
            }
    
    elif circuit == 'RRQ':
        d = {
            'R1'  : (1, guess['R1'], free['R1']),
            'R2'  : (2, guess['R2'], free['R2']),
            'Q1'  : (7, guess['Q1'], free['Q1']),
            'n1'  : (9, guess['n1'], free['n1']),
            '_Q1' : (10, 2, 0),
            'func': 'C'
            }
    
    else:
        print('Circuit not recognized by LEVM.py')
        raise ValueError
        
    return d
        
        


##############################################################################
#####                      LEVM INPUT PARAMS                             #####
##############################################################################

# Input fields defined in LEVM Manual, p. 69
# !! PRESERVE FIELD LENGTHS WHEN CHANGING VALUES !!
inputs = {
    'IOPT':'   0',
    'DINP':'  Z',
    'DFIT':'Z',
    'PINP':'R',
    'PFIT':'R',
    'FREEQ':'F',
    'NEG':' ',
    'FUN':'C',
    'CELCAP':' .0000D+00',
    'DATTYP':'C',
    'IPAR':'         0',
    'ROE':' .0000D+00',
    'IFP':'     7',
    'IRE':'   -11',

    'M':'   27', # M is number of frequencies, automatically determined from input data
    'N':'   40',
    'MAXFEV':'   99',
    'NPRINT':'    0',
    'IRCH':'    3',
    'MODE':'    0',
    'ICP':'    0',
    'IPRINT':'    1',
    'IGACC':'    1',
    'ATEMP':' .0000D+00'
    }




##############################################################################
#####                      GENERAL DATA PROCESSING                       #####
##############################################################################


def float_to_string(n, decimals = 8):
    # Convert scientific notation to Fortran D notation
    if type(n) == str:
        print(f'LEVM.py received string instead of float: {n}')
        return n
    
    if decimals == 8:
        a = "{0:.7E}".format(n)
    if decimals == 13:
        a = "{0:.12E}".format(n)
    
    digits, exponent = a.split('E')
    
    if digits[0] == '-':
        l = digits[1]
        digits = digits[3:]
        digits = '-.' + l + digits
        
    else:
        l = digits[0]
        digits = digits[2:]
        digits = '.' + l + digits
    
    exponent = int(exponent)
    
    
    if int(exponent) < 0 and int(exponent) > -11:
        s = '%sD-0%s'%(digits, str(abs(exponent)-1))
    
    if int(exponent) < 0 and int(exponent) <= -11:
        s = '%sD-%s'%(digits, str(abs(exponent)-1))
        
    if int(exponent) >= 0 and int(exponent) < 9:
        s = '%sD+0%s'%(digits, str(exponent+1))
    
    if int(exponent) >= 0 and int(exponent) >= 9:
        s = '%sD+%s'%(digits, str(exponent+1))
        
    if digits == '.00000000' and int(exponent) == 0:
        s = '.00000000D+00'
    
    return s



def string_to_float(s):
    # FORTRAN D to scientific notation
    
    digits = float(s[:9])
    sign = s[-3]
    exp = float(s[-2:])
    
    if sign == '+':
        n = digits * 10**(exp)
    
    if sign == '-':
        n = digits * 10**(-1*exp)
    
    return n



def params_to_LEVM_format(params):   
    
    binary_line = [0 for _ in range(40)]
    
    p = {i:0 for i in range(1,41)}
    for key, tup in params.items():
        if key != 'func':
            i, guess, free = tup
            
            p[i] = guess
            binary_line[i-1] = int(free)
    
    # Force Xi parameter = 1. Used in MEISP, for some reason this makes the 
    # fits less susceptiple to noise
    p[32] = 1
    binary_line[31] = 0
            
    binary_line = ''.join(str(j) for j in binary_line)
    function = params['func']
    
    return p, binary_line, function
    



##############################################################################
#####                      INPUT FILE CREATION                           #####
##############################################################################

def write_comment_line(file, comment):
    '''
    Write comment line. 1st line of INFL, 80 char max
    '''
    if len(comment) > 80:
        raise ValueError('Comment is too long!')
        sys.exit()
    
    with open(file, 'w') as f:
        f.write(comment + '\n')
    
    

def write_input_params(file):
    '''
    Write lines 2 and 3 containing fit settings.
    
    Settings defined in global inputs dict
    '''
    
    global inputs
    
    line2 = ''
    line3 = ''
    
    line2_order = ['IOPT', 'DINP', 'DFIT', 'PINP', 'PFIT',
               'FREEQ', 'NEG', 'FUN', 'CELCAP', 'DATTYP',
               'IPAR', 'ROE', 'IFP', 'IRE']


    line3_order = ['M', 'N', 'MAXFEV', 'NPRINT', 'IRCH',
               'MODE', 'ICP', 'IPRINT', 'IGACC', 'ATEMP']

    for key in line2_order:
        line2 = line2 + inputs[key]
    
    for key in line3_order:
        line3 = line3 + inputs[key]
    
    with open(file, 'a') as f:
        f.write(line2 + '\n')
        f.write(line3 + '\n')
     


def write_initial_params(file, p):
    '''
    Write initial guesses to file (lines 4-11)
    '''
    param_lines = {}
    param_lines[1] = '  %s  %s  %s  %s  %s'%(p[1], p[2], p[3], p[4], p[5])
    param_lines[2] = '  %s  %s  %s  %s  %s'%(p[6], p[7], p[8], p[9], p[10])
    param_lines[3] = '  %s  %s  %s  %s  %s'%(p[11], p[12], p[13], p[14], p[15])
    param_lines[4] = '  %s  %s  %s  %s  %s'%(p[16], p[17], p[18], p[19], p[20])
    param_lines[5] = '  %s  %s  %s  %s  %s'%(p[21], p[22], p[23], p[24], p[25])
    param_lines[6] = '  %s  %s  %s  %s  %s'%(p[26], p[27], p[28], p[29], p[30])
    param_lines[7] = '  %s  %s  %s  %s  %s'%(p[31], p[32], p[33], p[34], p[35])
    param_lines[8] = '  %s  %s  %s  %s  %s'%(p[36], p[37], p[38], p[39], p[40])
    
    with open(file, 'a') as f:
        for key, line in param_lines.items():
            f.write(line + '\n')



def write_binary_line(file, binary_line):
    '''
    Line 12 is a 40 character line of binary
    
    If character i == 1, p[i] is free during the fit
    If character i == 0, p[i] is fixed during the fit
    
    '''
    
    with open(file, 'a') as f:
        f.write(binary_line + '\n')



def write_Z_data(file, freqs, Z):
    '''
    Writes lines 13-n, containing all impedance data

    Parameters
    ----------
    file : String.
        Output file. Generally 'INFL'
    freqs : array-like.
        Array of frequencies
    Z : array-like
        Array of impedance data in format (re + 1j*im)

    '''
    freqs = np.asarray(freqs)
    re = np.real(Z)
    im = np.imag(Z)
    
    data_lines = {}

    for i in range(len(freqs)):
        index_val = str(i+1).rjust(5, ' ')
        freq_val = float_to_string(freqs[i], 13).rjust(25, ' ')
        re_val = float_to_string(re[i], 13).rjust(25, ' ')
        im_val = float_to_string(im[i], 13).rjust(25, ' ')
        
        data_lines[i+1] = index_val + freq_val + re_val + im_val
    
    with open(file, 'a') as f:
        for i in data_lines:
            f.write(data_lines[i] + '\n')
    


def write_input_file(file, freqs, Z, params, comment=' '):
    '''
    Parameters
    ----------
    file : String
        Target file to write. Should generally be 'INFL'
    freqs : Array-like
        Array of frequencies.
    Z : Array-like
        Array of (re - 1j*im) impedances.
    params: dict
        dict of {['param'] : (circuit_index, guess, free)}
    comment : String, optional
        Comment line to include on line 1.
        Max 80 characters.

    '''
    
    global inputs
    
    
    p, binary_line, function = params_to_LEVM_format(params)
            
    inputs['FUN'] = function    
    inputs['M'] = str(len(freqs)).rjust(5, ' ')
    
    for i in p:
        p[i] = float_to_string(p[i], 8)
        
    write_comment_line(file, comment)
    write_input_params(file)
    write_initial_params(file, p)
    write_binary_line(file, binary_line)
    write_Z_data(file, freqs, Z)




##############################################################################
#####                      RUN LEVM                                      #####
##############################################################################

def run_LEVM(LEVM_path, timeout):
    '''
    Run LEVM using subproccess.run()
    # '''
    try:
        subprocess.run([], executable=LEVM_path, timeout=timeout)
        return 0
    except subprocess.TimeoutExpired:
        print('LEVM.exe timed out')
        return 1


def extract_params(file, params):
    '''
    Function to extract fit parameters from OUTIN
    
    Parameters
    ----------
    file: string
        Output file to read. Should always be 'OUTIN'
    circuit: string
        Name of equivalent circuit used in fit
        (same as in circuits.py)


    Returns
    -------
    d: dict 
        Best-fit parameters, converted back to 
        EIS_fit.py names
    
    ''' 
    with open(file) as f:
        for lineno, line in enumerate(f):
            if lineno == 11:
                b = line
            
    
    p = {}
    for i in range(len(b)):
        if b[i] == '1':
            p[i+1] = 1
            
    with open(file) as f:
        m = 1
        for lineno, line in enumerate(f):
            if lineno > 2 and lineno < 11:
                for element in line.split():
                    p[m] = element
                    m += 1
    
    
    d = {}
    for key, tup in params.items():
        if key == 'func':
            continue
        if key.startswith('_'):
            # Fixed distributed element parameter assignment
            continue
        else:
            i, _, _ = tup
            d[key] = string_to_float(p[i])
          
    
    return d



def LEVM_fit(freqs, Z, guess, circuit, free_params,
             timeout = 2, comment = ' '):
    '''
    Main function to call to perform LEVM fit
    
    Parameters
    ----------
    freqs : Array-like
        List of frequencies.
        
    Z : Array-like
        List of (re - 1j*im) impedances.
        
    guess : Dict
        Initial guesses for fit parameters.


    comment : String, optional
        Comment line to include on line 1.
        Max 80 characters.
        
    Returns
    ---------
    fits : Dict
            Fitted parameters

    '''
    # Determine location of LEVM.py
    original_path = os.getcwd()
    path = os.path.realpath(__file__)[:-7]
    
    os.chdir(path)
    LEVM_path = 'LEVM.exe'
    
    params = assign_params(circuit, guess, free_params)
    
    write_input_file('INFL', freqs, Z, params, comment)
    timedout = run_LEVM(LEVM_path, timeout = timeout)
    if timedout == 1:
        return 0
    fits = extract_params('OUTIN', params)
    
    os.chdir(original_path)
    
    return fits












#%% Testing



if __name__ == '__main__':
    import matplotlib.pyplot as plt
    import re
    import time
    params = []
    kets = []
    
    # d = {'Rs': 543,
    #         'Rct': 3.44050e+004,
    #         'Cad': 4.79434e-007,
    #         'phi':8.40000e-001,
    #         'Cdl':2.25e-007}   
    
    # free_params = {'Rs': 1,
    #         'Rct': 1,
    #         'Cad': 1,
    #         'phi':0,
    #         'Cdl':1}
    
    
    d = {'R1': 100,
         'R2': 1000,
         'C1': 1e-6,}
    
    free_params = {'R1': 1,
         'R2': 1,
         'C1': 1,}
    
    file = r'C:/Users/broehrich/Desktop/EIS Output/2023-05-22/autosave/12-31-04/000001.txt'
    f, real, im = np.loadtxt(file, skiprows=1, unpack=True)
    Z = real + 1j*im
    
    fits = LEVM_fit(f, Z, d, 'RRC', free_params)
    print(fits)

    # folder = r'C:\Users\BRoehrich\Desktop\EIS fitting\test'
    # true_Rcts = []
    # R = 30000
    # for _ in range(400):
    #     R -= 0.005*R
    #     true_Rcts.append(R)
        
    # fits = r'C:/Users/BRoehrich/Desktop/EIS fitting/test/test.par'
    # _, _, Rs, meisp_Rcts, Cads, phis, Cdls = np.loadtxt(fits, unpack=True)
    
    # folder = r'C:\Users\BRoehrich\Desktop\EIS fitting\real'
    # fits = r'C:\Users\BRoehrich\Desktop\EIS fitting\real\real.par'
    # _, _, Rs, meisp_Rcts, Cads, phis, Cdls = np.loadtxt(fits, unpack=True)
         
    # pattern = r"^\d{4}s\.txt$"
    # i = 0
    # fit_times = []
    # for file in os.listdir(folder):
    #     if i > 100:
    #         break
    #     if not re.match(pattern, file):
    #         continue
        
    #     f, real, im = np.loadtxt(os.path.join(folder,file), skiprows=1, unpack=True)
    #     Z = real + 1j*im
        
    #     if i == 0:
    #         d = d
    #     else:
    #         d = params[i-1]
    #     # d['Rs'] = re[-1]
        
    #     st = time.time()
    #     fits = LEVM_fit(f, Z, d, 'Randles_adsorption', free_params)
    #     fit_times.append(time.time() - st)
    #     print(i, fits)
        
    #     params.append(fits)
    #     ket = 1/(2*fits['Rct']*fits['Cad'])
    #     kets.append(ket)
        
    #     i += 1
    
    # fig, ax = plt.subplots(figsize=(5,5), dpi=150)
    # ax.plot([p['Rct'] for p in params], label='LEVM')
    # ax.plot(meisp_Rcts, label='MEISP')
    # # ax.plot(true_Rcts, label='Actual')
    # ax.set_xlabel('File #')
    # ax.set_ylabel(r'$R_{ct}$/ $\Omega$')
    # ax.legend()
    # fig.tight_layout()
    
    # print(f'average fit time: {np.mean(fit_times):0.4f}')
    
                                    
                            
    

