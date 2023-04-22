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
from dzienciol_lib import *
from dzienciol_delay import *
 
log = core.getLogger()

#global variables init

start_time = 0.0
sent_time1=0.0
sent_time2=0.0
sent_time3=0.0
sent_time4=0.0
mytimer = 0
OWDs1_ctrl=0.0
OWDs2_ctrl=0.0
OWDs3_ctrl=0.0
OWDs4_ctrl=0.0

s1_dpid=0 
s2_dpid=0
s3_dpid=0
s4_dpid=0
s5_dpid=0

def _handle_ConnectionUp (event):
  # waits for connections from all switches, after connecting to all of them it starts a round robin timer for triggering h1-h4 routing changes
  global s1_dpid, s2_dpid, s3_dpid, s4_dpid, s5_dpid, my_timer
  print "ConnectionUp: ",dpidToStr(event.connection.dpid)
 
  #remember the connection dpid for the switch
  for m in event.connection.features.ports:
    if m.name == "s1-eth1":
      # s1_dpid: the DPID (datapath ID) of switch s1;
      s1_dpid = event.connection.dpid
      print "s1_dpid=", s1_dpid
    elif m.name == "s2-eth1":
      s2_dpid = event.connection.dpid
      print "s2_dpid=", s2_dpid
    elif m.name == "s3-eth1":
      s3_dpid = event.connection.dpid
      print "s3_dpid=", s3_dpid
    elif m.name == "s4-eth1":
      s4_dpid = event.connection.dpid
      print "s4_dpid=", s4_dpid
    elif m.name == "s5-eth1":
      s5_dpid = event.connection.dpid
      print "s5_dpid=", s5_dpid

  #when the controller knows all switches for delay measuring (i.e. between source s1_dpid and destination s2/s3/s4_dpid) are up, mytimer is started so that a probe packet is sent every 5 seconds across the link between respective switches
  if s1_dpid<>0 and s2_dpid<>0 and s3_dpid<>0 and s4_dpid<>0:
    mytimer=Timer(5, _timer_func, recurring=True)
    #mytimer.start() #DB: mytimer.start() was originally used, now supressed for rising assertion error

def _handle_portstats_received (event):
   #Here, port statistics responses are handled to calculate delays T1 (controller-s1) and T2 (s2/s3/s4-controller)

   global start_time, sent_time1, sent_time2, sent_time3, sent_time4, s1_dpid, s2_dpid, s3_dpid, s4_dpid, OWDs1_ctrl, OWDs2_ctrl, OWDs3_ctrl, OWDs4_ctrl
  
   received_time = time.time() * 1000*10 - start_time

   #measure T1 as of lab guide
   if event.connection.dpid == s1_dpid:
     OWDs1_ctrl=measure_delay_component(received_time=received_time, sent_time=sent_time1)
 
    #measure T2 as of lab guide
   elif event.connection.dpid == s2_dpid:
     OWDs2_ctrl=measure_delay_component(received_time=received_time, sent_time=sent_time2) #originally sent_time1 was here

    #measure T2 as of lab guide
   elif event.connection.dpid == s3_dpid:
     OWDs3_ctrl=measure_delay_component(received_time=received_time, sent_time=sent_time3) #originally sent_time1 was here

    #measure T2 as of lab guide
   elif event.connection.dpid == s4_dpid:
     OWDs4_ctrl=measure_delay_component(received_time=received_time, sent_time=sent_time4) #originally sent_time1 was here

