from pox.core import core
import pox.openflow.libopenflow_01 as of
from pox.lib.util import dpidToStr
from pox.lib.addresses import IPAddr, EthAddr
from pox.lib.packet.arp import arp
from pox.lib.packet.ethernet import ethernet, ETHER_BROADCAST
from pox.lib.packet.packet_base import packet_base
from pox.lib.packet.packet_utils import *
import pox.lib.packet as pkt
from pox.lib.recoco import Timer
import time

# Ta funkcja jest dla pakietow IP, dl_type=0x0800 na to wskazuje
def FlowEntryInPortOutPort(in_port, out_port):
    msg = of.ofp_flow_mod()
    msg.priority =10
    msg.idle_timeout = 0
    msg.hard_timeout = 0
    msg.match.in_port = in_port
    msg.match.dl_type=0x0800
    msg.actions.append(of.ofp_action_output(port = out_port))
    return msg

# Ta funkcja jest dla pakietow IP, dl_type=0x0800 na to wskazuje
def FlowEntryInAddressOutPort(dst_address, out_port):
    msg = of.ofp_flow_mod()
    msg.priority =100
    msg.idle_timeout = 0
    msg.hard_timeout = 0
    msg.match.dl_type = 0x0800	
    msg.match.nw_dst = dst_address
    msg.actions.append(of.ofp_action_output(port = out_port))
    return msg

def FlowEntryInPortAddressOutPort(in_port, dst_address, out_port):
    msg = of.ofp_flow_mod()
    msg.priority =10
    msg.idle_timeout = 0
    msg.hard_timeout = 0
    msg.match.in_port = in_port
    msg.match.nw_dst = dst_address
    msg.match.dl_type=0x0800
    msg.actions.append(of.ofp_action_output(port = out_port))
    return msg

# Ten msg mowi jak forwardowac pakiety ARP ruterom S2, S3, S4
def FlowEntryArpPortPort(in_port, out_port):
    msg = of.ofp_flow_mod()
    msg.priority =10
    msg.idle_timeout = 0
    msg.hard_timeout = 0
    msg.match.in_port = in_port
    msg.match.dl_type=0x0806	
    msg.actions.append(of.ofp_action_output(port = out_port))
    return msg

# Ten PacketOut mowi switchom S1 i S5 na jakim porcie maja  jaki adres IP
def AppendPacketOutWithPort(packet, out_port):
    msg = of.ofp_packet_out(data=packet)			# Create packet_out message; use the incoming packet as the data for the packet out
    msg.actions.append(of.ofp_action_output(port=out_port))		# Add an action to send to the specified port
    return msg

class Flow:
    def __init__(self, h_src, h_dst):
        self.h_src = h_src
        self.h_dst = h_dst

    def __str__(self):
        return "Flow[H{}<->H{}]".format(self.h_src, self.h_dst)
    
    def is_equal(self, flow):
        if flow==None:
            return False

        if self.h_src == flow.h_src and self.h_dst == flow.h_dst:
            return True
        return False

