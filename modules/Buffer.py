from collections import deque



class ADCDataBuffer():
    '''
    Buffer to facilitate data transfer between Oscilloscope and DataProcessing
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

