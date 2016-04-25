__author__="mcanuto"
__date__ ="$Feb 13, 2014 6:11:42 PM$"

#from subprocess import call, Popen
import subprocess
import re
import gmetric
import threading
import time
from gmetric import GmetricConf
from threading import Thread
from time import sleep
from logging import handlers
import logging
import os

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# create a file handler
handler = handlers.RotatingFileHandler('extraMetrics.log', maxBytes=1024*1024*10)  #max size = 10 MB
handler.setLevel(logging.INFO)

# create a logging format
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)

# add the handlers to the logger
logger.addHandler(handler)

counters_filename = "counters_events.data"

def check_pid(pid):        
    """ Check For the existence of a unix pid. """
    try:
        os.kill(int(pid), 0)
    except OSError:
        return False
    else:
        return True

def getPerfPath():

  with open("extraMetrics.conf", 'r') as f:
    for line in f:
      if line.startswith('perf_tool'):
        items = line.split("=")
        key, value = items[0].strip(), items[1].strip()

        if not value:
          perf_cmd = 'perf'
        else:
          perf_cmd = value

  return perf_cmd

class CountersMetricsDocker:
  def __init__(self, counters_directory, counters_interval, counters_list, mconf, gconf, docker_pids, docker_name):
    self.counters_interval = counters_interval
    self.counters_list = counters_list  
    self.mconf = mconf
    self.gconf = gconf
    self.counters_directory = counters_directory
    self.docker_pids = docker_pids
    self.docker_name = docker_name
    self._stopevent = threading.Event()

  def stopThreads(self):
    logger.info("stopping threads...")
    self._stopevent.set()
  
  def collectCountersMetrics(self):
    gmetric_obj = gmetric.Gmetric(self.gconf.host, self.gconf.port, self.gconf.protocol)
    list_metrics = {}
    perf_cmd = getPerfPath()
    ms_fake_latency_time = 0.178
    for docker_pid in self.docker_pids:
        time.sleep(ms_fake_latency_time)
        thread_AGGmetric = Thread(target = self.aggregateCounterMetric, args=(perf_cmd, docker_pid, list_metrics))
        thread_AGGmetric.start()
    
    #Wait threads to finish...
    time.sleep(float(self.counters_interval) + ms_fake_latency_time*len(self.docker_pids) + 1)
    
    #print "List metrics total %s" % self.docker_name
    #print list_metrics 
         
    # send metrics 
    self.sendCountersMetrics(list_metrics, gmetric_obj, self.docker_name)
  
  def aggregateCounterMetric(self, perf_cmd, docker_pid, list_metrics):
    separator = '|'
    if check_pid(docker_pid):
        pid_counters_file = self.counters_directory + "counters_events_" + docker_pid + ".data"
        cmd = [perf_cmd + " stat -o " + pid_counters_file + " -x " + separator + " -a -p " + docker_pid + " -e " + self.counters_list + " sleep " + self.counters_interval]
        #print cmd
        
        try:
          programs = [ subprocess.call(c.split()) for c in cmd ]
        except Exception, e:
          logger.error("%s",e)

        # parse metrics
        regex = re.compile("^[0-9.,]+")
        with open(pid_counters_file) as f:
          for line in f:
            #print line
            if re.match(regex, line.strip()):
              a = line.strip().split(separator)
              #print a
              if a[-1].strip() in list_metrics:
                list_metrics[a[-1].strip()] += float(a[0].strip())
              else:
                list_metrics[a[-1].strip()] = float(a[0].strip())
        
        #print "Partial metrics:"
        #print list_metrics

        if pid_counters_file:
          try:
            os.remove(pid_counters_file)
          except:
            pass
    else:
        logger.info("Counters PID %s has been destroyed", docker_pid)
        if pid_counters_file:
          try:
            os.remove(pid_counters_file)
          except:
            pass

  def sendCountersMetrics(self, list_metrics, gmetric_obj, vm_name):
    logger.info("sending docker (%s) Counters metrics", vm_name)
      
    for key,value in list_metrics.items():
      if key in self.mconf:
        n = vm_name +"." + self.mconf[key]["name"]
          
        if self.mconf[key]["spoof"].lower() == "yes":
            vm_group = "vm " + self.mconf[key]["group"]
            #print "Send(2) %s" % n
            gmetric_obj.send(n, value, self.mconf[key]["type"], self.mconf[key]["units"], self.gconf.slope, self.mconf[key]["tmax"], self.mconf[key]["dmax"], vm_group, self.gconf.spoof)
        else:
            vm_group = "vm " + self.mconf[key]["group"]
            #print "Send(1) %s" % n
            gmetric_obj.send(n , value, self.mconf[key]["type"], self.mconf[key]["units"], self.gconf.slope, self.mconf[key]["tmax"], self.mconf[key]["dmax"], vm_group)
