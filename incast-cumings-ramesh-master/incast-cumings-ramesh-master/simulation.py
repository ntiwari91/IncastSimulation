#!/usr/bin/python

import random
import re

from mininet.topo import Topo
from mininet.net import Mininet
from mininet.log import lg, output
from mininet.node import CPULimitedHost
from mininet.link import TCLink
from mininet.util import irange, custom, quietRun, dumpNetConnections
from mininet.cli import CLI

from time import sleep, time
from subprocess import check_output
import termcolor as T
import argparse

import os

def getCommandLineArguments():
  argumentParser = argparse.ArgumentParser( description="command-line arguments" )
  
  argumentParser.add_argument('--servers', '-n',
                      type=int,
                      help="Number of servers",
                      default=8)
  
  argumentParser.add_argument('--bytes','-b',
                      type=int,
                      help="Number of bytes to request per transaction",
                      default=2**20)
  
  argumentParser.add_argument('--time', '-t',
                      type=float,
                      help="Duration of the experiment",
                      default=5.0)
  
  argumentParser.add_argument('--port', '-p',
                      type=int,
                      help="Port number to use for communication",
                      default=5005)
  
  argumentParser.add_argument('--bandwidth', '-w',
                      type=int,
                      help="Link bandwidth in Mb/s",
                      default=100)
  
  argumentParser.add_argument('--rtt', '-r',
                      type=float,
                      help="Round trip time in microseconds",
                      default=0.0)
  
  argumentParser.add_argument('--rto_min', '-m',
                      type=int,
                      help="RTO_min in milliseconds",
                      default=200)
  
  argumentParser.add_argument('--output_queue_size', '-o',
                      type=int,
                      help="Size of outgoing queue on a link, in packets",
                      default=1)
  
  argumentParser.add_argument('--input_queue_size', '-i',
                      type=int,
                      help="Size of input queue on a link, in bytes",
                      default=1)
  
  argumentParser.add_argument('--ping',
                      action="store_true",
                      help="make the client ping the servers instead of performing the experiment",
                      default=False)
  
  argumentParser.add_argument('--test',
                      action="store_true",
                      help="Test the topology, etc. instead of performing the experiment",
                      default=False)
  
  return argumentParser.parse_args()

args = getCommandLineArguments()

SERVER_IP_FILE_NAME = "target_ips.txt"

def cprint(s, color, cr=True):
    """Print in color
       s: string to print
       color: color to use"""
    if cr:
        print T.colored(s, color)
    else:
        print T.colored(s, color),

def setOutputQueueSize(node):
  command = 'sudo ip link set dev %s-eth0 txqueuelen %d' % ( node.name, args.output_queue_size )
  node.cmd(command)

def setRtoMin(node):
  node.cmd( 'sudo ip route replace dev %s-eth0 rto_min %dms' % ( node.name, args.rto_min ) )
  #print node.cmd( 'sudo ip route show' )
  check_output( 'sudo ip route replace default dev eth0 rto_min %dms' % args.rto_min, shell=True )
  #print check_output( 'sudo ip route show', shell=True )
  
def showIfconfig(node):
  print node.cmd('ifconfig')
  
def launchServerProcess(server):
  server.sendCmd( "./server.py %s:%d" % ( server.IP(), args.port ) )
  
def runClient( client, serverIpFileName=SERVER_IP_FILE_NAME ):
  return client.cmd( "./client.py -s %s -b %d -t %f" % (serverIpFileName, args.bytes, args.time) )

def delay():
  return ("%dus" % ( (args.rtt) / 4 ) )

def ruleOfThumbInputQueueLength():
  '''input queue length, in bytes'''
  return args.rtt * args.bandwidth / 8

def setInputQueueLength(switch, hostNumber, length):
  '''Change queue size limit of interface'''
  command = ("tc qdisc change dev switch0-eth%i parent 1:1 "
         "handle 10: netem limit %s" % (hostNumber, length))
  switch.cmd(command)

def cpuShare():
  return 1.0/(args.servers + 1)

def netstat(node):
  stat = node.cmd('netstat -s | grep -i "segments retransmited"')
  return stat

