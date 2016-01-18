#!/usr/bin/env python
from __future__ import division
from pysnmp.entity.rfc3413.oneliner import cmdgen
from pysnmp.smi import builder

import logging
import gmetric
import threading
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

ip_pdu = '172.16.8.100'
snmp_port = 161

current_prefix = '1.3.6.1.4.1.232.165.5.4.1.1.6'
powerWatt_prefix = '1.3.6.1.4.1.232.165.5.4.1.1.7'
powerFactor_prefix = '1.3.6.1.4.1.232.165.5.4.1.1.8'

bscgrid28_suffix = '.1.2.4'
bscgrid29_suffix = '.1.2.5'
bscgrid30_suffix = '.1.3.1'
bscgrid31_suffix = '.1.3.2'
atom00_suffix = '.1.3.3'
atom01_suffix = '.1.3.4'

# configuration in the metrics.conf file
metric_config_current = 'current'
metric_config_powerWatt = 'powerWatts'
metric_config_powerFactor = 'powerFactor'

# gmetric spoof addresses

spoof_bscgrid28 = "172.16.8.28:bscgrid28"
spoof_bscgrid29 = "172.16.8.29:bscgrid29"
spoof_bscgrid30 = "172.16.8.30:bscgrid30"
spoof_bscgrid31 = "172.16.8.31:bscgrid31"
spoof_atom00 = "0.0.0.0:atom00"
spoof_atom01 = "0.0.0.0:atom01"

