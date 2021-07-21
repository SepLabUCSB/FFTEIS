import matplotlib.pyplot as plt
import matplotlib
import numpy as np
import pandas as pd
from matplotlib.widgets import Button
from matplotlib.widgets import Slider
import tkinter as tk
from tkinter import filedialog
matplotlib.use('qt5agg')
plt.ion() # Interactive mode
colors = plt.rcParams['axes.prop_cycle'].by_key()['color']


"""
Python script for interactive analysis of single entity echem step data.

Run file, select data files to analyze.

The program will automatically try to find steps (with >2% 

relative change). Click to select or deselect step points.

Click "Export" when finished to save a list of all step sizes

to a folder of your choice.

"""



def get_data(file):
    df = df = pd.read_fwf(file, skiprows=1, headers=0,
                          names=('t', 'i'))
    df['i'] = df['i']/1000 #convert mA -> A
    df = df[df['t'] > 5]
    
    df = df.groupby(np.arange(len(df))//10).mean() #compress to 100 Hz

    return df



class StepPicker(object):
    """Based on
    https://scipy-cookbook.readthedocs.io/items/Matplotlib_Interactive_Plotting.html
    """

    def __init__(self, xdata, ydata, points=[], avg = None, 
                 ax=None, steps=[]):
        self.xdata = np.array(xdata)
        self.ydata = np.array(ydata)
        self.criticalPoints = dict()
        self.steps = steps
        
        if ax is None:
            self.ax = plt.gca()
        else:
            self.ax = ax
        
        # initialize avg line
        self.line, = self.ax.plot([self.xdata[0]], [self.ydata[0]]) 
        
        self.avg = avg
        self.draw_average()
        
        for (x,y) in points:
            # If reinitializing, redraw critical points
            self.drawPoints(ax, x, y)   
        
        if len(points) == 0:
            # Else detect and draw points
            foundPoints = self.detect_steps()
            for (x,y) in foundPoints:
                self.drawPoints(ax, x, y)



    
    def __call__(self, event):
        '''
        Called on mouse click in graph axes
        
        Prioritizing removing marked point near cursor
        (+- xtol seconds)
        
        Otherwise add a new point at (x, y(x))
        '''
        xtol = 0.5
        deleted = False
        if event.inaxes and fig.canvas.manager.toolbar._active is None:
            clickX = event.xdata
            if (self.ax is None) or (self.ax is event.inaxes):
                # Prioritizing removing marked point
                for (x,y) in list(self.criticalPoints):
                    if (clickX-xtol < x < clickX+xtol):
                        self.drawPoints(event.inaxes, x, y)
                        deleted = True
                    else:
                        continue
                # Otherwise, add a new point
                if not deleted:
                    i = np.abs(self.xdata-clickX).argmin()
                    this_x = self.xdata[i]
                    this_y = self.ydata[i]
                    self.drawPoints(event.inaxes, this_x, this_y)

         

    
    def drawPoints(self, ax, x, y):
        """
        Draw or remove the point on the plot
        """
        if (x, y) in self.criticalPoints:
            # Remove point
            markers = self.criticalPoints[(x, y)]
            for m in markers:
                m.set_visible(False)
                m.remove()
            self.criticalPoints.pop((x,y), None)
            self.ax.figure.canvas.draw_idle()

            
        else:
            # Draw new point, add to criticalPoints dict
            t = ax.text(x, y, "",)
            m = ax.scatter([x], [y], marker='d', c='r', zorder=100)
            self.criticalPoints[(x, y)] = (t, m)
            self.ax.figure.canvas.draw_idle()
    
    
    
    
    def detect_steps(self, thresh=0.02):
        '''
        Step detection algorithm
        
        Finds points where step heights (determined by
            median values between points) are > thresh param.

        '''
        signals = np.ones(len(self.ydata))
        signals[0] = 0
           
        min_delta = 0
        n = 1
     
        
        while min_delta < thresh:
             if n > 5:
                 # Termination sequence if stuck
                 break
            
             # Initialize, find step points
             points = [0]
             avg = np.zeros(len(self.ydata))
             deltas = np.zeros(len(self.ydata))
             for i in range(len(signals)):
                 if signals[i] == 1:
                     points.append(i)
             points.append(len(signals))        
            
             # Get values between each point
             for c in range(0, len(points)-1):
                 index = points[c]
                 next_index = points[c+1]
                 for i in range(index, next_index):
                      avg[i] = np.median(self.ydata[index: next_index])
                      # m, b = np.polyfit(self.xdata[index:next_index+1], 
                      #                   self.ydata[index:next_index+1], 1)
                      # avg[i] = m*i + b
    
           
             # Remove steps with delta Z < thresh/2
             for i in range(len(self.ydata)-1):
                 deltas[i] = abs(avg[i+1]-avg[i])/avg[i]
                 if deltas[i] > thresh/2:
                     signals[i+1] = 1
                 else:
                     signals[i+1] = 0
             
            
             
             for i in range(len(signals)-1):
                 if signals[i] == 1:
                     signals[i-1] = 0 
                     deltas[i] = abs(avg[i-1]-avg[i+1])/avg[i-1]
                 else:
                     deltas[i] = 0
            
            
             l = []
             for delta in deltas:
                 if delta != 0:
                     l.append(delta)
            
             if not l:
                 min_delta = 1
             else:
                 min_delta = min(l)
            
             n += 1
        

        indices = [i for i in range(len(signals)) if signals[i]==1]
        points = [(self.xdata[i], self.ydata[i]) for i in indices]
        
        return points
    
    
    
    
    def calculate_steps(self, button):
        '''
        Refines step locations

        '''
        delta = np.zeros(len(self.xdata))
        self.avg = np.zeros(len(self.xdata))
        
        # Refine step locations
        for i in range(len(self.xdata)-1):
            delta[i] = abs((self.ydata[i+1]-self.ydata[i])/self.ydata[i])
            
        for (x,y) in list(self.criticalPoints):  
            # find largest local step, search +- m points
            m = 10
            xi = np.where(self.xdata == x)[0][0] #convert to index
            n = np.where(delta == max(delta[xi-m:xi+m+1]))[0][0]
            if not n == xi:
                for m in self.criticalPoints[(x,y)]:
                    m.remove()
                self.criticalPoints.pop((x,y), None)
                self.drawPoints(self.ax, self.xdata[n], self.ydata[n])
        
        
        # Fit data between steps to line
        indices = [np.where(self.xdata == x)[0][0] 
                   for (x,y) in list(self.criticalPoints)]
    
        indices.insert(0,0)
        indices.append(len(self.xdata-1))
        indices.sort()
        
        for i in range(len(indices)-1):
            index = indices[i]
            next_index = indices[i+1]
            for i in range(index, next_index):
                # m, b = np.polyfit(self.xdata[index+2:next_index-2], 
                #                   self.ydata[index+2:next_index-2], 1)
                # self.avg[i] = m*i + b
                self.avg[i] = np.median(self.ydata[index+5: next_index-5])
            if index != 0:
                self.avg[index] = self.avg[index-1]
                
        # Draw result on graph and save step sizes 
        self.draw_average()
        self.get_steps()
    
        
    
    
    def draw_average(self):
        # Redraw smoothed step line
        self.line.set_data(self.xdata, self.avg)
        self.line.figure.canvas.draw()
    
    
    
    
    def get_steps(self):
        # Save current step sizes to self.steps
        self.steps = []
        for (x,y) in self.criticalPoints:
            i = np.where(self.xdata==x)[0][0]
            step = (self.avg[i+1]-self.avg[i])/self.avg[i]
            self.steps.append(step)


class Index:
    '''
    Class for cycling through multiple graphs
    '''
    
    global files
    
    
    def __init__(self):
        

        self.ind = 0
        self.sp = dict() # sp[i] is StepPicker obj
        
        self.slider = dict()
        
        i = self.ind % len(files)
        self.i = i
        self.slider[i] =  0 #initialize slider index
        
        df = get_data(files[i])
        
        # Initialize plot
        name = files[i].split('/')[-1][:-4]
        self.x = df['t'].to_numpy()
        self.y = df['i'].to_numpy()
        self.line, = ax.plot(self.x, self.y, 'k-')
        ax.set_title('%s: %s'%((self.i+1), name), pad=15)
        
        self.sp[i] = StepPicker(self.x, self.y, ax=ax)
        self.cid = fig.canvas.mpl_connect('button_press_event', 
                                          self.sp[i])
        
        
        plt.show()
    
    
    
    def next(self, event):
        ax.clear()
        fig.canvas.mpl_disconnect(self.cid)
        self.ind += 1
        i = self.ind % len(files)  
        self.i = i
        
        name = files[i].split('/')[-1][:-4]
        ax.set_title('%s: %s'%((i+1), name), pad=15)
        
        if i not in self.sp:
            # Create new
            df = get_data(files[i])
            
            self.x = df['t'].to_numpy()
            self.y = df['i'].to_numpy()
            
            slider.set_val(self.x[0])
            self.line, = ax.plot(self.x, self.y, 'k-')
            self.sp[i] = StepPicker(self.x, self.y, ax=ax)
            
        else:
            # Reinitialize
            ind = self.slider[self.i]
            

            self.x = self.sp[i].xdata
            self.y = self.sp[i].ydata
            
            slider.set_val(self.x[ind])
            self.line, = ax.plot(self.sp[i].xdata[ind:], 
                                 self.sp[i].ydata[ind:], 'k-')
            
            self.sp[i].__init__(self.sp[i].xdata, self.sp[i].ydata, ax=ax, 
                                points=list(self.sp[i].criticalPoints), 
                                avg=self.sp[i].avg, steps = self.sp[i].steps)
            
        self.cid = fig.canvas.mpl_connect('button_press_event', self.sp[i])
        plt.show()
        
    
    
    
    def prev(self, event):
        ax.clear()
        fig.canvas.mpl_disconnect(self.cid)
        self.ind -= 1
        i = self.ind % len(files)
        self.i = i
        
        name = files[i].split('/')[-1][:-4]
        ax.set_title('%s: %s'%((i+1), name), pad=15)
        
        if i not in self.sp:
            # Create new
            df = get_data(files[i])
            
            self.x = df['t'].to_numpy()
            self.y = df['i'].to_numpy()
            
            slider.set_val(self.x[0])
            self.line, = ax.plot(self.x, self.y, 'k-')
            self.sp[i] = StepPicker(self.x, self.y, ax=ax)
            
        else:
            # Reinitialize
            ind = self.slider[self.i]

            self.x = self.sp[i].xdata
            self.y = self.sp[i].ydata
            
            slider.set_val(self.x[ind])
            self.line, = ax.plot(self.sp[i].xdata[ind:], 
                                 self.sp[i].ydata[ind:], 'k-')
            
            self.sp[i].__init__(self.sp[i].xdata, self.sp[i].ydata, ax=ax, 
                                points=list(self.sp[i].criticalPoints), 
                                avg=self.sp[i].avg, steps = self.sp[i].steps)
            
        self.cid = fig.canvas.mpl_connect('button_press_event', self.sp[i])
        
        plt.show()        

    
    def recalc(self, event):
        # i = self.ind % len(files)
        i = self.i
        ind = self.slider[i]
        
        try:
            self.sp[i].xdata = self.x[ind:]
            self.sp[i].ydata = self.y[ind:]

            self.sp[i].calculate_steps(event)
        
        except IndexError:
            print('ERROR: remove hanging points')
    
    
    def hist(self, event):
        # Display current histogram
        step_list = []
        for i in range(len(files)):
            try:
                steps = self.sp[i].steps
                for step in steps:
                    step_list.append(abs(step))
            except KeyError:
                print('No steps saved in File %s' %(i+1))
        
        if step_list:
            plt.figure(figsize=(5,5), dpi=100)
            bins = np.arange(0, 1, 0.005)
            plt.hist(step_list, bins, rwidth=0.8, 
                     label="N = %s" %len(step_list))
            plt.xlim(-0.005, 1.1*max(step_list))
            plt.xlabel('$\Delta$$I/I_{ss}$')
            plt.ylabel('Count')
            plt.legend(frameon=False)
            plt.show()
    
    
    def save(self, event):
        step_list = []
        for i in range(len(files)):
            try:
                steps = self.sp[i].steps
                for step in steps:
                    step_list.append(step)
            except KeyError:
                print('No steps saved in File %s' %(i+1))
        
        if step_list:
            root = tk.Tk()
            root.withdraw()
            root.attributes("-topmost", True)
            file = filedialog.asksaveasfilename(title='Save as...',
                                                defaultextension='.xlsx',
                                                filetypes=[('Excel', '.xlsx')])
    
    
            
            writer = pd.ExcelWriter(file, engine = 'xlsxwriter')
            out = pd.Series(step_list)
            out.to_excel(writer, index=False, header=False, startcol=0)
            writer.save()
            print('Saved as %s' %file)
        else:
            print('No steps!')
    
    
    def slider_changed(self, val):
        def find_nearest(array,value):
            idx = np.searchsorted(array, value, side="left")
            if idx > 0 and (idx == len(array) or abs(value - array[idx-1]) < abs(value - array[idx])):
                return array[idx-1]
            else:
                return array[idx]
        
        
        ind = np.where(self.x == find_nearest(self.x, val))[0][0]
        self.slider[self.i] = ind
        
        self.line.set_xdata(self.x[ind:])
        self.line.set_ydata(self.y[ind:])
        ax.figure.canvas.draw_idle()
        
        

root = tk.Tk()
root.withdraw()
root.attributes("-topmost", True)
files = filedialog.askopenfilenames(title='Select files', 
                                    filetypes=(('Text', '*.txt' ), 
                                               ('All files', '*')))

fig, ax = plt.subplots(figsize=(5,6), dpi=100)
plt.subplots_adjust(bottom=0.3)

callback = Index()

# Recalculate step sizes
axcalc = plt.axes([0.5, 0.1, 0.25, 0.075])
bcalc = Button(axcalc, 'Recalculate')
bcalc.on_clicked(callback.recalc)

# Next file
axnext = plt.axes([0.8, 0.1, 0.1, 0.075])
bnext = Button(axnext, 'Next')
bnext.on_clicked(callback.next)

# Previous file
axprev = plt.axes([0.35, 0.1, 0.1, 0.075])
bprev = Button(axprev, 'Prev')
bprev.on_clicked(callback.prev)

# Save as xlsx
axexport = plt.axes([0.1, 0.1, 0.2, 0.075])
bexport = Button(axexport, 'Export')
bexport.on_clicked(callback.save)

# Plot histogram
axplotbutton = plt.axes([0.1, 0.005, 0.3, 0.075])
histbutton = Button(axplotbutton, 'Plot histogram')
histbutton.on_clicked(callback.hist)

# Starting point slider
axslider = plt.axes([0.1, 0.2, 0.8, 0.025])
slider = Slider(axslider, '', callback.x[0], 
                callback.x[-1], valinit=callback.x[0])
slider.on_changed(callback.slider_changed)



