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
from pox.openflow.of_json import *
import time
import struct

class myproto(packet_base):
  #My Protocol packet struct
  """
  myproto class defines our special type of packet to be sent all the way along including the link between the switches to measure link delays;
  it adds member attribute named timestamp to carry packet creation/sending time by the controller, and defines the 
  function hdr() to return the header of measurement packet (header will contain timestamp)
  """
  #For more info on packet_base class refer to file pox/lib/packet/packet_base.py

  def __init__(self):
     packet_base.__init__(self)
     self.timestamp=0

  def hdr(self, payload):
     return struct.pack('!I', self.timestamp) # code as unsigned int (I), network byte order (!, big-endian - the most significant byte of a word at the smallest memory address)


class NetworkMonitor:

    def __init__(self):
        self.start_time = 0.0
        self.sent_time1=0.0
        self.sent_time2=0.0
        self.sent_time3=0.0
        self.sent_time4=0.0
        self.mytimer = 0
        self.t1=0.0
        self.t2_s2=0.0 # bylo OWDs2_ctrl
        self.t2_s3=0.0
        self.t2_s4=0.0

        self.s1_dpid = 0
        self.s2_dpid = 0
        self.s3_dpid = 0
        self.s4_dpid = 0
        self.s5_dpid = 0

        self.s1_s2_delay = 0
        self.s1_s3_delay = 0
        self.s1_s4_delay = 0


    # Measures T1 (from S1) or T2 (for S2, S3, S4)
    def handle_PortStats(self, event):
        received_time = time.time() * 1000*10 - self.start_time
        if event.connection.dpid == self.s1_dpid:
            self.t1=0.5*(received_time - self.sent_time1)
        elif event.connection.dpid == self.s2_dpid:
            self.t2_s2=0.5*(received_time - self.sent_time2)
        elif event.connection.dpid == self.s3_dpid:
            self.t2_s3=0.5*(received_time - self.sent_time3)
        elif event.connection.dpid == self.s4_dpid:
            self.t2_s4=0.5*(received_time - self.sent_time4)

    def handlePacketInProbe(self, event):

        packet = event.parsed
        if packet.type==0x5577: #0x5577 is unregistered EtherType, here assigned to probe packets
            received_time = time.time() * 1000*10 - self.start_time 
            if event.connection.dpid==self.s2_dpid:
                self.handle_probe_packetIn(packet=packet, received_time=received_time, OWDs1_ctrl=self.t1, other_s_OWD=self.t2_s2, switch_name="s2")
            elif event.connection.dpid==self.s3_dpid:
                self.handle_probe_packetIn(packet=packet, received_time=received_time, OWDs1_ctrl=self.t1, other_s_OWD=self.t2_s3, switch_name="s3")
            elif event.connection.dpid==self.s4_dpid:
                self.handle_probe_packetIn(packet=packet, received_time=received_time, OWDs1_ctrl=self.t1, other_s_OWD=self.t2_s4, switch_name="s4")

    def handle_probe_packetIn(self, packet, received_time, OWDs1_ctrl, other_s_OWD, switch_name):
        #Process a probe packet received in PACKET_IN message from 'switch2/3/4' (s2/s3/s4_dpid), previously sent to 'switch1' (s1_dpid) in PACKET_OUT.
        c=packet.find('ethernet').payload
        d,=struct.unpack('!I', c)  # note that d,=... is a struct.unpack and always returns a tuple
        #print "[ms*10]: received_time=", int(received_time), ", d=", d, ", OWDs1_ctrl=", int(OWDs1_ctrl), ", OWD",switch_name,"_ctrl=", int(other_s_OWD)
        delay = int(received_time - d - OWDs1_ctrl - other_s_OWD)/10
        # print "s1-",switch_name,"delay:", delay, "[ms]"# <=====" # divide by 10 to normalise to milliseconds
        if switch_name == "s2":
            print "NetworkMonitor: route 1 delay:", delay, "[ms]"
            self.s1_s2_delay = delay
        elif switch_name == "s3":
            print "NetworkMonitor: route 2 delay:", delay, "[ms]"
            self.s1_s3_delay = delay
        elif switch_name == "s4":
            print "NetworkMonitor: route 3 delay:", delay, "[ms]"
            self.s1_s4_delay = delay
    
    def print_delays(self):
        print "NetworkMonitor: s1-s2 delay:", self.s1_s2_delay, "[ms]"
        print "NetworkMonitor: s1-s3 delay:", self.s1_s3_delay, "[ms]"
        print "NetworkMonitor: s1-s4 delay:", self.s1_s4_delay, "[ms]"


    def trigger_measurement_procedure(self):
        if self.s1_dpid <>0 and not core.openflow.getConnection(self.s1_dpid) is None:
            self.sent_time1 = self.send_stats_request_packet(src_dpid=self.s1_dpid, start_time=self.start_time)
        # S1 sends probe packets to S2, S3, S4
        for i in range(2, 5):
            self.send_probe_packet(destination_switch=i, start_time=self.start_time, dpid=self.s1_dpid)
        # Request Stats from S2, S3, S4
        if self.s2_dpid <>0 and not core.openflow.getConnection(self.s2_dpid) is None:
            self.sent_time2 = self.send_stats_request_packet(src_dpid=self.s2_dpid, start_time=self.start_time)
        if self.s3_dpid <>0 and not core.openflow.getConnection(self.s3_dpid) is None:
            self.sent_time3 = self.send_stats_request_packet(src_dpid=self.s3_dpid, start_time=self.start_time)
        if self.s4_dpid <>0 and not core.openflow.getConnection(self.s4_dpid) is None:
            self.sent_time4 = self.send_stats_request_packet(src_dpid=self.s4_dpid, start_time=self.start_time)


    def send_probe_packet(self, destination_switch, start_time, dpid):
        #sequence of packet formating operations optimised to reduce the delay variation of e-2-e measurements (to measure T3)
        f = myproto() #create a probe packet object
        e = pkt.ethernet() #create L2 type packet (frame) object

        if destination_switch==2:
            src_MAC = "0:0:0:1:2:1"
            dst_MAC = "0:0:0:1:2:2"
            output_port = 4
        elif destination_switch==3:
            src_MAC = "0:0:0:1:3:1"
            dst_MAC = "0:0:0:1:3:2"
            output_port = 5
        elif destination_switch==4:
            src_MAC = "0:0:0:1:4:1"
            dst_MAC = "0:0:0:1:4:2"
            output_port = 6

        e.src = EthAddr(src_MAC)
        e.dst = EthAddr(dst_MAC)
        e.type=0x5577 #set unregistered EtherType in L2 header type field, here assigned to the probe packet type 
        msg = of.ofp_packet_out() #create PACKET_OUT message object
        msg.actions.append(of.ofp_action_output(port=output_port)) #set the output port for the packet in switch1
        f.timestamp = int(time.time()*1000*10 - start_time) #set the timestamp in the probe packet
        #print f.timestamp
        e.payload = f
        msg.data = e.pack()
        core.openflow.getConnection(dpid).send(msg)
        #print "=====> probe sent to", destination_switch, ": f=", f.timestamp, " after=", int(time.time()*1000*10 - start_time), " [10*ms]"

    def send_stats_request_packet(self, src_dpid, start_time):
        #send out port_stats_request packet through switch1/2/3/4 connection s1/s2/s3/s4_dpid (to measure T1/T2)
        core.openflow.getConnection(src_dpid).send(of.ofp_stats_request(body=of.ofp_port_stats_request()))
        sent_time=time.time() * 1000*10 - start_time #sending time of stats_req: ctrl => switch1/2/3/4
        #print "sent_time1:", sent_time1
        return sent_time