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
from network_monitor import *
from network_policer import *
from intent_policer import *
import signal
import socket
import threading

HEADER = 64
PORT = 5050
SERVER = socket.gethostbyname(socket.gethostname())
ADDR = (SERVER, PORT)
FORMAT = 'utf-8'
DISCONNECT_MESSAGE = "!DISCONNECT"

server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server.bind(ADDR)


log = core.getLogger()

networkMonitor = NetworkMonitor();

networkPolicer = NetworkPolicer();

s1_dpid=0 
s2_dpid=0
s3_dpid=0
s4_dpid=0
s5_dpid=0

def _handle_ConnectionUp (event):
  global s1_dpid, s2_dpid, s3_dpid, s4_dpid, s5_dpid, my_timer
  print "ConnectionUp: ",dpidToStr(event.connection.dpid)
 
  #remember the connection dpid for the switch
  for m in event.connection.features.ports:
    if m.name == "s1-eth1":
      s1_dpid = event.connection.dpid
      networkMonitor.s1_dpid = s1_dpid
      networkPolicer.s1_dpid = s1_dpid
      print "s1_dpid=", s1_dpid
    elif m.name == "s2-eth1":
      s2_dpid = event.connection.dpid
      networkMonitor.s2_dpid = s2_dpid
      print "s2_dpid=", s2_dpid
    elif m.name == "s3-eth1":
      s3_dpid = event.connection.dpid
      networkMonitor.s3_dpid = s3_dpid
      print "s3_dpid=", s3_dpid
    elif m.name == "s4-eth1":
      s4_dpid = event.connection.dpid
      networkMonitor.s4_dpid = s4_dpid
      print "s4_dpid=", s4_dpid
    elif m.name == "s5-eth1":
      s5_dpid = event.connection.dpid
      networkMonitor.s5_dpid = s5_dpid
      networkPolicer.s5_dpid = s5_dpid
      print "s5_dpid=", s5_dpid

  # delay measurement procedure starts
  if s1_dpid<>0 and s2_dpid<>0 and s3_dpid<>0 and s4_dpid<>0:
    mytimer=Timer(5, _timer_func, recurring=True)

def _handle_portstats_received (event):
   #Here, port statistics responses are handled to calculate delays T1 (controller-s1) and T2 (s2/s3/s4-controller)
   global networkMonitor
   networkMonitor.handle_PortStats(event)

def _handle_PacketIn(event):

  global networkMonitor, networkPolicer

  networkPolicer.openflow = core.openflow

  networkMonitor.handlePacketInProbe(event)


  if event.connection.dpid==s1_dpid:
    packet=event.parsed.find('arp')			# If packet object does not encapsulate a packet of the type indicated, find() returns None
    if packet:
      networkPolicer.install_arp_s1(event, packet)   
    else:
      # identyfikacja flow
      flow = networkPolicer.identify_flow(event, s1_dpid)
      # czy juz jest takie flow
      if networkPolicer.does_flow_exist(flow) == False:
        # jesli nie no to mamy nowe flow
        print "---------------------------------------------------------"
        print "Zidentyfikowane flow:", flow
        # wybranie sciezki
        route = networkPolicer.select_route()
        print "Wybrana sciezka:", route
        # powiazanie flow i jego sciezki 
        networkPolicer.flow_route_map.append((flow, route))
        networkPolicer.increment_route_counter(route, 1)
        print "Flow Route Map"
        networkPolicer.show_flow_route_map()
        print "Route flows counter:", networkPolicer.route_flow_counter
        # instalacja sciezki w sieci
        networkPolicer.install(flow, route)


  elif event.connection.dpid==s2_dpid:
    networkPolicer.install_transit_routing(event)
  elif event.connection.dpid==s3_dpid:
    networkPolicer.install_transit_routing(event)
  elif event.connection.dpid==s4_dpid:
    networkPolicer.install_transit_routing(event)
  elif event.connection.dpid==s5_dpid:
    packet=event.parsed.find('arp')			# If packet object does not encapsulate a packet of the type indicated, find() returns None
    if packet:
      networkPolicer.install_arp_s5(event, packet)   

def _handle_ConnectionDown (event):
  #Handle connection down - stop the timer for sending the probes
  global mytimer
  print "ConnectionDown: ", dpidToStr(event.connection.dpid)
  mytimer.cancel()

# Called periodically to trigger NetworkMonitor measurements
def _timer_func ():
  global networkMonitor
  networkMonitor.trigger_measurement_procedure()

def ctrl_z_handler(signum, frame):
  global networkMonitor
  print "elo"
  networkMonitor.print_delays()

signal.signal(signal.SIGTSTP, ctrl_z_handler)

def handle_client(conn, addr):
    connected = True
    while connected:
        msg_length = conn.recv(HEADER).decode(FORMAT)
        if msg_length:

            msg_length = int(msg_length)
            msg = conn.recv(msg_length).decode(FORMAT)
            if msg == DISCONNECT_MESSAGE:
                connected = False
            if msg != DISCONNECT_MESSAGE:
                data = msg.split()
                h_src = data[0]
                h_dst = data[1]
                limit = data[2]
                flow = Flow(h_src, h_dst)
                intent = Intent(flow, limit)
                print "Intent Handler: got ", intent

    conn.close()

def start():
    server.listen(5)
    while True:
        conn, addr = server.accept()
        thread = threading.Thread(target=handle_client, args=(conn,addr))
        thread.start()

def launch ():

  thread = threading.Thread(target=start)
  thread.start()

  global networkMonitor
  networkMonitor.start_time = time.time() * 1000*10 # factor *10 applied to increase the accuracy for short delays (capture tenths of ms)


  core.openflow.addListenerByName("ConnectionUp", _handle_ConnectionUp)
  core.openflow.addListenerByName("ConnectionDown", _handle_ConnectionDown)
  core.openflow.addListenerByName("PacketIn", _handle_PacketIn)
  core.openflow.addListenerByName("PortStatsReceived", _handle_portstats_received)