class NetworkPolicer:
    def __init__(self):
        self.route_flow_counter = [0, 0, 0]
        self.s1_dpid = 0
        self.s5_dpid = 0
        self.openflow = None
        self.flow_route_map = []
        self.intented_flow = None
        self.intented_flow_route = 0
        self.intented_flow_limit = 0
    
    # identyfikuje flow, narazie w switchu 1 i chyba tyle wystarczy
    def identify_flow(self, event, s_dpid):
        h_src = 0
        h_dst = 0
        packet = event.parsed.find('ipv4')
        if s_dpid == self.s1_dpid:
            if packet.srcip == "10.0.0.1":
                h_src = 1
            elif packet.srcip == "10.0.0.2":
                h_src = 2
            elif packet.srcip == "10.0.0.3":
                h_src = 3
            if packet.dstip == "10.0.0.4":
                h_dst = 4
            elif packet.dstip == "10.0.0.5":
                h_dst = 5
            elif packet.dstip == "10.0.0.6":
                h_dst = 6
        return Flow(h_src, h_dst)
    # zwieksza counter dla danej route
    # by passing `-1` as `n` you can decrement
    def increment_route_counter(self, route, n):
        self.route_flow_counter[route-1] += n

    # Zwraca najmniej obciazona sciezke. w przypadku remisu, zwraca route1, potem route 2, potem route 3
    # Oparte to jest o liste route_flow_counter, kilka jej postaci oraz output metody []
    def select_route(self):
        min_value = min(self.route_flow_counter)
        min_index = self.route_flow_counter.index(min_value)
        return min_index+1
    # Instalacja table flowow dla switchw tranzytowych, czeli port 1 na 2 i vice versa
    def install_transit_routing(self, event):
         # ARP ----------------------------------------------
        msg = FlowEntryArpPortPort(in_port=1, out_port=2)
        event.connection.send(msg)
        msg = FlowEntryArpPortPort(in_port=2, out_port=1)
        event.connection.send(msg)
        
        # IP ----------------------------------------------
        msg = FlowEntryInPortOutPort(in_port=1, out_port=2)
        event.connection.send(msg)
        msg = FlowEntryInPortOutPort(in_port=2, out_port=1)
        event.connection.send(msg)

    # Instaluje flow `flow` na sciezce route
    # Jako flow podajesz obiekt klasy Flow
    # a jak route numer sciezki (1,2 lub 3)
    def install(self, flow, route):
        # S1
        msg = FlowEntryInPortAddressOutPort(in_port=flow.h_src, dst_address="10.0.0.{}".format(flow.h_dst), out_port=route+3)
        self.openflow.getConnection(self.s1_dpid).send(msg)
        msg = FlowEntryInPortAddressOutPort(in_port=route+3, dst_address="10.0.0.{}".format(flow.h_src), out_port=flow.h_src)
        self.openflow.getConnection(self.s1_dpid).send(msg)
        # S5
        msg = FlowEntryInPortAddressOutPort(in_port=flow.h_dst, dst_address="10.0.0.{}".format(flow.h_src), out_port=route)
        self.openflow.getConnection(self.s5_dpid).send(msg)
        msg = FlowEntryInPortAddressOutPort(in_port=route, dst_address="10.0.0.{}".format(flow.h_dst), out_port=flow.h_dst)
        self.openflow.getConnection(self.s5_dpid).send(msg)

    def enforce_route_for_flow(self, route, flow):
        if self.does_flow_exist(flow) == True:
            # na liscie podmieniamy route dla flow
            self.replace_flow_route(flow, route)
            self.install(flow, route)
        else:
            # instalacja flow w sieci
            self.install(flow, route)
            # powiazanie flow i jego sciezki 
            self.flow_route_map.append((flow, route))
            self.increment_route_counter(route, 1)
        self.show_flow_route_map()

    def balance(self):
        print "NetworkPolicer: Current State", self.route_flow_counter
        print "NetworkPolicer: Do we need to balance?", self.do_balance()
        if self.do_balance() == True:
            max_loaded_route = self.max_route()
            min_loaded_route = self.min_route()
            moved_flow = self.select_flow_from_route(max_loaded_route)
            print "NetworkPolicer: Moved flow", moved_flow
            self.replace_flow_route(moved_flow, min_loaded_route)
            print "NetworkPolicer: After balance state", self.route_flow_counter
            self.show_flow_route_map()
        else:
            print "NetworkPolicer: No need for balance"

    def do_balance(self):
        if abs(self.route_flow_counter[0]-self.route_flow_counter[1]) > 1:
            return True
        if abs(self.route_flow_counter[0]-self.route_flow_counter[2]) > 1:
            return True
        if abs(self.route_flow_counter[2]-self.route_flow_counter[1]) > 1:
            return True
        return False

    # zwraca ktory nr route ma najwiecej flow
    def max_route(self):
        max = 0
        index = 0
        i = 1
        for x in self.route_flow_counter:
            if x > max:
                max = x
                index = i
            i+=1
        return index

    # zwraca ktory route ma najmniej flow
    def min_route(self):
        min = 100 
        index = 0
        i = 1
        for x in self.route_flow_counter:
            if x < min:
                min = x
                index = i
            i+=1
        return index
    
    def select_flow_from_route(self, route):
        for temp_flow, temp_route in self.flow_route_map:
            if temp_route == route and (not temp_flow.is_equal(self.intented_flow)):
                return temp_flow
            

    def replace_flow_route(self, flow, new_route):
        index = 0
        old_route = 0
        for x in range(len(self.flow_route_map)):
            flow_from_list, old_route = self.flow_route_map[x]
            if flow_from_list.is_equal(flow):
                break
            index+=1
        # teraz w index mamy index elementu ktory trzeba wyrzucic
        self.flow_route_map.pop(index)
        self.flow_route_map.append((flow, new_route))
        # dekrementujemy stary route
        self.increment_route_counter(old_route, -1)
        # inkrementujemy nowy  route
        self.increment_route_counter(new_route, 1)


    def does_flow_exist(self, checked_flow):
        a = self.flow_route_map
        for x in range(len(a)):
            flow, route = a[x]
            if flow.is_equal(checked_flow):
                return True
        return False    
        

    def show_flow_route_map(self):
        a = self.flow_route_map

        for x in range(len(a)):
            flow, route = a[x]
            if flow.is_equal(self.intented_flow):
                print "NetworkPolicer: [*", flow, "route", route,"*]"
            else:
                print "NetworkPolicer: [ ", flow, "route", route, " ]"

    def install_arp_s1(self, event, packet):
        if packet.protodst=="10.0.0.4":
            msg = AppendPacketOutWithPort(event.ofp, 4)
            event.connection.send(msg)
        if packet.protodst=="10.0.0.5":
            msg = AppendPacketOutWithPort(event.ofp, 4)
            event.connection.send(msg)
        if packet.protodst=="10.0.0.6":
            msg = AppendPacketOutWithPort(event.ofp, 4)
            event.connection.send(msg)
        if packet.protodst=="10.0.0.1":
            msg = AppendPacketOutWithPort(event.ofp, 1)
            event.connection.send(msg)
        if packet.protodst=="10.0.0.2":
            msg = AppendPacketOutWithPort(event.ofp, 2)
            event.connection.send(msg)
        if packet.protodst=="10.0.0.3":
            msg = AppendPacketOutWithPort(event.ofp, 3)
            event.connection.send(msg)
    def install_arp_s5(self, event, packet):
        if packet.protodst=="10.0.0.4":
            msg = AppendPacketOutWithPort(event.ofp, 4)
            event.connection.send(msg)
        if packet.protodst=="10.0.0.5":
            msg = AppendPacketOutWithPort(event.ofp, 5)
            event.connection.send(msg)
        if packet.protodst=="10.0.0.6":
            msg = AppendPacketOutWithPort(event.ofp, 6)
            event.connection.send(msg)
        if packet.protodst=="10.0.0.1":
            msg = AppendPacketOutWithPort(event.ofp, 1)
            event.connection.send(msg)
        if packet.protodst=="10.0.0.2":
            msg = AppendPacketOutWithPort(event.ofp, 1)
            event.connection.send(msg)
        if packet.protodst=="10.0.0.3":
            msg = AppendPacketOutWithPort(event.ofp, 1)
            event.connection.send(msg)