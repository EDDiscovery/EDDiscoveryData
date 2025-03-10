import json
import zmq
import queue
import time

# MASTER VERSION

# Variables
#    EDD.EDDVersion = version reported by EDD on start
#    EDD.APIVersion = API Level reported by EDD on start - you can use this to check your plugin can work with this EDD
#    EDD.HistoryLength = history length reported by EDD on start. If non zero, history is loaded. If zero, history is loading, wait for historyload push, then this is set.
#    EDD.Commander = commander reported by EDD, via start (may be None, no commander loaded) or by historyload push
#    EDD.Config = JSON dict() object of the config reported by EDD on start, and reported back to EDD on exit

class EDD:
	DefaultTimeout = 10000

	def __init__(self,port) -> None:
		self.cxt = zmq.Context.instance()
		self.worker = self.cxt.socket(zmq.DEALER)
		connectstr = "tcp://127.0.0.1:" + str(port)
		print("EDD initialising, connecting to " + connectstr)
		self.worker.connect(connectstr)
		self.messq = []
		self.Config = dict()

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
			self.TransparentMode = ret["transparencymode"]
			self.TransparentColorKey = ret["transparencycolorkey"]
			self.CurrentlyTransparent = ret["istransparent"];
			config = ret["config"]
			if config != "":
				self.Config = json.loads(config)
			print(f"EDD Start {self.EDDVersion} API {self.APIVersion} Cmdr {self.Commander} History {self.HistoryLength} Config {self.Config}")
			return True
		else:
			print("No start return")
			return False

	def SendExit(self,reason,close=False) -> None:
		data = {'requesttype':'exit', 'reason':reason, 'config':json.dumps(self.Config), 'close':close }
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

	def RequestJournal(self, last,timeout = DefaultTimeout) -> object:
		data = {'requesttype':'journal', 'last':last }
		self.worker.send_string(json.dumps(data));
		ret = self.PollWithContents(data["requesttype"],'last',last,timeout)
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

	def RequestStationShipyardOutfitting(self, station, timeout = DefaultTimeout) -> object:
		data = {'requesttype':'stationshipyardoutfitting', 'station':station }
		self.worker.send_string(json.dumps(data));
		ret = self.PollWithContents(data["requesttype"],'station',station,timeout)
		return ret

	def RequestScandata(self, system, systemid, timeout = DefaultTimeout) -> object:
		data = {'requesttype':'scandata', 'system':system, 'systemid':systemid }
		self.worker.send_string(json.dumps(data));
		ret = self.PollWithContents(data["requesttype"],'system',system,timeout)
		return ret

	def RequestSpanshdump(self, system, systemid, weblookup, cachelookup, timeout = DefaultTimeout) -> object:
		data = {'requesttype':'spanshdump', 'system':system, 'systemid':systemid, 'weblookup':weblookup, 'cachelookup':cachelookup }
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
	
	def UIGetColumnsSetting(self, control, timeout = DefaultTimeout) -> None:
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


