#!/usr/bin/env python

'''
	Copyright 2013, David Pany
	
	This program is free software: you can redistribute it and/or modify
	it under the terms of the GNU General Public License as published by
	the Free Software Foundation, either version 3 of the License, or
	(at your option) any later version.

	This program is distributed in the hope that it will be useful,
	but WITHOUT ANY WARRANTY; without even the implied warranty of
	MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
	GNU General Public License for more details.

	You should have received a copy of the GNU General Public License
	along with this program.  If not, see <http://www.gnu.org/licenses/>.


References:
http://ftp.kolibrios.org/users/Asper/docs/NTFS/ntfsdoc.html#attribute_index_root
http://inform.pucp.edu.pe/~inf232/Ntfs/ntfs_doc_v0.5/concepts/index_record.html


daveMFT v0.1

daveMFT was created to recover $30 filename attributes from the slack space of MFT $90 Index Root
attributes. Please report any bugs, questions, comments, or concerns to davidpany@gmail.com.

Please excuse any inefficient or messy code as this is a beta release.



Future Capabilities
	[ ] timestomping
		[ ] mismatch between $10 and $30
		[ ] seconds on 0
	[ ] unicode characters in filename
		[ ] rtlo characters
'''

import re
import binascii
import os
#from colorama import init, Fore, Back, Style
from datetime import datetime,timedelta,date
import struct
import codecs
import sys
import argparse

print
print "	Thank you for using daveMFT! This script is still in beta."
print 
print "	Usage:"
print "		daveMFT.py <MFT File Name>"
print
print "	The purpose of this tool is to recover full or partial $30 File Name attributes"
print "		from the slack space of MFT $90 Index Root attributes. It may not be 100%"
print "		successful yet, so please report any missed records to davidpany@gmail.com."
print
print "	New features, better parsing, and better output (excel) are in the plan for the future."
print

#argument handling
parser = argparse.ArgumentParser()
parser.add_argument("MFTFileName", help="The MFT file name you want to use")
args = parser.parse_args()

#get MFT File name from argument
MFTFileName = args.MFTFileName

MFTBin = open(MFTFileName, "rb")
#MFTBin = open("ADS", "rb")
#MFTBin = open("challenging5","rb")
#MFTBin = open("sample directory", "rb")
#MFTBin = open("sample directory - before", "rb")

#get size for status bar, needs to be adjusted to argument
global size
size =  ((os.path.getsize(MFTFileName)) /1024) -1.0

#

RecoveredOutText = open("RecoveredFNAttributes.txt","w")

def main():
	global size
	
	MFTBinRecord = MFTBin.read(1024)
	MFTHexRecord = binascii.hexlify(MFTBinRecord)
	
	while MFTHexRecord:
		RecoveredFNRecordString = ''

		headerDict = getRecordHeader(MFTHexRecord)
		MFTHexRecord = headerDict['MFTAdjusted']
		recordRealSize = headerDict['RealSize']
		nextAttType = headerDict['NextAttType']
		nextAttOffset = headerDict['NextAttOffset']
		nextAttOffset = headerDict['NextAttOffset']
		MFTFlags = headerDict['Flags']
		MFTNum = headerDict['MFTNum']
		
		IsDirectory = False
		if MFTFlags == '10' or MFTFlags == '11':
			IsDirectory = True
		
		#start taking care of output
		#print '\tMFT Record Number:\t\t{}'.format(MFTNum)
	
		#Clear StdOut
		sys.stdout.write("\b" * (40))
		sys.stdout.write("{}".format(" " * 50))
		sys.stdout.write("\b" * (50))
		sys.stdout.flush()
		
		# update StdOut with new info
		sys.stdout.write("	{}% complete. MFT Entry: {}".format(int((MFTNum / size) * 100),MFTNum))
		sys.stdout.flush()
		
		#Used to see if attribute may have slack entries we can use to parse
		ParseSlackTF = False 
		
		while nextAttType:
			
			if nextAttType == '10':
				###print
				attDict = getStdInfo(MFTHexRecord,nextAttOffset)
				nextAttType = attDict['NextAttType']
				nextAttOffset = attDict['NextAttOffset']
				#print "======={}============{}".format(nextAttType,nextAttOffset)
				
			elif nextAttType == '30':
				###print 
				attDict = getFileName(MFTHexRecord,nextAttOffset)
				nextAttType = attDict['NextAttType']
				nextAttOffset = attDict['NextAttOffset']
				if IsDirectory:
					FNAttributeName = attDict['FNAttributeName']
					RecoveredFNRecordString += "{} directory contains the following recovered $FN Attributes:\n".format(FNAttributeName)
				#print "======={}============{}".format(nextAttType,nextAttOffset)			
				
			elif nextAttType == '80':
				###print 
				attDict = get80Data(MFTHexRecord,nextAttOffset)
				nextAttType = attDict['NextAttType']
				nextAttOffset = attDict['NextAttOffset']
				#print "======={}============{}".format(nextAttType,nextAttOffset)
				# <--- remove
				
			elif nextAttType == '90':
				###print
				attDict = get90Index(MFTHexRecord,nextAttOffset)
				nextAttType = attDict['NextAttType']
				nextAttOffset = attDict['NextAttOffset']
				ParseSlackTF = attDict['ParseSlackTF']
				#print "======={}============{}".format(nextAttType,nextAttOffset)
				
			elif nextAttType == 'a0':
				nextAttType = ''
				ParseSlackTF = False
			
			elif nextAttType == 'ff':
				nextAttType = ''
				###print
				
			else:
				###print nextAttType
				###print nextAttOffset
				nextAttType = ''
				###print
				###print 'out of the loop'
				###print
				
		if ParseSlackTF == True:
			###print 
			###print 'Attempting to parse some Index Root Slack!!'
			RecoveredRecords = Parse90Slack(MFTHexRecord,nextAttOffset)
			if RecoveredRecords != '': #and type(RecoveredRecords) != "NoneType":
				RecoveredFNRecordString += RecoveredRecords + "\n"
				RecoveredOutText.write(RecoveredFNRecordString)
				
			###print
			
		'''
		print 'MFT Record (with update sequence corrected):\n'
		for x in range(0,2048,32):
			hexLine = MFTHexRecord[x:x+32]
			formattedHexLine = '{} {} {} {} {} {} {} {} - {} {} {} {} {} {} {} {}'.format(hexLine[0:2], hexLine[2:4],hexLine[4:6],hexLine[6:8],hexLine[8:10],hexLine[10:12],hexLine[12:14],hexLine[14:16],hexLine[16:18],hexLine[18:20],hexLine[20:22],hexLine[22:24],hexLine[24:26],hexLine[26:28],hexLine[28:30],hexLine[30:32])
			formattedASCIILine = ''
			
			for z in range(0,len(hexLine),2):
				if int(hexLine[z:z+2],16) < 32:
					formattedASCIILine += '.'
				else:
					formattedASCIILine += hexLine[z:z+2].decode('hex')

			print '{} | {}'.format(formattedHexLine,formattedASCIILine )
		'''
		
		MFTBinRecord = MFTBin.read(1024)
		MFTHexRecord = binascii.hexlify(MFTBinRecord)
	

#=========================================================================================================
def getRecordHeader(MFTHexRecord):
	###print '$MFT Record FILE Header'
	
	#Update Sequence Offset
	BEUSOff = ''
	UpdateSeqOffset = MFTHexRecord[8:12]
	for i in range(len(UpdateSeqOffset)-2,-2,-2):
		BEUSOff += UpdateSeqOffset[i:i+2]
	UpdateSeqOffset = int(BEUSOff,16)
	###print '\tUpdate Sequence Offset:\t{}'.format(UpdateSeqOffset)
	
	#Update Sequence Number & Array Size in Words (word = 2 bytes)
	BEUSSize = ''
	UpdateSeqSize = MFTHexRecord[12:16]
	for i in range(len(UpdateSeqSize)-2,-2,-2):
		BEUSSize += UpdateSeqSize[i:i+2]
	UpdateSeqSize = int(BEUSSize,16)
	###print '\tUpdate Seq # & Array Size:\t{}'.format(UpdateSeqSize)
	
	#$LogFile Sequence Number 
	BELFSN = ''
	LFSN = MFTHexRecord[16:32]
	for i in range(len(LFSN)-2,-2,-2):
		BELFSN += LFSN[i:i+2]
	LFSN = int(BELFSN,16)
	###print '\t$LogFile Sequence Number:\t{}'.format(LFSN)
	
	#Sequence Number
	BESeqNum = ''
	SeqNum = MFTHexRecord[32:36]
	for i in range(len(SeqNum)-2,-2,-2):
		BESeqNum += SeqNum[i:i+2]
	SeqNum = int(BESeqNum,16)
	###print '\tSequence Number:\t\t{}'.format(SeqNum)
	
	#Hard Link Count
	BEHLCount = ''
	HLCount = MFTHexRecord[36:40]
	for i in range(len(HLCount)-2,-2,-2):
		BEHLCount += HLCount[i:i+2]
	HLCount = int(BEHLCount,16)
	###print '\tHard Link Count:\t\t\t{}'.format(HLCount)
	
	#First Attribute Offset
	BEFAOffset = ''
	FAOffset= MFTHexRecord[40:44]
	for i in range(len(FAOffset)-2,-2,-2):
		BEFAOffset += FAOffset[i:i+2]
	FAOffset = int(BEFAOffset,16)
	###print '\tFirst Attribute Offset:\t\t{}'.format(FAOffset)
	
	#Flags
	BEFlags = ''
	Flags = MFTHexRecord[44:48]
	for i in range(len(Flags)-2,-2,-2):
		BEFlags += Flags[i:i+2]
	Flags = bin(int(BEFlags,16))[2:]
	###print "\tFlags:\t\t\t\t{}".format(int(Flags))
	'''
	if Flags == '1':
		###print '\t\tRecord is in use'
	elif Flags == '10':
		###print '\t\tRecord is a directory'
	elif Flags == '11':
		###print '\t\tRecord is a directory and in use'
	'''
		
	#Real Size of FILE MFT Record
	BERealSize = ''
	RealSize= MFTHexRecord[48:56]
	for i in range(len(RealSize)-2,-2,-2):
		BERealSize += RealSize[i:i+2]
	RealSize = int(BERealSize,16)
	###print '\tReal Size of Record:\t\t{}'.format(RealSize)
	
	#Allocated Size of FILE MFT Record
	BEAllSize = ''
	AllSize= MFTHexRecord[56:64]
	for i in range(len(AllSize)-2,-2,-2):
		BEAllSize += AllSize[i:i+2]
	AllSize = int(BEAllSize,16)
	###print '\tAllocated Size of Record:\t{}'.format(AllSize)
	
	#File Reference to the base FILE record
	BEBaseFILE = ''
	BaseFILE= MFTHexRecord[64:80]
	for i in range(len(BaseFILE)-2,-2,-2):
		BEBaseFILE += BaseFILE[i:i+2]
	BaseFILE = int(BEBaseFILE,16)
	###print '\tBase FILE record:\t\t\t{}'.format(BaseFILE)	
	
	#Next Attribute ID
	BENextAttrID = ''
	NextAttrID= MFTHexRecord[80:84]
	for i in range(len(NextAttrID)-2,-2,-2):
		BENextAttrID += NextAttrID[i:i+2]
	NextAttrID = int(BENextAttrID,16)
	###print '\tNext Attribute ID:\t\t{}'.format(NextAttrID)
	
	#Align to 4 byte boundary
	
	
	#Number of this MFT Record
	BEMFTNum = ''
	MFTNum= MFTHexRecord[88:96]
	for i in range(len(MFTNum)-2,-2,-2):
		BEMFTNum += MFTNum[i:i+2]
	MFTNum = int(BEMFTNum,16)
	
	#Update Sequence Number
	BEUSNum = ''
	USNum= MFTHexRecord[UpdateSeqOffset*2:UpdateSeqOffset*2+4]
	for i in range(len(USNum)-2,-2,-2):
		BEUSNum += USNum[i:i+2]
	USNum = int(BEUSNum,16)
	###print '\tUpdate Seq. Number (Hex):\t{}'.format(BEUSNum)
	
	#Update Sequence Array
	BEUSArray  = ''
	USArray= MFTHexRecord[UpdateSeqOffset*2 + 4:UpdateSeqOffset*2+12]
	USArray1 = USArray[0:4]
	USArray2 = USArray[4:8]
	USArray = "{} {} - {} {}".format(USArray1[0:2],USArray[2:4],USArray2[0:2],USArray2[2:4])
	###print '\tUpdate Seq. Array (Hex):\t{}'.format(USArray)
	
	#Next Attribute Type and Offset
	nextAttOffset = UpdateSeqOffset*2 + 16
	nextAttType =  str(MFTHexRecord[nextAttOffset:nextAttOffset + 2])
	###print '\tNext Attribute Type:\t\t{}'.format(nextAttType)
	
	#rework 
	MFTAdjusted = MFTHexRecord[:1020] + USArray1 + MFTHexRecord[1024:2044] + USArray2
	###print
	
	headerDict = {'RealSize':RealSize,'MFTAdjusted':MFTAdjusted,'NextAttType':nextAttType,'NextAttOffset':nextAttOffset,'Flags':Flags,'MFTNum':MFTNum}
	return headerDict
	
