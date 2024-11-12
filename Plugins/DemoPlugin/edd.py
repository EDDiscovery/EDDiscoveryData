import json
import zmq
import queue
import time

# server is stateless
#
# Variables
#	EDD.EDDVersion = version reported by EDD on start
#	EDD.APIVersion = API Level reported by EDD on start - you can use this to check your plugin can work with this EDD
#	EDD.HistoryLength = history length reported by EDD on start
#	EDD.Commander = commander reported by EDD on start (may be empty)
#   EDD.Config = JSON object of the config reported by EDD on start, and reported back to EDD on exit
#
################################################################################################ REQUESTS FROM PYTHON
#
# client requesttype = "start"
#				version = "x.y.z.b" - version of the plugin
#				apiversion = N - what version you were written to
#        server responsetype = "start"
#               eddversion = "x.y.z.b"
#               apiversion = 1
#				historylength = X (number of history entries currently loaded, may be zero)
#				commander = commander loaded (may be blank, none loaded yet)
#				config = config string (this code uses JSON) to configure tool with.  
#						If no config has been set, this will be empty, and edd.py will edd.Config to an empty JSON object
#
# client requesttype = "exit"	: Sent by client either because it wants to exit, or the server asked for a termination
#				reason = "string" : Reason for exit.  Empty string or reason for error
#				config = config string (this code uses  JSON). EDD, if not empty will store the config string in the user panel data store of EDD
#
# client requesttype = "history"
#				start = history entry start position 
#				length = number of entries to send. Can be longer than whats available from start
#		server responsetype = requesttype
#				start = requested start address
#				length = number of entries sent, 0 if start is out of range and none is available
#				commander = string, name of commander
#				rows[] containing an object of journal entries, and example is below:
#
# client requesttype = "historyjid"
#				jid to request
#		server responsetype = requesttype
#				jid back
#				entry = None if does not exist, or
#				length = number of entries sent, 0 if start is out of range and none is available
#				commander = string, name of commander
#				rows[] containing an object of journal entries, and example is below:
#
#		Each entry/row contains:
#			Index is the number used to look it up, EntryNumber is 1.. based. Unfiltered index is the entry number without all the filtered out entries 
#			 {"EntryNumber":22036,"Index":22035,"UnfilteredIndex":24753,
#			 .. Journal Entry itself
#			 "journalEntry":{"Station":"Two","StationType":"Crater Outpost","FDStationType":"CraterOutpost","CarrierDockingAccess":null,"StarSystem":"Eowyg Auscs FG-Y d34","MarketID":3534247946,"Commodities":[],"Id":2269018,"TLUId":2757,"IsJournalSourced":true,"CommanderId":36,"EventTypeID":"Market","EventTypeStr":"Market","EventTimeUTC":"2024-10-06T13:52:39Z","EventTimeLocal":"2024-10-06T14:52:39Z","SyncedEDSM":false,"SyncedEDDN":false,"StartMarker":false,"StopMarker":false,"IsBeta":false,"IsHorizons":true,"IsOdyssey":true,"GameVersion":"4.0.0.1808","Build":"r304197/r0 ","FullPath":"c:\\code\\logs\\empty\\Journal.2024-10-06T015203.01.log","SNC":null},
#			 .. System records where we are for all records
#			 "System":{"Source":"FromJournal","MainStarType":"A","Name":"Eowyg Auscs FG-Y d34","X":23091.96875,"Y":29.8125,"Z":19516.3125,"HasCoordinate":true,"SystemAddress":1183557095691,"EDSMID":null},
#			 "EventSummary":"Market","isTravelling":false,"TravelledTimeSec":0,"TravelledDistance":0.0,"TravelledJumps":0,"TravelledMissingJumps":0,
#			 "Status":{"OnFoot":false,"OnFootFleetCarrier":false,"IsDocked":true,"IsLandedInShipOrSRV":false,"IsInSupercruise":false,"IsInMultiCrew":false,"TravelState":"Docked","BodyName":"Eowyg Auscs FG-Y d34","BodyID":-1,"HasBodyID":false,"BodyType":"Star","StationName":"Two","StationType":"Crater Outpost","StationFaction":"The Dark Wheel","MarketID":35342479,"ShipID":2,"ShipType":"Asp Explorer","ShipTypeFD":"Asp","IsSRV":false,"IsFighter":false,"OnCrewWithCaptain":null,"IsOnCrewWithCaptain":false,"IsInMultiPlayer":false,"GameMode":"Solo","Group":"","Wanted":false,"BodyApproached":false,"BookedDropship":false,"BookedTaxi":false,"CurrentBoost":1.0,"FSDJumpNextSystemName":null,"FSDJumpNextSystemAddress":null,"FSDJumpSequence":false,"GameModeGroup":"Solo","GameModeGroupMulticrew":"Solo"},
#			 "WhereAmI":"Two","Visits":0,"FullBodyID":null,"Credits":95042663,"Loan":0,"Assets":156034834,
#			 .. Info always present, Detailed may be None/Null or more info
#			 "Info":"Prices on 0 items at Two in Eowyg Auscs FG-Y d34","Detailed":null}
#
# client requesttype = "missions" - request mission information at an historic point in time given by the journal entry
#				entry = history entry for information to report on. If out of range, the latest history entry is used
#		server responsetype = requesttype
#				entry = history entry for information to report on
#				current = Array of mission data of currently active missions
#				previous = Array of mission data of previous missions
#				Each mission data entry contains data from https://github.com/EDDiscovery/EliteDangerousCore/blob/d94c3f775e714f97a42d38758734929a5ae3c24b/EliteDangerous/Stats/MissionList.cs
#					e.Missions is the journal entry MissionAccepted
#					e.Completed is the journal entry MissionCompleted, null if not complete
#					e.Redirected is the journal entry MissionRedirected (may be null)
#					e.CargoDepot is the journal entry CargoDepot (may be null)
#					e.OriginatingSystem, e.MissionEndTime, 
#					e.State (InProgress,Completed,Abandoned,Failed,Died)
#
# client requesttype = "ship" - request ship information on current ship at this journal entry
#				entry = history entry for information to report on. If out of range, the latest history entry is used
#		server responsetype = requesttype
#				entry = history entry for information to report on
#				ship object containing information on ID, State, ShipType, ShipFD, etc. 
#				See https://github.com/EDDiscovery/EliteDangerousCore/blob/d94c3f775e714f97a42d38758734929a5ae3c24b/EliteDangerous/Ships/Ship.cs
#
# client requesttype = "shiplist" - request ship list information at this point in time
#		server responsetype = requesttype
#				shiplist containing
#					CurrentShipID Key string 
#					Ships object contains ship data, keys by Key String
#					StoredModules object containing StoredModules array of modules in store. Each module is an object
#				See https://github.com/EDDiscovery/EliteDangerousCore/blob/d94c3f775e714f97a42d38758734929a5ae3c24b/EliteDangerous/Ships/ShipList.cs
#
# client requesttype = "suitsweapons" - request ship information on current ship at this journal entry
#				entry = history entry for information to report on. If out of range, the latest history entry is used
#		server responsetype = requesttype
#				entry = history entry for information to report on
#				suits object containing keys of suit information at this point. https://github.com/EDDiscovery/EliteDangerousCore/blob/d94c3f775e714f97a42d38758734929a5ae3c24b/EliteDangerous/Suit/SuitInformation.cs
#				weapons object containing keys of weapon information at this point. https://github.com/EDDiscovery/EliteDangerousCore/blob/d94c3f775e714f97a42d38758734929a5ae3c24b/EliteDangerous/Suit/SuitWeapons.cs
#				loadouts oject containing keys of loadouts information at this point. https://github.com/EDDiscovery/EliteDangerousCore/blob/d94c3f775e714f97a42d38758734929a5ae3c24b/EliteDangerous/Suit/SuitLoadouts.cs
#
# client requesttype = "carrier" - request latest carrier data
#		server responsetype = requesttype
#				carrier = object containing lots of fields. See https://github.com/EDDiscovery/EliteDangerousCore/blob/63c95a00a8745860cf0bbb46566ad8b7c0349327/EliteDangerous/Stats/Carrier.cs
#
# client requesttype = "ledger" - request ledger.
#		server responsetype = requesttype
#				ledger = object containing Transactions and CashTotal, Assets, Load. See https://github.com/EDDiscovery/EliteDangerousCore/blob/63c95a00a8745860cf0bbb46566ad8b7c0349327/EliteDangerous/Stats/Ledger.cs
#
# client requesttype = "shipyards" - request all shipyards
#		server responsetype = requesttype
#				shipyards = object containing "ShipYards" array of yards, see https://github.com/EDDiscovery/EliteDangerousCore/blob/63c95a00a8745860cf0bbb46566ad8b7c0349327/EliteDangerous/Ships/ShipYard.cs
#							And AllowCobraMkIV (true,false,None if unknown)
#
# client requesttype = "outfitting" - request all outfitting
#		server responsetype = q
#				outfitting = ship yard list, see https://github.com/EDDiscovery/EliteDangerousCore/blob/63c95a00a8745860cf0bbb46566ad8b7c0349327/EliteDangerous/Stats/Outfitting.cs
#
# client requesttype = "scandata" - request scan data about system
#				system = system name
#				systemid = 56 bit system id, may be None
#				weblookup = Not present or None: use EDD data only, or EDSM, Spansh, SpandThenEDSM, All
#		server responsetype = requesttype
#				system = system name
#				systemid = 56 bit system id, may be None
#				scan = scan data. See https://github.com/EDDiscovery/EliteDangerousCore/blob/master/EliteDangerous/StarScan/StarScanNode.cs
#
# client requesttype = "faction" - request information about faction
#				faction = string of faction name
#		server responsetype = requesttype
#				faction = string of faction name
#				data = Faction data. See https://github.com/EDDiscovery/EliteDangerousCore/blob/master/EliteDangerous/Stats/Stats.cs
#
# client requesttype = "factions" - request information about faction
#		server responsetype = requesttype
#				data = object array of faction name keys vs faction data. See https://github.com/EDDiscovery/EliteDangerousCore/blob/master/EliteDangerous/Stats/Stats.cs
#
# client requesttype = "mcmr" - request information about materials, commodities, microresources at this point
#				entry = history entry for information to report on. If out of range, the latest history entry is used
#		server responsetype = requesttype
#				entry = entry reported on
#				mcmr = list of data
#
################################################################################################ REQUESTS TO RUN ACTION PROGRAMS
#
# client requesttype = "runactionprogram"	- in the .act files of the plugin try and find program and run it.  
#				name = "program name"
#				[variables] = JSON of variables to give to program.  Such as an object containing { "Fred"=10, "Jim"= "Jimmy", "Sheila" = [1,2,3], "George"=true}
#						 these will appear in the action program.  Bools will appear with the postfix _BOOL (George_BOOL)
#		server responsetype = "runactionprogram"
#				name = "program name"
#				status = "errorstring" - empty if program run successfully, or the reason why it did not
#				[variables] = Variables given back by the action program.  The action program uses Action function ToJSON to convert from action vars to JSON.
#
################################################################################################ DEBUG
#
# client requesttype = "showlog"	- show the log screen of the user control panel - debug
#				no server response
#
################################################################################################ PUSHES FROM EDD
#
# push server responsetype = "terminate"
#				No parameters, please quit - client sends exit
#
#!! push server responsetype = "historypush"		-latest entry just received
#				firstrow = history entry number
#				length = 1
#				commander = string, name of commander
#				rows[] containing an a single object of history entry (with the journal entry as an object called journalEntry)
#
#!! push server responsetype = "journalentry"		-unfiltered journal entry before filtering, it may be reported in historypush later
#				commander = string, name of commander
#				journalEntry as an journal object (as per JournalEntry in historypush)
#
# push server responsetype = "historyload"		-when history is refreshed
#				historylength = X (number of history entries currently loaded, may be zero)
#				commander = commander loaded (may be blank, none loaded yet)
#
# push server responsetype = "travelhistorymoved"	
#				row = row selected by travel history
#
# push server responsetype = "edduievent"
#				type = UI event type
#				event = JSON of a EDD UI event. 
#				See EDD for UI events they consist of events from status.json and some journal events such as music/fsdtarget.
#				Important one sent at startup is UIOverallStatus which gives you broad info on current state: {'responsetype': 'edduievent', 'type': 'UIOverallStatus', 'event': {'MajorMode': 'None', 'Mode': 'None', 'Flags': [], 'Focus': 'NoFocus', 'Pips': {'Valid': False, 'Systems': -1.7976931348623157e+308, 'Engines': -1.7976931348623157e+308, 'Weapons': -1.7976931348623157e+308}, 'Firegroup': -1, 'Fuel': -1.0, 'Reserve': -1.0, 'Cargo': -1, 'Pos': {'ValidPosition': False, 'Latitude': -999999.0, 'Longitude': -999999.0, 'ValidAltitude': False, 'Altitude': -999999.0, 'AltitudeFromAverageRadius': False}, 'ValidHeading': False, 'Heading': -999999.0, 'ValidRadius': False, 'PlanetRadius': -999999.0, 'LegalState': None, 'BodyName': None, 'Health': -1.0, 'LowHealth': False, 'Gravity': -1.0, 'Temperature': -1.0, 'TemperatureState': 'Normal', 'Oxygen': -1.0, 'LowOxygen': False, 'BreathableAtmosphere': False, 'FSDState': 'Normal', 'SelectedWeapon': None, 'SelectedWeapon_Localised': None, 'DestinationName': '', 'DestinationBodyID': 0, 'DestinationSystemAddress': 0, 'EventTimeUTC': '2024-09-08T15:00:58Z', 'EventTypeID': 'OverallStatus', 'EventTypeStr': 'OverallStatus', 'EventRefresh': False}}
#
# push server responsetype = "screenshot"
#				outfile = file name
#				width = width of image
#				height = width of image
#
# push server responsetype = "newtarget"		- EDD target system has been changed by the user
#				system = system name
#				X = x coord
#				Y = y coord
#				Z = z coord
#
#
################################################################################################ UI Interaction 
# See Action Document DialogControl section and the commands in it, this mirrors those commands
#
# push responsetype = "uievent"
#				control = control name that event occurred on
#				event = [optional] event that occurred - some controls (buttons) have only 1 event, so this is not given
#				data = [optional] string data associated with the event - some controls (buttons etc) dont have data
#				value = [optional] JSON representation of data of event
#				value2 = [optional] JSON representation of data2 of event
#
#		See action doc for list of triggers (in Dialog section).  Event will be the text after the name
#		DGV right click menu will return value=right click menu tag, value2 = row.  Data will be text representation of these both.
#		A window sizing event is reported as {'responsetype': 'uievent', 'control': 'UC', 'event': 'Resize', 'data': '941,620', 'value': {'IsEmpty': False, 'Width': 941, 'Height': 620}}					 
#
# client requesttype = "uisuspend" - suspend update to this control pending updates. Use resume to continue normal operation
#				control = "control name"
#				no server response
#
# client requesttype = "uiresume" - resume updates to this control after suspend
#				control = "control name"
#				no server response
#
# client requesttype = "uiget"
#				control = "control name"
#        server responsetype = "uiget"
#				control = "control name"
#				value = Value, either a string or a number, or null if does not exist
#
# client requesttype = "uiset" or "uisetescape" - set value of control (second form expands escape sequences /r/n etc)
#				control = "control name"
#				value = "set value"
#				no server response
#
# client requesttype = "uiaddtext" - add text to richtext box (escape sequences are expanded)
#				control = "control name"
#				value = "set value"
#				no server response
#
# client requesttype = "uiadd" - Add a new controls
#				controldefinitions = JArray of string of controls to add, see Action Documentation Control Definition for strings.
#				no server response
#
# client requesttype = "uiremove" - Remove a control
#				controllist = JArray of string names of controls to remove
#				no server response
#
# client requesttype = "uiaddsetrows" - Add or change (set) rows on a DGV
#				control = "control name"
#				changelist = JArray of change definitions, each one is an object.
#							 Object is: row:  Integer -1 to insert at start, -2 to append at end
#										[headertext] : String, set the header text optionally to this text
#							            [cellstart] : Integer, first cell number. 0 if not present.  Only if overwriting rows, new rows must start with cell 0
#							            JArray cells, optional, each one an object containing: 
#											type : Always "text" at present (may be expanded later for different cell types)
#							                [tooltip] optional tooltip to assign
#							                [cell] optional cell number override, only for overrighting rows not for new rows, restart count at this value
#							                value : value to set cell to. If its a number it will be converted using culture invariance to a string. Use your own string converters and pass the value as a string if you want it in a culture format
#				no server response
#
# client requesttype = "uiinsertcolumns" - Insert columns into the DGV
#				control = "control name"
#				[position] = insert position, 0 to column count. Default 0
#				columndefinitions = JArray of objects defining the columns:
#										type : Always "text" at present (may be expanded later for different cell types)
#										headertext : Header text								
#										[fillsize] : integer % fill size, 100 is default
#										[sortmode] : Sort mode of column, if not present Alpha. Types are defined in action document DGV Dialog paragraph
#
#				no server response
#
# client requesttype = "uiremovecolumns" - Remove columns from the DGV
#				control = "control name"
#				[position] = insert position, 0 to column count. Default 0
#				[count] = count, 1 is the default
#				no server response
#
# client requesttype = "uirightclickmenu" - set right click menu for DGV
#				control = "control name"
#				tags = JArray of strings giving tags
#				text = JArray of strings giving text
#				no server response
#
# client requesttype = "uigetcolumnssetting" - get the columns setting
#				control = "control name"
#        server responsetype = "uigetcolumnssetting"
#				control = "control name"
#				settings = JObject containing column settings
#								
# client requesttype = "uisetcolumnssetting" - set the columns setting
#				control = "control name"
#				settings = JObject containing column settings
#				no server response
#
# client requesttype = "uisetdgvsetting" - control what the user can do to the dgv via right clicks on header
#				control = "control name"
#				columnreorder = bool, allow columns to be reordered
#				percolumnwordwrap = bool, allow columns to be word wrap controlled
#				allowheadervisibility = bool, allow header column to be hidden
#				singlerowselect = bool, right click selects whole row
#				no server response
#
# client requesttype = "uisetwordwrap" - set word wrap state for all columns on DGV
#				control = "control name"
#				wordwrap = bool, on/off for entire grid
#				no server response
#
# client requesttype = "uiclear" - Clear a DGV or Rich Text Box
#				control = "control name"
#
# client requesttype = "uiremoverows" - Remove rows from the DGV
#				control = "control name"
#				rowstart = Row start number (+ is row number, - is rows from the end, so -1 is last row, -2 is row before last, etc)
#				count = Row count (may be greater than rows remaining)
#
# client requesttype = "uienable" - Set enable state of a control
#				control = "control name"
#				state = bool, enable or disabled
#
# client requesttype = "uivisible" - Set visible state of a control
#				control = "control name"
#				state = bool, visible or invisible
#
# client requesttype = "uiposition" - Move control (in dialog units)
#				control = "control name"
#				x = x pos
#				y = y pos
#
# client requesttype = "uisize" - Size a control (in dialog units)
#				control = "control name"
#				width = width
#				height = height
#
# client requesttype = "uimessagebox" - Show a Message box
#				caption = string caption
#				message = string message
#				buttons = string of OK | OKCancel | AbortRetryIgnore | YesNoCancel | YesNo | RetryCancel (case insensitive)
#				icon = string of None | Hand | Stop | Error | Question | Exclamation | Warning | Asterisk | Information (case insensitive)
#        server responsetype = "uimessagebox"
#				message = message given
#				response = None | OK | Cancel | Abort | Retry | Ignore | Yes | No
#
# client requesttype = "uiclosedropdownbutton" - close any open drop down button
#

