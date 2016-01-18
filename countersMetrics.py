__author__="mcanuto"
__date__ ="$Feb 13, 2014 6:11:42 PM$"

#from subprocess import call, Popen
import subprocess
import re
import gmetric
import threading
from gmetric import GmetricConf
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

class CountersMetrics:
  def __init__(self, counters_directory, counters_interval, counters_list, mconf, gconf, vm_pid, vm_name):
    self.counters_interval = counters_interval
    self.counters_list = counters_list  
    self.mconf = mconf
    self.gconf = gconf
    self.counters_directory = counters_directory

    if vm_pid is None:
      self.vm_pid = None
    else:
      self.vm_pid = vm_pid

    if vm_name is not None:
      self.vm_name = vm_name
    else:
      self.vm_name = None
      
    self._stopevent = threading.Event()

  def stopThreads(self):
    logger.info("stopping threads...")
    self._stopevent.set()

  def collectCountersMetrics(self):
    separator = '|'
    vm_counters_file = ""

    perf_cmd = getPerfPath()
    
    gmetric_obj = gmetric.Gmetric(self.gconf.host, self.gconf.port, self.gconf.protocol)

    while not self._stopevent.isSet():
      list_metrics = {}
      # commands = [ "perf stat -a -e cpu-cycles sleep 1" ]
      if self.vm_pid is None:
        counters_file = self.counters_directory + counters_filename

        # get system wide counters metrics
        cmd = [perf_cmd + " stat -o "+counters_file+" -x "+ separator +" -a -e "+ self.counters_list +" sleep "+ self.counters_interval]

        try:
          programs = [ subprocess.call(c.split()) for c in cmd ]
        except Exception, e:
          logger.error("%s",e)
        
        # parse metrics
        regex = re.compile("^[0-9.,]+")
        with open(counters_file) as f:
          for line in f:
          
            if re.match(regex, line.strip()):
              a = line.split(separator)
              list_metrics[a[1].strip()] = a[0].strip()

      else:
        # get counters metrics for the VM PID
        if check_pid(self.vm_pid):
          vm_counters_file = self.counters_directory + "counters_events_"+ self.vm_name +".data"
          cmd = [perf_cmd + " kvm stat -o "+vm_counters_file+" -x "+ separator +" -a -p "+ self.vm_pid +" -e "+ self.counters_list +" sleep "+ self.counters_interval]

          try:
            programs = [ subprocess.call(c.split()) for c in cmd ]
          except Exception, e:
            logger.error("%s",e)
        
          # parse metrics
          regex = re.compile("^[0-9.,]+")
          with open(vm_counters_file) as f:
            for line in f:
              #print line 
              if re.match(regex, line.strip()):
                a = line.split(separator)
                list_metrics[a[1].strip()] = a[0].strip()

          if vm_counters_file:
            try:
              os.remove(vm_counters_file)
            except:
              pass
        else:
          logger.info("Counters PID %s: %s has been destroyed", self.vm_pid, self.vm_name)
          if vm_counters_file:
            try:
              os.remove(vm_counters_file)
            except:
              pass
          break

      # send metrics 
      self.sendCountersMetrics(list_metrics, gmetric_obj, self.vm_name)



  def sendCountersMetrics(self, list_metrics, gmetric_obj, vm_name):
    #send metric
    if vm_name is not None:
      logger.info("%s: sending VM (%s) Counters metrics", threading.currentThread().name, vm_name)
    else:
      logger.info("%s: sending host Counters metrics", threading.currentThread().name)
      
    for key,value in list_metrics.items():
      if key in self.mconf:
        if vm_name is not None:
          n = vm_name +"." + self.mconf[key]["name"]
        else:
          n = self.mconf[key]["name"]
          
        if self.mconf[key]["spoof"].lower() == "yes":
          if vm_name is not None:    
            vm_group = "vm " + self.mconf[key]["group"]
            gmetric_obj.send(n, value, self.mconf[key]["type"], self.mconf[key]["units"], self.gconf.slope, self.mconf[key]["tmax"], self.mconf[key]["dmax"], vm_group, self.gconf.spoof)
          else:
            gmetric_obj.send(n, value, self.mconf[key]["type"], self.mconf[key]["units"], self.gconf.slope, self.mconf[key]["tmax"], self.mconf[key]["dmax"], self.mconf[key]["group"], self.gconf.spoof)

        else:
          if vm_name is not None:    
            vm_group = "vm " + self.mconf[key]["group"]
            gmetric_obj.send(n , value, self.mconf[key]["type"], self.mconf[key]["units"], self.gconf.slope, self.mconf[key]["tmax"], self.mconf[key]["dmax"], vm_group)
          else:
            gmetric_obj.send(n , value, self.mconf[key]["type"], self.mconf[key]["units"], self.gconf.slope, self.mconf[key]["tmax"], self.mconf[key]["dmax"], self.mconf[key]["group"])




