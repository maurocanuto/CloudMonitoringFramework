__author__ = 'jsubirat'
__date__ ="$Mar 25, 2014 11:34:42 AM$"

import subprocess
import re
import gmetric
import threading
from logging import handlers
from time import sleep
import logging
from wattsUpProcess import WUProcessWrapper

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# create a file handler
handler = handlers.RotatingFileHandler('wattsUp.log', maxBytes=1024*1024*10)  #max size = 10 MB
handler.setLevel(logging.INFO)

# create a logging format
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)

# add the handlers to the logger
logger.addHandler(handler)

wattsupMetricEquivalent = {'watts':'powerWatts', 'volts':'voltage', 'amps':'current', 'kwh':'kwh', 'power-factor':'powerFactor'}

class WattsupPowerMetrics:
  def __init__(self, energy_interval, energy_metrics_list, wattsup_path, wattsup_device, connected_node, mconf, gconf):
    self.energy_interval = energy_interval
    self.energy_metrics_list = energy_metrics_list.split(",")
    self.wattsup_path = wattsup_path
    self.wattsup_device = wattsup_device
    self.connected_node = connected_node
    self.mconf = mconf
    self.gconf = gconf
    self._stopevent = threading.Event()
    self.wattsup = WUProcessWrapper(logger, wattsup_path, wattsup_device, energy_metrics_list)
    self.threadWattsUp = threading.Thread(target = self.wattsup.continuousCollector)
    self.threadWattsUp.start()

  def stopThreads(self):
    logger.info("Stopping Wattsup module...")
    self._stopevent.set()
    self.threadWattsUp.stopThreads()
  
  def collectPowerMetrics(self):

    gmetric_obj = gmetric.Gmetric(self.gconf.host, self.gconf.port, self.gconf.protocol)
    while not self._stopevent.isSet():
      list_metrics = {}

      captured_energy = self.wattsup.getCurrentReading()   # Obtain a copy of the string, thread safe

      # parse metrics
      regex = re.compile("^[0-9.,]+")
      if re.match(regex, captured_energy.strip()):
        a = captured_energy.strip().split(", ")
        for i in range(len(self.energy_metrics_list)):
            list_metrics[self.energy_metrics_list[i]] = a[i] 

      # send metrics
      self.sendPowerMetrics(list_metrics, gmetric_obj)

      # sleep until next capture
      sleep(int(self.energy_interval))

  # def collectPowerMetrics(self):

  #   gmetric_obj = gmetric.Gmetric(self.gconf.host, self.gconf.port, self.gconf.protocol)

  #   while not self._stopevent.isSet():
  #     list_metrics = {}

  #     #./wattsup -c 1 ttyUSB0 watts
  #     cmd = self.wattsup_path + " -c " + self.energy_interval + " " + self.wattsup_device + " " + " ".join(str(x) for x in self.energy_metrics_list)

  #     output = ""
  #     try:
  #       output = subprocess.check_output(cmd.split())
  #     except Exception, e:
  #       logger.error("%s",e)
  #       sleep(int(self.energy_interval))
  #       continue

  #     # parse metrics
  #     regex = re.compile("^[0-9.,]+")

  #     if int(self.energy_interval) > 1:
  #         list_metrics_tmp = self.empty_metrics_dictionary()
  #         lines = output.split("\n")
  #         for line in lines:
  #           if re.match(regex, line.strip()):
  #               a = line.strip().split(", ")
  #               for i in range(len(self.energy_metrics_list)):
  #                   list_metrics_tmp[self.energy_metrics_list[i]].append(float(a[i]))
  #         list_metrics = self.compact_metrics(list_metrics_tmp)
  #     elif int(self.energy_interval) == 1:
  #         if re.match(regex, output.strip()):
  #           a = output.strip().split(", ")
  #           for i in range(len(self.energy_metrics_list)):
  #               list_metrics[self.energy_metrics_list[i]] = a[i] 

  #     # send metrics
  #     self.sendPowerMetrics(list_metrics, gmetric_obj)


  # def compact_metrics(self, metrics_map_lists):
  #       compacted_metrics = {}
  #       for metric, values in metrics_map_lists.items():
  #           compactedValue = 0.0
  #           if metric != "kwh":
  #               for value in values:
  #                   compactedValue += value
  #               compactedValue /= len(values)
  #           else:
  #               compactedValue = max(values)
  #           compacted_metrics[metric] = compactedValue
  #       return compacted_metrics

  def empty_metrics_dictionary(self):
        list_metrics_tmp = {}
        for metric in self.energy_metrics_list:
            list_metrics_tmp[metric] = []
        return list_metrics_tmp

  def sendPowerMetrics(self, list_metrics, gmetric_obj):
    #send metric
    logger.info("%s: sending host energy metrics", threading.currentThread().name)
    for wattsupkey,value in list_metrics.items():
      key = wattsupMetricEquivalent[wattsupkey]
      if key in self.mconf:
        gmetric_obj.send(key, value, self.mconf[key]["type"], self.mconf[key]["units"], self.gconf.slope, self.mconf[key]["tmax"], self.mconf[key]["dmax"], self.mconf[key]["group"], self.connected_node)
        
        # Left here in case more than one Wattsup device ends up connected.
        # if self.mconf[key]["spoof"].lower() == "yes":
        #   gmetric_obj.send(key, value, self.mconf[key]["type"], self.mconf[key]["units"], self.gconf.slope, self.mconf[key]["tmax"], self.mconf[key]["dmax"], self.mconf[key]["group"], self.connected_node)
        # else:
        #   gmetric_obj.send(key , value, self.mconf[key]["type"], self.mconf[key]["units"], self.gconf.slope, self.mconf[key]["tmax"], self.mconf[key]["dmax"], self.mconf[key]["group"])