class EDD:
	DefaultTimeout = 10000

	def __init__(self,port) -> None:
		self.cxt = zmq.Context.instance()
		self.worker = self.cxt.socket(zmq.DEALER)
		connectstr = "tcp://127.0.0.1:" + str(port)
		print("EDD initialising, connecting to " + connectstr)
		self.worker.connect(connectstr)
		self.messq = []
		
########################################################################################## Start/Exit

	def SendStart(self,version,timeout = DefaultTimeout) -> bool:
		data = {'requesttype':'start', 'version':version, 'apiversion':1}
		self.worker.send_string(json.dumps(data));
	
		ret = self.Poll("start",timeout)

		self.EDDVersion = ""				# indicates no version
		if ret and ret["responsetype"] == "start":
			self.EDDVersion = ret["eddversion"]
			self.APIVersion = ret["apiversion"]
			self.HistoryLength = ret["historylength"]
			self.Commander = ret["commander"]
			config = ret["config"]
			if config == "":
				self.Config = json.loads("{}")
			else:
				self.Config = json.loads(config)
			print(f"EDD Start {self.EDDVersion} API {self.APIVersion} Cmdr {self.Commander} History {self.HistoryLength} Config {self.Config}")				
			return True
		else:
			print("No start return")
			return False

	def SendExit(self,reason) -> None:
		data = {'requesttype':'exit', 'reason':reason, 'config':json.dumps(self.Config) }
		self.worker.send_string(json.dumps(data))
		