def countRetransmits(netstatOut):
  total = 0
  for line in netstatOut.split('\n'):
    match = re.search('\d+',line)
    if match:
      total += int(match.group(0))
  return total

class BarrierTransactionMininet(Mininet):
  def __init__( self, **params ):
    """Mininet set up to test barrier transactions with one client
       and a specified number of servers.
       numberOfServers: number of servers 
       linkBandwidth: link bandwidth in Mb/s
       roundTripTime: unloaded round trip time from client to server, in microseconds"""
    
    host = custom( CPULimitedHost, cpu=cpuShare() )  
    link = custom( TCLink, bw=args.bandwidth, delay=delay() )
    
    Mininet.__init__(
      self,
      topo=BarrierTransactionTopo( **params ),
      host=host,
      link=link )
    
  def servers(self):
    return map(
      lambda hostName: self.getNodeByName( hostName ),
      filter( lambda hostName: "server" in hostName, self.topo.hosts() ) )
      
  def client(self):
    for hostName in self.topo.hosts():
      if 'client' in hostName:
        return self.getNodeByName( hostName )
    raise Exception( 'client not found in topology' )
  
  def writeServerIpFile(self, serverIpFileName=SERVER_IP_FILE_NAME ):
    targetIps = open( serverIpFileName, "w" )
    for server in self.servers():
      targetIps.write( "%s:%d\n" % ( server.IP(), args.port ) )
    targetIps.close()
    
  def testGoodput( self ):
    """Measure barrier transaction goodput on this topology for a specified value of RTO_min.
       duration: the duration of the test, in seconds
       rtoMin: the RTO_min the servers should use, in milliseconds"""
       
    for server in self.servers():
      setOutputQueueSize( server )
      setRtoMin( server )
      launchServerProcess(server)
    
    switch = self.getNodeByName( 'switch0' )  
    setOutputQueueSize( switch )

    for i in range(1,args.servers+1):
      setInputQueueLength(switch,i,args.input_queue_size)
  
    setOutputQueueSize( self.client() )
    setRtoMin( self.client() )

    if args.ping:
      for server in self.servers():
        print self.client().cmd( 'ping -c 9 %s' % server.IP() )
      return 0.0
      
    self.writeServerIpFile()
   
    goodput = float(runClient(self.client()))
    
    retransmits = 0
    for server in self.servers():
      server.waitOutput()
      retransmits += countRetransmits(netstat(server))

    retransFile = open('retransmissions.txt','a')
    retransFile.write( "%d servers: %d retransmissions\n" % (args.servers, retransmits ))
    retransFile.close()

    return goodput
      
  def testTopology(self):
    for host in self.topo.hosts() + self.topo.switches():
      print ""
      print host
      print "------------"
      showIfconfig(self.getNodeByName(host))

# Topology to be instantiated in Mininet
class BarrierTransactionTopo(Topo):
  "Topology for a client/server network that performs barrier transactions"

  def __init__(self, **params):
    """Barrier transaction topology with one client"""

    # Initialize topo
    Topo.__init__(self, **params)

    # Host and link configuration
    hostConfiguration = {'cpu': cpuShare()}
    linkConfiguration = {'bw': args.bandwidth, 'delay': delay(), 'max_queue_len': args.input_queue_size }
    
    # Create the actual topology
    client = self.add_host( 'client0', **hostConfiguration )
    
    switch = self.add_switch('switch0' )
    
    self.add_link( switch, client, port1=0, port2=0, **linkConfiguration )
    
    for i in range(1,args.servers+1):
      server = self.add_host( 'server%d' % i, **hostConfiguration )
      self.add_link( switch, server, port1=i, port2=0, **linkConfiguration )

def main():

#  start = time()

  net = BarrierTransactionMininet()

  net.start()

#  cprint("*** Dumping network connections:", "green")
#  dumpNetConnections(net)

#  cprint("*** Testing connectivity", "blue")

#  net.pingAll()

#  cprint("*** Running experiment", "magenta")
  if args.test:
    net.testTopology()
  else:
    print net.testGoodput()

  net.stop()
#  end = time()
#  os.system("killall -9 bwm-ng client.py server.py")
#  cprint("Experiment took %.3f seconds" % (end - start), "yellow")

if __name__ == '__main__':
  main()
