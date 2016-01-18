__author__ = 'mcanuto, jsubirat'
__date__ ="$May 15, 2014 13:54:34 AM$"

import subprocess
import re
import gmetric
import threading
from logging import handlers
import logging
from time import sleep

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# create a file handler
handler = handlers.RotatingFileHandler('odroidXUE.log', maxBytes=1024*1024*10)  #max size = 10 MB
handler.setLevel(logging.INFO)

# create a logging format
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)

# add the handlers to the logger
logger.addHandler(handler)

device_metric_commands = {
          'a7':{
            'current':'cat /sys/bus/i2c/drivers/ina2xx/4-0045/hwmon/hwmon1/curr1_input', 
            'shunt_voltage':'cat /sys/bus/i2c/drivers/ina2xx/4-0045/hwmon/hwmon1/in0_input', 
            'bus_voltage':'cat /sys/bus/i2c/drivers/ina2xx/4-0045/hwmon/hwmon1/in1_input', 
            'power':'cat /sys/bus/i2c/drivers/ina2xx/4-0045/hwmon/hwmon1/power1_input'}, 
          'a15':{
            'current':'cat /sys/bus/i2c/drivers/ina2xx/4-0040/hwmon/hwmon0/curr1_input', 
            'shunt_voltage':'cat /sys/bus/i2c/drivers/ina2xx/4-0040/hwmon/hwmon0/in0_input', 
            'bus_voltage':'cat /sys/bus/i2c/drivers/ina2xx/4-0040/hwmon/hwmon0/in1_input', 
            'power':'cat /sys/bus/i2c/drivers/ina2xx/4-0040/hwmon/hwmon0/power1_input'},
          'mem':{
            'current':'cat /sys/bus/i2c/drivers/ina2xx/4-0041/hwmon/hwmon2/curr1_input', 
            'shunt_voltage':'cat /sys/bus/i2c/drivers/ina2xx/4-0041/hwmon/hwmon2/in0_input', 
            'bus_voltage':'cat /sys/bus/i2c/drivers/ina2xx/4-0041/hwmon/hwmon2/in1_input', 
            'power':'cat /sys/bus/i2c/drivers/ina2xx/4-0041/hwmon/hwmon2/power1_input'},
          'gpu':{
            'current':'cat /sys/bus/i2c/drivers/ina2xx/4-0044/hwmon/hwmon3/curr1_input', 
            'shunt_voltage':'cat /sys/bus/i2c/drivers/ina2xx/4-0044/hwmon/hwmon3/in0_input', 
            'bus_voltage':'cat /sys/bus/i2c/drivers/ina2xx/4-0044/hwmon/hwmon3/in1_input', 
            'power':'cat /sys/bus/i2c/drivers/ina2xx/4-0044/hwmon/hwmon3/power1_input'}}

class OdroidXUPowerMetrics:
  def __init__(self, energy_interval, mconf, gconf):
    self.energy_interval = int(energy_interval)
    self.mconf = mconf
    self.gconf = gconf
    self._stopevent = threading.Event()

  def stopThreads(self):
    logger.info("stopping threads...")
    self._stopevent.set()

  def collectPowerMetrics(self):

    regex = re.compile("^[0-9.,]+")
    gmetric_obj = gmetric.Gmetric(self.gconf.host, self.gconf.port, self.gconf.protocol)

    while not self._stopevent.isSet():

      # Clear metrics structure
      device_metrics = {
          'a7':{'current':[], 'shunt_voltage':[], 'bus_voltage':[], 'power':[]}, 
          'a15':{'current':[], 'shunt_voltage':[], 'bus_voltage':[], 'power':[]},
          'mem':{'current':[], 'shunt_voltage':[], 'bus_voltage':[], 'power':[]},
          'gpu':{'current':[], 'shunt_voltage':[], 'bus_voltage':[], 'power':[]}
          }

      for i in range(self.energy_interval):
        for device,commands in device_metric_commands.items():
          for metric, command in commands.items():
            try:
              output = subprocess.check_output(command.split())
              if re.match(regex, output.strip()):
                device_metrics[device][metric].append(float(output))
            except Exception, e:
              logger.error("%s",e)
              continue
        sleep(1)

      # Compact metrics
      averaged_metrics = self.compact_metrics(device_metrics)
      
      # Send metrics
      self.sendPowerMetrics(averaged_metrics, gmetric_obj)


  def compact_metrics(self, metrics_device_maps):
        compacted_device_metrics = {
          'a7':{'current':0.0, 'shunt_voltage':0.0, 'bus_voltage':0.0, 'power':0.0}, 
          'a15':{'current':0.0, 'shunt_voltage':0.0, 'bus_voltage':0.0, 'power':0.0},
          'mem':{'current':0.0, 'shunt_voltage':0.0, 'bus_voltage':0.0, 'power':0.0},
          'gpu':{'current':0.0, 'shunt_voltage':0.0, 'bus_voltage':0.0, 'power':0.0}
          }

        for device, metrics in metrics_device_maps.items():
          for metric, values in metrics.items():
            compacted_value = 0.0
            for value in values:
                compacted_value += value
            compacted_value /= len(values)
            compacted_value /= 1000000.0    #Units are in uV, uA, uW. Convert it to V, A and W.
            compacted_device_metrics[device][metric] = compacted_value
        return compacted_device_metrics


  def sendPowerMetrics(self, metrics_device_maps, gmetric_obj):
    
    for device, metrics in metrics_device_maps.items():
      logger.info("%s: sending device " + device + " energy metrics", threading.currentThread().name)
      for metric, value in metrics.items():
        metric_name = device + "_" + metric
        if metric_name in self.mconf:
          gmetric_obj.send(metric_name, metrics_device_maps[device][metric], self.mconf[metric_name]["type"], self.mconf[metric_name]["units"], self.gconf.slope, self.mconf[metric_name]["tmax"], self.mconf[metric_name]["dmax"], self.mconf[metric_name]["group"])