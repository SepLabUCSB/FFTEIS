import sys
import os
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from tkinter import filedialog

plt.style.use('../ffteis.mplstyle')

target = 'Vancomycin'

# file = filedialog.askopenfilename()
# if not file:
#     sys.exit()
file = r'C:/Users/BRoehrich/Desktop/06-13-2023-Vancomycin titration few datapoints/!fits16.csv'


#### Parse data file ####    
df = pd.read_csv(file)
df['ket'] = 1/(2*df['Rct']*df['Cads'])

sensors, concs = [], []
for fname in df['file']:
    fname = fname.replace('.txt', '')
    s, c = fname.split('_')
    if s not in sensors:
        sensors.append(s)
    if c not in concs:
        concs.append(c)
    
print(f'Found {len(sensors)} sensors, {len(concs)} concentrations.')
print(sensors)
print(concs)



#### Avg. and stdev. at each concentration ####

avgs = {}
stds = {}
for conc in concs:
    df2 = df[df['file'].str.contains(conc)]
    this_avg = {}
    this_std = {}
    for col in df2.columns:
        if col == 'file':
            continue
        this_avg[col] = np.mean(df2[col])
        this_std[col] = np.std(df2[col])    
    
    avgs[conc] = this_avg
    stds[conc] = this_std
    
    

avgdf = pd.DataFrame(avgs).transpose()
stddf = pd.DataFrame(stds).transpose()

avgdf = avgdf.rename_axis('conc').reset_index()
avgdf.astype({'conc': 'float'})
stddf = stddf.rename_axis('conc').reset_index()
stddf.astype('conc', 'float'})

combined_df = pd.concat(
    (avgdf, stddf.rename(lambda s:f'{s}_std', axis=1)),
    axis=1)
combined_df.to_csv(file.replace('.csv', '_result.csv'),
                   index=False)


concs = [float(c) for c in concs]


#### Making plots ####

if '0' in avgdf.index:
    concs.remove(0)
    avgdf.drop('0', axis=0, inplace=True)
    stddf.drop('0', axis=0, inplace=True)
    
concs.sort()
avgdf = avgdf.sort_values('conc', ascending=True)
stddf = stddf.sort_values('conc', ascending=True)


fig, ax = plt.subplots(figsize=(5,5), dpi=100)
for col in ['Rs', 'Rct', 'Cdl', 'Cads']:
    stddf[col] /= avgdf[col]
    avgdf[col] /= avgdf[col][0]
    ax.errorbar(concs, avgdf[col], stddf[col], marker='o', linestyle='--',
                capsize=4, elinewidth=2, label= col)

ax.set_xlabel(f'{target}/ M')
ax.set_ylabel('Normalized Parameter/ a.u.')
ax.set_xscale('log')
ax.legend()
fig.tight_layout()


fig, ax = plt.subplots(figsize=(5,5), dpi=100)
ax.errorbar(concs, avgdf['ket'], stddf['ket'], marker='o', linestyle='--',
                capsize=4, elinewidth=2)
ax.set_xlabel(f'{target}/ M')
ax.set_ylabel(r'$k_{et}$/ $s^{-1}$')
ax.set_xscale('log')
fig.tight_layout()




        
    