#====================================================================================================	
def getAttHeader(MFTHexRecord,attStart):
	###print '\tAttribute Header:'
	#Get Non-Resident Flag
	nonResFlag = int(MFTHexRecord[attStart + 16: attStart + 18],16)
	if nonResFlag == 1:
		residentTF = False
		#print "not resident=================================="
	elif nonResFlag == 0:
		residentTF = True
		#print "resident====================================="
		###else:
		###print 'problem with resident flag'
	
	#Get Name Length to determine whether or not attribute is named
	nameLength = int(MFTHexRecord[attStart + 18: attStart + 20],16)
	if nameLength == 0:
		namedTF = False
	elif nameLength > 0:
		namedTF = True
		###else:
		###print 'problem with nameLength'

	if residentTF:
		#LocName = '\tLocation/Name:\t\t\tResident and Not Named'
		LocationString = '\t\tLocation:\t\t\tResident'
		if namedTF:
			NamedString = '\t\tNamed or Not:\t\t\tNamed'
		else:
			NamedString = '\t\tNamed or Not:\t\t\tNot Named'
		
		#Attribute Type
		BEAttType = ''
		AttType = MFTHexRecord[attStart: attStart + 8]
		for i in range(len(AttType)-2,-2,-2):
			BEAttType += AttType[i:i+2]
		AttType = int(BEAttType,16)
		AttTypeString =  "\t\tAttributeType:\t\t\t%x" % AttType
		
		#Attribute Length
		BEAttLength = ''
		AttLength = MFTHexRecord[attStart+8: attStart + 16]
		for i in range(len(AttLength)-2,-2,-2):
			BEAttLength += AttLength[i:i+2]
		AttLength = int(BEAttLength,16)
		AttRows = AttLength/16.0
		AttLengthString = '\t\tAttr. Length /w Header:\t\t{} bytes, {} rows of 16 bytes'.format(AttLength,AttRows)
		
		#Offset to Name
		BEOffToName = ''
		OffToName  = MFTHexRecord[attStart+18: attStart + 20]
		for i in range(len(OffToName )-2,-2,-2):
			BEOffToName  += OffToName [i:i+2]
		OffToName  = int(BEOffToName ,16)
		OffToNameString = '\t\tOffset to Attribute Name:\t{} bytes'.format(OffToName)
		
		#Flags
		BEFlags = ''
		Flags  = MFTHexRecord[attStart+24: attStart + 28]
		for i in range(len(Flags )-2,-2,-2):
			BEFlags  += Flags [i:i+2]
		Flags = BEFlags
		FlagsString = '\t\tFlags:\t\t\t\t{}'.format(Flags)
		if Flags[3] == '1':
			FlagsString += '\n\t\t\tCompressed'
		if Flags[0] == '4':
			FlagsString += '\n\t\t\tEncrypted'
		if Flags[0] == '8':
			FlagsString += '\n\n\t\tSparse'
			
		#Attribute ID String
		BEAttID = ''
		AttID  = MFTHexRecord[attStart+28: attStart + 32]
		for i in range(len(AttID )-2,-2,-2):
			BEAttID  += AttID [i:i+2]
		AttID  = int(BEAttID ,16)
		AttIDString = '\t\tAttribute ID:\t\t\t{}'.format(AttID)
		
		#Attribute Length
		BEJustAttLength = ''
		JustAttLength  = MFTHexRecord[attStart+32: attStart + 40]
		for i in range(len(JustAttLength )-2,-2,-2):
			BEJustAttLength  += JustAttLength [i:i+2]
		JustAttLength  = int(BEJustAttLength ,16)
		JustAttLengthString = '\t\tAttr. Length /wo Header:\t{} bytes'.format(JustAttLength)
		
		# Offset to the Attribute
		BEAttrOffset = ''
		AttrOffset  = MFTHexRecord[attStart+40: attStart + 44]
		for i in range(len(AttrOffset )-2,-2,-2):
			BEAttrOffset  += AttrOffset [i:i+2]
		AttrOffset  = int(BEAttrOffset ,16)
		AttrOffsetString = '\t\tAttr. Offset, Header Length:\t{}'.format(AttrOffset)
		
		# Indexed Flag
		BEIndexedFlag = ''
		IndexedFlag  = MFTHexRecord[attStart+44: attStart + 46]
		for i in range(len(IndexedFlag )-2,-2,-2):
			BEIndexedFlag  += IndexedFlag [i:i+2]
		IndexedFlag  = int(BEIndexedFlag ,16)
		if IndexedFlag == 1:
			IndexedFlagString = '\t\tIndexed or Not:\t\t\tIndexed'
		elif IndexedFlag == 0:
			IndexedFlagString = '\t\tIndexed or Not:\t\t\tNot Indexed'
		else:
			IndexedFlagString = 'Problem with Indexed Flag=================='
			
		#Attribute Name
		#This attribute has been marked as NOT Named so Name is simply assigned a null ''
		if not namedTF:
			AttName = ''
			AttNameString = ''
		else:
			###AttName = MFTHexRecord[attStart+48: attStart + 48 + nameLength*4]
			###AttName = str(AttName.decode('hex'))
			###AttNameString = '\t\tAttribute Name: \t\t{}'.format(AttName)	

			BEAttName = ''
			AttNameString = ''
			AttName = MFTHexRecord[attStart+48: (attStart + 48) + (nameLength * 4)]
			
			
			for i in range(0,len(AttName ),4):
				BEAttName  += AttName[i+2:i+4] + AttName[i:i+2]
				
			for x in range(0,len(BEAttName),4):
				try:
					tempString =(codecs.BOM_UTF16_BE + binascii.unhexlify(BEAttName[x:x+4])).decode('utf-16','xmlcharrefreplace')
					AttNameString += "{}".format(tempString)
				except:
					AttNameString += "<U+{}>".format(BEAttName[x:x+4])			
			
		#Attribute Offset
		#This attribute has been marked as NOT Named and Resident so Offset is simply assigned
		AttOffset = 24 + (nameLength * 2)
		
		attHeaderDict = {}
		
		attHeaderDict['IsResident'] = residentTF
		attHeaderDict['IsNamed'] = namedTF
		attHeaderDict['Location'] = LocationString
		attHeaderDict['AttType'] = AttTypeString
		attHeaderDict['AttLength'] = AttLengthString
		attHeaderDict['Named'] = NamedString
		attHeaderDict['NameOffset'] = OffToNameString
		attHeaderDict['AttNameString'] = AttNameString
		attHeaderDict['AttName'] = AttName
		attHeaderDict['AttLengthInt'] = AttLength
		attHeaderDict['Flags']=FlagsString
		attHeaderDict['AttIDString'] = AttIDString
		attHeaderDict['JustAttLength'] = JustAttLengthString
		attHeaderDict['AttrOffset'] = AttrOffsetString
		attHeaderDict['IndexedFlag'] = IndexedFlagString
		
		attHeaderDict['AttOffset'] = AttrOffset
		
	elif not residentTF: # if not resident
		#look to add if for named or not named
		#LocName = '\tLocation/Name:\t\t\tResident and Not Named'
		LocationString = '\t\tLocation:\t\t\tNot Resident'
		if namedTF:
			NamedString = '\t\tNamed or Not:\t\t\tNamed'
		else:
			NamedString = '\t\tNamed or Not:\t\t\tNot Named'
		
		#Attribute Type
		BEAttType = ''
		AttType = MFTHexRecord[attStart: attStart + 8]
		for i in range(len(AttType)-2,-2,-2):
			BEAttType += AttType[i:i+2]
		AttType = int(BEAttType,16)
		AttTypeString =  "\t\tAttributeType:\t\t\t%x" % AttType

		#Attribute Length
		BEAttLength = ''
		AttLength = MFTHexRecord[attStart+8: attStart + 16]
		for i in range(len(AttLength)-2,-2,-2):
			BEAttLength += AttLength[i:i+2]
		AttLength = int(BEAttLength,16)
		AttRows = AttLength/16.0
		AttLengthString = '\t\tAttr. Length /w Header:\t\t{} bytes, {} rows of 16 bytes'.format(AttLength,AttRows)

		#Offset to Name
		BEOffToName = ''
		OffToName  = MFTHexRecord[attStart+20: attStart + 24]
		for i in range(len(OffToName )-2,-2,-2):
			BEOffToName  += OffToName [i:i+2]
		OffToName  = int(BEOffToName ,16)
		OffToNameString = '\t\tOffset to Attribute Name:\t{} bytes'.format(OffToName)

		#Flags
		BEFlags = ''
		Flags  = MFTHexRecord[attStart+24: attStart + 28]
		for i in range(len(Flags )-2,-2,-2):
			BEFlags  += Flags [i:i+2]
		Flags = BEFlags
		FlagsString = '\t\tFlags:\t\t\t\t{}'.format(Flags)
		if Flags[3] == '1':
			FlagsString += '\n\t\t\tCompressed'
		if Flags[0] == '4':
			FlagsString += '\n\t\t\tEncrypted'
		if Flags[0] == '8':
			FlagsString += '\n\n\t\tSparse'
			
		#Attribute ID String
		BEAttID = ''
		AttID  = MFTHexRecord[attStart+28: attStart + 32]
		for i in range(len(AttID )-2,-2,-2):
			BEAttID  += AttID [i:i+2]
		AttID  = int(BEAttID ,16)
		AttIDString = '\t\tAttribute ID:\t\t\t{}'.format(AttID)
		
		#Starting VCN
		BEStartVCN = ''
		StartVCN  = MFTHexRecord[attStart+32: attStart + 46]
		for i in range(len(StartVCN )-2,-2,-2):
			BEStartVCN  += StartVCN [i:i+2]
		StartVCN  = int(BEStartVCN ,16)
		StartVCNString = '\t\tStart VCN:\t\t\t{}'.format(StartVCN)
		
		#Last VCN
		BELastVCN = ''
		LastVCN  = MFTHexRecord[attStart+46: attStart + 64]
		for i in range(len(LastVCN )-2,-2,-2):
			BELastVCN += LastVCN [i:i+2]
		LastVCN  = int(BELastVCN ,16)
		LastVCNString = '\t\tLast VCN:\t\t\t{}'.format(LastVCN)
		
		#Offset to Data Runs
		BEDROffset = ''
		DROffset  = MFTHexRecord[attStart+64: attStart + 68]
		for i in range(len(DROffset )-2,-2,-2):
			BEDROffset += DROffset [i:i+2]
		DROffset  = int(BEDROffset ,16)
		DROffsetString = '\t\tOffset to Data Runs:\t\t{}'.format(DROffset)

		#Compression Unit Size
		BECompUnitSize = ''
		CompUnitSize  = MFTHexRecord[attStart+68: attStart + 72]
		for i in range(len(CompUnitSize )-2,-2,-2):
			BECompUnitSize += CompUnitSize [i:i+2]
		CompUnitSize  = int(BECompUnitSize ,16)
		CompUnitSizeString = '\t\tCompression Unit Size:\t{}'.format(CompUnitSize)
		
		#Padding
		#[attStart + 72 : attStart + 80] is padding
		
		#Allocated size of the attribute
		BEAlloSize = ''
		AlloSize  = MFTHexRecord[attStart+80: attStart + 96]
		for i in range(len(AlloSize )-2,-2,-2):
			BEAlloSize += AlloSize [i:i+2]
		AlloSize  = int(BEAlloSize ,16)
		AlloSizeString = '\t\tAllocated Attribute Size:\t{}'.format(AlloSize)
		
		#Real size of the attribute
		BERealSize = ''
		RealSize  = MFTHexRecord[attStart+96: attStart + 112]
		for i in range(len(RealSize )-2,-2,-2):
			BERealSize += RealSize [i:i+2]
		RealSize  = int(BERealSize ,16)
		RealSizeString = '\t\tReal Attribute Size:\t\t{}'.format(RealSize)
		
		#Initialized data size of the stream
		BEStreamIDS = ''
		StreamIDS  = MFTHexRecord[attStart+112: attStart + 128]
		for i in range(len(StreamIDS )-2,-2,-2):
			BEStreamIDS += StreamIDS [i:i+2]
		StreamIDS  = int(BEStreamIDS ,16)
		StreamIDSString = '\t\tInitialized Stream Size:\t{}'.format(StreamIDS)
		
		#Attribute's name  #Needs testing with ADS or other named attribute
		#if available
		if namedTF:
			#Name - would be ADS in 80 DATA attribute
			BEAttName = ''
			StringName = ''
			AttName = MFTHexRecord[attStart+128: (attStart + 128) + (nameLength * 4)]
			
			
			for i in range(0,len(AttName ),4):
				BEAttName  += AttName[i+2:i+4] + AttName[i:i+2]
				
			for x in range(0,len(BEAttName),4):
				try:
					tempString =(codecs.BOM_UTF16_BE + binascii.unhexlify(BEAttName[x:x+4])).decode('utf-16','xmlcharrefreplace')
					StringName += "{}".format(tempString)
				except:
					StringName += "<U+{}>".format(BEAttName[x:x+4])
			###print StringName
			
			'''
			for i in range(0,len(AttName ),4):
				BEAttName  += AttName[i+2:i+4] + AttName[i:i+2]
			for x in range(0,len(BEAttName),4):
				
				tempString =(codecs.BOM_UTF16_BE + binascii.unhexlify(BEAttName[x:x+4])).decode('utf-16','replace')
				StringName += "{}".format(tempString)
			'''
			
			'''
			print AttName
			AttName = (codecs.BOM_UTF16_BE + binascii.unhexlify(AttName)).decode('utf-16','xmlcharrefreplace')	
			print AttName
			'''
			AttNameString =  '\t\tAttribute Name:\t\t\t{}'.format(StringName)
			
			#Data Runs Offset
			DROffset = (attStart + 128) + (nameLength * 4)			
			
		else:
			AttNameString = ''
			AttName = ''
			
			#Data Runs Offset
			DROffset = (attStart +128)
			
		#Get Data Runs
		DREnd = attStart + (AttLength * 2)
		DataRuns =  MFTHexRecord[DROffset: DREnd]
		DataRunsString = '\t\tData Runs:\t\t\t{}'.format(DataRuns)
		
		moreDR = True
		DRCounter = 1
		while moreDR:			
			#Get and parse first byte of data run so we know where to read cluster offset and length
			DataRunInfo = DataRuns[:2]
			DROffsetBytes = int(DataRuns[:1],16)
			DRLengthBytes = int(DataRuns[1:2],16)
			DRHexLength = (2 + (DROffsetBytes * 2) + (DRLengthBytes * 2))
			
			#Read Length and Offset of current DR in Hex
			DRLengthHex = DataRuns[2:2+ (DRLengthBytes * 2)]
			DROffsetHex = DataRuns[2+ (DRLengthBytes * 2):DRHexLength]
			
			#Convert Hex to int for length and offset
			if DRLengthHex == '':
				DRLengthDec = 'Not Available, may be error or System File'
			else:
				BEDRLengthHex = ''
				for i in range(len(DRLengthHex )-2,-2,-2):
					BEDRLengthHex  += DRLengthHex [i:i+2]
				DRLengthDec  = int(BEDRLengthHex ,16)
			
			if DROffsetHex == '':
				DROffsetDec = 'Not Available, may be error or System File'
			else:
				BEDROffsetHex = ''
				for i in range(len(DROffsetHex )-2,-2,-2):
					BEDROffsetHex  += DROffsetHex [i:i+2]
				DROffsetDec  = int(BEDROffsetHex ,16)
			
			#Add current DR Info to string
			DataRunsString += '\n\t\t\tData Run #{}:'.format(DRCounter)
			DataRunsString += '\n\t\t\t\tStart Cluster:\t{}'.format(DROffsetDec)
			DataRunsString += '\n\t\t\t\tCluster Length:\t{}'.format(DRLengthDec)
			#print DataRunsString
			
			
			#Get rid of current DR, Increment counter, and check for another DR
			DataRuns = DataRuns[DRHexLength:]
			DRCounter += 1			
			if DataRuns[:2] == '00' or DataRuns[:2] == 'ff' or DataRuns[:2] == '':
				moreDR = False
		
		
		
		
		
		
		
		attHeaderDict = {}
	
		attHeaderDict['IsResident'] = residentTF
		attHeaderDict['IsNamed'] = namedTF
		attHeaderDict['Location'] = LocationString
		attHeaderDict['AttType'] = AttTypeString
		attHeaderDict['AttLength'] = AttLengthString
		attHeaderDict['Named'] = NamedString
		attHeaderDict['NameOffset'] = OffToNameString
		attHeaderDict['AttNameString'] = AttNameString
		attHeaderDict['AttName'] = AttName
		attHeaderDict['AttLengthInt'] = AttLength
		attHeaderDict['Flags']=FlagsString
		attHeaderDict['AttIDString'] = AttIDString
		attHeaderDict['StartVCN'] = StartVCNString
		attHeaderDict['LastVCN'] = LastVCNString
		attHeaderDict['DROffset'] = DROffsetString
		attHeaderDict['CompUnitSize'] = CompUnitSizeString
		attHeaderDict['AlloSize'] = AlloSizeString
		attHeaderDict['RealSize'] = RealSizeString
		attHeaderDict['StreamIDS'] = StreamIDSString
		
		attHeaderDict['DataRunsString'] = DataRunsString
		
	else:
		print " Problem with Resident ========================================"
		LocationString = 'Problem with Resident ====================================='
	
	return attHeaderDict
	
