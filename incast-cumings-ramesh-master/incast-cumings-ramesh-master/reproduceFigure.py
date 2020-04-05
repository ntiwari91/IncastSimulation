#!/usr/bin/python

import argparse
import os
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from subprocess import check_output
from datetime import datetime

def getCommandLineArguments():
  argumentParser = argparse.ArgumentParser( description="command-line arguments" )
  
  argumentParser.add_argument('--rtt', '-r',
                      type=float,
                      help="round trip time, in microseconds",
                      default=0)
  
  argumentParser.add_argument('--time', '-t',
                      type=float,
                      help="Duration of the simluations",
                      default=20.0)
  
  argumentParser.add_argument('--block_size', '-b',
                      type=int,
                      help="block size, in bytes",
                      default=2**20)
  
  argumentParser.add_argument('--bandwidth', '-w',
                      type=int,
                      help="Link bandwidth in Mb/s",
                      default=10)
  
  argumentParser.add_argument('--input_queue_size', '-i',
                      type=int,
                      help="Size of incoming queue on a link, in packets",
                      default=1)
  
  argumentParser.add_argument('--output_queue_size', '-o',
                      type=int,
                      help="Size of outgoing queue on a link, in packets",
                      default=1)

  argumentParser.add_argument('--nofigure1',
                      action="store_true",
                      help="Don't generate data for Figure 1",
                      default=False)
  
  argumentParser.add_argument('--nofigure2',
                      action="store_true",
                      help="Don't generate data for Figure 2",
                      default=False)
  
  argumentParser.add_argument('--nofigure3',
                      action="store_true",
                      help="Don't generate data for Figure 3",
                      default=False)
  
  return argumentParser.parse_args()

args = getCommandLineArguments()

start = datetime.now()

os.system('sudo sysctl net.ipv4.tcp_congestion_control=reno')

def plotFigure1(yvalues,path,xvalues):
  plt.figure(1)
  plt.plot(xvalues, yvalues, '^--', label='200ms RTOmin')
  plt.gca().set_xticks(range(0,50,5))
  plt.ylabel('Goodput (Mbps)')
  plt.xlabel('Number of Servers')
  plt.legend()
  plt.savefig(path)


if not args.nofigure1:
  xvaluesForFigure1 = list()
  yvaluesForFigure1 = list()

  print "Data for Figure 1:"

  xvaluesForFigure1 = range(1,50,3)
  for i in xvaluesForFigure1:
    yvaluesForFigure1.append(float(check_output(
      ['sudo', './simulation.py',
       '-n', str(i),
       '-m', '200',
       '-t', str(args.time),
       '-w', str(1000),
       '-b', str(args.block_size),
       '-i', str(65536),
       '-o', str(1024),
       '-r', str(4) ] ) ) )
    print str(yvaluesForFigure1[-1])

  print "Data for Figure 1:"
  print str(xvaluesForFigure1)
  print str(yvaluesForFigure1)
  plotFigure1(yvaluesForFigure1,'figure1.png',xvaluesForFigure1)

def style(index):
  colors = ['g','r','b']
  linesStyles = [':','-','--','-.']
  markerStyles = ['D','o','^','x']
  return '%s%s%s' % (colors[index],linesStyles[index],markerStyles[index])

def plotFigure2(dataPerNumberOfServers,path):
  styleIndex = 0
  plt.figure(2)
  for numberOfServers, rtoMins, goodputs in dataPerNumberOfServers:
    plt.plot(rtoMins, goodputs, style(styleIndex), label='%d servers' % numberOfServers )
    styleIndex += 1
    
  plt.ylabel('Goodput (Mbps)')
  plt.xlabel('RTOmin (milliseconds)')
  plt.gca().set_xscale('log')
  plt.gca().set_xticks(rtoMins)
  plt.gca().set_xticklabels(rtoMins)
  plt.gca().set_xbound(upper=200,lower=0)
  plt.gca().set_ybound(lower=0,upper=1000)
  plt.legend()
  plt.savefig(path)
  

if not args.nofigure2:
  dataForFigure2 = list()
  rtoMins = [1,5,10,50,100,200]
  print "Data for Figure 2:"
  for noOfServers in map( lambda x: int(x), [4,8,16] ):
    print noOfServers
    goodputs = list()
    for rtoMin in rtoMins:
      goodputs.append(float(check_output(
        ['sudo', './simulation.py',
         '-n', str(noOfServers),
         '-m', str(rtoMin),
         '-t', str(args.time),
         '-b', str(args.block_size),
         '-w', str(1000),
         '-i', str(65536),
         '-o', str(1024),
         '-r', str(args.rtt) ])))
    dataForFigure2.append((noOfServers, rtoMins, goodputs))
    print str(dataForFigure2[-1])

  plotFigure2(dataForFigure2,'figure2.png')


def plotFigure3(yvalues,path,xvalues):
  plt.figure(3)
  plt.plot(xvalues, yvalues, '^--', label='200ms RTOmin')
  plt.gca().set_xticks(range(0,5,1))
  plt.ylabel('Goodput (Mbps)')
  plt.xlabel('Number of Servers')
  plt.gca().set_ybound(lower=0)
  plt.legend()
  plt.savefig(path)

if not args.nofigure3:
  #Empty the retransmissions log.
  retransFile = open('retransmissions.txt','w')
  retransFile.write('')
  retransFile.close()

  xvaluesForFigure1 = list()
  yvaluesForFigure1 = list()

  print "Data for Figure 3:"

  xvaluesForFigure1 = range(1,5)
  for i in xvaluesForFigure1:
    yvaluesForFigure1.append(float(check_output(
      ['sudo', './simulation.py',
       '-n', str(i),
       '-m', '200',
       '-t', str(args.time),
       '-w', str(args.bandwidth),
       '-b', str(args.block_size),
       '-i', str(args.input_queue_size),
       '-o', str(args.output_queue_size),
       '-r', str(args.rtt) ] ) ) )
    print str(yvaluesForFigure1[-1])

  print "Data for Figure 3:"
  print str(xvaluesForFigure1)
  print str(yvaluesForFigure1)
  plotFigure3(yvaluesForFigure1,'figure3.png',xvaluesForFigure1)


print ( "Elapsed time: %s" % str(datetime.now() - start) )
