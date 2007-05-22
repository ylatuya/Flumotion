# -*- Mode: Python -*-
# vi:si:et:sw=4:sts=4:ts=4
#
# Flumotion - a streaming media server
# Copyright (C) 2004,2005,2006,2007 Fluendo, S.L. (www.fluendo.com).
# All rights reserved.

# This file may be distributed and/or modified under the terms of
# the GNU General Public License version 2 as published by
# the Free Software Foundation.
# This file is distributed without any warranty; without even the implied
# warranty of merchantability or fitness for a particular purpose.
# See "LICENSE.GPL" in the source distribution for more information.

# Licensees having purchased or holding a valid Flumotion Advanced
# Streaming Server license may use this file in accordance with the
# Flumotion Advanced Streaming Server Commercial License Agreement.
# See "LICENSE.Flumotion" in the source distribution for more information.

# Headers in this file shall remain intact.

import gst
from gst.extend import discoverer

import time
import calendar
from StringIO import StringIO

from xml.dom import Node

from twisted.internet import reactor

from flumotion.common import log, fxml

class PlaylistItem(object, log.Loggable):
    def __init__(self, id, timestamp, uri, offset, duration):
        self.id = id
        self.timestamp = timestamp
        self.uri = uri
        self.offset = offset
        self.duration = duration

        self.hasAudio = True
        self.hasVideo = True

        self.next = None
        self.prev = None

class Playlist(object, log.Loggable):
    def __init__(self, producer):
        """
        Create an initially empty playlist
        """
        self.items = None # PlaylistItem linked list
        self._itemsById = {}

        self.producer = producer

    def _findItem(self, position):
        # Get the item that corresponds to position, or None
        cur = self.items
        while cur:
            if cur.timestamp < position and \
                    cur.timestamp + cur.duration > position:
                return cur
            if cur.timestamp > position:
                return None # fail without having to iterate over everything
            cur = cur.next
        return None

    def _getCurrentItem(self):
        position = self.producer.getCurrentPosition()
        item = self._findItem(position)
        self.debug("Item %r found as current for playback position %d", 
            item, position)
        return item

    def removeItems(self, id):
        current = self._getCurrentItem()
            
        items = self._itemsById[id]
        for item in items:
            if (current and item.timestamp < current.timestamp + 
                    current.duration):
                self.debug("Not removing current item!")
                continue
            if item.prev:
                item.prev.next = item.next
            else:
                self.items = item.next

            if item.next:
                item.next.prev = item.prev
            self.producer.unscheduleItem(item)

        del self._itemsById[id]
        
    def addItem(self, id, timestamp, uri, offset, duration, hasAudio, hasVideo):
        """
        Add an item to the playlist.

        This may remove overlapping entries, or adjust timestamps/durations of
        entries to make the new one fit.
        """
        current = self._getCurrentItem()
        if current and timestamp < current.timestamp + current.duration:
            self.warning("New object at uri %s starts during current object, "
                "cannot add")
            return None
        # We don't care about anything older than now; drop references to them
        if current:
            self.items = current

        newitem = PlaylistItem(id, timestamp, uri, offset, duration)
        newitem.hasAudio = hasAudio
        newitem.hasVideo = hasVideo

        if id in self._itemsById:
            self._itemsById[id].append(newitem)
        else:
            self._itemsById[id] = [newitem]

        # prev starts strictly before the new item
        # next starts after the new item, and ends after the end of the new item
        prev = next = None
        item = self.items
        while item:
            if item.timestamp < newitem.timestamp:
                prev = item
            else:
                break
            item = item.next

        if item:
            item = item.next
        while item:
            if (item.timestamp + item.duration > newitem.timestamp):
                next = item
                break
            item = item.next

        if prev:
            # Then things between prev and next (next might be None) are to be 
            # deleted. Do so.
            cur = prev.next
            while cur != next:
                self._itemsById[cur.id].remove(cur)
                if not self._itemsById[cur.id]:
                    del self._itemsById[cur.id]
                self.producer.unscheduleItem(cur)
                cur = cur.next

        # update links.
        if prev:
            prev.next = newitem
            newitem.prev = prev
        else:
            self.items = newitem

        if next:
            newitem.next = next
            next.prev = newitem

        # Duration adjustments -> Reflect into gnonlin timeline
        if prev and prev.timestamp + prev.duration > newitem.timestamp:
            self.debug("Changing duration of previous item from %d to %d", 
                prev.duration, newitem.timestamp - prev.timestamp)
            prev.duration = newitem.timestamp - prev.timestamp
            self.producer.adjustItemScheduling(prev)

        if next and newitem.timestamp + newitem.duration > next.timestamp:
            self.debug("Changing timestamp of next item from %d to %d to fit", 
                newitem.timestamp, newitem.timestamp + newitem.duration)
            ts = newitem.timestamp + newitem.duration
            duration = next.duration - (ts - next.timestamp)
            next.duration = duration
            next.timestamp = ts
            self.producer.adjustItemScheduling(next)

        # Then we need to actually add newitem into the gnonlin timeline
        self.producer.scheduleItem(newitem)

        return newitem

