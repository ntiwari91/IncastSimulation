import re

IPPattern = re.compile( r"\d+\.\d+\.\d+\.\d+:\d+" )

def isIP( string ):
  return not IPPattern.match( string ) is None 

def readIP( string ):
  host, port = IPPattern.match( string ).group( 0 ).split( ":" )
  port = int( port )  
  return ( host, port )

def readLines( path ):
  textFile = open( path, "r" )
  lines = textFile.readlines()
  textFile.close()
  return lines
  
