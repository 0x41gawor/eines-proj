class Intent:
    def __init__(self, flow, limit):
        self.flow = flow
        self.limit = limit
    
    def __str__(self):
        return "Intent [H{}<->H{}, {}ms]".format(self.flow.h_src, self.flow.h_dst, self.limit)
    
class IntentPolicer:
    def __init__(self, networkPolicer, networkMonitor):
        self.networkPolicer = networkPolicer
        self.networkMonitor = networkMonitor

    def handle_intent(self, intent):
        route1_delay = self.networkMonitor.s1_s2_delay
        route2_delay = self.networkMonitor.s1_s3_delay
        route3_delay = self.networkMonitor.s1_s4_delay
        print "IntentPolicer: intent.limit", intent.limit
        print "IntentPolicer: Route1.delay", route1_delay
        print "IntentPolicer: Route2.delay", route2_delay
        print "IntentPolicer: Route3.delay", route3_delay

        if intent.limit > route1_delay:
            print "IntentPolicer: route1 is matching the requirement"
            self.networkPolicer.enforce_route_for_flow(1, intent.flow)
        elif intent.limit > route2_delay:
            print "IntentPolicer: route2 is matching the requirement"
            self.networkPolicer.enforce_route_for_flow(2, intent.flow)
        elif intent.limit > route3_delay:
            print "IntentPolicer: route3 is matching the requirement"
            self.networkPolicer.enforce_route_for_flow(3, intent.flow)
        else:
            print "IntentPolicer: No route is marching the requirement"
        
        self.networkPolicer.balance()

