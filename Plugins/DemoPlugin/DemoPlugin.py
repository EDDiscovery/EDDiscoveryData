#!/usr/bin/env python3

import time
from threading import Thread
import zmq
import sys
import json
from edd import EDD
from GridFill import *
import keyboard

print(f"Client PI Start on port {sys.argv[1]} instance {sys.argv[2]}")

eddif = EDD(sys.argv[1])
griddata = GridFill()

# first we establish comms with EDD, tell it our version number, and receive info back from EDD stored in the EDDIF variables, including Config
if eddif.SendStart('1.2.3.4',30000) == False:
	print("Failed to communicate with EDD")
	sys.exit(0)

# display on the RTB that we are running
eddif.UIAddText("RTB", "Python Plugin running\r\n")

# make sure we have a DDB entry in there, if not set it blank (no ticks set)
if not ("DDB" in eddif.Config):
	eddif.Config['DDB'] = ""
	print("Send control DDB to default")

# demonstrate updating the setting of control DDB
eddif.UISet("DDB",eddif.Config['DDB'])

# demonstrate setting the DGV word wrap mode
eddif.UISetWordWrap("DGV",False)

# And if this is in the config file, set up the column settings
if "DGVSettings" in eddif.Config:
	eddif.UISetColumnsSetting("DGV",eddif.Config["DGVSettings"])
	
#set DGV mode 
eddif.UISetDGVSetting("DGV",True,True,True,True)

#install a right click menu
eddif.UIRightClickMenu("DGV", ["RCM1","RCM2","RCM3"] , ["Right click 1","Right click 2","Right click 3"])

#add a control - normally i'd do this in UIInterface.act but just demoing here you can build a UI in here

eddif.UISuspend("P1")
eddif.UIAdd(["CB1,Checkbox,\"CB1\",In:P1,0,0,50,22,\"Check box\""])
eddif.UIAdd(["INSC,Button,\"InsCol\",In:P1,0,0,50,22,\"Ins Column\""])
eddif.UIAddButton("DELC","DelCol",0,0,50,22,"Del Column","P1")
eddif.UIAddButton("REMR","RemRows",0,0,50,22,"Remove rows 2#4","P1")
eddif.UIAddButton("UIP","UIP",0,0,50,22,"Change pos","P1")
eddif.UIAddButton("UIS","UIS",0,0,50,22,"Change size","P1")
eddif.UIAddCheckBox("CB2","CB2",0,0,50,22,"CB2","P1")
eddif.UIAddButton("ACP1","Run Dialog",0,0,50,22,"Dialog","P1")
eddif.UIAddButton("MB","Msg Box",0,0,50,22,"A message box","P1")
eddif.UIAddButton("SFD","Save File",0,0,50,22,"Save file dialog","P1")
eddif.UIAddButton("OFD","Open File",0,0,50,22,"Open file dialog","P1")
eddif.UIAddButton("FolderD","Folder",0,0,50,22,"Folder dialog","P1")
eddif.UIAddButton("InputB","InputBox",0,0,50,22,"Input box","P1")
eddif.UIAddButton("InfoB","InfoBox",0,0,50,22,"Info box","P1")
eddif.UIAddButton("Missions","Missons",0,0,50,22,"Latest missions","P1")
eddif.UIAddButton("Ship","Ship",0,0,50,22,"Current ship stats","P1")
eddif.UIAddButton("ShipList","ShipList",0,0,50,22,"Current ship list","P1")
eddif.UIAddButton("SuitWeapon","SuitWeapon",0,0,50,22,"Current suit weapon","P1")
eddif.UIAddButton("Carrier","Carrier",0,0,50,22,"Get","P1")
eddif.UIAddButton("Ledger","Ledger",0,0,50,22,"Get","P1")
eddif.UIAddButton("Shipyards","Shipyards",0,0,50,22,"Get","P1")
eddif.UIAddButton("Outfitting","Outfitting",0,0,50,22,"Get","P1")
eddif.UIAddButton("Scandata","Scandata",0,0,50,22,"Get","P1")
eddif.UIAddButton("Faction","Faction",0,0,50,22,"Get","P1")
eddif.UIAddButton("Factions","Factions",0,0,50,22,"Get","P1")
eddif.UIAddButton("MCMR","MCMR",0,0,50,22,"Get","P1")
eddif.UIAddButton("JID","HistoryJID",0,0,50,22,"Get","P1")
eddif.UIAddButton("Journal","Journal",0,0,50,22,"Get","P1")
eddif.UIAddButton("History","History",0,0,50,22,"Get","P1")
eddif.UIAddButton("SHLOG","Show Log",0,0,50,22,"Show panel log screen","P1")
eddif.UIResume("P1")

