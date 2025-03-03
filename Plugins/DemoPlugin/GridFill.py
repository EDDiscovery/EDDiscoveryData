#!/usr/bin/env python3

import time
from threading import Thread
import zmq
import sys
import json
from edd import EDD
import keyboard

class GridFill:
	def FillRows(self, jrows):
		rows=[]
		for entry in jrows:
			#print(f"Journal {entry}")
			rows.append( { "row":-1 , "cells": [ 
										   {"type":"text", "value": entry["Index"]}, 
										   {"type":"text", "value": entry["journalEntry"]["EventTimeUTC"]}, 
										   {"type":"text", "value": entry["EventSummary"]}, 
										   {"type":"text", "value": entry["InfoText"]},
										   {"type":"text", "value": entry["DetailedText"]} 
										   ],
					 })
	
		return rows

	def RequestAndFillGrid(self, eddif,length):
		eddif.UIClear("DGV");
		self.LastestEntry = self.FirstEntry = -1
		self.LatestSystem = ""
		self.LatestJID = 0
		journals = eddif.RequestHistory(eddif.HistoryLength-length,length)

		if not(journals is None) and journals["length"]>0:
			rows = self.FillRows(journals["rows"])
			# rows = []
			# for entry in journals["rows"]:
			# 	#print(f"Journal {entry}")
			# 	rows.append( { "row":-1 , "cells": [ 
			# 							   {"type":"text", "value": entry["Index"]}, 
			# 							   {"type":"text", "value": entry["journalEntry"]["EventTimeUTC"]}, 
			# 							   {"type":"text", "value": entry["EventSummary"]}, 
			# 							   {"type":"text", "value": entry["InfoText"]},
			# 							   {"type":"text", "value": entry["DetailedText"]} 
			# 							   ],
					 #})
			#print(f"Row set {rows}")
			eddif.UIAddSetRows("DGV",rows)
			self.FirstEntry = journals["start"]
			length = journals["length"]
			self.LastestEntry = self.FirstEntry + length-1
			self.LatestSystem = journals["rows"][length-1]["System"]["Name"]
			self.LatestJID = journals["rows"][length-1]["journalEntry"]["Id"]
			print(f"Grid fill {self.FirstEntry} -> {self.LastestEntry} at {self.LatestSystem} jid {self.LatestJID}")

