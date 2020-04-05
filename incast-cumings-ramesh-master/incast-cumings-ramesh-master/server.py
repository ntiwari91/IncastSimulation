#!/usr/bin/python

import re
import socket
import sys
import common

from subprocess import check_output

sendPattern = re.compile( r"SEND\s*(\d+)\n", re.IGNORECASE )
quitPattern = re.compile( r"QUIT\n" )

def isQuitCommand( message ):
  return not quitPattern.match( message ) is None

def isSendCommand( message ):
  return not sendPattern.match( message ) is None

def parseBytesRequested( sendCommand ):
  return int( sendPattern.match( sendCommand ).group( 1 ) )

TCP_IP = '127.0.0.1'
TCP_PORT = 5005

print "server running"

if len( sys.argv ) > 1:
  TCP_IP, TCP_PORT = common.readIP( sys.argv[1] )

#socket.setdefaulttimeout( 0 )
s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.bind((TCP_IP, TCP_PORT))
s.listen(1)
print "listening..."

connection, _ = s.accept()
print "connection accepted"
filestream = connection.makefile( "r" )
data = ""

while True:
    data = filestream.readline()
    if isQuitCommand( data ):
      break
    elif isSendCommand( data ):
      connection.sendall( "a" * parseBytesRequested( data ) )
      # Remove the send command from the head of the accumulated data.
      data = re.sub( r"^[^\n]*\n", "", data )

connection.close()

