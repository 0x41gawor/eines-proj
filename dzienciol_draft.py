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
import socket
import threading
 
log = core.getLogger()

networkMonitor = NetworkMonitor();

HEADER = 64
PORT = 5050
SERVER = socket.gethostbyname(socket.gethostname())
ADDR = (SERVER, PORT)
FORMAT = 'utf-8'
DISCONNECT_MESSAGE = "!DISCONNECT"

server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server.bind(ADDR)

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
      print "s5_dpid=", s5_dpid

  # delay measurement procedure starts
  if s1_dpid<>0 and s2_dpid<>0 and s3_dpid<>0 and s4_dpid<>0:
    mytimer=Timer(5, _timer_func, recurring=True)

def _handle_portstats_received (event):
   #Here, port statistics responses are handled to calculate delays T1 (controller-s1) and T2 (s2/s3/s4-controller)
   global networkMonitor
   networkMonitor.handle_PortStats(event)

def _handle_PacketIn(event):

  global networkMonitor

  networkMonitor.handlePacketInProbe(event)

  networkPolicer = NetworkPolicer(core.openflow, s1_dpid, s5_dpid)

  if event.connection.dpid==s1_dpid:
    handle_packetIn_s1(event)
  elif event.connection.dpid==s2_dpid:
    networkPolicer.install_transit_routing(event)
  elif event.connection.dpid==s3_dpid:
    networkPolicer.install_transit_routing(event)
  elif event.connection.dpid==s4_dpid:
    networkPolicer.install_transit_routing(event)
  elif event.connection.dpid==s5_dpid:
    handle_packetIn_s5(event)

def _handle_ConnectionDown (event):
  #Handle connection down - stop the timer for sending the probes
  global mytimer
  print "ConnectionDown: ", dpidToStr(event.connection.dpid)
  mytimer.cancel()

# Called periodically to trigger NetworkMonitor measurements
def _timer_func ():
  global networkMonitor
  networkMonitor.trigger_measurement_procedure()

def handle_client(conn, addr):
    #print(f"[NEW CONNECTION] {addr} connected")
    print ("[NEW CONNECTION]" + str(addr) + " connected") 


    connected = True

    while connected:
        msg_length = conn.recv(HEADER).decode(FORMAT)
        if msg_length:

            msg_length = int(msg_length)
            msg = conn.recv(msg_length).decode(FORMAT)
            if msg == DISCONNECT_MESSAGE:
                connected = False


            if msg != DISCONNECT_MESSAGE:
                print(addr)
                print("Choosen flow path: " + msg)
            

    conn.close()

def start():
    print("SSSS")
    server.listen(5)
    print("ZZZZZ")
    print ("[LISTENING] Server is listening on " + SERVER)


    while True:
        conn, addr = server.accept()
        thread = threading.Thread(target=handle_client, args=(conn,addr))
        thread.start()
        activeConnections = threading.activeCount() - 1
        print("[ACTIVE CONNECTIONS] " + str(activeConnections))

  
def launch ():
  #This is launch function that POX calls to initialize the component (delay_measurement.py here).
  #This is usually a function actually named 'launch', though there are exceptions.
  #Fore more info: http://intronetworks.cs.luc.edu/auxiliary_files/mininet/poxwiki.pdf

  print("[STARTING] server is starting...")
  print(SERVER)
  print(ADDR)
  thread = threading.Thread(target=start)
  thread.start()

  global networkMonitor
  start_time = time.time() * 1000*10 # factor *10 applied to increase the accuracy for short delays (capture tenths of ms)
  networkMonitor.start_time = start_time


  core.openflow.addListenerByName("ConnectionUp", _handle_ConnectionUp) # listen for the establishment of a new control channel with a switch, https://noxrepo.github.io/pox-doc/html/#connectionup
  core.openflow.addListenerByName("ConnectionDown", _handle_ConnectionDown)
  core.openflow.addListenerByName("PacketIn", _handle_PacketIn)
  core.openflow.addListenerByName("PortStatsReceived", _handle_portstats_received)

    