########################################################################################## Requests

	def RequestHistory(self, start, length,timeout = DefaultTimeout) -> object:
		data = {'requesttype':'history', 'start':start, 'length':length }
		self.worker.send_string(json.dumps(data));
		ret = self.PollWithContents(data["requesttype"],'start',start,timeout)
		return ret

	def RequestHistoryByJID(self, jid,timeout = DefaultTimeout) -> object:
		data = {'requesttype':'historyjid', 'jid':jid }
		self.worker.send_string(json.dumps(data));
		ret = self.PollWithContents(data["requesttype"],'jid',jid,timeout)
		return ret

	def RequestMissions(self, entry,timeout = DefaultTimeout) -> object:
		return self.CommonRequest('missions',timeout,entry)

	def RequestShip(self, entry,timeout = DefaultTimeout) -> object:
		return self.CommonRequest('ship',timeout,entry)

	def RequestShipList(self, timeout = DefaultTimeout) -> object:
		return self.CommonRequest('shiplist',timeout)

	def RequestSuitsWeapons(self, entry,timeout = DefaultTimeout) -> object:
		return self.CommonRequest('suitsweapons',timeout,entry)

	def RequestCarrier(self, timeout = DefaultTimeout) -> object:
		return self.CommonRequest('carrier',timeout)

	def RequestLedger(self, timeout = DefaultTimeout) -> object:
		return self.CommonRequest('ledger',timeout)

	def RequestShipyards(self, timeout = DefaultTimeout) -> object:
		return self.CommonRequest('shipyards',timeout)

	def RequestOutfitting(self, timeout = DefaultTimeout) -> object:
		return self.CommonRequest('outfitting',timeout)

	def RequestScandata(self, system, systemid, timeout = DefaultTimeout) -> object:
		data = {'requesttype':'scandata', 'system':system, 'systemid':systemid }
		self.worker.send_string(json.dumps(data));
		ret = self.PollWithContents(data["requesttype"],'system',system,timeout)
		return ret

	def RequestFaction(self, faction,timeout = DefaultTimeout) -> object:
		data = {'requesttype':'faction', 'faction':faction }
		self.worker.send_string(json.dumps(data));
		ret = self.PollWithContents(data["requesttype"],'faction',faction,timeout)
		return ret

	def RequestFactions(self, timeout = DefaultTimeout) -> object:
		return self.CommonRequest('factions',timeout)

	def RequestMCMR(self, entry,timeout = DefaultTimeout) -> object:
		return self.CommonRequest('mcmr',timeout,entry)

	def CommonRequest(self,request,timeout,entry = None) -> None:
		data = {'requesttype':request}
		if entry != None:
			data['entry']=entry
			self.worker.send_string(json.dumps(data));
			ret = self.PollWithContents(request,'entry',entry,timeout)
		else:
			self.worker.send_string(json.dumps(data));
			ret = self.Poll(request,timeout)
		return ret

	def ShowLog(self) -> None:
		data = {'requesttype':'showlog'}
		self.worker.send_string(json.dumps(data));
		