#remove a control

#eddif.UIRemove(["RB1"])

historyloadlength=20

# using helper function, talk to EDD and get 100 history entries to fill grid
griddata.RequestAndFillGrid(eddif,historyloadlength)

ddbvisible = True
ddbenable = True

while True:
	eddif.FillQueue(50)
	p = eddif.GetNext()
	if p:
		responsetype = p["responsetype"]
		print(f"Python back {p} resonsetype {responsetype}")

		if responsetype == "terminate":
			# on terminate, update config with DGV column settings
			settings = eddif.UIGetColumnsSetting("DGV")
			print(f"Settings received {settings}")
			eddif.Config["DGVSettings"] = settings
			
			# send exit to EDD and tell it our config
			print(f"Send terminate")
			eddif.SendExit("Server requested")
			break
		elif responsetype == "historyload":
			griddata.RequestAndFillGrid(eddif,historyloadlength)

		elif responsetype == "historypush":
			rows = griddata.FillRows(p["rows"])
			eddif.UIAddSetRows("DGV",rows)
			
		elif responsetype == "journalpush":
			print(f"Journal push {p["commander"]} {p["journalEntry"]}")

		elif responsetype == "uievent":
			controlname = p["control"]
			if controlname == "DDB":
				event = p["event"]
				value = p["data"]
				if event == "DropDownButtonClosed":
					eddif.Config['DDB'] = value
					print(f"Config saved for DDB as {value}")
				elif event == "DropDownButtonPressed":
					print(f"Button  {value} pressed")
					eddif.UICloseDropDownButton();
			elif controlname == "RELOAD":
				griddata.RequestAndFillGrid(eddif,historyloadlength)
			elif controlname == "HIDE":
				ddbvisible = not(ddbvisible)
				eddif.UIVisible("DDB",ddbvisible)
			elif controlname == "DISABLE":
				ddbenable= not(ddbenable)
				eddif.UIEnable("DDB",ddbenable)
			elif controlname == "INSC":
				eddif.UIInsertColumns("DGV",1,[ {"type":"text","headertext":"INSC" }])
			elif controlname == "DELC":
				eddif.UIRemoveColumns("DGV",1,2)
			elif controlname == "REMR":
				eddif.UIRemoveRows("DGV",2,4)
			elif controlname == "UIP":
				eddif.UIPosition("DDB",100,100)
			elif controlname == "UIS":
				eddif.UISize("DDB",64,64)
			elif controlname == "ACP1":
				eddif.ActionRunProgram("DemoDialog",{ "PATH":"c:\\code\\demo.txt", "V1":10, "V2":True, "V3":"string", "V4":[1,2,3]})
				ret = eddif.ActionWaitForProgram("DemoDialog",100000)
				if ret != None:
					eddif.UIAddText("RTB", f"Dialog returned {ret["Success"]}\r\n")
			elif controlname == "MB":
				ret = eddif.UIMessageBoxWait("Snake syntax sucks","A message from the snake","AbortRetryIgnore","Exclamation",100000)
				print(f"Message box returned {ret}")
			elif controlname == "SHLOG":
				ret = eddif.ShowLog()
			elif controlname == "SFD":
				ret = eddif.UISaveFileDialog("c:\\code","Log files|*.log|All Files|*.*","*.log",True,100000)
				print(f"SFD returned {ret}")
			elif controlname == "OFD":
				ret = eddif.UIOpenFileDialog("c:\\code","Log files|*.log|All Files|*.*","*.log",True,100000)
				print(f"OFD returned {ret}")
			elif controlname == "FolderD":
				ret = eddif.UIFolderDialog("Open folder","MyDocuments",100000)
				print(f"OFD returned {ret}")
			elif controlname == "InputB":
				ret = eddif.UIInputBox("Input box",["P1","P2","P3"],["I1","I2",""],["T1","T2","T3"],True,100000)
				print(f"OFD returned {ret}")
			elif controlname == "InfoB":
				ret = eddif.UIInfoBox("Caption text", "Message text\r\nAnd more..",100000)
				print(f"OFD returned {ret}")
			elif controlname == "Missions":
				ret = eddif.RequestMissions(griddata.LastestEntry,100000)
				eddif.UIInfoBox("Missions returned", json.dumps(ret, indent=2), 100000)
			elif controlname == "Ship":
				ret = eddif.RequestShip(griddata.LastestEntry,100000)
				eddif.UIInfoBox("Ship returned", json.dumps(ret, indent=2), 100000)
			elif controlname == "ShipList":
				ret = eddif.RequestShipList(100000)
				eddif.UIInfoBox("Ship List", json.dumps(ret, indent=2), 100000)
			elif controlname == "SuitWeapon":
				ret = eddif.RequestSuitsWeapons(griddata.LastestEntry,100000)
				eddif.UIInfoBox("Suit/Weapons List", json.dumps(ret, indent=2), 100000)
			elif controlname == "Carrier":
				ret = eddif.RequestCarrier(100000)
				eddif.UIInfoBox("Carrier", json.dumps(ret, indent=2), 100000)
			elif controlname == "Ledger":
				ret = eddif.RequestLedger(100000)
				eddif.UIInfoBox("Ledger", json.dumps(ret, indent=2), 100000)
			elif controlname == "Shipyards":
				ret = eddif.RequestShipyards(100000)
				eddif.UIInfoBox("Shipyards", json.dumps(ret, indent=2), 100000)
			elif controlname == "Outfitting":
				ret = eddif.RequestOutfitting(100000)
				eddif.UIInfoBox("Outfitting", json.dumps(ret, indent=2), 100000)
			elif controlname == "Scandata":
				ret = eddif.RequestScandata(griddata.LatestSystem, None, 100000)
				eddif.UIInfoBox("Scandata", json.dumps(ret, indent=2), 100000)
			elif controlname == "Faction":
				ret = eddif.RequestFaction("Aornum Republic Party", 100000)
				eddif.UIInfoBox("Faction", json.dumps(ret, indent=2), 100000)
			elif controlname == "Factions":
				ret = eddif.RequestFactions(100000)
				eddif.UIInfoBox("Factions", json.dumps(ret, indent=2), 100000)
			elif controlname == "MCMR":
				ret = eddif.RequestMCMR(griddata.LastestEntry,100000)
				eddif.UIInfoBox("MCMR", json.dumps(ret, indent=2), 100000)
			elif controlname == "JID":
				ret = eddif.RequestHistoryByJID(griddata.LatestJID,100000)		# by JID
				eddif.UIInfoBox("JID", json.dumps(ret, indent=2), 100000)
			elif controlname == "Journal":
				ret = eddif.RequestJournal(0,100000)		# journal JSON records
				eddif.UIInfoBox("Journal", json.dumps(ret, indent=2), 100000)
			elif controlname == "History":
				ret = eddif.RequestHistory(0,10)		# history records
				eddif.UIInfoBox("History", json.dumps(ret, indent=2), 100000)
				
					

	
	# if keyboard.is_pressed('X'):
	# 	eddif.SendExit("User Terminated",True)
	# 	print(f"Sent exit")
	# 	keyboard.read_key()
	# 	break
		
print("Python exit")
sys.exit(0)

