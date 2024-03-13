#!/usr/bin/python3

import sys
import matplotlib
import numpy as np
from matplotlib import cm
from matplotlib.ticker import LinearLocator
import matplotlib.pyplot as plt


def get_cmap(n, name='hsv'):
    '''Returns a function that maps each index in 0, 1, ..., n-1 to a distinct 
    RGB color; the keyword argument name must be a standard mpl colormap name.'''
    return plt.cm.get_cmap(name, n)


def main():

  benchmarks = {}

  import json
  f = open(sys.argv[1], 'r')
  for line in f.readlines():
    if "speed" in line:
       gops = float(line.split()[2])
       n_elem = int(line.split()[4].split('=')[1])
       n_lane = int(line.split()[5].split('=')[1][0])
       if n_lane in benchmarks.keys():
         benchmarks[n_lane].append((n_elem, gops))
       else:
         benchmarks[n_lane] = [(n_elem, gops)]

  cmap = get_cmap(max(benchmarks.keys()) + 1)

  plt.figure( figsize = ( 9, 6 ) )
  plt.title('RVV kernels benchmark')
  plt.xlabel('Elements')
  plt.ylabel('GOP/sec')
  plt.yticks(np.arange(0, 1000, step=2))

  # plot
  for lane in benchmarks.keys():
    lanes, gops = np.array(benchmarks[lane]).T
    max_gops = np.max(gops)
    plt.plot(lanes, gops, color=cmap(lane), label="lanes=%i (max=%.2f)" % (lane, max_gops))
    plt.scatter(lanes, gops, color=cmap(lane))

  plt.legend(shadow=True)
  plt.savefig( "%s.png" % sys.argv[1], format='png', bbox_inches='tight')
  #plt.show()
  plt.close()

if __name__ == "__main__":
  main()
