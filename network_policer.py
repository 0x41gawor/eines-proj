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
    def __init__(self, h1, h2):
        self.h1 = h1
        self.h2 = h2

    def __str__(self):
        return "Flow[H{}<->H{}]".format(self.h1, self.h2)
    
    def is_equal(self, flow):
        if self.h1 == flow.h1 and self.h2 == self.h2:
            return True
        return False

class NetworkPolicer:
    def __init__(self, openflow, s1_dpid, s5_dpid):
        self.route_flow_counter = [0, 0, 0]
        self.s1_dpid = s1_dpid
        self.s5_dpid = s5_dpid
        self.openflow = openflow
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
        msg = FlowEntryInPortAddressOutPort(in_port=flow.h1, dst_address="10.0.0.{}".format(flow.h2), out_port=route+3)
        self.openflow.getConnection(self.s1_dpid).send(msg)
        # S5
        msg = FlowEntryInPortAddressOutPort(in_port=flow.h2, dst_address="10.0.0.{}".format(flow.h1), out_port=route)
        self.openflow.getConnection(self.s5_dpid).send(msg)
