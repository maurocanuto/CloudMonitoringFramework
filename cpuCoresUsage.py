#!/usr/bin/env python
import sys, psutil, threading, logging, gmetric
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

class CoreUsage:
	def __init__(self, sleep_interval, mconf, gconf):
		self.sleep_interval = float(sleep_interval)
		self.mconf = mconf
		self.gconf = gconf
		self._stopevent = threading.Event()

	def stopThreads(self):
		logger.info("stopping threads...")
		self._stopevent.set() 

	# get overall cpu use
	def total_cpu(self):
		total_cpu_use = psutil.cpu_percent(interval=1, percpu=False)
		return total_cpu_use

	# get per core cpu use
	def percore_cpu(self):
		percore_cpu_use = []
		cpu_id = 0
		for cpu in psutil.cpu_percent(interval=1, percpu=True):
			array_line = str(cpu_id), cpu
			percore_cpu_use.append(array_line)
			cpu_id += 1
		return percore_cpu_use

	def collectCoreMetrics(self):
  		gmetric_obj = gmetric.Gmetric(self.gconf.host, self.gconf.port, self.gconf.protocol)

  		while not self._stopevent.isSet():
  			#get metrics
  			percore_cpu_use = self.percore_cpu()
			#send metrics
			self.sendCoreUsageMetrics(percore_cpu_use, gmetric_obj)

			sleep(self.sleep_interval - 1)

		logger.info("Terminating %s", threading.currentThread().name)


	def sendCoreUsageMetrics(self, percore_cpu_use, gmetric_obj):
    
		logger.info("%s: sending CPU Cores Usage metrics", threading.currentThread().name)
		for core_use in percore_cpu_use:
			core_id = core_use[0]
			core_load = core_use[1]

			name = "Core_" + core_id

			temp = 'coreUsage'
			if temp in self.mconf:
				if self.mconf[temp]["spoof"].lower() == "yes":    
					gmetric_obj.send(name, core_load, self.mconf[temp]["type"], self.mconf[temp]["units"], self.gconf.slope, self.mconf[temp]["tmax"], self.mconf[temp]["dmax"], self.mconf[temp]["group"], self.gconf.spoof)
				else:
					gmetric_obj.send(name, core_load, self.mconf[temp]["type"], self.mconf[temp]["units"], self.gconf.slope, self.mconf[temp]["tmax"], self.mconf[temp]["dmax"], self.mconf[temp]["group"])

			
