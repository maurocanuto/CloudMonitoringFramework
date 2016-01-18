#!/usr/bin/env python
import sensors
import logging
import gmetric
import threading
import subprocess
from time import sleep
from gmetric import GmetricConf
from logging import handlers

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


class TemperatureMetrics:
  def __init__(self, temperature_interval, mconf, gconf):
    self.temperature_interval = float(temperature_interval)
    self.mconf = mconf
    self.gconf = gconf
    self._stopevent = threading.Event()

  def stopThreads(self):
    logger.info("stopping threads...")
    self._stopevent.set() 

  def collectTemperatureMetrics(self):
        gmetric_obj = gmetric.Gmetric(self.gconf.host, self.gconf.port, self.gconf.protocol)

        while not self._stopevent.isSet():
                try:
                    sensors.init()
                    list_metrics = {}
                    for chip in sensors.iter_detected_chips():
                        for feature in chip:
                            fname = str(chip)+"-"+feature.label
                            feature_id = fname.replace (" ", "_")
                            #print '%s: %.2f' % (feature_id, feature.get_value())
                            list_metrics[feature_id] = feature.get_value()

                    #send metrics

                    # IPMI TOOL FOR mb TEMPERATURE
                    # get system wide counters metrics
                    p = subprocess.Popen("sudo ipmitool sdr | grep \"MB Temperature\" | awk '{print $4}'", shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                    try:
                        ipmi_value = float(p.stdout.readline().strip())
                        list_metrics["MB_Temperature"] = ipmi_value
                    except ValueError:
                      pass

                    self.sendTemperatureMetrics(list_metrics, gmetric_obj)
                    #print list_metrics
                finally:
                    sensors.cleanup()

                sleep(self.temperature_interval)

        logger.info("Terminating %s", threading.currentThread().name)

  def sendTemperatureMetrics(self, list_metrics, gmetric_obj):
    
      logger.info("%s: sending Temperature metrics", threading.currentThread().name)
      print list_metrics
      #send metric
            
      temp = 'temperature'
      for key,value in list_metrics.items():
         if temp in self.mconf:
           if self.mconf[temp]["spoof"].lower() == "yes":    
             gmetric_obj.send(self.mconf[temp]["name"]+"-"+key , value, self.mconf[temp]["type"], self.mconf[temp]["units"], self.gconf.slope, self.mconf[temp]["tmax"], self.mconf[temp]["dmax"], self.mconf[temp]["group"], self.gconf.spoof)
           else:
             gmetric_obj.send(self.mconf[temp]["name"]+"-"+key , value, self.mconf[temp]["type"], self.mconf[temp]["units"], self.gconf.slope, self.mconf[temp]["tmax"], self.mconf[temp]["dmax"], self.mconf[temp]["group"])