class PlaylistParser(object, log.Loggable):
    def __init__(self, playlist):
        self.playlist = playlist

        self._pending_items = []
        self._discovering = False

        self._baseDirectory = None

    def setBaseDirectory(self, baseDir):
        if not baseDir.endswith('/'):
            baseDir = baseDir + '/'
        self._baseDirectory = baseDir

    def _discoverPending(self):
        def _discovered(disc, is_media):
            self.debug("Discovered!")
            reactor.callFromThread(_discoverer_done, disc, is_media)

        def _discoverer_done(disc, is_media):
            if is_media:
                self.debug("Discovery complete, media found")
                filename = item[0]
                if filename[0] != '/' and self._baseDirectory:
                    filename = self._baseDirectory + filename

                uri = "file://" + filename
                timestamp = item[1]
                duration = item[2]
                offset = item[3]
                id = item[4]

                hasA = disc.is_audio
                hasV = disc.is_video
                durationDiscovered = min(disc.audiolength, 
                    disc.videolength)
                if not duration or duration > durationDiscovered:
                    duration = durationDiscovered

                if duration + offset > durationDiscovered:
                    offset = 0

                if duration > 0:
                    self.playlist.addItem(id, timestamp, uri, offset, duration, 
                        hasA, hasV)
                else:
                    self.warning("Duration of item is zero, not adding")
            else:
                self.warning("Discover failed to find media in %s", item[0])
    
            # We don't want to burn too much cpu discovering all the files;
            # this throttles the discovery rate to a reasonable level
            self.debug("Continuing on to next file in one second")
            reactor.callLater(1, self._discoverPending)

        if not self._pending_items:
            self.debug("No more files to discover")
            self._discovering = False
            return

        self._discovering = True
        
        item = self._pending_items.pop(0)

        self.debug("Discovering file %s", item[0])
        disc = discoverer.Discoverer(item[0])

        disc.connect('discovered', _discovered)
        disc.discover()

    def addItemToPlaylist(self, filename, timestamp, duration, offset, id):
        # We only want to add it if it's plausibly schedulable.
        end = timestamp
        if duration is not None:
            end += duration
        if end < time.time() * gst.SECOND:
            self.debug("Early-out: ignoring add for item in past")
            return

        self._pending_items.append((filename, timestamp, duration, offset, id))

        # Now launch the discoverer for any pending items
        if not self._discovering:
            self._discoverPending()

class PlaylistXMLParser(PlaylistParser):

    def parseData(self, data):
        """
        Parse playlist XML document data
        """
        file = StringIO(data)
        self.parseFile(file)

    def replaceFile(self, file, id):
        self.playlist.removeItems(id)
        self.parseFile(file, id)

    def parseFile(self, file, id=None):
        """
        Parse a playlist file. Adds the contents of the file to the existing 
        playlist, overwriting any existing entries for the same time period.
        """
        parser = fxml.Parser()

        root = parser.getRoot(file)

        node = root.documentElement
        self.debug("Parsing playlist from file %s", file)
        if node.nodeName != 'playlist':
            raise fxml.ParserError("Root node is not 'playlist'")

        for child in node.childNodes:
            if child.nodeType == Node.ELEMENT_NODE and \
                    child.nodeName == 'entry':
                self.debug("Parsing entry")
                self._parsePlaylistEntry(parser, child, id)

    def _parsePlaylistEntry(self, parser, entry, id):
        mandatory = ['filename', 'time']
        optional = ['duration', 'offset']

        (filename, timestamp, duration, offset) = parser.parseAttributes(
            entry, mandatory, optional)

        if duration is not None:
            duration = int(float(duration) * gst.SECOND)
        if offset is None:
            offset = 0
        offset = int(offset) * gst.SECOND

        timestamp = self._parseTimestamp(timestamp)

        self.addItemToPlaylist(filename, timestamp, duration, offset, id)

    def _parseTimestamp(self, ts):
        # Take TS in YYYY-MM-DDThh:mm:ss.ssZ format, return timestamp in 
        # nanoseconds since the epoch

        # time.strptime() doesn't handle the fractional seconds part. We ignore
        # it entirely, after verifying that it has the right format.
        tsmain, trailing = ts[:-4], ts[-4:]
        if trailing[0] != '.' or trailing[3] != 'Z' or \
                not trailing[1].isdigit() or not trailing[2].isdigit():
            raise fxml.ParserError("Invalid timestamp %s" % ts)
        format = "%Y-%m-%dT%H:%M:%S"

        try:
            timestruct = time.strptime(tsmain, format)
            return int(calendar.timegm(timestruct) * gst.SECOND)
        except ValueError:
            raise fxml.ParserError("Invalid timestamp %s" % ts)