#====================================================================================================
def getStdInfo(MFTHexRecord,nextAttOffset):
	###print '$STD INFO:'
	attStart = nextAttOffset
	attHeaderDict = getAttHeader(MFTHexRecord,attStart)
	
	Location = attHeaderDict['Location']
	Named = attHeaderDict['Named']
	AttType = attHeaderDict['AttType']
	AttLength = attHeaderDict['AttLength']
	NameOffset = attHeaderDict['NameOffset']
	Flags = attHeaderDict['Flags']
	AttID = attHeaderDict['AttIDString']
	JustAttLength = attHeaderDict['JustAttLength']
	AttrOffsetString = attHeaderDict['AttrOffset']
	IndexedFlag = attHeaderDict['IndexedFlag']
	AttName = attHeaderDict['AttName']
	AttOffset = attHeaderDict['AttOffset']
	
	###print AttType
	###print AttLength
	###print Location
	###print Named
	###print NameOffset
	###print Flags
	###print AttID
	###print JustAttLength
	###print AttrOffsetString
	###print IndexedFlag
	###if AttName:
		###print AttName
	
	#Begin finding actual STD Info Attribute info
	###print
	###print '\tAttribute Data:'
	
	#Double Attribute Offset For Our Use
	AttOffsetx2 = (AttOffset * 2) + attStart
	
	#get Created Time
	BECreatedTime = ''
	CreatedTime  = MFTHexRecord[AttOffsetx2: AttOffsetx2 + 16]
	for i in range(len(CreatedTime )-2,-2,-2):
		BECreatedTime  += CreatedTime [i:i+2]
	CreatedTime  = int(BECreatedTime ,16) / 10.
	CreatedTime = datetime(1601,1,1) + timedelta(microseconds=CreatedTime)
	###print  '\t\tCreated Time:\t\t\t{}'.format(CreatedTime)
	
	#get Modified Time
	BEModifiedTime = ''
	ModifiedTime  = MFTHexRecord[AttOffsetx2 + 16: AttOffsetx2 + 32]
	for i in range(len(ModifiedTime )-2,-2,-2):
		BEModifiedTime  += ModifiedTime [i:i+2]
	ModifiedTime  = int(BEModifiedTime ,16) / 10.
	ModifiedTime = datetime(1601,1,1) + timedelta(microseconds=ModifiedTime)
	###print  '\t\tModified Time:\t\t\t{}'.format(ModifiedTime)
	
	#get $MFT Time
	BEMFTTime = ''
	MFTTime  = MFTHexRecord[AttOffsetx2 + 32: AttOffsetx2 + 48]
	for i in range(len(MFTTime )-2,-2,-2):
		BEMFTTime  += MFTTime [i:i+2]
	MFTTime  = int(BEMFTTime ,16) / 10.
	MFTTime = datetime(1601,1,1) + timedelta(microseconds=MFTTime)
	###print  '\t\t$MFT Entry Modified Time:\t{}'.format(MFTTime)
	
	#get Accessed Time
	BEAccessedTime = ''
	AccessedTime  = MFTHexRecord[AttOffsetx2 + 48: AttOffsetx2 + 64]
	for i in range(len(AccessedTime )-2,-2,-2):
		BEAccessedTime  += AccessedTime [i:i+2]
	AccessedTime  = int(BEAccessedTime ,16) / 10.
	AccessedTime = datetime(1601,1,1) + timedelta(microseconds=AccessedTime)
	###print  '\t\tAccessed Time:\t\t\t{}'.format(AccessedTime)
	
	#get DOS File Permissions (Attributes)
	BEDOSFP = ''
	DOSFP  = MFTHexRecord[AttOffsetx2 + 64: AttOffsetx2 + 72]
	for i in range(len(DOSFP )-2,-2,-2):
		BEDOSFP  += DOSFP [i:i+2]
	DOSFP  = bin(int(BEDOSFP))[2:].zfill(16)
	###print  '\t\tDOS Flags:\t\t\t0b{}'.format(DOSFP)
	
	'''
	#Print individual flags
	if DOSFP[0] == '1':
		###print '\t\t\tEncrypted'
	if DOSFP[2] == '1':
		###print '\t\t\tNot Content Indexed'
	if DOSFP[3] == '1':
		###print '\t\t\tOffline'
	if DOSFP[4] == '1':
		###print '\t\t\tCompressed'
	if DOSFP[5] == '1':
		###print '\t\t\tReparse Point'
	if DOSFP[6] == '1':
		###print '\t\t\tSparse File '
	if DOSFP[7] == '1':
		###print '\t\t\tTemporary '
	if DOSFP[8] == '1':
		###print '\t\t\tNormal '
	if DOSFP[9] == '1':
		###print '\t\t\tDevice'
	if DOSFP[10] == '1':
		###print '\t\t\tArchive '
	if DOSFP[13] == '1':
		###print '\t\t\tSystem '
	if DOSFP[14] == '1':
		###print '\t\t\tHidden '
	if DOSFP[15] == '1':
		###print '\t\t\tRead-Only '
	'''
	
	#Get Maximum Number of Versions
	BEMaxNumVer = ''
	MaxNumVer  = MFTHexRecord[AttOffsetx2 + 72: AttOffsetx2 + 80]
	for i in range(len(MaxNumVer )-2,-2,-2):
		BEMaxNumVer  += MaxNumVer [i:i+2]
	MaxNumVer  = int(BEMaxNumVer)
	###print  '\t\tMax # of Versions:\t\t{}'.format(MaxNumVer)
	
	#Version Number
	BENumVer = ''
	NumVer  = MFTHexRecord[AttOffsetx2 + 80: AttOffsetx2 + 88]
	for i in range(len(NumVer )-2,-2,-2):
		BENumVer  += NumVer [i:i+2]
	NumVer  = int(BENumVer)
	###print  '\t\tVersion Number:\t\t\t{}'.format(NumVer)
	
	#Class ID
	BEClassID = ''
	ClassID  = MFTHexRecord[AttOffsetx2 + 88: AttOffsetx2 + 96]
	for i in range(len(ClassID )-2,-2,-2):
		BEClassID += ClassID [i:i+2]
	ClassID  = int(BEClassID)
	###print  '\t\tClass ID:\t\t\t{}'.format(ClassID)
	
	#Owner ID
	BEOwnerID = ''
	OwnerID  = MFTHexRecord[AttOffsetx2 + 96: AttOffsetx2 + 104]
	for i in range(len(OwnerID )-2,-2,-2):
		BEOwnerID += OwnerID [i:i+2]
	OwnerID  = int(BEOwnerID)
	###print  '\t\tOwner ID (Win2K):\t\t{}'.format(OwnerID)
	
	#Security ID
	BESecID= ''
	SecID  = MFTHexRecord[AttOffsetx2 + 104: AttOffsetx2 + 112]
	for i in range(len(SecID )-2,-2,-2):
		BESecID += SecID [i:i+2]
	#SecID  = int(BESecID,16)
	SecID = BESecID
	###print  '\t\tSecurity ID (Win2K):\t\t{}, 0x{}'.format(int(BESecID,16),SecID)
	
	#Quota Charged
	BEQuota = ''
	Quota  = MFTHexRecord[AttOffsetx2 + 112: AttOffsetx2 + 128]
	for i in range(len(Quota )-2,-2,-2):
		BEQuota += Quota [i:i+2]
	Quota  = int(BEQuota)
	###print  '\t\tQuota Charged (Win2K):\t\t{}'.format(Quota)
	
	#Update Sequence Number (USN)
	BEUSN = ''
	USN  = MFTHexRecord[AttOffsetx2 + 128: AttOffsetx2 + 144]
	for i in range(len(USN )-2,-2,-2):
		BEUSN += USN [i:i+2]
	#USN  = int(BEUSN)
	USN = BEUSN
	###print  '\t\tUpdate Seq. Num. (Win2K):\t{}'.format(USN)
	
	#Get next Attribute Type
	NextAttType = MFTHexRecord[AttOffsetx2+144:AttOffsetx2+146]
	###print '\t\tNext Attribute Type:\t\t{}'.format(NextAttType)
	
	#Next Attribute Offset
	NextAttOffset = AttOffsetx2 + 144
	#print NextAttOffset
	
	NextAttDict = {'NextAttType':NextAttType,'NextAttOffset':NextAttOffset}
	
	return NextAttDict
	
