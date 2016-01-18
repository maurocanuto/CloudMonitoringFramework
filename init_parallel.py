#!/usr/bin/env python

# To change this license header, choose License Headers in Project Properties.
# To change this template file, choose Tools | Templates
# and open the template in the editor.

__author__="mcanuto"
__date__ ="$Feb 13, 2014 6:03:13 PM$"

from domain_info import domainsVM, VMobject
from ConfigParser import ConfigParser
from countersMetrics import CountersMetrics
from powerMetrics import PowerMetrics
from wattsUp import WattsupPowerMetrics
from odroidXUE import OdroidXUPowerMetrics
from rawCountersMetrics import RawCountersMetrics
from extraVMmetrics import ExtraVMmetrics
from temperatureMetrics import TemperatureMetrics
from cpuCoresUsage import CoreUsage
from threading import Thread
from subprocess import Popen, PIPE
from threading import Thread
from time import sleep
from gmetric import GmetricConf
from logging import handlers

import gmetric
import signal
import sys
import guestfs
import os
import errno
import logging



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


pid_file = 'extra_monitoring.pid'
log_file = 'logging.out'
sflow_conf_path = '/etc/hsflowd.auto'
protocol = 'udp'
slope = 'both'
counters_directory = 'counters_data/'

def readScriptConfig():
  conf_dict = {}
  with open("extraMetrics.conf", 'r') as f:
    for line in f:
      if line != '\n' and not line.startswith('#'):
        items = line.split("=")
        key, values = items[0].strip(), items[1].strip()
        conf_dict[key] = values 
  return conf_dict


def readMetricConf(confFile):
  config = ConfigParser()
  fp = open(confFile)
  config.readfp(fp)
  fp.close()
  return config._sections

def sFlowConf():
    sflow_dict = {}
    with open(sflow_conf_path, 'r') as f:
     for line in f:
      li=line.strip()
      if not li.startswith("#"):
       items = line.split("=")
       key, values = items[0], items[1].strip()
       sflow_dict[key] = values
      
    return sflow_dict


def sendHostMetrics(mconf, sflow, g):

   host_m = ExtraHostMetrics()
   #for keymet, valuemet in host_m.readMetrics().items():
   for keymet, valuemet in host_m.readMetrics().items():
    if keymet in mconf:
      #logger.info('sendHostMetrics -', keymet, valuemet)
      if mconf[keymet]["spoof"].lower() == "yes":
        spoof = spoof_ip +":"+ spoof_hostname
        g.send(keymet , valuemet, mconf[keymet]["type"], mconf[keymet]["units"], slope, mconf[keymet]["tmax"], mconf[keymet]["dmax"], mconf[keymet]["group"], spoof)
      else:
        g.send(keymet , valuemet, mconf[keymet]["type"], mconf[keymet]["units"], slope, mconf[keymet]["tmax"], mconf[keymet]["dmax"], mconf[keymet]["group"])


def is_process_running():
  if (os.path.isfile(pid_file)):
    f = open(pid_file)
    process_id = int(f.readline())
    f.close()
    try:
        os.kill(process_id, 0)
        return True
    except OSError:
        logger.info('PID file existed but process ' + str(process_id) + ' was not found')
        return False

  else:
	return False

def terminate_process():
  try:
      with open(pid_file, "r") as f:
        pid = f.readline()
        os.kill(int(pid), signal.SIGTERM)
        os.remove(pid_file)

        logger.info('Process terminated')
        print "Process terminated"
  except IOError:
    os.remove(pid_file)
  except IOError, io:
    logger.error('Terminating process', io)
    print "Process not running: "

