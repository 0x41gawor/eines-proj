class Intent:
    def __init__(self, flow, limit):
        self.flow = flow
        self.limit = limit
    
    def __str__(self):
        return "Flow [H{}<->H{}, {}ms]".format(self.flow.h_src, self.flow.h_dst, self.limit)