class PowerMetrics:
    	def __init__(self, power_interval, mconf, gconf):
        	self.power_interval = float(power_interval)
        	self.gconf = gconf
        	self.mconf = mconf
        	self._stopevent = threading.Event()

   	def stopThreads(self):
        	logger.info("stopping threads...")
        	self._stopevent.set() 
	
	def collectPowerMetrics(self):
		gmetric_obj = gmetric.Gmetric(self.gconf.host, self.gconf.port, self.gconf.protocol)

		try:
            		while not self._stopevent.isSet():
                		cmdGen = cmdgen.CommandGenerator()

				errorIndication, errorStatus, errorIndex, varBinds = cmdGen.getCmd(
   					cmdgen.CommunityData('admin'),
   					cmdgen.UdpTransportTarget((ip_pdu, snmp_port)),
   					powerWatt_prefix + bscgrid28_suffix,
   					current_prefix + bscgrid28_suffix,
   					powerFactor_prefix + bscgrid28_suffix,

   					powerWatt_prefix + bscgrid29_suffix,
   					current_prefix + bscgrid29_suffix,
   					powerFactor_prefix + bscgrid29_suffix,

   					powerWatt_prefix + bscgrid30_suffix,
   					current_prefix + bscgrid30_suffix,
   					powerFactor_prefix + bscgrid30_suffix,

   					powerWatt_prefix + bscgrid31_suffix,
   					current_prefix + bscgrid31_suffix,
   					powerFactor_prefix + bscgrid31_suffix,

   					powerWatt_prefix + atom00_suffix,
   					current_prefix + atom00_suffix,
   					powerFactor_prefix + atom00_suffix,

   					powerWatt_prefix + atom01_suffix,
   					current_prefix + atom01_suffix,
   					powerFactor_prefix + atom01_suffix,
   				)

				# Check for errors and print out results
				if errorIndication:
    					print(errorIndication)
				elif errorStatus:
    					print(errorStatus)
				else:
					#send metrics
					self.sendPowerMetrics(self.mconf, gmetric_obj, varBinds)

				sleep(self.power_interval)

			logger.info("Terminating %s", threading.currentThread().name)

		except (KeyboardInterrupt, SystemExit):
			self.stopThreads()
			self.exit = True
			sys.exit(0)					


	def sendPowerMetrics(self, mconf, gmetric_obj, varBinds):
    
    		logger.info("%s: sending Power metrics", threading.currentThread().name)
    		#send metric
    		for name, val in varBinds:
	        	#print('%s = %s' % (name.prettyPrint(), val.prettyPrint()))
	        	n = str(name)
	        	v = int(val)

	        	value = v;
	
	        	# ------------------- bscgrid28 --------------------#
	        	if n.endswith(bscgrid28_suffix):
	
	        		#set spoof for the host
	        		spoof = spoof_bscgrid28
	
	        		if n.startswith(powerWatt_prefix):
	        			key = metric_config_powerWatt
	        			if key in self.mconf:
	        				gmetric_obj.send(self.mconf[key]["name"], value, self.mconf[key]["type"], self.mconf[key]["units"], self.gconf.slope, self.mconf[key]["tmax"], self.mconf[key]["dmax"], self.mconf[key]["group"], spoof)

        			elif n.startswith(current_prefix):
	        			value = v/100
	        			key = metric_config_current
	        			if key in self.mconf:
	        				gmetric_obj.send(self.mconf[key]["name"], value, self.mconf[key]["type"], self.mconf[key]["units"], self.gconf.slope, self.mconf[key]["tmax"], self.mconf[key]["dmax"], self.mconf[key]["group"], spoof)

	        		elif n.startswith(powerFactor_prefix):
        				value = v/100
	        			key = metric_config_powerFactor
        				if key in self.mconf:
	        				gmetric_obj.send(self.mconf[key]["name"], value, self.mconf[key]["type"], self.mconf[key]["units"], self.gconf.slope, self.mconf[key]["tmax"], self.mconf[key]["dmax"], self.mconf[key]["group"], spoof)

        		# ------------------- bscgrid29 --------------------#
        		if n.endswith(bscgrid29_suffix):

	        		#set spoof for the host
	        		spoof = spoof_bscgrid29
	
        			if n.startswith(powerWatt_prefix):
	        			key = metric_config_powerWatt
	        			if key in self.mconf:
	        				gmetric_obj.send(self.mconf[key]["name"], value, self.mconf[key]["type"], self.mconf[key]["units"], self.gconf.slope, self.mconf[key]["tmax"], self.mconf[key]["dmax"], self.mconf[key]["group"], spoof)

        			elif n.startswith(current_prefix):
	        			value = v/100
	        			key = metric_config_current
	        			if key in self.mconf:
        					gmetric_obj.send(self.mconf[key]["name"], value, self.mconf[key]["type"], self.mconf[key]["units"], self.gconf.slope, self.mconf[key]["tmax"], self.mconf[key]["dmax"], self.mconf[key]["group"], spoof)

        			elif n.startswith(powerFactor_prefix):
	        			value = v/100
	        			key = metric_config_powerFactor
	        			if key in self.mconf:
	        				gmetric_obj.send(self.mconf[key]["name"], value, self.mconf[key]["type"], self.mconf[key]["units"], self.gconf.slope, self.mconf[key]["tmax"], self.mconf[key]["dmax"], self.mconf[key]["group"], spoof)

        		# ------------------- bscgrid30 --------------------#
        		if n.endswith(bscgrid30_suffix):

        			#set spoof for the host
	        		spoof = spoof_bscgrid30

	        		if n.startswith(powerWatt_prefix):
        				key = metric_config_powerWatt
	        			if key in self.mconf:
	        				gmetric_obj.send(self.mconf[key]["name"], value, self.mconf[key]["type"], self.mconf[key]["units"], self.gconf.slope, self.mconf[key]["tmax"], self.mconf[key]["dmax"], self.mconf[key]["group"], spoof)

        			elif n.startswith(current_prefix):
	        			value = v/100
	        			key = metric_config_current
	        			if key in self.mconf:
        					gmetric_obj.send(self.mconf[key]["name"], value, self.mconf[key]["type"], self.mconf[key]["units"], self.gconf.slope, self.mconf[key]["tmax"], self.mconf[key]["dmax"], self.mconf[key]["group"], spoof)

        			elif n.startswith(powerFactor_prefix):
	        			value = v/100
	        			key = metric_config_powerFactor
	        			if key in self.mconf:
	        				gmetric_obj.send(self.mconf[key]["name"], value, self.mconf[key]["type"], self.mconf[key]["units"], self.gconf.slope, self.mconf[key]["tmax"], self.mconf[key]["dmax"], self.mconf[key]["group"], spoof)

        		# ------------------- bscgrid31 --------------------#
	        	if n.endswith(bscgrid31_suffix):

        			#set spoof for the host
	        		spoof = spoof_bscgrid31

        			if n.startswith(powerWatt_prefix):
	        			key = metric_config_powerWatt
	        			if key in self.mconf:
	        				gmetric_obj.send(self.mconf[key]["name"], value, self.mconf[key]["type"], self.mconf[key]["units"], self.gconf.slope, self.mconf[key]["tmax"], self.mconf[key]["dmax"], self.mconf[key]["group"], spoof)

        			elif n.startswith(current_prefix):
	        			value = v/100
	        			key = metric_config_current
	        			if key in self.mconf:
        					gmetric_obj.send(self.mconf[key]["name"], value, self.mconf[key]["type"], self.mconf[key]["units"], self.gconf.slope, self.mconf[key]["tmax"], self.mconf[key]["dmax"], self.mconf[key]["group"], spoof)

	        		elif n.startswith(powerFactor_prefix):
        				value = v/100
	        			key = metric_config_powerFactor
	        			if key in self.mconf:
	        				gmetric_obj.send(self.mconf[key]["name"], value, self.mconf[key]["type"], self.mconf[key]["units"], self.gconf.slope, self.mconf[key]["tmax"], self.mconf[key]["dmax"], self.mconf[key]["group"], spoof)
