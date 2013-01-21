__author__ = 'vinayak'

import re
import time
import xml.dom.minidom
import sys
import curses
import thread
import threading
import argparse
import os

def tuiMap(stanzaMap):
    tuimap = {}
    x1 = 1
    x2 = 30
    x3 = 40
    x4 = 70
    x5 = 80
    y = 2
    for key in stanzaMap:
        coordinateMap = {}
        coordinateMap['packet'] = (x1,y)
        coordinateMap['cout'] = (x2,y)
        coordinateMap['din'] = (x3,y)
        coordinateMap['dout'] = (x4,y)
        coordinateMap['cin'] = (x5,y)
        tuimap[key] = coordinateMap
        y = y + 1

    return tuimap, y


def printKeys(displayMap, win):
    for key in displayMap:
        keypos = displayMap[key]['packet']
        #print keypos[1],keypos[0],key
        win.addstr(keypos[1], keypos[0], key)
        win.refresh()
    win.addstr(20,2,'Press q to quit')
    win.refresh()


def incrementAndUpdate(displayMap, screen, key , sd):
    freqMap[key][sd] += 1
    screen.addstr(displayMap[key][sd][1], displayMap[key][sd][0], str(freqMap[key][sd]))
    screen.refresh()


def parseXml(packet):
    try:
        doc = xml.dom.minidom.parseString(packet)
        root = doc.documentElement
        return "element", root
    except xml.parsers.expat.ExpatError:
        moddedString = "<dummy>" + packet + "</dummy>"
        #print moddedString
        try:
            doc = xml.dom.minidom.parseString(moddedString)
            root = doc.documentElement
            return "elementlist", root.childNodes
        except xml.parsers.expat.ExpatError:
            openpacket = handleStreamStart(packet)
            try:
                doc = xml.dom.minidom.parseString(openpacket)
                root = doc.documentElement
                return "element", root
            except xml.parsers.expat.ExpatError:
                if packet == "</stream:stream>":
                    return "streamclose",None
                elif packet == "</session>":
                    iqfile.write(packet)
                    return "sessionclose",None
                else:
                    if packet.find("stream:stream") == 1:
                        rawpacket = packet + "</stream:stream>"
                    else:
                        rawpacket = packet
                    binderror = rawpacket.replace(":","")
                    try:
                        doc = xml.dom.minidom.parseString(binderror)
                        root = doc.documentElement
                        return "element", root
                    except xml.parsers.expat.ExpatError:
                        return "none", None


def handleStreamStart(packet):
    if packet.find('stream:stream') == 1:
        streamStart = packet+"</stream:stream>"
        return streamStart
    elif packet.find('<session') ==0:
        session = packet + "</session>"
        return session
    else:
        return packet
def processPacketList(packetList):
    for packet in packetList:
        processPacket(packet)


def processPacket(root):
    #print root
    if root.nodeName.find('stream') == 0:
        incrementAndUpdate(displayMap, screen, 'stream',srcdest)
    elif root.nodeName == "message":
        #print root.getElementsByTagName('composing')
        if root.getElementsByTagName('composing') or root.getElementsByTagName('active'):
            #print "chatState"
            incrementAndUpdate(displayMap, screen, 'chatstates',srcdest)
        elif root.getElementsByTagName('read') or root.getElementsByTagName('received'):
            #print "receipts"
            incrementAndUpdate(displayMap, screen, 'readreceipts',srcdest)
        else:
            #print "chatMessage"
            incrementAndUpdate(displayMap, screen, 'chat',srcdest)
    elif root.nodeName == "presence":
        #print "presence packet"
        incrementAndUpdate(displayMap,screen,'presence',srcdest)

    elif root.nodeName == "iq":
        #print root.childNodes[0].attributes.items()
        if root.childNodes == []:
            incrementAndUpdate(displayMap, screen, 'IqwithoutchildTypeResult',srcdest)
        elif root.getElementsByTagName('query'):
            queryelem = root.getElementsByTagName('query')[0]
            queryxmlns = queryelem.getAttributeNode('xmlns').nodeValue
            if queryxmlns == "http://talk.to/extension#reflection":
                #print "reflection"
                incrementAndUpdate(displayMap, screen, 'reflection',srcdest)
            elif queryxmlns == "google:shared-status":
                #print "google shared status"
                incrementAndUpdate(displayMap, screen, 'googlesharedstatus',srcdest)
            elif queryxmlns == "jabber:iq:roster":
                incrementAndUpdate(displayMap, screen, 'roster',srcdest)
            else:
                #print "IQwithQuery undetected"
                incrementAndUpdate(displayMap, screen, 'iq',srcdest)
                #print m.group(1)
                #iqfile.write(m.group(1)+"\n")
        elif root.getElementsByTagName('vCard'):
            incrementAndUpdate(displayMap, screen, 'vcard',srcdest)
        elif root.getElementsByTagName('bind'):
            incrementAndUpdate(displayMap, screen, 'bind',srcdest)
        elif root.getElementsByTagName('session'):
            incrementAndUpdate(displayMap, screen, 'session',srcdest)
        else:
            #print "IQ undected"
            incrementAndUpdate(displayMap, screen, 'iq',srcdest)
            #print m.group(1)
            #iqfile.write(m.group(1)+"\n")
    elif root.nodeName == "session":
        incrementAndUpdate(displayMap,screen,'session',srcdest)


