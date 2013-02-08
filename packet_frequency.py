__author__ = 'vinayak'

import time
import xml.dom.minidom
import sys
import curses
import threading
import argparse
from collections import namedtuple

Point = namedtuple("Point", "x y")


class PacketCounter:
    def __init__(self, name):
        self._name = name
        self._cloud_in_freq = 0
        self._cloud_out_freq = 0
        self._device_in_freq = 0
        self._device_out_freq = 0

    @property
    def name(self):
        return self._name.toUpper()


def terminal_ui(stanza_map):
    """
    Takes a map with key 'stanza name' and value is a list of 5 values
    """
    stanza_coords = {}
    y = 3
    for key in stanza_map:
        coordinateMap = {}
        coordinateMap['packet'] = Point(1, y)
        coordinateMap['cout'] = Point(30, y)
        coordinateMap['din'] = Point(40, y)
        coordinateMap['dout'] = Point(70, y)
        coordinateMap['cin'] = Point(80, y)
        stanza_coords[key] = coordinateMap
        y += 1

    return stanza_coords, y


def printKeys(displayMap, win):
    for key in displayMap:
        keypos = displayMap[key]['packet']
        #print keypos[1],keypos[0],key
        win.addstr(keypos[1], keypos[0], key)
        win.addstr(1,30,'Cloud->SSC->Device')
        win.addstr(1,70,'Device->SSC->Cloud')
        win.refresh()
    win.addstr(20,2,'Press q to quit')
    win.refresh()


def incrementAndUpdate(freqMap,displayMap, screen, key , sd):
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
                    #undetected_iq_file.write(packet)
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



def processPacket(root,displayMap,screen,freqMap):
    #print root
    if root.nodeName.find('stream') == 0:
        incrementAndUpdate(freqMap,displayMap, screen, 'stream',srcdest)
    elif root.nodeName == "message":
        #print root.getElementsByTagName('composing')
        if root.getElementsByTagName('body'):
            incrementAndUpdate(freqMap,displayMap, screen, 'chat',srcdest)
        elif root.getElementsByTagName('composing') or root.getElementsByTagName('active') or root.getElementsByTagName('inactive') or root.getElementsByTagName('paused'):
            #print "chatState"
            incrementAndUpdate(freqMap,displayMap, screen, 'chatstates',srcdest)
        elif root.getElementsByTagName('read') or root.getElementsByTagName('received'):
            #print "receipts"
            incrementAndUpdate(freqMap,displayMap, screen, 'readreceipts',srcdest)

    elif root.nodeName == "presence":
        #print "presence packet"
        incrementAndUpdate(freqMap,displayMap,screen,'presence',srcdest)

    elif root.nodeName == "iq":
        #print root.childNodes[0].attributes.items()
        if root.childNodes == []:
            incrementAndUpdate(freqMap,displayMap, screen, 'IqwithoutchildTypeResult',srcdest)
        elif root.getElementsByTagName('query'):
            queryelem = root.getElementsByTagName('query')[0]
            queryxmlns = queryelem.getAttributeNode('xmlns').nodeValue
            if queryxmlns == "http://talk.to/extension#reflection":
                #print "reflection"
                incrementAndUpdate(freqMap,displayMap, screen, 'reflection',srcdest)
            elif queryxmlns == "google:shared-status":
                #print "google shared status"
                incrementAndUpdate(freqMap,displayMap, screen, 'googlesharedstatus',srcdest)
            elif queryxmlns == "jabber:iq:roster":
                incrementAndUpdate(freqMap,displayMap, screen, 'roster',srcdest)
            else:
                #print "IQwithQuery undetected"
                incrementAndUpdate(freqMap,displayMap, screen, 'iq',srcdest)
                #print m.group(1)
                #iqfile.write(m.group(1)+"\n")
        elif root.getElementsByTagName('vCard'):
            incrementAndUpdate(freqMap,displayMap, screen, 'vcard',srcdest)
        elif root.getElementsByTagName('bind'):
            incrementAndUpdate(freqMap,displayMap, screen, 'bind',srcdest)
        elif root.getElementsByTagName('session'):
            incrementAndUpdate(freqMap,displayMap, screen, 'session',srcdest)
        else:
            #print "IQ undected"
            incrementAndUpdate(freqMap,displayMap, screen, 'iq',srcdest)
            #print m.group(1)
            #iqfile.write(m.group(1)+"\n")
    elif root.nodeName == "session":
        incrementAndUpdate(freqMap,displayMap,screen,'session',srcdest)


def setup_packet_entries():
    result = {}
    stanzaList = ['sessionclose','streamclose','nopacket','IqwithoutchildTypeResult','session','bind','roster','IncompleteStanza','iq','stream','googlesharedstatus','readreceipts','chat','chatstates','presence','vcard','reflection']
    for each in stanzaList:
        result[each] = PacketCounter(each)
    return result


def parse_args():
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


def parseAndUpdate(input_file,refresh_rate,displayMap,screen,freqMap):
    global line, m, xmlStanza, totalLine, response, responseType, responseElem , quitFlag , resume , srcdest
    if resume == True:
        input_file.seek(0,2)
    while quitFlag:
        line = input_file.readline()
        if not line:
            time.sleep(float(refresh_rate))
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
                    incrementAndUpdate(freqMap,displayMap,screen,'streamclose',srcdest)
                elif responseType == "sessionclose":
                    incrementAndUpdate(freqMap,displayMap,screen,'sessionclose',srcdest)
                else:
                    #print "Invalid XML"
                    #print m.group(1)
                    invalid_xml_logs.write(xmlStanza + "\n")
                    incrementAndUpdate(freqMap,displayMap, screen, 'IncompleteStanza',srcdest)


def receiveUserInput(screen):
    global quitFlag
    while 1:
        user_input = screen.getch()
        if str(user_input) == '113':
            quitFlag = 0
            curses.echo()
            curses.endwin()
            break



def main():
    global quitFlag,invalid_xml_logs
    args = parse_args()
    refresh_rate = args.refreshRate
    resume = args.resume

    input_file = open(args.logfile, 'r')
    invalid_xml_logs = open("invalidXmlLog", 'w')
    undetected_iq_file = open("undetectedIQ", 'w')

    freqMap = setup_packet_entries()
    response1 = terminal_ui(freqMap)
    displayMap = response1[0]
    screen = curses.initscr()
    curses.noecho()
    screen.border(0)
    printKeys(displayMap, screen)
    quitFlag = 1
    userThread = threading.Thread(target=receiveUserInput,screen)
    userThread.start()
    backThread = threading.Thread(target=parseAndUpdate,refresh_rate)
    backThread.start()

    userThread.join()
    backThread.join()
