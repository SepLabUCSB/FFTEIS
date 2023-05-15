import tkinter as tk
from tkinter import *
from tkinter.ttk import *



def ask_duration_popup():
    popup = Toplevel()
    popup.title('Record for...')
    popup.attributes('-topmost', 1)
    
    frame = Frame(popup)
    frame.grid(row=0, column=0)
                    
    hrs = StringVar(value='0')
    Entry(frame, textvariable=hrs, width=3).grid(row=0, column=0, sticky=(W,E))
    Label(frame, text='hr ').grid(column=1, row=0, sticky=(W,E))
    
    mins = StringVar(value='0')
    Entry(frame, textvariable=mins, width=3).grid(row=0, column=2, sticky=(W,E))
    Label(frame, text='min ').grid(column=3, row=0, sticky=(W,E))
    
    secs = StringVar(value='0')
    Entry(frame, textvariable=secs, width=3).grid(row=0, column=4, sticky=(W,E))
    Label(frame, text='s ').grid(column=5, row=0, sticky=(W,E))
    
    Button(frame, text='Start', command=popup.destroy).grid(
        row=1, column=2, columnspan=2, sticky=(W,E))
    
    popup.wait_window()
    
    hrs  = hrs.get()
    mins = mins.get()
    secs = secs.get()
    try:
        hrs, mins, secs = float(hrs), float(mins), float(secs)
    except:
        print('Invalid inputs!')
        return None
    
    return 60*60*hrs + 60*mins + secs


def message_popup(message):
    popup = Toplevel()
    popup.attributes('-topmost', 1)
    frame = Frame(popup)
    frame.grid(row=0, column=0)
    Label(frame, text=message).grid(column=0, row=0, columnspan=3, sticky=(W,E))
    Button(frame, text='OK', command=popup.destroy).grid(row=1, column=1)
    popup.wait_window()
    return


def confirm_dialog(msg=''):
    '''
    Simple OK/ Cancel confirm dialog. returns True/ False
    '''
    class popup:
        def __init__(self, msg):
            self.pop = Toplevel()
            self.pop.attributes('-topmost', 1)
            frame = Frame(self.pop)
            frame.grid(row=0, column=0)
            Label(frame, text=msg).grid(column=0, row=0, columnspan=2)
            Button(frame, text='OK', command=self.ok).grid(row=1, column=0)
            Button(frame, text='Cancel', command=self.cancel).grid(row=1, column=1)
        
        def ok(self):
            self.result = True
            self.pop.destroy()
        
        def cancel(self):
            self.result = False
            self.pop.destroy()
    
    d = popup(msg)
    d.pop.wait_window()
    return d.result
    
    
    