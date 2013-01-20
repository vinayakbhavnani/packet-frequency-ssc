__author__ = 'vinayak'

import re
import time
import xml.dom.minidom
import sys
import curses
import thread
import threading

def tuiMap(stanzaMap):
    tuimap = {}
    x1 = 1
    x2 = 30
    y = 2
    for key in stanzaMap:
        tuimap[key] = [(x1, y), (x2, y)]
        y = y + 1

    return tuimap, y


def printKeys(displayMap, win):
    for key in displayMap:
        keypos = displayMap[key][0]
        #print keypos[1],keypos[0],key
        win.addstr(keypos[1], keypos[0], key)
        win.refresh()


def updateFrequency(displayMap, screen, key):
    screen.addstr(displayMap[key][1][1], displayMap[key][1][0], str(freqMap[key]))
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
                return "none", None


def handleStreamStart(packet):
    if packet.find('stream:stream') == 1:
        streamStart = packet+"</stream:stream>"
        iqfile.write(streamStart+"\n")
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
    if root.nodeName == "stream:stream":
        freqMap['stream'] += 1
        updateFrequency(displayMap, screen, 'stream')
    elif root.nodeName == "message":
        #print root.getElementsByTagName('composing')
        if root.getElementsByTagName('composing') or root.getElementsByTagName('active'):
            #print "chatState"
            freqMap['chatstates'] += 1
            updateFrequency(displayMap, screen, 'chatstates')
        elif root.getElementsByTagName('read') or root.getElementsByTagName('received'):
            #print "receipts"
            freqMap['readreceipts'] += 1
            updateFrequency(displayMap, screen, 'readreceipts')
        else:
            #print "chatMessage"
            freqMap['chat'] += 1
            updateFrequency(displayMap, screen, 'chat')
    elif root.nodeName == "presence":
        #print "presence packet"
        freqMap['presence'] += 1
        screen.addstr(displayMap['presence'][1][1], displayMap['presence'][1][0], str(freqMap['presence']))
        screen.refresh()

    elif root.nodeName == "iq":
        #print root.childNodes[0].attributes.items()
        if root.childNodes == []:
            freqMap['IqwithoutchildTypeResult'] += 1
            updateFrequency(displayMap, screen, 'IqwithoutchildTypeResult')
        elif root.getElementsByTagName('query'):
            queryelem = root.getElementsByTagName('query')[0]
            queryxmlns = queryelem.getAttributeNode('xmlns').nodeValue
            if queryxmlns == "http://talk.to/extension#reflection":
                #print "reflection"
                freqMap['reflection'] += 1
                updateFrequency(displayMap, screen, 'reflection')
            elif queryxmlns == "google:shared-status":
                #print "google shared status"
                freqMap['googlesharedstatus'] += 1
                updateFrequency(displayMap, screen, 'googlesharedstatus')
            elif queryxmlns == "jabber:iq:roster":
                freqMap['roster'] += 1
                updateFrequency(displayMap, screen, 'roster')
            else:
                #print "IQwithQuery undetected"
                freqMap['iq'] += 1
                updateFrequency(displayMap, screen, 'iq')
                #print m.group(1)
                #iqfile.write(m.group(1)+"\n")
        elif root.getElementsByTagName('vCard'):
            freqMap['vcard'] += 1
            updateFrequency(displayMap, screen, 'vcard')
        elif root.getElementsByTagName('bind'):
            freqMap['bind'] += 1
            updateFrequency(displayMap, screen, 'bind')
        elif root.getElementsByTagName('session'):
            freqMap['session'] += 1
            updateFrequency(displayMap, screen, 'session')
        else:
            #print "IQ undected"
            freqMap['iq'] += 1
            updateFrequency(displayMap, screen, 'iq')
            #print m.group(1)
            #iqfile.write(m.group(1)+"\n")
    elif root.nodeName == "session":
        freqMap['session'] += 1
        updateFrequency(displayMap,screen,'session')


def initMap():
    loadmap = {}
    loadmap['chat'] = 0
    loadmap['chatstates'] = 0
    loadmap['presence'] = 0
    loadmap['vcard'] = 0
    loadmap['reflection'] = 0
    loadmap['readreceipts'] = 0
    loadmap['googlesharedstatus'] = 0
    loadmap['stream'] = 0
    loadmap['iq'] = 0
    loadmap['IncompleteStanza'] = 0
    loadmap['roster'] = 0
    loadmap['bind'] = 0
    loadmap['session'] = 0
    loadmap['IqwithoutchildTypeResult'] = 0
    loadmap['nopacket'] = 0
    return loadmap


def fetchInputAndValidate():
    if len(sys.argv) > 1:
        if len(sys.argv) == 3:
            refreshRate = sys.argv[2]
        else:
            refreshRate = '0.1'
        return sys.argv[1],refreshRate
    else:
        print "Please Enter the Path to the Log File as Command Line Argument"
        sys.exit(0)

def parseAndUpdate():
    global line, m, xmlStanza, totalLine, response, responseType, responseElem , quitFlag
    while quitFlag:
        line = inputfile.readline()
        if not line:
            time.sleep(float(refreshRate))
            continue
        else:
            if incoming in line:
                m = True
                xmlStanza = line.split(incoming)[1]
                xmlStanza = xmlStanza.strip()
            elif outgoing in line:
                m = True
                xmlStanza = line.split(outgoing)[1]
                xmlStanza = xmlStanza.strip()
            else:
                m = False
            totalLine += 1
            if m:
                response = parseXml(xmlStanza)
                responseType = response[0]
                responseElem = response[1]
                if responseType == "element":
                    processPacket(responseElem)
                elif responseType == "elementlist":
                    processPacketList(responseElem)
                else:
                    #print "Invalid XML"
                    #print m.group(1)
                    logfile.write(xmlStanza + "\n")
                    freqMap['IncompleteStanza'] += 1
                    updateFrequency(displayMap, screen, 'IncompleteStanza')


def receiveUserInput():
    global quitFlag
    screen.getch()
    quitFlag = 0
    curses.endwin()

inp = fetchInputAndValidate()
inpfile = inp[0]
refreshRate = inp[1]
#inputfile = open("serverRecd",'r')
inputfile = open(inpfile, 'r')
logfile = open("invalidXmlLog", 'w')
iqfile = open("undetectedIQ", 'w')
freqMap = initMap()
response1 = tuiMap(freqMap)
displayMap = response1[0]
screen = curses.initscr()
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


