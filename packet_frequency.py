__author__ = 'vinayak'

import time
import xml.dom.minidom #TODO: Change to SAX parser
import sys
import curses
import threading
import argparse
from collections import namedtuple

Point = namedtuple("Point", "x y")
PacketDetail = namedtuple("PacketDetail", "point count")

class PacketEntry:
    def __init__(self, name):
        self._name = name
        self._name_pos = None
        self._cloud_in = PacketDetail(None, 0)
        self._cloud_out = PacketDetail(None, 0)
        self._device_in = PacketDetail(None, 0)
        self._device_out = PacketDetail(None, 0)

    @property
    def name(self):
        return self._name

    @property
    def name_pos(self):
        return self._name_pos

    @name_pos.setter
    def name_pos(self, value):
        self._name_pos = value

    @property
    def cloud_in(self):
        return self._cloud_in

    @cloud_in.setter
    def cloud_in(self, value):
        self._cloud_in = value


    @property
    def cloud_out(self):
        return self._cloud_out

    @cloud_out.setter
    def cloud_out(self, value):
        self._cloud_out = value

    @property
    def device_in(self):
        return self._device_in

    @device_in.setter
    def device_in(self, value):
        self._device_in = value


    @property
    def device_out(self):
        return self._device_out

    @device_out.setter
    def device_out(self, value):
        self._device_out = value

    def increment_count(self, key, increment):
        if(key == 'cin'):
            point  = self.cloud_in.point
            count = self.cloud_in.count
            value = count + increment
            self.cloud_in = PacketDetail(point, value)
            return self.cloud_in
        if(key == 'cout'):
            point = self.cloud_out.point
            count = self.cloud_out.count
            value = count + increment
            self.cloud_out = PacketDetail(point, value)
            return self.cloud_out
        if(key == 'din'):
            point = self.device_in.point
            count = self.device_in.count
            value = count + increment
            self.device_in = PacketDetail(point, value)
            return self.device_in
        if(key == 'dout'):
            point = self.device_out.point
            count = self.device_out.count
            value = count + increment
            self.device_out = PacketDetail(point, value)
            return self.device_out


class Config:
    def __init__(self, refresh_rate, resume):
        self._refresh_rate = refresh_rate
        self._resume = resume
        self._quit_flag = False

    @property
    def refresh_rate(self):
        return self._refresh_rate

    @property
    def resume(self):
        return self._resume

    @property
    def should_run(self):
        return not(self._quit_flag)


    def quit_app(self):
        self._quit_flag = True


def init_packet_entries(entries):
    #TODO: Accept list not map
    """
    Takes a map with key 'stanza name' and value is a list of 5 values
    """
    last_y = 0
    for i in range(len(entries)):
        last_y = i + 3
        entries[i].name_pos = Point(1, last_y)
        entries[i].cloud_out = PacketDetail(Point(30, last_y), 0)
        entries[i].device_in = PacketDetail(Point(40, last_y), 0)
        entries[i].device_out = PacketDetail(Point(70, last_y), 0)
        entries[i].cloud_in = PacketDetail(Point(80, last_y), 0)
    return last_y


def printKeys(entries, win):
    for entry in entries:
        keypos = entry.name_pos
        win.addstr(keypos.y, keypos.x, entry.name)
        win.addstr(1, 30, 'Cloud->SSC->Device')
        win.addstr(1, 70, 'Device->SSC->Cloud')
        win.refresh()
    win.addstr(20, 2, 'Press q to quit')
    win.refresh()


def incrementAndUpdate(entries, key, sd, screen):
    entry = get_entry(entries, key)
    detail = entry.increment_count(sd, 1)
    screen.addstr(detail.point.y, detail.point.x, str(detail.count))
    screen.refresh()


def get_entry(entries, key):
    for each in entries:
        if (each.name == key):
            return each


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
                    return "streamclose", None
                elif packet == "</session>":
                    #undetected_iq_file.write(packet)
                    return "sessionclose", None
                else:
                    if packet.find("stream:stream") == 1:
                        rawpacket = packet + "</stream:stream>"
                    else:
                        rawpacket = packet
                    binderror = rawpacket.replace(":", "")
                    try:
                        doc = xml.dom.minidom.parseString(binderror)
                        root = doc.documentElement
                        return "element", root
                    except xml.parsers.expat.ExpatError:
                        return "none", None


def handleStreamStart(packet):
    if packet.find('stream:stream') == 1:
        streamStart = packet + "</stream:stream>"
        return streamStart
    elif packet.find('<session') == 0:
        session = packet + "</session>"
        return session
    else:
        return packet


def processPacketList(packetList, entries, screen):
    for packet in packetList:
        processPacket(packet, entries, screen)