########################################################################################## UI Sends

	def UIGet(self, control, timeout = DefaultTimeout) -> object:
		data = {'requesttype':'uiget', 'control':control }
		self.worker.send_string(json.dumps(data));
		ret = self.PollWithContents("uiget","control",control,timeout)
		return ret

	def UISet(self, control, value) -> None:
		data = {'requesttype':'uiset', 'control':control, 'value': value }
		self.worker.send_string(json.dumps(data));

	def UISuspend(self, control) -> None:
		data = {'requesttype':'uisuspend', 'control':control }
		self.worker.send_string(json.dumps(data));

	def UIResume(self, control) -> None:
		data = {'requesttype':'uiresume', 'control':control }
		self.worker.send_string(json.dumps(data));

	def UISetEscape(self, control, value) -> None:
		data = {'requesttype':'uisetescape', 'control':control, 'value': value }
		self.worker.send_string(json.dumps(data));

	def UIAddText(self, control, value) -> None:
		data = {'requesttype':'uiaddtext', 'control':control, 'value':value }
		self.worker.send_string(json.dumps(data));

	def UIAdd(self, definition) -> None:
		data = {'requesttype':'uiadd', 'controldefinitions':definition}
		self.worker.send_string(json.dumps(data));
	
	def UIAddBasicItem(self, name, ctype, text, x,y,width,height,tooltip, inpanel = "",margin="") -> None:
		if inpanel != "":
			inpanel = ",In:" + inpanel
		if margin != "":
			margin = ",Margin:" + margin
		self.UIAdd( [ f"{name},{ctype},\"{text}\"{inpanel}{margin},{x},{y},{width},{height},\"{tooltip}\"" ]);

	def UIAddButton(self, name, text, x,y,width,height,tooltip, inpanel = "",margin="") -> None:
		self.UIAddBasicItem(name,"Button",text,x,y,width,height,tooltip,inpanel,margin)
	def UIAddCheckBox(self, name, text, x,y,width,height,tooltip, inpanel = "",margin="") -> None:
		self.UIAddBasicItem(name,"CheckBox",text,x,y,width,height,tooltip,inpanel,margin)

	def UIRemove(self, arrayofcontrolnames) -> None:
		data = {'requesttype':'uiremove', 'controllist':arrayofcontrolnames }
		self.worker.send_string(json.dumps(data));
	
	def UIAddSetRows(self, control, rowlist) -> None:
		data = {'requesttype':'uiaddsetrows', 'control':control, 'changelist': rowlist }
		self.worker.send_string(json.dumps(data));
	
	def UIInsertColumns(self, control, position, coldefarrayofobjects) -> None:
		data = {'requesttype':'uiinsertcolumns', 'control':control, 'position':position, 'columndefinitions': coldefarrayofobjects }
		self.worker.send_string(json.dumps(data));
	
	def UIRemoveColumns(self, control, position, count) -> None:
		data = {'requesttype':'uiremovecolumns', 'control':control, 'position':position, 'count': count }
		self.worker.send_string(json.dumps(data));
	
	def UIRightClickMenu(self, control, tagarraystrings, textarraystrings) -> None:
		data = {'requesttype':'uirightclickmenu', 'control':control, 'tags':tagarraystrings, 'text':textarraystrings }
		self.worker.send_string(json.dumps(data));
	
	def UIGetColumnsSetting(self, control, timeout = DefaultTimeout) -> 'JSON':
		data = {'requesttype':'uigetcolumnssetting', 'control':control }
		self.worker.send_string(json.dumps(data));
		ret = self.PollWithContents("uigetcolumnssetting","control",control,timeout)
		if "settings" in ret:
			return ret["settings"]
		else:
			return None

	def UISetColumnsSetting(self, control, columnssettingsobject) -> None:
		data = {'requesttype':'uisetcolumnssetting', 'control':control , 'settings':columnssettingsobject }
		self.worker.send_string(json.dumps(data));

	def UISetDGVSetting(self, control, columnreorder, percolumnwordwrap, allowheadervisibility, singlerowselect) -> None:
		data = {'requesttype':'uisetdgvsetting', 'control':control , 
		  'columnreorder': columnreorder, 
		  'percolumnwordwrap': percolumnwordwrap, 
		  'allowheadervisibility': allowheadervisibility,
		  'singlerowselect': singlerowselect
		  }
		self.worker.send_string(json.dumps(data));

	def UISetWordWrap(self, control, wordwrap) -> None:
		data = {'requesttype':'uisetwordwrap', 'control':control , 'wordwrap' : wordwrap }
		self.worker.send_string(json.dumps(data));

	def UIClear(self, control) -> None:
		data = {'requesttype':'uiclear', 'control':control }
		self.worker.send_string(json.dumps(data));

	def UIRemoveRows(self, control, rowstart, count) -> None:
		data = {'requesttype':'uiremoverows', 'control':control, 'rowstart':rowstart, 'count':count }
		self.worker.send_string(json.dumps(data));

	def UIEnable(self, control, state) -> None:
		data = {'requesttype':'uienable', 'control':control, 'state':state }
		self.worker.send_string(json.dumps(data));

	def UIVisible(self, control, state) -> None:
		data = {'requesttype':'uivisible', 'control':control, 'state':state }
		self.worker.send_string(json.dumps(data));

	def UIPosition(self, control, x,y) -> None:			# x,y in dialog units
		data = {'requesttype':'uiposition', 'control':control, 'x':x, 'y':y }
		self.worker.send_string(json.dumps(data));

	def UISize(self, control, width, height) -> None:	# width,height in dialog units
		data = {'requesttype':'uisize', 'control':control, 'width':width, 'height':height}
		self.worker.send_string(json.dumps(data));

	def UICloseDropDownButton(self) -> None:	
		data = {'requesttype':'uiclosedropdownbutton'}
		self.worker.send_string(json.dumps(data));
	