def initMap():
    loadmap = {}
    stanzaList = ['sessionclose','streamclose','nopacket','IqwithoutchildTypeResult','session','bind','roster','IncompleteStanza','iq','stream','googlesharedstatus','readreceipts','chat','chatstates','presence','vcard','reflection']
    for key in stanzaList:
        tempMap = {}
        tempMap['cin'] = 0
        tempMap['cout'] = 0
        tempMap['din'] = 0
        tempMap['dout'] = 0
        loadmap[key] = tempMap
    return loadmap


def fetchInputAndValidate():
    parse = argparse.ArgumentParser(prog='input.py')
    parse.add_argument('executablefile')
    parse.add_argument('logfile')
    parse.add_argument('-r',type=float,default=1.0,help='refresh Rate',dest='refreshRate')
    parse.add_argument('-o',default=False,help='true for resume , false for restart',dest='resume',action='store_const',const=True)
    namespace = parse.parse_args(sys.argv)
    return namespace

def extractPacketAndSrcDest(logstring):
    combinationMap = {}
    combinationMap['cin'] = 'C <<'
    combinationMap['cout'] = 'C >>'
    combinationMap['din'] = 'D <<'
    combinationMap['dout'] = 'D >>'
    for key in combinationMap:
        value = combinationMap[key]
        if value in logstring:
            packet = logstring.split(value)[1]
            packet = packet.strip()
            return key,packet
    return None,None


def parseAndUpdate():
    global line, m, xmlStanza, totalLine, response, responseType, responseElem , quitFlag , fileposition , srcdest
    inputfile.seek(fileposition)
    while quitFlag:
        fileposition = inputfile.tell()
        line = inputfile.readline()
        if not line:
            time.sleep(float(refreshRate))
            continue
        else:
            packetinfo = extractPacketAndSrcDest(line)
            if packetinfo[0] == None:
                m = False
            else:
                m = True
                srcdest = packetinfo[0]
                xmlStanza = packetinfo[1]
            totalLine += 1
            if m:
                response = parseXml(xmlStanza)
                responseType = response[0]
                responseElem = response[1]
                if responseType == "element":
                    processPacket(responseElem)
                elif responseType == "elementlist":
                    processPacketList(responseElem)
                elif responseType == "streamclose":
                    incrementAndUpdate(displayMap,screen,'streamclose',srcdest)
                elif responseType == "sessionclose":
                    incrementAndUpdate(displayMap,screen,'sessionclose',srcdest)
                else:
                    #print "Invalid XML"
                    #print m.group(1)
                    logfile.write(xmlStanza + "\n")
                    incrementAndUpdate(displayMap, screen, 'IncompleteStanza',srcdest)
    posfile.write(str(fileposition))
    posfile.close()


def receiveUserInput():
    global quitFlag
    while 1:
        user_input = screen.getch()
        if str(user_input) == '113':
            quitFlag = 0
            curses.echo()
            curses.endwin()
            break

def getFilePosition(resumption):
    if resumption == True :
        line = posfile.readline()
        if not line:
            return 0
        else:
            return int(line)
    else:
        return 0
inp = fetchInputAndValidate()
inpfile = inp.logfile
refreshRate = inp.refreshRate
resume = inp.resume
#inputfile = open("serverRecd",'r')
inputfile = open(inpfile, 'r')
logfile = open("invalidXmlLog", 'w')
iqfile = open("undetectedIQ", 'w')
try:
    posfile = open("pos",'r')
    fileposition = getFilePosition(resume)
except IOError :
    fileposition = 0
posfile = open("pos",'w')
freqMap = initMap()
response1 = tuiMap(freqMap)
displayMap = response1[0]
screen = curses.initscr()
curses.noecho()
screen.border(0)
#screen.addstr(10,20,"hey")
printKeys(displayMap, screen)
incoming = '<<'
outgoing = '>>'
streamclose = "RECD: "
totalLine = 0
quitFlag = 1
userThread = threading.Thread(target=receiveUserInput)
userThread.start()
backThread = threading.Thread(target=parseAndUpdate)
backThread.start()

userThread.join()
backThread.join()


