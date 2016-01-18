#!/usr/bin/python

import libvirt
import sys
import libxml2

class VMobject(object):
   def __init__(self, id=0, name=None):
	self.id = id
	self.name = name
	self.stillAlive = True
	self.firstTime = True

class domainsVM():
   def __init__(self):
     self.vm_map = {}

   def getDomains(self):
#     print len(self.vm_map)
     conn = libvirt.openReadOnly(None)
     assert conn, 'Failed to open connection'

     for key, value in self.vm_map.iteritems():
	value.stillAlive=False
     
     for id in conn.listDomainsID():
       dom = conn.lookupByID(id)
       vname = dom.name()
       if vname in self.vm_map:
	  self.vm_map[vname].stillAlive = True
	  self.vm_map[vname].firstTime = False
       else:
	  vm = VMobject(dom.ID(),vname)
	  self.vm_map[vname] = vm

     #remove from list VM destroyed
     for key, value in self.vm_map.items():
	if not value.stillAlive:
	   del self.vm_map[key]

     return self.vm_map