#==========================================================================================
#def getAttributeList(MFTHexRecord,nextAttOffset):
	
#==========================================================================================
def getFileName(MFTHexRecord,nextAttOffset):
	###print '$FILE NAME:'
	attStart = nextAttOffset
	attHeaderDict = getAttHeader(MFTHexRecord,attStart)
	
	Location = attHeaderDict['Location']
	Named = attHeaderDict['Named']
	AttType = attHeaderDict['AttType']
	AttLength = attHeaderDict['AttLength']
	AttLengthInt = attHeaderDict['AttLengthInt']
	NameOffset = attHeaderDict['NameOffset']
	Flags = attHeaderDict['Flags']
	AttID = attHeaderDict['AttIDString']
	JustAttLength = attHeaderDict['JustAttLength']
	AttrOffsetString = attHeaderDict['AttrOffset']
	IndexedFlag = attHeaderDict['IndexedFlag']
	AttName = attHeaderDict['AttName']
	AttOffset = attHeaderDict['AttOffset']
	
	###print AttType
	###print AttLength
	###print Location
	###print Named
	###print NameOffset
	###print Flags
	###print AttID
	###print JustAttLength
	###print AttrOffsetString
	###print IndexedFlag
	###if AttName:
		###print AttName
	
	#Begin finding actual FILE NAME Attribute info
	###print
	###print '\tAttribute Data:'
	
	#Double Attribute Offset For Our Use
	AttOffsetx2 = (AttOffset * 2) + attStart

	#File Reference to Parent Directory
	BEParDirRef = ''
	ParDirRef = MFTHexRecord[AttOffsetx2: AttOffsetx2 + 16]
	for i in range(len(ParDirRef )-2,-2,-2):
		BEParDirRef  += ParDirRef [i:i+2]
	#print BEParDirRef
	ParDirRef = int(BEParDirRef,16)
	###print '\t\tParent Directory Reference:\t{}'.format(ParDirRef)
	
	#get Created Time
	BECreatedTime = ''
	CreatedTime  = MFTHexRecord[AttOffsetx2+16: AttOffsetx2 + 32]
	for i in range(len(CreatedTime )-2,-2,-2):
		BECreatedTime  += CreatedTime [i:i+2]
	CreatedTime  = int(BECreatedTime ,16) / 10.
	CreatedTime = datetime(1601,1,1) + timedelta(microseconds=CreatedTime)
	###print  '\t\tCreated Time:\t\t\t{}'.format(CreatedTime)
	
	#get Modified Time
	BEModifiedTime = ''
	ModifiedTime  = MFTHexRecord[AttOffsetx2 + 32: AttOffsetx2 + 48]
	for i in range(len(ModifiedTime )-2,-2,-2):
		BEModifiedTime  += ModifiedTime [i:i+2]
	ModifiedTime  = int(BEModifiedTime ,16) / 10.
	ModifiedTime = datetime(1601,1,1) + timedelta(microseconds=ModifiedTime)
	###print  '\t\tModified Time:\t\t\t{}'.format(ModifiedTime)
	
	#get $MFT Time
	BEMFTTime = ''
	MFTTime  = MFTHexRecord[AttOffsetx2 + 48: AttOffsetx2 + 64]
	for i in range(len(MFTTime )-2,-2,-2):
		BEMFTTime  += MFTTime [i:i+2]
	MFTTime  = int(BEMFTTime ,16) / 10.
	MFTTime = datetime(1601,1,1) + timedelta(microseconds=MFTTime)
	###print  '\t\t$MFT Entry Modified Time:\t{}'.format(MFTTime)
	
	#get Accessed Time
	BEAccessedTime = ''
	AccessedTime  = MFTHexRecord[AttOffsetx2 + 64: AttOffsetx2 + 80]
	for i in range(len(AccessedTime )-2,-2,-2):
		BEAccessedTime  += AccessedTime [i:i+2]
	AccessedTime  = int(BEAccessedTime ,16) / 10.
	AccessedTime = datetime(1601,1,1) + timedelta(microseconds=AccessedTime)
	###print  '\t\tAccessed Time:\t\t\t{}'.format(AccessedTime)
	
	#Allocated Size of the File
	BEAllocSize = ''
	AllocSize = MFTHexRecord[AttOffsetx2 + 80: AttOffsetx2 + 96]
	for i in range(len(AllocSize )-2,-2,-2):
		BEAllocSize  += AllocSize [i:i+2]
	AllocSize = int(BEAllocSize,16)
	###print '\t\tFile Allocated Size:\t\t{} bytes'.format(AllocSize)
	
	#Real Size of the File
	BERealSize = ''
	RealSize = MFTHexRecord[AttOffsetx2 + 96: AttOffsetx2 + 112]
	for i in range(len(RealSize )-2,-2,-2):
		BERealSize  += RealSize [i:i+2]
	RealSize = int(BERealSize,16)
	###print '\t\tReal File Size:\t\t\t{} bytes'.format(RealSize)
	
	#Flags
	BEDOSFP = ''
	DOSFP  = MFTHexRecord[AttOffsetx2 + 112: AttOffsetx2 + 120]
	for i in range(len(DOSFP )-2,-2,-2):
		BEDOSFP  += DOSFP [i:i+2]
	DOSFP  = bin(int(BEDOSFP))[2:].zfill(32)
	###print  '\t\tDOS Flags:\t\t\t0b{}'.format(DOSFP)
	
	'''
	#Print individual flags
	if DOSFP[2] == '':
		print '\t\t\tIndex View'
	if DOSFP[3] == '1':
		print '\t\t\tDirectory'
	if DOSFP[16] == '1':
		print '\t\t\tEncrypted'
	if DOSFP[18] == '1':
		print '\t\t\tNot Content Indexed'
	if DOSFP[19] == '1':
		print '\t\t\tOffline'
	if DOSFP[20] == '1':
		print '\t\t\tCompressed'
	if DOSFP[21] == '1':
		print '\t\t\tReparse Point'
	if DOSFP[22] == '1':
		print '\t\t\tSparse File '
	if DOSFP[23] == '1':
		print '\t\t\tTemporary '
	if DOSFP[24] == '1':
		print '\t\t\tNormal '
	if DOSFP[25] == '1':
		print '\t\t\tDevice'
	if DOSFP[26] == '1':
		print '\t\t\tArchive '
	if DOSFP[29] == '1':
		print '\t\t\tSystem '
	if DOSFP[30] == '1':
		print '\t\t\tHidden '
	if DOSFP[31] == '1':
		print '\t\t\tRead-Only '
	'''
	
	#EAs and Reparse
	BEEAReparse = ''
	EAReparse = MFTHexRecord[AttOffsetx2 + 120: AttOffsetx2 + 128]
	for i in range(len(EAReparse )-2,-2,-2):
		BEEAReparse  += EAReparse [i:i+2]
	#EAReparse = int(BEEAReparse,16)
	###print '\t\tEA / Reparse Info:\t\t0b{}'.format(BEEAReparse)
	
	#Filename length in Unicode Characters
	BEFilenameLength = ''
	FilenameLength = MFTHexRecord[AttOffsetx2 + 128: AttOffsetx2 + 130]
	for i in range(len(FilenameLength )-2,-2,-2):
		BEFilenameLength  += FilenameLength [i:i+2]
	FilenameLength = int(BEFilenameLength,16)
	###print '\t\tFilename Length (Uni Chars):\t{}'.format(FilenameLength)	
	
	#Filename namespace
	BEFilenameNS = ''
	FilenameNS = MFTHexRecord[AttOffsetx2 + 130: AttOffsetx2 + 132]
	for i in range(len(FilenameNS )-2,-2,-2):
		BEFilenameNS  += FilenameNS [i:i+2]
	FilenameNS = int(BEFilenameNS,16)
	'''
	if FilenameNS == 0:
		###print '\t\tFilename Namespace:\t\tPOSIX'
	elif FilenameNS == 1:
		###print '\t\tFilename Namespace:\t\tWin32'
	elif FilenameNS == 2:
		###print '\t\tFilename Namespace:\t\tDOS'
	elif FilenameNS == 3:
		###print '\t\tFilename Namespace:\t\tWin32 & DOS'
	else:
		###print 'problem with Filename Namespace====================='
	'''
	
	#Filename in Unicode
	'''
	BEFilenameUni = ''
	FilenameUni = MFTHexRecord[AttOffsetx2 + 132: (AttOffsetx2 + 132) + (FilenameLength * 4)]
	for i in range(0,len(FilenameUni ),4):
		BEFilenameUni  += FilenameUni[i+2:i+4] + FilenameUni[i:i+2]
	FNASCII = (codecs.BOM_UTF16_BE + binascii.unhexlify(BEFilenameUni)).decode('utf-16')	
	###print '\t\tFile Name:\t\t\t{}'.format(FNASCII)
	'''
	
	
	BEAttName = ''
	FNASCII = ''
	AttName = MFTHexRecord[AttOffsetx2 + 132: (AttOffsetx2 + 132) + (FilenameLength * 4)]
	
	for i in range(0,len(AttName ),4):
		BEAttName  += AttName[i+2:i+4] + AttName[i:i+2]
		
	for x in range(0,len(BEAttName),4):
		try:
			tempString =(codecs.BOM_UTF16_BE + binascii.unhexlify(BEAttName[x:x+4])).decode('utf-16','xmlcharrefreplace')
			FNASCII += "{}".format(tempString)
		except:
			FNASCII += "<U+{}>".format(BEAttName[x:x+4])		
	
	#Next Attribute Offset
	NextAttOffset = nextAttOffset + (AttLengthInt *2)	
	#print NextAttOffset
	
	#Get next Attribute Type
	NextAttType = MFTHexRecord[NextAttOffset:NextAttOffset + 2]
	###print '\t\tNext Attribute Type:\t\t{}'.format(NextAttType)
	
	NextAttDict = {'NextAttType':NextAttType,'NextAttOffset':NextAttOffset,'FNAttributeName':FNASCII}
	
	return NextAttDict
	