"""
        		# ------------------- atom00 --------------------#
        		if n.endswith(atom00_suffix):

	        		#set spoof for the host
        			spoof = spoof_atom00

	        		if n.startswith(powerWatt_prefix):
	        			key = metric_config_powerWatt
	        			if key in self.mconf:
        					gmetric_obj.send(self.mconf[key]["name"], value, self.mconf[key]["type"], self.mconf[key]["units"], self.gconf.slope, self.mconf[key]["tmax"], self.mconf[key]["dmax"], self.mconf[key]["group"], spoof)

        			elif n.startswith(current_prefix):
	        			value = v/10
	        			key = metric_config_current
	        			if key in self.mconf:
        					gmetric_obj.send(self.mconf[key]["name"], value, self.mconf[key]["type"], self.mconf[key]["units"], self.gconf.slope, self.mconf[key]["tmax"], self.mconf[key]["dmax"], self.mconf[key]["group"], spoof)

	        		elif n.startswith(powerFactor_prefix):
        				value = v/100
	        			key = metric_config_powerFactor
        				if key in self.mconf:
        					gmetric_obj.send(self.mconf[key]["name"], value, self.mconf[key]["type"], self.mconf[key]["units"], self.gconf.slope, self.mconf[key]["tmax"], self.mconf[key]["dmax"], self.mconf[key]["group"], spoof)

        		# ------------------- atom01 --------------------#
	        	if n.endswith(atom01_suffix):
	
        			#set spoof for the host
	        		spoof = spoof_atom01

	        		if n.startswith(powerWatt_prefix):
        				key = metric_config_powerWatt
	        			if key in self.mconf:
        					gmetric_obj.send(self.mconf[key]["name"], value, self.mconf[key]["type"], self.mconf[key]["units"], self.gconf.slope, self.mconf[key]["tmax"], self.mconf[key]["dmax"], self.mconf[key]["group"], spoof)

        			elif n.startswith(current_prefix):
	        			value = v/10
        				key = metric_config_current
	        			if key in self.mconf:
	        				gmetric_obj.send(self.mconf[key]["name"], value, self.mconf[key]["type"], self.mconf[key]["units"], self.gconf.slope, self.mconf[key]["tmax"], self.mconf[key]["dmax"], self.mconf[key]["group"], spoof)

	        		elif n.startswith(powerFactor_prefix):
        				value = v/100
	        			key = metric_config_powerFactor
	        			if key in self.mconf:
	        				gmetric_obj.send(self.mconf[key]["name"], value, self.mconf[key]["type"], self.mconf[key]["units"], self.gconf.slope, self.mconf[key]["tmax"], self.mconf[key]["dmax"], self.mconf[key]["group"], spoof)
"""

 		
