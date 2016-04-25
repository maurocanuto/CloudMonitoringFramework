
__author__="mcanuto"
__date__ ="$Feb 13, 2014 6:11:42 PM$"

import sys
from time import sleep
import os
import gmetric
from domain_info import domainsVM, VMobject
from countersMetrics import CountersMetrics
from countersMetricsDocker import CountersMetricsDocker
from rawCountersMetrics import RawCountersMetrics
from threading import Thread
from gmetric import GmetricConf
from logging import handlers
from docker import Client
import threading
import guestfs
import errno
import gmetric
import Queue
import time
import logging
import subprocess

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# create a file handler
handler = handlers.RotatingFileHandler('extraMetrics.log', maxBytes=1024*1024)
handler.setLevel(logging.INFO)

# create a logging format
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)

# add the handlers to the logger
logger.addHandler(handler)


check_vm_interval = 2
MAX_COUNT = 6
vm_pid_path_prefix = '/var/run/libvirt/qemu/'

class ExtraVMmetrics:
  def __init__(self, vm_file_path, vm_metrics_interval, mconf, gconf, counters_directory, counters_interval, counters_list, raw_counters_list, get_vm_metrics, get_vm_counters, get_vm_raw_counters):
    self.vm_file_path = vm_file_path
    self.vm_metrics_interval = vm_metrics_interval
    self.mconf = mconf
    self.gconf = gconf
    self.counters_interval = counters_interval
    self.counters_list = counters_list
    self.raw_counters_list = raw_counters_list
    self.get_vm_metrics = get_vm_metrics
    self.get_vm_counters = get_vm_counters
    self.get_vm_raw_counters = get_vm_raw_counters
    self.counters_directory = counters_directory
    self._stopevent = threading.Event()
    self.cli = None

  def stopThreads(self):
    logger.info("stopping threads...")
    self._stopevent.set()
  
  def collectDockerMetrics(self):
    try:
      while(True):
        
        if self.cli is None:
            self.cli = Client(base_url='unix://var/run/docker.sock')
          
        for container in self.cli.containers(latest=True):
            info = self.cli.inspect_container(container['Id'])
            
            docker_name = info['Config']['Hostname']
            container_pid = str(info['State']['Pid'])
            
            container_processes = subprocess.check_output('pgrep -P %s' % container_pid, shell=True).strip().split("\n")
            docker_pids = [container_pid] + container_processes
            #print  docker_pids

            logger.info("Collecting Docker Counters for %s", docker_name)
            if self.counters_list != "" and self.raw_counters_list != "":
                all_counter_list = self.counters_list + "," + self.raw_counters_list
            elif self.counters_list != "":
                all_counter_list = self.counters_list
            elif self.raw_counters_list != "":
                all_counter_list = self.raw_counters_list
            else:
                logger.error("No counter list provided!")
                return false
            
            if len(all_counter_list) > 0:
                counters_metric = CountersMetricsDocker(self.counters_directory, self.counters_interval, all_counter_list, self.mconf, self.gconf, docker_pids, docker_name)
                #print "counters_metric.collectCountersMetrics"
                counters_metric.collectCountersMetrics()

        sleep(check_vm_interval)

    except (KeyboardInterrupt, SystemExit):
      self.stopThreads()
      self.exit = True
      sys.exit(0)
  
  def collectVMmetrics(self):
    domains = domainsVM()

    try:
      while not self._stopevent.isSet():
      #while True:
      #for i in range(1,6):
        #print "...getting Domains..."

        dom_list = domains.getDomains()
        #print "Number of VMs:", len(dom_list)

        for key in dom_list:
          if dom_list[key].firstTime:
            vm_name = dom_list[key].name

            if self.get_vm_metrics is True:
              # for each NEW VM start a thread for collecting and sending VM metrics
              logger.info("New VM detected: starting thread for %s", vm_name)
              thread_VMmetric = Thread(target = self.readVMmetrics, args=(vm_name, ))
              thread_VMmetric.daemon = True
              thread_VMmetric.start()

            if self.get_vm_counters or self.get_vm_raw_counters:
              # get pid of vm

              path = vm_pid_path_prefix + vm_name + '.pid'
              with open(path, 'r') as f:
                vm_pid = f.read()

            if self.get_vm_counters is True and self.counters_list:
              # for each NEW VM start a thread for collecting and sending counters metrics
              logger.info("New VM detected: starting collecting VM Counters - thread for %s", vm_name)
              counters_metric = CountersMetrics(self.counters_directory, self.counters_interval, self.counters_list, self.mconf, self.gconf, vm_pid, vm_name)
              thread_VMCountersMetric = Thread(target = counters_metric.collectCountersMetrics)
              thread_VMCountersMetric.daemon = True
              thread_VMCountersMetric.start()

              #send metrics

            if self.get_vm_raw_counters is True and  self.raw_counters_list:
              # for each NEW VM start a thread for collecting and sending counters metrics
              logger.info("New VM detected: starting collecting VM Raw Counters - thread for %s", vm_name)

              raw_counters_metric = RawCountersMetrics(self.counters_directory, self.counters_interval, self.raw_counters_list, self.mconf, self.gconf, vm_pid, vm_name)
              thread_VMRawCountersMetric = Thread(target = raw_counters_metric.collectCountersMetrics)
              thread_VMRawCountersMetric.daemon = True
              thread_VMRawCountersMetric.start()

        sleep(check_vm_interval)


      logger.info("All VM threads terminated")

    except (KeyboardInterrupt, SystemExit):
      self.stopThreads()
      self.exit = True
      sys.exit(0)

  def readVMmetrics(self, vm_name): 
    gmetric_obj = gmetric.Gmetric(self.gconf.host, self.gconf.port, self.gconf.protocol)

    list_metrics = {}
    exec_time = 0

    while not self._stopevent.isSet():
      #check if vm is still alive
      domains = domainsVM()
      dom_list = domains.getDomains()
      if vm_name not in dom_list:
        logger.info("%s has been destroyed", vm_name)
        break

      try:

        start_time = time.time()
        g = guestfs.GuestFS ()
        # Attach the disk image read-only to libguestfs. 
        g.add_domain(vm_name, readonly=1)
        # Run the libguestfs back-end.
        
        g.launch()
        
        # Ask libguestfs to inspect for operating systems.
        roots = g.inspect_os ()
        if len (roots) == 0:
          logger.error("no operating systems found")
          break

        if len (roots) > 1:
          logger.error("dual/multi-boot images are not supported")
          break

        root = roots[0]
        # Mount up the disks, like guestfish -i.
        mps = g.inspect_get_mountpoints (root)
        for device in mps:
          try:
            g.mount(device[1], device[0])
          except RuntimeError as msg:
            logger.error("%s (ignored)",msg)

        try:    
          lines = g.read_lines(self.vm_file_path)
              
          for l in lines:
            if len(l.strip()) > 0:
              token = l.split('|')

              n = token[0].strip()
              v = token[1].strip()
                
              list_metrics[n] = v
                  
          #send metrics
          self.sendVMmetrics(list_metrics, gmetric_obj, vm_name)
        except RuntimeError, io:
          logger.warning("%s %s %s", threading.currentThread().name, vm_name, io)

        g.umount_all()
        g.close()
        exec_time = time.time() - start_time

      except (KeyboardInterrupt, SystemExit):
        self.stopThreads()
        sys.exit(0)

      except Exception, e:
        logger.error("%s",e)

      sleep_time = float(self.vm_metrics_interval) - float(exec_time)
      if sleep_time < 0:
        sleep_time = float(self.vm_metrics_interval)
      
      #print "sleep:", sleep_time  
      sleep(sleep_time)

    logger.info("Terminating %s", threading.currentThread().name)
        


  def sendVMmetrics(self, list_metrics, gmetric_obj, vm_name):
    
    logger.info("%s: sending metrics for %s", threading.currentThread().name, vm_name)
    #send metric
    for key,value in list_metrics.items():
      n = vm_name+".v"+key
      if key in self.mconf:
        #gmetric_obj.send("TESTGROUP", "812344", 'float', "kb", "both", 50, 500, 'vm memory', "127.0.0.1:minerva-21")
        if self.mconf[key]["spoof"].lower() == "yes":    
          gmetric_obj.send(n , value, self.mconf[key]["type"], self.mconf[key]["units"], self.gconf.slope, self.mconf[key]["tmax"], self.mconf[key]["dmax"], self.mconf[key]["group"], self.gconf.spoof)
        else:
          gmetric_obj.send(n , value, self.mconf[key]["type"], self.mconf[key]["units"], self.gconf.slope, self.mconf[key]["tmax"], self.mconf[key]["dmax"], self.mconf[key]["group"])