# Build in MessageBox interface to python panel
	
	def UIMessageBox(self,message,caption,buttons,icon) -> None:
		data = {'requesttype':'uimessagebox', 'message':message, 'caption':caption, 'buttons':buttons, 'icon':icon}
		self.worker.send_string(json.dumps(data));
	
	def UIWaitForMessageBox(self,message, timeout) -> object:
		ret = self.PollWithContents("uimessagebox","message", message, timeout)
		return ret

	def UIMessageBoxWait(self,message,caption,buttons,icon,timeout) -> None:
		self.UIMessageBox(message,caption,buttons,icon)
		return self.UIWaitForMessageBox(message,timeout)

# these rely on UIInterface.act action helper programs to run the action equivalent of these dialogs and return back data
	
	def UISaveFileDialog(self,folder,filter,defaultextension,warnonoverwrite,timeout) -> None:
		self.ActionRunProgram("SaveFileDialog",{ "Folder":folder, "Filter":filter, "DefaultExtension":defaultextension, "WarnOnOverwrite":warnonoverwrite})
		ret = self.ActionWaitForProgram("SaveFileDialog",timeout)
		return ret

	def UIOpenFileDialog(self,folder,filter,defaultextension,checkfileexistance,timeout) -> None:
		self.ActionRunProgram("OpenFileDialog",{ "Folder":folder, "Filter":filter, "DefaultExtension":defaultextension, "Check":checkfileexistance})
		ret = self.ActionWaitForProgram("OpenFileDialog",timeout)
		return ret
	