def processPacket(root, entries, screen):
    #print root
    if root.nodeName.find('stream') == 0:
        incrementAndUpdate(entries, 'stream', srcdest , screen)
    elif root.nodeName == "message":
        #print root.getElementsByTagName('composing')
        if root.getElementsByTagName('body'):
            incrementAndUpdate(entries, 'chat', srcdest, screen)
        elif root.getElementsByTagName('composing') or root.getElementsByTagName('active') or root.getElementsByTagName(
            'inactive') or root.getElementsByTagName('paused'):
            #print "chatState"
            incrementAndUpdate(entries,  'chatstates', srcdest, screen)
        elif root.getElementsByTagName('read') or root.getElementsByTagName('received'):
            #print "receipts"
            incrementAndUpdate(entries, 'readreceipts', srcdest, screen)

    elif root.nodeName == "presence":
        #print "presence packet"
        incrementAndUpdate(entries, 'presence', srcdest, screen)

    elif root.nodeName == "iq":
        #print root.childNodes[0].attributes.items()
        if root.childNodes == []:
            incrementAndUpdate(entries, 'IqwithoutchildTypeResult', srcdest, screen)
        elif root.getElementsByTagName('query'):
            queryelem = root.getElementsByTagName('query')[0]
            queryxmlns = queryelem.getAttributeNode('xmlns').nodeValue
            if queryxmlns == "http://talk.to/extension#reflection":
                #print "reflection"
                incrementAndUpdate(entries, 'reflection', srcdest, screen)
            elif queryxmlns == "google:shared-status":
                #print "google shared status"
                incrementAndUpdate(entries, 'googlesharedstatus', srcdest, screen)
            elif queryxmlns == "jabber:iq:roster":
                incrementAndUpdate(entries, 'roster', srcdest,screen)
            else:
                #print "IQwithQuery undetected"
                incrementAndUpdate(entries,'iq', srcdest, screen)
                #print m.group(1)
                #iqfile.write(m.group(1)+"\n")
        elif root.getElementsByTagName('vCard'):
            incrementAndUpdate(entries, 'vcard', srcdest, screen)
        elif root.getElementsByTagName('bind'):
            incrementAndUpdate(entries, 'bind', srcdest, screen)
        elif root.getElementsByTagName('session'):
            incrementAndUpdate(entries, 'session', srcdest, screen)
        else:
            #print "IQ undected"
            incrementAndUpdate(entries, 'iq', srcdest, screen)
            #print m.group(1)
            #iqfile.write(m.group(1)+"\n")
    elif root.nodeName == "session":
        incrementAndUpdate(entries, 'session', srcdest, screen)


def setup_packet_entries():
    result = []
    stanzaList = ['sessionclose', 'streamclose', 'nopacket', 'IqwithoutchildTypeResult', 'session', 'bind', 'roster',
                  'IncompleteStanza', 'iq', 'stream', 'googlesharedstatus', 'readreceipts', 'chat', 'chatstates',
                  'presence', 'vcard', 'reflection']
    for each in stanzaList:
        result.append(PacketEntry(each))
    return result


def parse_args():
    parse = argparse.ArgumentParser(prog='input.py')
    parse.add_argument('executablefile')
    parse.add_argument('logfile')
    parse.add_argument('-r', type=float, default=1.0, help='refresh Rate', dest='refreshRate')
    parse.add_argument('-o', default=False, help='true for resume , false for restart', dest='resume',
        action='store_const', const=True)
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
            return key, packet
    return None, None


def parseAndUpdate(input_file, refresh_rate, entries, screen, config):
    global srcdest
    if resume == True:
        input_file.seek(0, 2)
    while config.should_run:
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
            if m:
                response = parseXml(xmlStanza)
                responseType = response[0]
                responseElem = response[1]
                if responseType == "element":
                    processPacket(responseElem, entries, screen)
                elif responseType == "elementlist":
                    processPacketList(responseElem, entries, screen)
                elif responseType == "streamclose":
                    incrementAndUpdate(entries, 'streamclose', srcdest , screen)
                elif responseType == "sessionclose":
                    incrementAndUpdate(entries, 'sessionclose', srcdest , screen)
                else:
                    #print "Invalid XML"
                    #print m.group(1)
                    invalid_xml_logs.write(xmlStanza + "\n")
                    incrementAndUpdate(entries, 'IncompleteStanza', srcdest , screen)


def receiveUserInput(screen, config):
    while 1:
        user_input = screen.getch()
        if str(user_input) == '113':
            config.quit_app()
            curses.echo()
            curses.endwin()
            break


def main():
    global quitFlag, invalid_xml_logs, resume
    args = parse_args()
    refresh_rate = args.refreshRate
    resume = args.resume
    config = Config(refresh_rate, resume)
    input_file = open(args.logfile, 'r')
    invalid_xml_logs = open("invalidXmlLog", 'w')
    undetected_iq_file = open("undetectedIQ", 'w')

    packet_entries = setup_packet_entries()
    last_y_pos = init_packet_entries(packet_entries)
    screen = curses.initscr()
    curses.noecho()
    screen.border(0)
    printKeys(packet_entries, screen)
    userThread = threading.Thread(group=None, target=receiveUserInput, name='UserInput', args=( screen, config))
    userThread.start()
    backThread = threading.Thread(target=parseAndUpdate,
        args=(input_file, refresh_rate, packet_entries,screen, config))
    backThread.start()

    userThread.join()
    backThread.join()


if __name__ == '__main__':
    main()
