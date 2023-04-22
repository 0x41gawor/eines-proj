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
 
log = core.getLogger()

#global variables init

start_time = 0.0
sent_time1=0.0
sent_time2=0.0
received_time1 = 0.0
received_time2 = 0.0
mytimer = 0
OWD1=0.0
OWD2=0.0

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

  #when the controller knows both src_dpid and dst_dpid are up, mytimer is started so that a probe packet is sent every 2 seconds across the link between respective switches
  if s1_dpid<>0 and s2_dpid<>0:
    mytimer=Timer(2, _timer_func, recurring=True)
    #mytimer.start() #DB: mytimer.start() was originally used, now supressed for rising assertion error

def _handle_portstats_received (event):
   #Here, port statistics responses are handled to calculate delays T1 and T2 (see the lab instructions)

   global start_time, sent_time1, sent_time2, received_time1, received_time2, s1_dpid, s2_dpid, OWD1, OWD2

   received_time = time.time() * 1000*10 - start_time
   #measure T1 as of lab guide
   if event.connection.dpid == s1_dpid:
     OWD1=0.5*(received_time - sent_time1)
     #print "OWD1: ", OWD1, "ms"
 
   #measure T2 as of lab guide
   elif event.connection.dpid == s2_dpid:
     OWD2=0.5*(received_time - sent_time2) #originally sent_time1 was here
     #print "OWD2: ", OWD2, "ms"

def _handle_PacketIn(event):

  global start_time, OWD1, OWD2

  received_time = time.time() * 1000*10 - start_time #amount of time elapsed from start_time

  if event.connection.dpid==s1_dpid:
    handle_packetIn_s1(event)
  elif event.connection.dpid==s2_dpid:
    packet = event.parsed
    if packet.type==0x5577: #0x5577 is unregistered EtherType, here assigned to probe packets
      #Process a probe packet received in PACKET_IN message from 'switch1' (s2_dpid), previously sent to 'switch0' (s1_dpid) in PACKET_OUT.

      c=packet.find('ethernet').payload
      d,=struct.unpack('!I', c)  # note that d,=... is a struct.unpack and always returns a tuple
      print "[ms*10]: received_time=", int(received_time), ", d=", d, ", OWD1=", int(OWD1), ", OWD2=", int(OWD2)
      print "delay:", int(received_time - d - OWD1 - OWD2)/10, "[ms] <=====" # divide by 10 to normalise to milliseconds
    else:
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

  global start_time, sent_time1, sent_time2, s1_dpid, s2_dpid
 
  #the following executes only when a connection to 'switch0' exists (otherwise AttributeError can be raised)
  if s1_dpid <>0 and not core.openflow.getConnection(s1_dpid) is None:

    #send out port_stats_request packet through switch0 connection src_dpid (to measure T1)
    core.openflow.getConnection(s1_dpid).send(of.ofp_stats_request(body=of.ofp_port_stats_request()))
    sent_time1=time.time() * 1000*10 - start_time #sending time of stats_req: ctrl => switch0
    #print "sent_time1:", sent_time1

    #sequence of packet formating operations optimised to reduce the delay variation of e-2-e measurements (to measure T3)
    f = myproto() #create a probe packet object
    e = pkt.ethernet() #create L2 type packet (frame) object
    e.src = EthAddr("0:0:0:1:2:1")
    e.dst = EthAddr("0:1:0:1:2:2")
    e.type=0x5577 #set unregistered EtherType in L2 header type field, here assigned to the probe packet type 
    msg = of.ofp_packet_out() #create PACKET_OUT message object
    msg.actions.append(of.ofp_action_output(port=4)) #set the output port for the packet in switch0
    f.timestamp = int(time.time()*1000*10 - start_time) #set the timestamp in the probe packet
    #print f.timestamp
    e.payload = f
    msg.data = e.pack()
    core.openflow.getConnection(s1_dpid).send(msg)
    print "=====> probe sent: f=", f.timestamp, " after=", int(time.time()*1000*10 - start_time), " [10*ms]"

  #the following executes only when a connection to 'switch1' exists (otherwise AttributeError can be raised)
  if s2_dpid <>0 and not core.openflow.getConnection(s2_dpid) is None:
    #send out port_stats_request packet through switch1 connection dst_dpid (to measure T2)
    core.openflow.getConnection(s2_dpid).send(of.ofp_stats_request(body=of.ofp_port_stats_request()))
    sent_time2=time.time() * 1000*10 - start_time #sending time of stats_req: ctrl => switch1
    #print "sent_time2:", sent_time2

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