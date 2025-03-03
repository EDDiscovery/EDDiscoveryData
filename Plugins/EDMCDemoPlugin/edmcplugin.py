#!/usr/bin/env python3

import time
from threading import Thread
import zmq
import sys
import json
from edd import EDD
import keyboard
from plug import *
from config import config, appname, appversion,copyright,appcmdname
from EDMCLogging import get_main_logger
import logging
from monitor import monitor

plugincmdr = None

# Generate a commander changed if required, send to monitor last journal file, fire a startup event to the plugins
def PlayStoredJournal():
	journal = eddif.RequestJournal(0)
	if journal!= None:
		if monitor.cmdr != plugincmdr and plugincmdr != None:		
			notify_prefs_cmdr_changed(monitor.cmdr,monitor.is_beta)
			plugincmdr = monitor.cmdr
			
		for entry in journal["journal"]:
			journalbytes = entry.encode()
			monitor.parse_entry(journalbytes)
			
		if monitor.cmdr:
			startupevent = monitor.synthesize_startup_event()
			plugincmdr = monitor.cmdr
			notify_journal_entry(monitor.cmdr, monitor.is_beta, monitor.state['SystemName'], monitor.state['StationName'], startupevent,monitor.state)


# Set EDDIF interface up
eddif = EDD(sys.argv[1])

# Hook EDD config implementation up to EDDIF Config object - config will be saved now

config.SetEDDConfig(eddif.Config)		

#eddif.Config['DDB'] = "20"
#eddif.Config['I1'] = 202
# strv = config.get_str("DDB")
# intv = config.get_int("I1")
# print(f"{strv} {intv}")
# config.set("I2",203)
# print(f"I2 = {config.get_int("I2")}")
# intv2 = config.get_int("I3")
# config.delete("I2")
# intv3 = config.get_int("I2")

# Start logging system up

logging.basicConfig(level=logging.DEBUG)
logger = get_main_logger()
logger.info(f"Client PI Start on port {sys.argv[1]} instance {sys.argv[2]}")

# Start monitor up a bit but we don't use a lot of monitor - just the parse->State part


# Load plugins

load_plugins()

# we establish comms with EDD, tell it our version number, and receive info back from EDD stored in the EDDIF variables, including Config

if eddif.SendStart('1.2.3.4',30000) == False:
	print("Failed to communicate with EDD")
	sys.exit(0)

# loop awaiting data from EDD
if eddif.HistoryLength > 0:
	PlayStoredJournal()

while True:
	eddif.FillQueue(50)
	p = eddif.GetNext()
	if p:
		responsetype = p["responsetype"]
		print(f"Python back {p} resonsetype {responsetype}")

		if responsetype == "terminate":
			# send exit to EDD and tell it our config
			eddif.SendExit("Server requested")
			break
		elif responsetype == "historyload":
			PlayStoredJournal()

		elif responsetype == "journalpush":
			print("null")

		elif responsetype == "uievent":
			print("null")
			
	if keyboard.is_pressed('X'):
		# send exit to EDD and tell it our config, and indicate you should close the window if its open
		eddif.SendExit("User Terminated",True)
		print(f"Sent exit")
		keyboard.read_key()
		break
				
print("Python exit")
sys.exit(0)