# RootFolder = folder to present. See https://learn.microsoft.com/en-us/dotnet/api/system.environment.specialfolder?view=net-8.0&redirectedfrom=MSDN
	def UIFolderDialog(self,description,rootfolder,timeout) -> None:
		self.ActionRunProgram("FolderDialog",{ "Description":description, "RootFolder":rootfolder})
		ret = self.ActionWaitForProgram("FolderDialog",timeout)
		return ret

	def UIInputBox(self,caption,promptarray,defaultarray,tooltipsarray,multilinebool,timeout) -> None:
		separ = "\u2345";
		inputstring = separ.join(promptarray)
		defaultstring= separ.join(defaultarray)
		tooltipstring = separ.join(tooltipsarray)
		featurelist = "MultiLine" if multilinebool else ""
		featurelist += ";0x2345"
		self.ActionRunProgram("InputBox",{ "Caption":caption, "PromptList" : inputstring, "DefaultList" : defaultstring , "ToolTipList":tooltipstring , "FeatureList":featurelist})
		ret = self.ActionWaitForProgram("InputBox",timeout)
		return ret

	def UIInfoBox(self,caption,message,timeout) -> None:
		self.ActionRunProgram("InfoBox",{ "Caption":caption, "Message" : message})
		ret = self.ActionWaitForProgram("InfoBox",timeout)
		return ret