#===============================================================================================================================
def get80Data(MFTHexRecord,nextAttOffset):
	###print '$DATA:'
	attStart = nextAttOffset
	attHeaderDict = getAttHeader(MFTHexRecord,attStart)
	
	IsResident = attHeaderDict['IsResident'] 
	IsNamed = attHeaderDict['IsNamed'] 
	
	
	
	if IsNamed:
		AttName = attHeaderDict['AttNameString']
		###print AttName
	
	#resident
	if IsResident:
		
		Location = attHeaderDict['Location']
		Named = attHeaderDict['Named']
		AttType = attHeaderDict['AttType']
		AttLength = attHeaderDict['AttLength']
		AttLengthInt = attHeaderDict['AttLengthInt']
		NameOffset = attHeaderDict['NameOffset']
		Flags = attHeaderDict['Flags']
		AttID = attHeaderDict['AttIDString']
		
		###print AttType
		###print AttLength
		###print Location
		#print AttLengthInt
		###print Named
		###print NameOffset
		###print Flags
		###print AttID
		
	#not resident	
	else:
		Location = attHeaderDict['Location']
		Named = attHeaderDict['Named']
		AttType = attHeaderDict['AttType']
		AttLength = attHeaderDict['AttLength']
		AttLengthInt = attHeaderDict['AttLengthInt']
		NameOffset = attHeaderDict['NameOffset']
		Flags = attHeaderDict['Flags']
		AttID = attHeaderDict['AttIDString']
		StartVCN = attHeaderDict['StartVCN']
		LastVCN = attHeaderDict['LastVCN']
		DROffset = attHeaderDict['DROffset']
		CompUnitSize = attHeaderDict['CompUnitSize']
		AlloSize = attHeaderDict['AlloSize']
		RealSize = attHeaderDict['RealSize']
		StreamIDS = attHeaderDict['StreamIDS']
		AttName = attHeaderDict['AttName']
		DataRuns = attHeaderDict['DataRunsString']
			
		###print AttType
		###print AttLength
		###print Location
		#print AttLengthInt
		###print Named
		###print NameOffset
		###print Flags
		###print AttID
		###print StartVCN
		###print LastVCN
		###print DROffset
		###print CompUnitSize
		###print AlloSize
		###print RealSize
		###print StreamIDS
		
		###print DataRuns
		
		
	#Begin finding actual DATA Attribute info
	###print
	###print '\tAttribute Data:'
	
	#Double Attribute Offset For Our Use
	#AttOffsetx2 = (AttOffset * 2) + attStart
	

	#Next Attribute Offset
	NextAttOffset = nextAttOffset + (AttLengthInt *2)	
	#print NextAttOffset
	
	#Get next Attribute Type
	NextAttType = MFTHexRecord[NextAttOffset:NextAttOffset + 2]
	#print NextAttType
	
	NextAttDict = {'NextAttType':NextAttType,'NextAttOffset':NextAttOffset}
	
	return NextAttDict
	