if __name__ == '__main__':

  #redirect output to log file

  #old = os.dup(1)
  #os.close(1)
  #os.open(log_file, os.O_WRONLY|os.O_CREAT)
  if os.geteuid() != 0:
    exit("You need to have root privileges to run this script.\nPlease try again, this time using 'sudo'. Exiting.")

  if (len(sys.argv) == 2 and sys.argv[1] == 'stop'):
    terminate_process()
  elif (len(sys.argv) == 2 and sys.argv[1] == 'start'):  
    if is_process_running():
      logger.info('Process already running')
    else:

      # Read script configuration 
      sconf = readScriptConfig()

      # get vm metrics - yes/no
      vm_metrics = sconf['vm_metrics'].strip()

      # get performance counters of the vm pid - yes/no
      vm_counters = sconf['vm_counters'].strip()

      # get performance raw counters of the vm pid - yes/no
      vm_raw_counters = sconf['vm_raw_counters'].strip()

      # get host performance counters - yes/no
      host_counters = sconf['host_counters'].strip()

      # get host performance raw counters - yes/no
      host_raw_counters = sconf['host_raw_counters'].strip()

      # get temperature metrics - yes/no
      temperature_metrics = sconf['temperature_metrics'].strip()

      # get power metrics - yes/no
      power_metrics = sconf['power_metrics'].strip()

      #get other configuration parameters
      counters_interval = sconf['counters_interval'].strip()
      counters_list = sconf['counters_list'].strip()
      power_interval = sconf['power_interval'].strip()
      power_sensors = sconf['power_sensors'].strip().split(',')
      raw_counters_list = sconf['raw_counters_list'].strip()
      vm_metrics_interval = sconf["vm_metrics_interval"].strip()
      metrics_config_path = sconf["metrics_config_path"].strip()
      vm_file_path = sconf["vm_file_path"].strip()
      temperature_interval = sconf['temperature_interval'].strip()
      
      core_usage = sconf['core_usage'].strip()



      #print (counters_interval, vm_metrics_interval, extra_host_metrics_interval, metrics_config_path)
      # Read sFlow configuration
      sflow = sFlowConf()

      # Read metrics configuration
      mconf = readMetricConf(metrics_config_path)

      spoof_ip = sflow["agentIP"]
      spoof_hostname = sflow["hostname"]
      spoof = spoof_ip +":"+ spoof_hostname
      items = sflow["collector"].split(" ")
      host = items[0]
      port = int(items[1])-6343+8649

      # save PID of main process
      with open(pid_file, "w") as myfile:
        myfile.write(str(os.getpid()))


      # create directory for counter metrics
      if not os.path.exists(counters_directory):
        os.makedirs(counters_directory)
      #read and send metrics
      
      try:

        # gmetric configuration
        gconf = GmetricConf(host, port, protocol, slope, spoof)
 
        # VM metrics + VM counters (vm pid in pysichal host) + VM raw counters
        if vm_counters == 'yes':
          if vm_metrics == 'yes':
            if vm_raw_counters == 'yes':
              # VM raw counters (vm pid in pysichal host)
              logger.info("Start collecting VM metrics, VM Counters and VM Raw Counters metrics")
              # ExtraVMmetrics(vm_file_path, vm_metrics_interval, mconf, gconf, counters_directory, counters_interval, counters_list, raw_counters_list GET_VM_METRICS, GET_VM_COUNTERS, GET_VM_RAW_COUNTERS)
              extra_vm = ExtraVMmetrics(vm_file_path, vm_metrics_interval, mconf, gconf, counters_directory, counters_interval, counters_list, raw_counters_list, True, True, True)
              thread_VM = Thread(target = extra_vm.collectVMmetrics)
              thread_VM.start()
            else:
              logger.info("Start collecting VM metrics and VM Counters")
              extra_vm = ExtraVMmetrics(vm_file_path, vm_metrics_interval, mconf, gconf, counters_directory, counters_interval, counters_list, None, True, True, False)
              thread_VM = Thread(target = extra_vm.collectVMmetrics)
              thread_VM.start()
          else:
            if vm_raw_counters == 'yes':
              logger.info("Start collecting VM Counters and VM Raw Counters metrics")
              # ExtraVMmetrics(vm_file_path, vm_metrics_interval, mconf, gconf, counters_interval, counters_list, GET_VM_METRICS, GET_VM_COUNTERS, GET_VM_RAW_COUNTERS)
              extra_vm = ExtraVMmetrics(vm_file_path, vm_metrics_interval, mconf, gconf, counters_directory, counters_interval, counters_list, raw_counters_list, False, True, True)
              thread_VM = Thread(target = extra_vm.collectVMmetrics)
              thread_VM.start()
            else:
              logger.info("Start collecting VM Counters metrics")
              extra_vm = ExtraVMmetrics(vm_file_path, vm_metrics_interval, mconf, gconf, counters_directory, counters_interval, counters_list, None, False, True, False)
              thread_VM = Thread(target = extra_vm.collectVMmetrics)
              thread_VM.start()
          #

        elif vm_metrics == 'yes': 
              if vm_raw_counters == 'yes':
                # VM raw counters (vm pid in pysichal host)
                logger.info("Start collecting VM metrics and VM Raw Counters metrics")
                extra_vm = ExtraVMmetrics(vm_file_path, vm_metrics_interval, mconf, gconf, counters_directory, counters_interval, counters_list, raw_counters_list, True, False, True)
                thread_VM = Thread(target = extra_vm.collectVMmetrics)
                thread_VM.start()

              else:
                logger.info("Start collecting VM metrics")
                extra_vm = ExtraVMmetrics(vm_file_path, vm_metrics_interval, mconf, gconf, None, None, None, None, True, False, False)
                thread_VM = Thread(target = extra_vm.collectVMmetrics)
                thread_VM.start()
        else:
          if vm_raw_counters == 'yes':
              # VM raw counters (vm pid in pysichal host)
              logger.info("Start collecting VM metrics and VM Raw Counters metrics")
              extra_vm = ExtraVMmetrics(vm_file_path, vm_metrics_interval, mconf, gconf, counters_directory, counters_interval, None, raw_counters_list, False, True, True)
              thread_VM = Thread(target = extra_vm.collectVMmetrics)
              thread_VM.start()

        # Standard counters metrics
        if host_counters == 'yes' and counters_list:
          logger.info("Start collecting Host Counters metrics")
          counters_metric = CountersMetrics(counters_directory, counters_interval, counters_list, mconf, gconf, None, None)
          threadCounters = Thread(target = counters_metric.collectCountersMetrics)
          threadCounters.start()

        # Raw counters metrics
        if host_raw_counters == 'yes' and raw_counters_list:
          logger.info("Start collecting Host Raw Counters metrics")
          raw_counters_metric = RawCountersMetrics(counters_directory, counters_interval, raw_counters_list, mconf, gconf, None, None)
          threadRawCounters = Thread(target = raw_counters_metric.collectCountersMetrics)
          threadRawCounters.start()

        # Temperature metrics
        if temperature_metrics == 'yes':
          logger.info("Start collecting Temperature metrics")
          temperature_metric = TemperatureMetrics(temperature_interval, mconf, gconf)
          threadTemperature = Thread(target = temperature_metric.collectTemperatureMetrics)
          threadTemperature.start()


        # Power metrics
        if power_metrics == 'yes':
          logger.info("Start collecting Power metrics")
          
          for power_sensor in power_sensors:
            power_metric = None
            if power_sensor == "bscgrid":
              power_metric = PowerMetrics(power_interval, mconf, gconf)
            elif power_sensor == "wattsup":
              power_metrics_list = sconf['power_metrics_list'].strip()
              wattsup_path = sconf['wattsup_path'].strip()
              wattsup_device = sconf['wattsup_device'].strip()
              connected_node = sconf['connected_node'].strip()
              power_metric = WattsupPowerMetrics(power_interval, power_metrics_list, wattsup_path, wattsup_device, connected_node, mconf, gconf)
            elif power_sensor == "odroidxue":
              power_metric = OdroidXUPowerMetrics(power_interval, mconf, gconf)
            else:
              logger.error("Error, sensor " + power_sensor + " not supported")  

            if power_metric != None:
              threadPower= Thread(target = power_metric.collectPowerMetrics)
              threadPower.start()
          

        # Cpu Cores Usage metrics
        if core_usage == 'yes':
          logger.info("Start collecting Core usage  metrics")
          core_usage = CoreUsage(counters_interval, mconf, gconf)
          threadCoreUsage= Thread(target = core_usage.collectCoreMetrics)
          threadCoreUsage.start()

      except (KeyboardInterrupt, SystemExit):
        extra_vm.stopThreads()
        sys.exit(0)

      logger.info("Threads created...")
  else:
      print "Usage: "+sys.argv[0]+" start or "+sys.argv[0]+" stop"
