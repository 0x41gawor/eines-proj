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
            print "IntentPolicer: route 1 is matching the requirement"
            self.networkPolicer.intented_flow = intent.flow
            self.networkPolicer.intented_flow_route = 1
            self.networkPolicer.intented_flow_limit = intent.limit
            self.networkPolicer.enforce_route_for_flow(1, intent.flow)
        elif intent.limit > route2_delay:
            print "IntentPolicer: route 2 is matching the requirement"
            self.networkPolicer.intented_flow = intent.flow
            self.networkPolicer.intented_flow_route = 2
            self.networkPolicer.intented_flow_limit = intent.limit
            self.networkPolicer.enforce_route_for_flow(2, intent.flow)
        elif intent.limit > route3_delay:
            print "IntentPolicer: route 3 is matching the requirement"
            self.networkPolicer.intented_flow = intent.flow
            self.networkPolicer.intented_flow_route = 3
            self.networkPolicer.intented_flow_limit = intent.limit
            self.networkPolicer.enforce_route_for_flow(3, intent.flow)
        else:
            print "IntentPolicer: No route is marching the requirement"
        
        self.networkPolicer.balance()

    def trigger_policy_procedure(self):
        # Ta metoda wykonuje sie tylko wtedy gdy isntieje intented flow
        if self.networkPolicer.intented_flow != None:
            # Zczytanie delayi na poszczegolinych routeach
            route_delays = []
            route_delays.append(self.networkMonitor.s1_s2_delay) # route1_delay --> index 0
            route_delays.append(self.networkMonitor.s1_s3_delay) # route2_delay --> index 1
            route_delays.append(self.networkMonitor.s1_s4_delay) # route3_delay --> index 2
            # Zczytanie limit oraz route intented flow
            limit = self.networkPolicer.intented_flow_limit
            route = self.networkPolicer.intented_flow_route

            if limit > route_delays[route-1]:
                # Jesli tak to NIC
                print "IntentPolicer: delay {}ms for intented flow {}ms is satisfied".format(route_delays[route-1], self.networkPolicer.intented_flow_limit)
            else:
                # Jesli nie to sprawdza czy jest jakis route, ktory spelnia limit
                new_route_for_intented_flow = self.get_route_with_lower_delay(limit)
                # Jesli tak, to przenosimy intented_flow na route, ktory spelnia wymagania
                if new_route_for_intented_flow != None:
                    print "IntentPolicer: delay {}ms for intented flow {}ms is too high".format(route_delays[route-1], self.networkPolicer.intented_flow_limit)
                    print "IntentPolicer: Moving flow..."
                    self.networkPolicer.enforce_route_for_flow(new_route_for_intented_flow, self.networkPolicer.intented_flow)
                    self.networkPolicer.balance()
                else:
                    #jesli nie to komunikat, ze nie da sie spelnic requirements for intented flow
                    print "IntentPolicer: delay for intented flow cannot be satisfied"
                
    # Sprawdza czy istnieje route, ktory spelnia dany limit, jesli tak to zwraca jego numer, jesli nie to zwraca None
    def get_route_with_lower_delay(self, limit):
        # Czy route 1 ok?
        if self.networkMonitor.s1_s2_delay < limit:
            return 1
        # Czy route 2 ok?
        elif self.networkMonitor.s1_s3_delay < limit:
            return 2
        # Czy route 3 OK?
        elif self.networkMonitor.s1_s4_delay < limit:
            return 3
        # Zaden route nie pasuje :((
        else:
            return None