def get90Index(MFTHexRecord,nextAttOffset):
	
	###print '$Index Root:'
	attStart = nextAttOffset
	attHeaderDict = getAttHeader(MFTHexRecord,attStart)
	
	Location = attHeaderDict['Location']
	Named = attHeaderDict['Named']
	AttType = attHeaderDict['AttType']
	AttLength = attHeaderDict['AttLength']
	AttLengthInt = attHeaderDict['AttLengthInt']
	NameOffset = attHeaderDict['NameOffset']
	AttNameString = attHeaderDict['AttNameString']
	AttName = attHeaderDict['AttName']
	Flags = attHeaderDict['Flags']
	AttID = attHeaderDict['AttIDString']
	JustAttLength = attHeaderDict['JustAttLength']
	AttrOffsetString = attHeaderDict['AttrOffset']
	IndexedFlag = attHeaderDict['IndexedFlag']
	AttOffset = attHeaderDict['AttOffset']
	
	
	
	###print AttType
	###print AttLength
	###print Location
	###print Named
	###print NameOffset
	###print AttNameString
	###print Flags
	###print AttID
	###print JustAttLength
	###print AttrOffsetString
	###print IndexedFlag
	#print AttNameString
	
	#Begin finding actual Index Root Attribute info
	###print
	###print '\tAttribute Data:'
	
	#Double Attribute Offset For Our Use
	AttOffsetx2 = (AttOffset * 2) + attStart
	
	#Attribute Type in Root
	BERootAttType = ''
	RootAttType = MFTHexRecord[AttOffsetx2: AttOffsetx2 + 8]
	for i in range(len(RootAttType )-2,-2,-2):
		BERootAttType  += RootAttType [i:i+2]
	DecRootAttType = int(BERootAttType,16)
	if DecRootAttType == 48:
		StrRootAttType = 'File Name'
	else:
		StrRootAttType = 'Invalid RootAttType'
	###print '\t\tIndex Root Att. Type:\t\t{}, {}'.format(BERootAttType,StrRootAttType)

	#Collation Rule
	BECollationRule = ''
	CollationRule = MFTHexRecord[AttOffsetx2 + 8: AttOffsetx2 + 16]
	for i in range(len(CollationRule )-2,-2,-2):
		BECollationRule  += CollationRule [i:i+2]
	DecCollationRule = int(BECollationRule,16)
	if DecCollationRule == 0:
		StrCollationRule = 'Binary'
	elif DecCollationRule == 1:
		StrCollationRule = 'Filename'
	elif DecCollationRule == 2:
		StrCollationRule = 'Unicode String'
	elif DecCollationRule == 16:
		StrCollationRule = 'Unsigned Long'
	elif DecCollationRule == 17:
		StrCollationRule = 'SID'
	elif DecCollationRule == 18:
		StrCollationRule = 'Security Hash'
	elif DecCollationRule == 19:
		StrCollationRule = 'Multiple Unsigned Longs'
	else:
		StrCollationRule = 'Invalid Collation Rule'
	
	###print '\t\tCollation Rule:\t\t\t{}, {}'.format(BECollationRule,StrCollationRule)
	
	#Size of Index Allocation Entry in Bytes
	BEIndexAlloSize = ''
	IndexAlloSize = MFTHexRecord[AttOffsetx2 + 16: AttOffsetx2 + 24]
	for i in range(len(IndexAlloSize )-2,-2,-2):
		BEIndexAlloSize  += IndexAlloSize [i:i+2]
	DecIndexAlloSize = int(BEIndexAlloSize,16)
	###print '\t\tIndex Allocation Size:\t\t{} bytes'.format(DecIndexAlloSize)
	
	#Clusters per Index Record
	BEClusPerInxRec = MFTHexRecord[AttOffsetx2 + 24: AttOffsetx2 + 26]
	DecClusPerInxRec = int(BEClusPerInxRec,16)
	###print '\t\tClusters per Index Record:\t{} cluster/s'.format(DecClusPerInxRec)
	
	#Offset to First Index Entry
	BEFirstInxEntryOffset = ''
	FirstInxEntryOffset = MFTHexRecord[AttOffsetx2 + 32: AttOffsetx2 + 40]
	for i in range(len(FirstInxEntryOffset )-2,-2,-2):
		BEFirstInxEntryOffset  += FirstInxEntryOffset [i:i+2]
	DecFirstInxEntryOffset = int(BEFirstInxEntryOffset,16)
	###print '\t\tFirst Index Entry Offset:\t{} bytes'.format(DecFirstInxEntryOffset)
	
	#Total Size of Index Entries
	BEIndxEntrySize = ''
	IndxEntrySize = MFTHexRecord[AttOffsetx2 + 40: AttOffsetx2 + 48]
	for i in range(len(IndxEntrySize )-2,-2,-2):
		BEIndxEntrySize  += IndxEntrySize [i:i+2]
	DecIndxEntrySize = int(BEIndxEntrySize,16)
	###print '\t\tSize of Index Entries:\t\t{} bytes'.format(DecIndxEntrySize)
	
	#Allocated Size of Index Entries
	BEAllocIndxEntrySize = ''
	AllocIndxEntrySize = MFTHexRecord[AttOffsetx2 + 48: AttOffsetx2 + 56]
	for i in range(len(AllocIndxEntrySize )-2,-2,-2):
		BEAllocIndxEntrySize  += AllocIndxEntrySize [i:i+2]
	DecAllocIndxEntrySize = int(BEAllocIndxEntrySize,16)
	###print '\t\tAlloc. Size of Index Entries:\t{} bytes'.format(DecAllocIndxEntrySize)
	
	#Index Flags
	BEIndexFlags = MFTHexRecord[AttOffsetx2 + 56: AttOffsetx2 + 58]
	DecIndexFlags = int(BEIndexFlags,16)
	if DecIndexFlags == 0:
		IndexFlagsDesc = 'Index fits in Index Root'
	elif DecIndexFlags == 1:
		IndexFlagsDesc = 'Index uses Index Allocation'
	###print '\t\tIndex Flags:\t\t\t{}, {}'.format(DecIndexFlags, IndexFlagsDesc)
	
	#Use Index Entrie placement for offsets
	IndexEntryOffset = AttOffsetx2 + 64
	
	#go through Index Entries while the exist
	#for use only if filename entry types, 0x30 = dec48
	if  DecRootAttType == 48:
		#While there are still entries left, we will parse them
		IndxEntryRemaining = DecIndxEntrySize - 32
		###print
		###print "\tIndex Entries:"
		
		while IndxEntryRemaining > 0:

			#MFT File Reference of File
			BEFilesMFTRef = ''
			FilesMFTRef = MFTHexRecord[IndexEntryOffset: IndexEntryOffset + 16]
			for i in range(len(FilesMFTRef )-2,-2,-2):
				BEFilesMFTRef  += FilesMFTRef [i:i+2]
			###print "\t\tFile's MFT Reference:\t\t{}".format(BEFilesMFTRef)
			
			#Size of this index entry
			BEIndxEntrySize = ''
			IndxEntrySize = MFTHexRecord[IndexEntryOffset + 16: IndexEntryOffset + 20]
			for i in range(len(IndxEntrySize )-2,-2,-2):
				BEIndxEntrySize  += IndxEntrySize [i:i+2]
			###print "\t\tSize of this index entry:\t{}".format(BEIndxEntrySize)
			
			#Offset to the filename
			BEFilenameOffset = ''
			FilenameOffset = MFTHexRecord[IndexEntryOffset + 20: IndexEntryOffset + 24]
			for i in range(len(FilenameOffset )-2,-2,-2):
				BEFilenameOffset  += FilenameOffset [i:i+2]
			###print "\t\tOffset to Filename:\t\t{}".format(BEFilenameOffset)
			
			#Entry Index Flags ===================need more info!!
			BEEntryIndexFlags = ''
			EntryIndexFlags = MFTHexRecord[IndexEntryOffset + 24: IndexEntryOffset + 28]
			for i in range(len(EntryIndexFlags )-2,-2,-2):
				BEEntryIndexFlags += EntryIndexFlags [i:i+2]
			###print "\t\tEntry Index Flags:\t\t{}".format(BEEntryIndexFlags)
			
			#Parent's MFT Ref
			BEParentMFTRef = ''
			ParentMFTRef = MFTHexRecord[IndexEntryOffset + 32: IndexEntryOffset + 48]
			for i in range(len(ParentMFTRef )-2,-2,-2):
				BEParentMFTRef  += ParentMFTRef [i:i+2]
			###print "\t\tParent's MFT Reference:\t\t{}".format(BEParentMFTRef)
			
			#get Created Time
			BECreatedTime = ''
			CreatedTime  = MFTHexRecord[IndexEntryOffset + 48: IndexEntryOffset + 64]
			for i in range(len(CreatedTime )-2,-2,-2):
				BECreatedTime  += CreatedTime [i:i+2]
			CreatedTime  = int(BECreatedTime ,16) / 10.
			CreatedTime = datetime(1601,1,1) + timedelta(microseconds=CreatedTime)
			###print  '\t\tCreated Time:\t\t\t{}'.format(CreatedTime)
			
			#get Modified Time
			BEModifiedTime = ''
			ModifiedTime  = MFTHexRecord[IndexEntryOffset + 64: IndexEntryOffset + 80]
			for i in range(len(ModifiedTime )-2,-2,-2):
				BEModifiedTime  += ModifiedTime [i:i+2]
			ModifiedTime  = int(BEModifiedTime ,16) / 10.
			ModifiedTime = datetime(1601,1,1) + timedelta(microseconds=ModifiedTime)
			###print  '\t\tModified Time:\t\t\t{}'.format(ModifiedTime)
			
			#get $MFT Time
			BEMFTTime = ''
			MFTTime  = MFTHexRecord[IndexEntryOffset + 80: IndexEntryOffset + 96]
			for i in range(len(MFTTime )-2,-2,-2):
				BEMFTTime  += MFTTime [i:i+2]
			MFTTime  = int(BEMFTTime ,16) / 10.
			MFTTime = datetime(1601,1,1) + timedelta(microseconds=MFTTime)
			###print  '\t\t$MFT Entry Modified Time:\t{}'.format(MFTTime)
			
			#get Accessed Time
			BEAccessedTime = ''
			AccessedTime  = MFTHexRecord[IndexEntryOffset + 96: IndexEntryOffset + 112]
			for i in range(len(AccessedTime )-2,-2,-2):
				BEAccessedTime  += AccessedTime [i:i+2]
			AccessedTime  = int(BEAccessedTime ,16) / 10.
			AccessedTime = datetime(1601,1,1) + timedelta(microseconds=AccessedTime)
			###print  '\t\tAccessed Time:\t\t\t{}'.format(AccessedTime)
			
			#Allocated Size of the File
			BEAllocSize = ''
			AllocSize = MFTHexRecord[IndexEntryOffset + 112: IndexEntryOffset + 128]
			for i in range(len(AllocSize )-2,-2,-2):
				BEAllocSize  += AllocSize [i:i+2]
			AllocSize = int(BEAllocSize,16)
			###print '\t\tFile Allocated Size:\t\t{} bytes'.format(AllocSize)
			
			#Real Size of the File
			BERealSize = ''
			RealSize = MFTHexRecord[IndexEntryOffset + 128: IndexEntryOffset + 144]
			for i in range(len(RealSize )-2,-2,-2):
				BERealSize  += RealSize [i:i+2]
			RealSize = int(BERealSize,16)
			###print '\t\tReal File Size:\t\t\t{} bytes'.format(RealSize)
			
			#Flags
			BEDOSFP = ''
			DOSFP  = MFTHexRecord[IndexEntryOffset + 144: IndexEntryOffset + 152]
			for i in range(len(DOSFP )-2,-2,-2):
				BEDOSFP  += DOSFP [i:i+2]
			DOSFP  = bin(int(BEDOSFP,16))[2:].zfill(32)
			###print  '\t\tDOS Flags:\t\t\t0b{}'.format(DOSFP)
			'''
			#Print individual flags
			if DOSFP[2] == '':
				###print '\t\t\tIndex View'
			if DOSFP[3] == '1':
				###print '\t\t\tDirectory'
			if DOSFP[16] == '1':
				###print '\t\t\tEncrypted'
			if DOSFP[18] == '1':
				###print '\t\t\tNot Content Indexed'
			if DOSFP[19] == '1':
				###print '\t\t\tOffline'
			if DOSFP[20] == '1':
				###print '\t\t\tCompressed'
			if DOSFP[21] == '1':
				###print '\t\t\tReparse Point'
			if DOSFP[22] == '1':
				###print '\t\t\tSparse File '
			if DOSFP[23] == '1':
				###print '\t\t\tTemporary '
			if DOSFP[24] == '1':
				###print '\t\t\tNormal '
			if DOSFP[25] == '1':
				###print '\t\t\tDevice'
			if DOSFP[26] == '1':
				###print '\t\t\tArchive '
			if DOSFP[29] == '1':
				###print '\t\t\tSystem '
			if DOSFP[30] == '1':
				###print '\t\t\tHidden '
			if DOSFP[31] == '1':
				###print '\t\t\tRead-Only '
			'''
			
			#Length of File Name
			BEFNLength = MFTHexRecord[IndexEntryOffset + 160: IndexEntryOffset + 162]			
			FNLength = int(BEFNLength,16)
			###print  '\t\tFile Name Length:\t\t{} characters'.format(FNLength)
			
			#Filename namespace
			BEFilenameNS = ''
			FilenameNS = MFTHexRecord[IndexEntryOffset + 162: IndexEntryOffset + 164]
			for i in range(len(FilenameNS )-2,-2,-2):
				BEFilenameNS  += FilenameNS [i:i+2]
			FilenameNS = int(BEFilenameNS,16)
			'''
			if FilenameNS == 0:
				###print '\t\tFilename Namespace:\t\tPOSIX'
			elif FilenameNS == 1:
				###print '\t\tFilename Namespace:\t\tWin32'
			elif FilenameNS == 2:
				###print '\t\tFilename Namespace:\t\tDOS'
			elif FilenameNS == 3:
				###print '\t\tFilename Namespace:\t\tWin32 & DOS'
			else:
				###print 'problem with Filename Namespace====================='
			'''
			
			#Filename in Unicode
			BEFilenameUni = ''
			FilenameUni = MFTHexRecord[IndexEntryOffset + 164: (IndexEntryOffset + 164) + (FNLength * 4)]
			for i in range(0,len(FilenameUni ),4):
				BEFilenameUni  += FilenameUni[i+2:i+4] + FilenameUni[i:i+2]
			FNASCII = (codecs.BOM_UTF16_BE + binascii.unhexlify(BEFilenameUni)).decode('utf-16')	
			
			#Math to determine how much of the entry index is left and how what to change offset to
			EntryLength = (164) + (FNLength * 4) 
			if (EntryLength % 16) == 0:
				EntryUsed = EntryLength
			else:
				EntryUsed = EntryLength + (16-(EntryLength % 16))			
			
			#If we are using index allocation records, we have "VCN of index buffer with sub-nodes" that needs to be taken care of
			if DecIndexFlags == 1:
				BEVCNData = ''
				VCNData = MFTHexRecord[IndexEntryOffset + 128: IndexEntryOffset + 144]
				for i in range(len(VCNData )-2,-2,-2):
					BEVCNData  += VCNData [i:i+2]
				###print '\t\tVCN Data:\t\t\t{} bytes'.format(BEVCNData)
				EntryUsed += 16
			
			IndxEntryRemaining -= (EntryUsed / 2)
			IndexEntryOffset += EntryUsed
			
			###print
			###print
		
	if AttNameString == "$I30" :
		NextAttType =  MFTHexRecord[attStart + (AttLengthInt * 2): attStart + (AttLengthInt * 2) + 2]
		NextAttOffset = attStart + (AttLengthInt * 2) + 16
		if NextAttType == 'ff':
			ParseSlackTF = True
		else:
			ParseSlackTF = False
	else:
		NextAttOffset = AttOffsetx2 + AttLengthInt
		NextAttType = MFTHexRecord[NextAttOffset:NextAttOffset + 2]
		ParseSlackTF = False	
	
	NextAttDict = {'NextAttType':NextAttType,'NextAttOffset':NextAttOffset,'ParseSlackTF':ParseSlackTF }	
	
	return NextAttDict