def _handle_PacketIn(event):

  global start_time, OWDs1_ctrl, OWDs2_ctrl, OWDs3_ctrl, OWDs4_ctrl

  received_time = time.time() * 1000*10 - start_time #amount of time elapsed from start_time

  packet = event.parsed
  if packet.type==0x5577: #0x5577 is unregistered EtherType, here assigned to probe packets
    if event.connection.dpid==s2_dpid:
      handle_probe_packetIn(packet=packet, received_time=received_time, OWDs1_ctrl=OWDs1_ctrl, other_s_OWD=OWDs2_ctrl, switch_name="s2")
    elif event.connection.dpid==s3_dpid:
      handle_probe_packetIn(packet=packet, received_time=received_time, OWDs1_ctrl=OWDs1_ctrl, other_s_OWD=OWDs3_ctrl, switch_name="s3")
    elif event.connection.dpid==s4_dpid:
      handle_probe_packetIn(packet=packet, received_time=received_time, OWDs1_ctrl=OWDs1_ctrl, other_s_OWD=OWDs4_ctrl, switch_name="s4")

  else: #other packet types for routing purposes
    if event.connection.dpid==s1_dpid:
      handle_packetIn_s1(event)
    elif event.connection.dpid==s2_dpid:
      handle_packetIn_s2(event)
    elif event.connection.dpid==s2_dpid:
      handle_packetIn_s3(event)
    elif event.connection.dpid==s2_dpid:
      handle_packetIn_s4(event)
    elif event.connection.dpid==s5_dpid:
      handle_packetIn_s5(event)

def _handle_ConnectionDown (event):
  #Handle connection down - stop the timer for sending the probes
  global mytimer
  print "ConnectionDown: ", dpidToStr(event.connection.dpid)
  mytimer.cancel()

def _timer_func ():
  #This function is called periodically to send measurement-oriented messages to the switches.
  """
  Three OpenFlow commands are sent in sequence: one to measure T1, second to measure T3, and third to 
  measure T2 (see the lab instructions). T1 and T2 are used with ststistics requerst/response method
  (other OpenFlow command could be used), while T3 is measured with sending/receiving PACKET_OUT/PACKET_IN by 
  the controller. For more on the use of timers for non-blocking tasks in POX see section: "Threads, Tasks, and 
  Timers: pox.lib.recoco" in http://intronetworks.cs.luc.edu/auxiliary_files/mininet/poxwiki.pdf.
  NOTE: it may happen that trying to optimize signalling traffic the controller aggregates in one TCP segment
  multiple commands directed to a given switch. This may degrade the quality of measurements with hard to control
  delay variations. Little can be done about it without modyfying POX libraries and we rather have to live with this feature.
  """

  global start_time, sent_time1, sent_time2, sent_time3, sent_time4, s1_dpid, s2_dpid, s3_dpid, s4_dpid
 
  #the following executes only when a connection to 's1' exists (otherwise AttributeError can be raised)
  if s1_dpid <>0 and not core.openflow.getConnection(s1_dpid) is None:
    sent_time1 = send_stats_request_packet(src_dpid=s1_dpid, start_time=start_time)

    for i in range(2, 5):
      send_probe_packet(destination_switch=i, start_time=start_time, dpid=s1_dpid)

  #the following executes only when a connection to 'switch2' exists (otherwise AttributeError can be raised)
  if s2_dpid <>0 and not core.openflow.getConnection(s2_dpid) is None:
    sent_time2 = send_stats_request_packet(src_dpid=s2_dpid, start_time=start_time)

  #the following executes only when a connection to 'switch3' exists (otherwise AttributeError can be raised)
  if s3_dpid <>0 and not core.openflow.getConnection(s3_dpid) is None:
    sent_time3 = send_stats_request_packet(src_dpid=s3_dpid, start_time=start_time)

  #the following executes only when a connection to 'switch4' exists (otherwise AttributeError can be raised)
  if s4_dpid <>0 and not core.openflow.getConnection(s4_dpid) is None:
    sent_time4 = send_stats_request_packet(src_dpid=s4_dpid, start_time=start_time)

def launch ():
  #This is launch function that POX calls to initialize the component (delay_measurement.py here).
  #This is usually a function actually named 'launch', though there are exceptions.
  #Fore more info: http://intronetworks.cs.luc.edu/auxiliary_files/mininet/poxwiki.pdf

  global start_time
  start_time = time.time() * 1000*10 # factor *10 applied to increase the accuracy for short delays (capture tenths of ms)
  print "start_time:", start_time/10

  core.openflow.addListenerByName("ConnectionUp", _handle_ConnectionUp) # listen for the establishment of a new control channel with a switch, https://noxrepo.github.io/pox-doc/html/#connectionup
  core.openflow.addListenerByName("ConnectionDown", _handle_ConnectionDown)
  core.openflow.addListenerByName("PacketIn", _handle_PacketIn)
  core.openflow.addListenerByName("PortStatsReceived", _handle_portstats_received)