########################################################################################## Action Programs

	def ActionRunProgram(self, progname, varobject) -> None:
		data = {'requesttype':'runactionprogram', 'name': progname, 'variables': varobject }
		self.worker.send_string(json.dumps(data));

	# will return None on timeout, or the returned variables from Action
	def ActionWaitForProgram(self,progname, timeout) -> object:
		ret = self.PollWithContents("runactionprogram","name", progname,timeout)
		#print(f"Wait for program {ret}")
		return ret

########################################################################################## Get Messages

	def GetNext(self)	-> object:		# return oldest item
		if len(self.messq)>0:
			msg = self.messq.pop(0)
			responsetype = msg["responsetype"]
			# process some messages to keep Self up to date
			if responsetype == "historyload":
				self.Commander = msg["commander"]
				self.HistoryLength = msg["historylength"]
				print(f"Updated history length to {self.HistoryLength} and commander to {self.Commander}")
			elif responsetype == "historypush":
				self.HistoryLength = msg["firstrow"]+1
				print(f"Updated history length to {self.HistoryLength}")
			return msg
		return None

########################################################################################## INTERNALS

	# for timeout in ms, wait for messagetype to appear.
	def Poll(self, messagetype,timeout) -> object:
		endtime = time.perf_counter() + timeout/1000.0
		while time.perf_counter() < endtime:
			ret = self.GetQueue(messagetype)
			if ret:
				return ret
			self.FillQueue(25)

		return None

	def PollWithContents(self, messagetype,fieldname,fieldcontents,timeout) -> object:
		endtime = time.perf_counter() + timeout/1000.0
		while time.perf_counter() < endtime:
			ret = self.GetQueueWithContents(messagetype,fieldname,fieldcontents)
			if ret:
				return ret
			self.FillQueue(25)

		return None

	def GetQueue(self, messagetype)	-> object:	# return item in queue matching messagetype
		i = 0
		while i < len(self.messq):		# see if message is already queued
			if self.messq[i]["responsetype"] == messagetype:
				ret = self.messq[i]
				self.messq.pop(i)
				#print(f"Returning {ret} queue size {len(self.messq)}")
				return ret
			i = i+1
		return None

	def GetQueueWithContents(self, messagetype,fieldname,fieldcontents)	-> object:	# return item in queue matching messagetype and a field as well
		i = 0
		while i < len(self.messq):		# see if message is already queued
			if self.messq[i]["responsetype"] == messagetype and self.messq[i][fieldname] == fieldcontents:
				ret = self.messq[i]
				self.messq.pop(i)
				#print(f"Returning {ret} at {i} queue size {len(self.messq)}")
				return ret
			i = i+1
		return None

	def FillQueue(self,timeout):		# fill queue
		if self.worker.poll(timeout)>0:
			request = self.worker.recv_string()
			jsonobj = json.loads(request)
			if jsonobj:
				self.messq.append(jsonobj)
		
	def Close(self) -> None:
		print("EDD closing")
		self.worker.close()


