# -*- Mode: Python -*-
# vi:si:et:sw=4:sts=4:ts=4
#
# Flumotion - a video streaming server
#
# flumotion/tester/httpclient.py: http testing client class
#
# Copyright (C) 2004 Fluendo
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Street #330, Boston, MA 02111-1307, USA.

import gobject

import urllib2
import time

import sys
import socket

from flumotion.utils import log
from flumotion.tester import client

class HTTPClient(gobject.GObject, log.Loggable):
    """
    Base class for HTTP clients.
    """
    
    __gsignals__ = {
        'stopped': (gobject.SIGNAL_RUN_FIRST, None, (int, )),
    }
    
    logCategory = "httpclient"

    def __init__(self, id, url):
        """
        @param id: id of the client.
        @param url: URL to open.
        @type url: string.
        """
        self.__gobject_init__()
        self._url = url
        self._id = id
        self._fd = None
        self._stop_time = 0 # delta to start time
        self._stop_size = 0

    # if we have it then we can't test when we don't, FIXME
    #def verify(self, data):
    #    raise "verify needs to be handed to me by the application"

    def next_read_time(self):
	    """
        Calculate the next time to read.

        @rtype: float
        @returns: next read time in seconds since epoch.
        """
        raise "next_read_time needs to be implemented by a subclass"

    def read_size(self):
	    """
        calculate and return the size of the current read'
        raise "read_size needs to be implemented by a subclass"
        """

    def set_stop_time(self, stop_time):
        """
        Set a maximum time to run for.  If a client reaches this,
        it means the run was successful.
        """
        self._stop_time = stop_time
        
    def set_stop_size(self, stop_size):
        """
        Set a maximum size to read.  If a client reaches this,
        it means the run was successful.
        """
        self._stop_size = stop_size
         
    def open(self):
        'open the connection'
        self._start_time = time.time()
        self._bytes = 0
        try:
            self._fd = urllib2.urlopen(self._url)
        except urllib2.HTTPError, error:
            self.warning("%4d: HTTPError: code %s, msg %s" % (self._id, error.code, error.msg))
            self.emit('stopped', client.STOPPED_CONNECT_ERROR)
            return
        except urllib2.URLError, exception:
            code = None
            #try:
            code = exception.reason[0]
            #except:
            #    print "Unhandled exception: %s" % exception
            #    self.emit('stopped')
            #    return

            if code == 111:
                self.warning("%4d: connection refused" % self._id)
                self.emit('stopped', client.STOPPED_REFUSED)
                return
            else:
                self.warning("%4d: unhandled URLError with code %d" % (self._id, code))
                self.emit('stopped', client.STOPPED_CONNECT_ERROR)
                return
        except socket.error, (code, msg):
            if code == 104:
                # Connection reset by peer
                self.warning("%4d: %s" % (self._id, msg))
                self.emit('stopped', client.STOPPED_CONNECT_ERROR)
                return
            else:
                self.warning("%4d: unhandled socket.error with code %d" % (self._id, code))
                self.emit('stopped', self.stopped_CONNECT_ERROR)
                return
        if not self._fd:
           self.warning("%4d: didn't get fd from urlopen" % self._id)
           self.emit('stopped', self.stopped_CONNECT_ERROR)
           return
              
        delta = self.next_read_time() - self._start_time
        timeout = int(delta * 1000)
        gobject.timeout_add(timeout, self.read)

    def read(self):
        size = self.read_size()
        self.log("%4d: read(%d)" % (self._id, size))
        try:
            data = self._fd.read(size)
        except KeyboardInterrupt:
            sys.exit(1)

        if len(data) == 0:
            self.warning("zero bytes readm closing")
            self.close(client.STOPPED_READ_ERROR)
        #print "%4d: %d bytes read" % (self._id, len(data))
        self._bytes += len(data)
        #if not self.verify(data):
        #    print "OH MY GOD ! THIEF !"

        now = time.time()

        # handle exit conditions
        if self._stop_time:
            if now - self._start_time > self._stop_time:
                self.warning("%4d: stop time reached, closing" % self._id)
                self._fd.close()
                self.close(client.STOPPED_SUCCESS)
                return False
        if self._stop_size:
            if self._bytes > self._stop_size:
                self.info("%4d: stop size reached, closing" % self._id)
                self._fd.close()
                self.close(client.STOPPED_SUCCESS)
                return False

        # schedule next read
        delta = self.next_read_time() - time.time()
        timeout = int(delta * 1000)
        if timeout < 0:
            timeout = 0
        #print "%4d: timeout to next read: %d ms" % (self._id, timeout)
        gobject.timeout_add(timeout, self.read)

        #calculate stats
        rate = self._bytes / (now - self._start_time) / 1024.0
        #print "%d: %f: read: %d bytes, nominal actual rate: %f" % (self._id, now, self._bytes, rate)
        return False


    def close(self, reason):
        'close the connection'
        self.emit('stopped', reason)

class HTTPClientStatic(HTTPClient):
    """
    HTTP client reading at regular intervals with a fixed read size and
    a fixed rate in KByte/sec.
    """

    logCategory = "h-c-s"
    def __init__(self, id, url, rate = 5.0, readsize = 1024):
        self._rate = rate
        self._readsize = readsize
        HTTPClient.__init__(self, id, url)

    def next_read_time(self):
        'calculate the next time we want to read.  Could be in the past.'
	    # calculate the next byte count
        next_byte_count = self._bytes + self._readsize
 
        # calculate the elapsed time corresponding to this read moment
        time_delta = next_byte_count / (self._rate * 1024.0)

        return self._start_time + time_delta

    def read_size(self):
        return self._readsize

lastbyte = {}
def verify(client, data):
    if not lastbyte.has_key(client):
        next = ord(data[0])
    else:
        next = ord(lastbyte[client]) + 1
        if next > 255: next = 0
    #print " next byte: %x" % next
    print len(data)

    import struct
    # create a range of integer values starting at next and as long as the data
    numbers = range(next, next + len(data))
    # map a mod on to it so they get truncated to the pattern
    bytes = map(lambda x: x % 256, numbers)

    buffer = struct.pack("B" * len(bytes), *bytes)
    #print "comparing buffer to data: %d - %d" % (len(buffer), len(data))
    #print "comparing buffer to data: %d - %d" % (ord(buffer[0]), ord(data[0]))
    #print "comparing buffer to data: %d - %d" % (ord(buffer[-1]), ord(data[-1]))
    if (buffer != data):
       print "WOAH NELLY !"
       return False
    return True

gobject.type_register(HTTPClient)
gobject.type_register(HTTPClientStatic)
