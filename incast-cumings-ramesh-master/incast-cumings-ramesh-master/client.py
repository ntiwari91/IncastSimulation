#!/usr/bin/python

import argparse
import socket
import time

import common

def sendRequest( bytes, connection ):
  connection.sendall( "SEND %d\n" % bytes )
  
def sendCommandToQuit( connection ):
  connection.sendall( "QUIT\n" )
  
def allBytesReceived( bytes, counts ):
  return any( map( lambda count: count >= bytes, counts ) )
    
def doBarrierTransaction( bytes, connections, endTime ):
  #send a request for a number of bytes to each connection
  bytesPerConnection = bytes / len( connections )
  map( lambda connection: sendRequest( bytesPerConnection, connection ), connections )
  
  counts = [0] * len( connections )
  
  #collect data from each connection until all bytes have been received
  while not allBytesReceived( bytesPerConnection, counts ) and time.time() <= endTime:
    for i, connection in enumerate( connections ):
      counts[ i ] += len( connection.recv( bytesPerConnection ) ) 

def getCommandLineArguments():
  argumentParser = argparse.ArgumentParser( description="command-line arguments" )
  
  argumentParser.add_argument('--servers', '-s',
                      help="Path to a file that lists servers to communicate with",
                      required=True)
  
  argumentParser.add_argument('--bytes','-b',
                      type=int,
                      help="Number of bytes to request from each server per iteration",
                      default=2**20)
  
  argumentParser.add_argument('--time', '-t',
                      dest="time",
                      type=float,
                      help="Duration of the experiment",
                      default=5.0)
  
  return argumentParser.parse_args()

args = getCommandLineArguments()

# Make connections to the servers.
connections = list()
for line in common.readLines( args.servers ):
  if common.isIP(line):
    connection = socket.socket( socket.AF_INET, socket.SOCK_STREAM )
    connection.connect( common.readIP( line ) )
    connections.append( connection )

# Perform barrier transactions for the commanded amount of time.
timeToStartCounting = time.time() + 1.0
endTime = timeToStartCounting + args.time
iterations = 0

# Due to the nature of these TCP flows, connection startup
# doesn't have much effect on what we're measuring, but we'll leave
# it in to be thorough, anyway.
while time.time() < timeToStartCounting:
  doBarrierTransaction( args.bytes, connections, endTime )

while time.time() <= endTime:
  iterations += 1
  doBarrierTransaction( args.bytes, connections, endTime )
  
# Close sockets.
for connection in connections:
  sendCommandToQuit( connection )
  connection.close()

# Print the goodput, in megabits per second
print float(args.bytes) / args.time * 8.0 / float(2**20) * iterations

