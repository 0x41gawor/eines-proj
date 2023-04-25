#!/usr/bin/python
 
from mininet.topo import Topo
from mininet.net import Mininet
from mininet.node import CPULimitedHost
from mininet.link import TCLink
from mininet.util import dumpNodeConnections, quietRun
from mininet.log import setLogLevel, info
from mininet.node import Controller 
from mininet.cli import CLI
from functools import partial
from mininet.node import RemoteController
from threading import Timer, Thread
from time import sleep
import os
import random

# Topology: switches interconnected in diamond topology (3 parallel paths, no cross-links); 3 hosts on each side of the diamond

class MyTopo(Topo):
    "Single switch connected to n hosts."
    def __init__(self):
        Topo.__init__(self)
        s1=self.addSwitch('s1')
        s2=self.addSwitch('s2')
        s3=self.addSwitch('s3')
        s4=self.addSwitch('s4')
        s5=self.addSwitch('s5')
        h1=self.addHost('h1')
        h2=self.addHost('h2')
        h3=self.addHost('h3')
        h4=self.addHost('h4')
        h5=self.addHost('h5')
        h6=self.addHost('h6')

        delay = '10ms'
        self.addLink(h1, s1, bw=1, delay=delay, loss=0, max_queue_size=1000, use_htb=True)
        self.addLink(h2, s1, bw=1, delay=delay, loss=0, max_queue_size=1000, use_htb=True)
        self.addLink(h3, s1, bw=1, delay=delay, loss=0, max_queue_size=1000, use_htb=True)
        self.addLink(s1, s2, addr1="0:0:0:1:2:1", addr2="0:0:0:1:2:2", bw=1, delay=delay, loss=0, max_queue_size=1000, use_htb=True)
        self.addLink(s1, s3, addr1="0:0:0:1:3:1", addr2="0:0:0:1:3:2", bw=1, delay=delay, loss=0, max_queue_size=1000, use_htb=True)
        self.addLink(s1, s4, addr1="0:0:0:1:4:1", addr2="0:0:0:1:4:2", bw=1, delay=delay, loss=0, max_queue_size=1000, use_htb=True)
        self.addLink(s2, s5, bw=1, delay=delay, loss=0, max_queue_size=1000, use_htb=True)
        self.addLink(s3, s5, bw=1, delay=delay, loss=0, max_queue_size=1000, use_htb=True)
        self.addLink(s4, s5, bw=1, delay=delay, loss=0, max_queue_size=1000, use_htb=True)
        self.addLink(s5, h4, bw=1, delay=delay, loss=0, max_queue_size=1000, use_htb=True)
        self.addLink(s5, h5, bw=1, delay=delay, loss=0, max_queue_size=1000, use_htb=True)
        self.addLink(s5, h6, bw=1, delay=delay, loss=0, max_queue_size=1000, use_htb=True)

def perfTest():
    "Create network and run simple performance test"
    topo = MyTopo()
    #net = Mininet(topo=topo, host=CPULimitedHost, link=TCLink, controller=POXcontroller1)
    net = Mininet(topo=topo, host=CPULimitedHost, link=TCLink, controller=partial(RemoteController, ip='127.0.0.1', port=6633))
    net.start()
    print "Dumping host connections"
    dumpNodeConnections(net.hosts)
    h1,h2,h3=net.get('h1','h2','h3')
    h4,h5,h6=net.get('h4','h5','h6')
    s1,s2,s3,s4,s5=net.get('s1','s2','s3','s4','s5')
    h1.setMAC("0:0:0:0:0:1")
    h2.setMAC("0:0:0:0:0:2")
    h3.setMAC("0:0:0:0:0:3")
    h4.setMAC("0:0:0:0:0:4")
    h5.setMAC("0:0:0:0:0:5")
    h6.setMAC("0:0:0:0:0:6")
    
    print("How many times do you want to change the delay? ")
    limit = input()

    cmdline=CLI(net)
    iterator = 1
    while iterator<=limit:
        change_delay(s1)
        iterator+=1
        cmdline.run()

    net.stop()

def change_delay(switch): #function called back to set the link delay to 50 ms; both directions have to be set
    eth = random.randint(4, 6)
    delay = random.randrange(10, 110, 20)

    #switch.cmdPrint('ethtool -K s0-eth1 gro off') #not supported by VBox, use the tc tool as below
    switch.cmd('tc qdisc del dev s1-eth{} root'.format(eth))
    switch.cmd('tc qdisc add dev s1-eth{} root handle 10: netem delay {}ms'.format(eth, delay))  #originally 50ms
    info( '+++++++++++++ {}ms delay started on s1-eth{} interface +++++++++++++\n'.format(delay, eth) )

if __name__ == '__main__':
    setLogLevel('info')
    perfTest()

