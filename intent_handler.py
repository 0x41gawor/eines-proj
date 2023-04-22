import signal
import random
import time



class Intent:
    def __init__(self, h_src, h_dst, limit):
        self.h_src = h_src
        self.h_dst = h_dst
        self.limit = limit
    
    def __str__(self):
        return "Flow [H{}<->H{}, {}ms]".format(self.h_src, self.h_dst, self.limit)
    
def rand_source_host():
    return random.randint(1,3)

def rand_destination_host():
    return random.randint(4,6)

def rand_delay_value():
    return random.randint(1,10)

def termination_handler(signum, frame):
    print ("Termination buttons clicked")
    intent = Intent(rand_source_host(), rand_destination_host(), rand_delay_value())
    print(intent)


signal.signal(signal.SIGTSTP, termination_handler)

while True:
    print("Dzienciol sobie leci")
    time.sleep(1)

