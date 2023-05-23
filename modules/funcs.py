import numpy as np
import threading


def nearest(array, value):
    array = np.asarray(array)
    idx = (np.abs(array - value)).argmin()
    return idx, array[idx]


def run(func, args=()):
    t = threading.Thread(target=func, args=args)
    t.start()
    return t


