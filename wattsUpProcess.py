__author__ = 'jsubirat'
__date__ ="$May 22, 2014 17:37:42 AM$"

import subprocess
import threading
import logging
import re
import pexpect

#If the process emits many errors, it's better to restart it, as it tends to work better
MAX_ERRORS = 5

class WUProcessWrapper:
    def __init__(self, logger, wattsup_path, wattsup_device, energy_metrics_list):
        self.logger = logger
        self._stopevent = threading.Event()
        self.wattsup_path = wattsup_path
        self.wattsup_device = wattsup_device
        self.energy_metrics_list = energy_metrics_list.split(",")
        self.current_reading = ""
        self.errors = 0

    def stopThreads(self):
        self.logger.info("Stopping Wattsup process wrapper...")
        self._stopevent.set()

    def getCurrentReading(self):
        return self.current_reading[:]

    def continuousCollector(self):

        #./wattsup -c 1 ttyUSB0 watts
        #./wattsup ttyUSB0 watts
        cmd = self.wattsup_path + " " + self.wattsup_device + " " + " ".join(str(x) for x in self.energy_metrics_list)
        while not self._stopevent.isSet():
            child = pexpect.spawn(cmd, timeout=None)
            for line in child: 
                self.logger.info(line)
                regex = re.compile("^[0-9.,]+")
                if re.match(regex, line.strip()):
                    self.current_reading = line[:]
                else:
                    self.errors = (self.errors + 1) % MAX_ERRORS
                    if self.errors == 0:
                        break
                
                if self._stopevent.isSet():
                    break
            child.close()