def Parse90Slack(MFTHexRecord,nextAttOffset):
	###print
	###print "The following file name records have been recovered:"
	IndexEntryOffset = nextAttOffset
	
	SlackRemaining = True
	
	
	RecoveredFNAttributesString = ''
	
	while SlackRemaining and (IndexEntryOffset < 2048):
		
		TempRecoveredString = ''
		
		#Try to figure out how the next section of slack begins, it may differ
		nextSectionStart = MFTHexRecord[IndexEntryOffset: IndexEntryOffset + 4] 
		nextSectionStart = nextSectionStart[2:] + nextSectionStart[:2]
		
		#Choose course of action depending on next section type
		if nextSectionStart == "0000":
			###print "empty!"
			SlackRemaining = False
			IndexEntryOffset += 16
		
		elif nextSectionStart == "ffff":
			###print "another EOF Marker"
			SlackRemaining = True
			IndexEntryOffset += 16
		
		else:
			
			process2 = False
			CreatedTimeExists = True
			ModifiedTimeExists = True
			MFTTimeExists = True
			#AccessedTimeExists = True  #If one time exists, it should always be the accessed time
			
			# If first section is a valid date
			if IsValidHexDateTime(MFTHexRecord[IndexEntryOffset: IndexEntryOffset + 16]):
				TempIndexEntryOffset = IndexEntryOffset
				#If 4th section is valid date
				if IsValidHexDateTime(MFTHexRecord[TempIndexEntryOffset + 48: TempIndexEntryOffset + 64]):
					pass
					#This means all 4 times exist, we don't have to change anything
					
				else:
					#This means 4th section doesn't exist so Created Time was overwritten
					CreatedTimeExists = False
					IndexEntryOffset -= 16
					
					#If 3rd section is a valid date
					if IsValidHexDateTime(MFTHexRecord[TempIndexEntryOffset + 32: TempIndexEntryOffset + 48]):
						pass
						#This means Created time does not exist, but Modified, MFT, and Accessed time does
					else:
						#This means 3rd section doesn't exist so Modified Time was overwritten
						ModifiedTimeExists = False
						IndexEntryOffset -= 16
						
						#If 2nd section  is a valid date
						if IsValidHexDateTime(MFTHexRecord[TempIndexEntryOffset + 16: TempIndexEntryOffset + 32]):
							pass
							#This means Created and Modified Times don't exist, but MFT and Accessed Times do
							
						else:
							#This means 2nd section doesn't exist so MFT Time was overwritten
							MFTTimeExists = False
							IndexEntryOffset -= 16
					
					
				
			elif IsValidHexDateTime(MFTHexRecord[IndexEntryOffset + 16: IndexEntryOffset + 32]):
				process2 = True
			elif IsValidHexDateTime(MFTHexRecord[IndexEntryOffset + 32: IndexEntryOffset + 48]):
				
				#if date is in 3rd section of 8, we start here
				###print "fullish name record"
				
				#Size of this index entry
				BEIndxEntrySize = ''
				IndxEntrySize = MFTHexRecord[IndexEntryOffset : IndexEntryOffset + 4]
				for i in range(len(IndxEntrySize )-2,-2,-2):
					BEIndxEntrySize  += IndxEntrySize [i:i+2]
				###print "\tSize of this index entry:\t{}".format(BEIndxEntrySize)
				#TempRecoveredString += "\t\tSize of this index entry:\t{}\n".format(BEIndxEntrySize)
				
				#Offset to the filename
				BEFilenameOffset = ''
				FilenameOffset = MFTHexRecord[IndexEntryOffset + 4: IndexEntryOffset + 8]
				for i in range(len(FilenameOffset )-2,-2,-2):
					BEFilenameOffset  += FilenameOffset [i:i+2]
				###print "\tOffset to Filename:\t\t{}".format(BEFilenameOffset)
				#TempRecoveredString += "\t\tOffset to Filename:\t\t{}\n".format(BEFilenameOffset)
				
				#Entry Index Flags ===================need more info!!
				BEEntryIndexFlags = ''
				EntryIndexFlags = MFTHexRecord[IndexEntryOffset + 8: IndexEntryOffset + 12]
				for i in range(len(EntryIndexFlags )-2,-2,-2):
					BEEntryIndexFlags += EntryIndexFlags [i:i+2]
				###print "\tEntry Index Flags:\t\t{}".format(BEEntryIndexFlags)
				#TempRecoveredString += "\t\tEntry Index Flags:\t\t{}\n".format(BEEntryIndexFlags)
				
				#If we parse this info, we need to push the offset up 16
				IndexEntryOffset += 16
				
				process2 = True
				
			else:
				IndexEntryOffset += 16
				continue
				
			if process2:
				#Parent's MFT Ref
				BEParentMFTRef = ''
				ParentMFTRef = MFTHexRecord[IndexEntryOffset: IndexEntryOffset + 16]
				for i in range(len(ParentMFTRef )-2,-2,-2):
					BEParentMFTRef  += ParentMFTRef [i:i+2]
				###print "\tParent's MFT Reference:\t\t{}".format(BEParentMFTRef)
				TempRecoveredString += "\t\tParent's MFT Reference:\t\t{}\n".format(BEParentMFTRef)
				
				#If we parse this info, we need to push the offset up 16
				IndexEntryOffset += 16
				
			if CreatedTimeExists:
				#get Created Time
				BECreatedTime = ''
				CreatedTime  = MFTHexRecord[IndexEntryOffset: IndexEntryOffset + 16]
				for i in range(len(CreatedTime )-2,-2,-2):
					BECreatedTime  += CreatedTime [i:i+2]
				CreatedTime  = int(BECreatedTime ,16) / 10.
				CreatedTime = datetime(1601,1,1) + timedelta(microseconds=CreatedTime)
				###print  '\tCreated Time:\t\t\t{}'.format(CreatedTime)
				TempRecoveredString += '\t\tCreated Time:\t\t\t{}\n'.format(CreatedTime)
			
			if ModifiedTimeExists:
				#get Modified Time
				BEModifiedTime = ''
				ModifiedTime  = MFTHexRecord[IndexEntryOffset + 16: IndexEntryOffset + 32]
				for i in range(len(ModifiedTime )-2,-2,-2):
					BEModifiedTime  += ModifiedTime [i:i+2]
				ModifiedTime  = int(BEModifiedTime ,16) / 10.
				ModifiedTime = datetime(1601,1,1) + timedelta(microseconds=ModifiedTime)
				###print  '\tModified Time:\t\t\t{}'.format(ModifiedTime)
				TempRecoveredString += '\t\tModified Time:\t\t\t{}\n'.format(ModifiedTime)
			
			if MFTTimeExists:
				#get $MFT Time
				BEMFTTime = ''
				MFTTime  = MFTHexRecord[IndexEntryOffset + 32: IndexEntryOffset + 48]
				for i in range(len(MFTTime )-2,-2,-2):
					BEMFTTime  += MFTTime [i:i+2]
				MFTTime  = int(BEMFTTime ,16) / 10.
				MFTTime = datetime(1601,1,1) + timedelta(microseconds=MFTTime)
				###print  '\t$MFT Entry Modified Time:\t{}'.format(MFTTime)
				TempRecoveredString += '\t\t$MFT Entry Modified Time:\t{}\n'.format(MFTTime)
				
			#get Accessed Time
			BEAccessedTime = ''
			AccessedTime  = MFTHexRecord[IndexEntryOffset + 48: IndexEntryOffset + 64]
			for i in range(len(AccessedTime )-2,-2,-2):
				BEAccessedTime  += AccessedTime [i:i+2]
			AccessedTime  = int(BEAccessedTime ,16) / 10.
			AccessedTime = datetime(1601,1,1) + timedelta(microseconds=AccessedTime)
			###print  '\tAccessed Time:\t\t\t{}'.format(AccessedTime)
			TempRecoveredString += '\t\tAccessed Time:\t\t\t{}\n'.format(AccessedTime)
			
			#Allocated Size of the File
			BEAllocSize = ''
			AllocSize = MFTHexRecord[IndexEntryOffset + 64: IndexEntryOffset + 80]
			for i in range(len(AllocSize )-2,-2,-2):
				BEAllocSize  += AllocSize [i:i+2]
			AllocSize = int(BEAllocSize,16)
			###print '\tFile Allocated Size:\t\t{} bytes'.format(AllocSize)
			TempRecoveredString += '\t\tFile Allocated Size:\t\t{} bytes\n'.format(AllocSize)
			
			#Real Size of the File
			BERealSize = ''
			RealSize = MFTHexRecord[IndexEntryOffset + 80: IndexEntryOffset + 96]
			for i in range(len(RealSize )-2,-2,-2):
				BERealSize  += RealSize [i:i+2]
			RealSize = int(BERealSize,16)
			###print '\tReal File Size:\t\t\t{} bytes'.format(RealSize)
			TempRecoveredString += '\t\tReal File Size:\t\t\t{} bytes\n'.format(RealSize)
			
			#Flags
			BEDOSFP = ''
			DOSFP  = MFTHexRecord[IndexEntryOffset + 96: IndexEntryOffset + 104]
			for i in range(len(DOSFP )-2,-2,-2):
				BEDOSFP  += DOSFP [i:i+2]
			DOSFP  = bin(int(BEDOSFP,16))[2:].zfill(32)
			###print  '\tDOS Flags:\t\t\t0b{}'.format(DOSFP)
			TempRecoveredString += '\t\tDOS Flags:\t\t\t0b{}\n'.format(DOSFP)
			
			
			#Print individual flags
			if DOSFP[2] == '':
				TempRecoveredString +=  '\t\t\tIndex View\n'
			if DOSFP[3] == '1':
				TempRecoveredString +=  '\t\t\tDirectory\n'
			if DOSFP[16] == '1':
				TempRecoveredString +=  '\t\t\tEncrypted\n'
			if DOSFP[18] == '1':
				TempRecoveredString +=  '\t\t\tNot Content Indexed\n'
			if DOSFP[19] == '1':
				TempRecoveredString +=  '\t\t\tOffline\n'
			if DOSFP[20] == '1':
				TempRecoveredString +=  '\t\t\tCompressed\n'
			if DOSFP[21] == '1':
				TempRecoveredString +=  '\t\t\tReparse Point\n'
			if DOSFP[22] == '1':
				TempRecoveredString +=  '\t\t\tSparse File\n'
			if DOSFP[23] == '1':
				TempRecoveredString +=  '\t\t\tTemporary\n'
			if DOSFP[24] == '1':
				TempRecoveredString +=  '\t\t\tNormal\n'
			if DOSFP[25] == '1':
				TempRecoveredString +=  '\t\t\tDevice\n'
			if DOSFP[26] == '1':
				TempRecoveredString +=  '\t\t\tArchive\n'
			if DOSFP[29] == '1':
				TempRecoveredString +=  '\t\t\tSystem\n'
			if DOSFP[30] == '1':
				TempRecoveredString +=  '\t\t\tHidden\n'
			if DOSFP[31] == '1':
				TempRecoveredString +=  '\t\t\tRead-Only\n'
			
			
			#Length of File Name
			BEFNLength = MFTHexRecord[IndexEntryOffset + 112: IndexEntryOffset + 114]			
			FNLength = int(BEFNLength,16)
			###print  '\t\tFile Name Length:\t\t{} characters'.format(FNLength)
			#TempRecoveredString +=  '\t\t\tFile Name Length:\t\t{} characters\n'.format(FNLength)
			
			#Filename namespace
			BEFilenameNS = ''
			FilenameNS = MFTHexRecord[IndexEntryOffset + 114: IndexEntryOffset + 116]
			for i in range(len(FilenameNS )-2,-2,-2):
				BEFilenameNS  += FilenameNS [i:i+2]
			FilenameNS = int(BEFilenameNS,16)
			
			'''
			if FilenameNS == 0:
				TempRecoveredString +=  '\t\t\tFilename Namespace:\t\tPOSIX\n'
			elif FilenameNS == 1:
				TempRecoveredString +=  '\t\t\tFilename Namespace:\t\tWin32\n'
			elif FilenameNS == 2:
				TempRecoveredString +=  '\t\t\tFilename Namespace:\t\tDOS\n'
			elif FilenameNS == 3:
				TempRecoveredString +=  '\t\t\tFilename Namespace:\t\tWin32 & DOS\n'
			else:
				TempRecoveredString +=  '\t\t\tproblem with Filename Namespace=====================\n'
			'''
			
			#Filename in Unicode
			BEFilenameUni = ''
			FilenameUni = MFTHexRecord[IndexEntryOffset + 116: (IndexEntryOffset + 116) + (FNLength * 4)]
			for i in range(0,len(FilenameUni ),4):
				BEFilenameUni  += FilenameUni[i+2:i+4] + FilenameUni[i:i+2]
			
			FNASCII = (codecs.BOM_UTF16_BE + binascii.unhexlify(BEFilenameUni)).decode('utf-16','xmlcharrefreplace')	
			TempRecoveredString = '\tFile Name:\t\t\t{}\n'.format(FNASCII)+ TempRecoveredString + "\n"
			
			RecoveredFNAttributesString += TempRecoveredString
			
			'''
			try:
				FNASCII = (codecs.BOM_UTF16_BE + binascii.unhexlify(BEFilenameUni)).decode('utf-16','xmlcharrefreplace')	
				print '\t\tFile Name:\t\t\t{}'.format(FNASCII)
			except:
				DecypheredUni = ''
				for z in range(0,len(BEFilenameUni),2):
					if int(BEFilenameUni[z:z+2],16) < 32:
						DecypheredUni += '.'
					else:
						DecypheredUni += BEFilenameUni[z:z+2].decode('hex')
				#FNASCII = BEFilenameUni.decode('hex')
				print '\t\tFile Name:\t\t\t{} !Unicode Error!'.format(DecypheredUni)
			'''
			
			#Math to determine how much space is left
			LastOffsetOfName = (IndexEntryOffset + 116) + (FNLength * 4)
			
			if (LastOffsetOfName %16) == 0:
				PaddingNeeded = 32
			else:
				#EntryUsed = EntryLength + (16-(EntryLength % 16))	
				PaddingNeeded = 16 - (LastOffsetOfName %16) + 32    #32 is only needed since we are in slack space
			
			###print LastOffsetOfName
			###print PaddingNeeded
			#get us to the next FFFF...
			IndexEntryOffset = LastOffsetOfName + PaddingNeeded
			
			#Get us to the start of next record or empty space
			IndexEntryOffset += 16
			
			###print IndexEntryOffset
	return RecoveredFNAttributesString
			
def IsValidHexDateTime(DateTimeInQuestion):

	#Check if it is real date
	BEHexDateTimeInQuestion = ''
	for i in range(len(DateTimeInQuestion )-2,-2,-2):
		BEHexDateTimeInQuestion  += DateTimeInQuestion [i:i+2]
	DateTimeInQuestion  = int(BEHexDateTimeInQuestion ,16) / 10.
	DateTimeInQuestion = datetime(1601,1,1) + timedelta(microseconds=DateTimeInQuestion)

	OldestTime = datetime(1980,1,1)
	NewestTime = datetime.today()
	
	if DateTimeInQuestion < NewestTime and DateTimeInQuestion > OldestTime:
		return True
	else:
		return False
		
	
	
	
	

main()

RecoveredOutText.close()

sys.stdout.write("\n")
print
print "	Thank you for using daveMFT. Any recovered $30 FileName Attributes have been placed"
print "		in the RecoveredFNAttributes.txt file."

#deinit()
