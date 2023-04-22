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
def FlowEntryPortPort(in_port, out_port):
    msg = of.ofp_flow_mod()
    msg.priority =10
    msg.idle_timeout = 0
    msg.hard_timeout = 0
    msg.match.in_port = in_port
    msg.match.dl_type=0x0800
    msg.actions.append(of.ofp_action_output(port = out_port))
    return msg

# Ta funkcja jest dla pakietow IP, dl_type=0x0800 na to wskazuje
def FlowEntryAddressPort(dst_address, out_port):
    msg = of.ofp_flow_mod()
    msg.priority =100
    msg.idle_timeout = 0
    msg.hard_timeout = 0
    msg.match.dl_type = 0x0800	
    msg.match.nw_dst = dst_address
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

def handle_packetIn_s1(event):
    packet = event.parsed

    ## ARP -------------------------------
    a=packet.find('arp')					# If packet object does not encapsulate a packet of the type indicated, find() returns None
    if a:
      if a.protodst=="10.0.0.4":
         msg = AppendPacketOutWithPort(event.ofp, 4)
         event.connection.send(msg)
      if a.protodst=="10.0.0.5":
         msg = AppendPacketOutWithPort(event.ofp, 4)
         event.connection.send(msg)
      if a.protodst=="10.0.0.6":
         msg = AppendPacketOutWithPort(event.ofp, 4)
         event.connection.send(msg)
      if a.protodst=="10.0.0.1":
         msg = AppendPacketOutWithPort(event.ofp, 1)
         event.connection.send(msg)
      if a.protodst=="10.0.0.2":
         msg = AppendPacketOutWithPort(event.ofp, 2)
         event.connection.send(msg)
      if a.protodst=="10.0.0.3":
         msg = AppendPacketOutWithPort(event.ofp, 3)
         event.connection.send(msg)
    ## IP ---------------------------------

    msg = FlowEntryPortPort(in_port=1, out_port=4)
    event.connection.send(msg)
    msg = FlowEntryPortPort(in_port=2, out_port=4)
    event.connection.send(msg)
    msg = FlowEntryPortPort(in_port=3, out_port=4)
    event.connection.send(msg)

    msg = FlowEntryAddressPort(dst_address="10.0.0.1", out_port=1)
    event.connection.send(msg)
    msg = FlowEntryAddressPort(dst_address="10.0.0.2", out_port=2)
    event.connection.send(msg)
    msg = FlowEntryAddressPort(dst_address="10.0.0.3", out_port=3)
    event.connection.send(msg)

def handle_packetIn_s2(event):

    # ARP ----------------------------------------------
    msg = FlowEntryArpPortPort(in_port=1, out_port=2)
    event.connection.send(msg)

    msg = FlowEntryArpPortPort(in_port=2, out_port=1)
    event.connection.send(msg)
    
    # IP ----------------------------------------------
    msg = FlowEntryPortPort(in_port=1, out_port=2)
    event.connection.send(msg)

    msg = FlowEntryPortPort(in_port=2, out_port=1)
    event.connection.send(msg)

def handle_packetIn_s3(event):
    
    # ARP ----------------------------------------------
    msg = FlowEntryArpPortPort(in_port=1, out_port=2)
    event.connection.send(msg)

    msg = FlowEntryArpPortPort(in_port=2, out_port=1)
    event.connection.send(msg)
    
    # IP ----------------------------------------------
    msg = FlowEntryPortPort(in_port=1, out_port=2)
    event.connection.send(msg)

    msg = FlowEntryPortPort(in_port=2, out_port=1)
    event.connection.send(msg)

def handle_packetIn_s4(event):
    
    # ARP ----------------------------------------------
    msg = FlowEntryArpPortPort(in_port=1, out_port=2)
    event.connection.send(msg)

    msg = FlowEntryArpPortPort(in_port=2, out_port=1)
    event.connection.send(msg)
    
    # IP ----------------------------------------------
    msg = FlowEntryPortPort(in_port=1, out_port=2)
    event.connection.send(msg)

    msg = FlowEntryPortPort(in_port=2, out_port=1)
    event.connection.send(msg)

def handle_packetIn_s5(event):
    packet = event.parsed
    ## ARP ---------------------------
    a=packet.find('arp')					# If packet object does not encapsulate a packet of the type indicated, find() returns None
    if a:
      if a.protodst=="10.0.0.4":
         msg = AppendPacketOutWithPort(event.ofp, 4)
         event.connection.send(msg)
      if a.protodst=="10.0.0.5":
         msg = AppendPacketOutWithPort(event.ofp, 5)
         event.connection.send(msg)
      if a.protodst=="10.0.0.6":
         msg = AppendPacketOutWithPort(event.ofp, 6)
         event.connection.send(msg)
      if a.protodst=="10.0.0.1":
         msg = AppendPacketOutWithPort(event.ofp, 1)
         event.connection.send(msg)
      if a.protodst=="10.0.0.2":
         msg = AppendPacketOutWithPort(event.ofp, 1)
         event.connection.send(msg)
      if a.protodst=="10.0.0.3":
         msg = AppendPacketOutWithPort(event.ofp, 1)
         event.connection.send(msg)

    ## IP -----------------------------------------------

    msg = FlowEntryPortPort(in_port=4, out_port=1)
    event.connection.send(msg)
    msg = FlowEntryPortPort(in_port=5, out_port=1)
    event.connection.send(msg)
    msg = FlowEntryPortPort(in_port=6, out_port=1)
    event.connection.send(msg)

    msg = FlowEntryAddressPort("10.0.0.4", 4)
    event.connection.send(msg)
    msg = FlowEntryAddressPort("10.0.0.5", 5)
    event.connection.send(msg)
    msg = FlowEntryAddressPort("10.0.0.6", 6)
    event.connection.send(msg)