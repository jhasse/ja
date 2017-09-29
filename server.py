#!/usr/bin/env python3

import os
import hashlib
from pydbus import SessionBus
from gi.repository import GObject

class JaServer(object):
	def __init__(self, quit_loop):
		self.reader = os.fdopen(3, 'rb', 0)
		self.quit_loop = quit_loop

	def read(self, size):
		return self.reader.read(size)

	def kill(self):
		self.quit_loop()

with open(os.path.join(os.path.dirname(__file__), "com.bixense.Ja.xml"), "r") as xml_file:
	JaServer.dbus = ''.join(xml_file.readlines())

loop = GObject.MainLoop()
bus = SessionBus()
# Add a hash of the working directory so that it's possible to run ja multiple times per session,
# but not per directory:
bus.publish("com.bixense.Ja." + hashlib.sha256(os.path.realpath(os.getcwd()).encode()).hexdigest(),
            JaServer(loop.quit))
try:
	loop.run()
except KeyboardInterrupt:
	pass
