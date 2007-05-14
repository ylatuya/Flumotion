# -*- Mode: Python -*-
# vi:si:et:sw=4:sts=4:ts=4
#
# Flumotion - a streaming media server
# Copyright (C) 2006,2007 Fluendo, S.L. (www.fluendo.com).
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


from datetime import datetime

from twisted.internet import reactor

from flumotion.common import log, avltree


class Event(log.Loggable):
    """
    I am an event. I have a start and stop time and a "content" that can
    be anything. I can recur.
    """

    def __init__(self, start, end, content, recur=None, now=None):
        from dateutil import rrule
        self._rrulestr = rrule.rrulestr

        self.debug('new event, content=%r, start=%r, end=%r', start,
                   end, content)
        self.setBounds(recur, start, end, now or datetime.now())
        self.content = content
        self.recur = recur

    def setBounds(self, recur, start, end, now):
        self.recur = recur
        if recur:
            startRecurRule = self._rrulestr(recur, dtstart=start)
            endRecurRule = self._rrulestr(recur, dtstart=end) 
            if end < now:
                end = endRecurRule.after(now)
                start = startRecurRule.before(end)
                self.debug("adjusting start and end times to %r, %r",
                           start, end)
                self.start, self.end = start, end

    def reschedule(self):
        if self.recur:
            return Event(self.start, self.end, self.content, self.recur)
        else:
            return None

    def __lt__(self, other):
        return self.start < other.start

    def __gt__(self, other):
        return self.start > other.start

    def __eq__(self, other):
        return self.start == other.start


class Scheduler(log.Loggable):
    """
    I keep track of upcoming events.
    
    I can provide notifications when events stop and start, and maintain
    a set of current events.
    """

    def __init__(self):
        self.current = []
        self._delayedCall = None
        self._subscribeId = 0
        self.subscribers = {}
        self.replaceEvents([])

    def addEvent(self, start, end, content, recur=None):
        """Add a new event to the scheduler.

        @param start: wall-clock time of event start
        @type  start: datetime
        @param   end: wall-clock time of event end
        @type    end: datetime
        @param content: content of this event
        @type  content: str
        @param recur: recurrence rule
        @type  recur: str

        @returns: an Event that can later be passed to removeEvent, if
        so desired. The event will be removed or rescheduled
        automatically when it stops.
        """
        now = datetime.now()
        event = Event(start, end, content, recur, now)
        if event.end < now:
            self.warning('attempted to schedule event in the past: %r',
                         event)
        else:
            self.events.insert(event)
            if event.start < now:
                self._eventStarted(event)
        self._reschedule()
        return event

    def removeEvent(self, event):
        """Remove an event from the scheduler.

        @param event: an event, as returned from addEvent()
        @type  event: Event
        """
        currentEvent = event.reschedule() or event
        self.events.delete(currentEvent)
        if currentEvent in self.current:
            self._eventStopped(currentEvent)
        self._reschedule()

    def replaceEvents(self, events):
        """Replace the set of events in the scheduler.

        This function is different than simply removing all events then
        adding new ones, because it tries to avoid spurious
        stopped/start notifications.

        @param events: the new events
        @type  events: a sequence of Event
        """
        now = datetime.now()
        self.events = avltree.AVLTree(events)
        current = []
        for event in self.events:
            if now < event.start:
                break
            elif event.end < now:
                # yay functional trees: we don't modify the iterator
                self.events.delete(event)
            else:
                current.append(event)
        for event in self.current[:]:
            if event not in current:
                self._eventStopped(event)
        for event in current:
            if event not in self.current:
                self._eventStarted(event)
        assert self.current == current
        self._reschedule()
        
    def subscribe(self, eventStarted, eventStopped):
        """Subscribe to event happenings in the scheduler.

        @param eventStarted: Function that will be called when an event
        starts.
        @type eventStarted: Event -> None
        @param eventStopped: Function that will be called when an event
        stops.
        @type eventStopped: Event -> None

        @returns: A subscription ID that can later be passed to
        unsubscribe().
        """
        sid = self._subscribeId
        self._subscribeId += 1
        self.subscribers[sid] = (eventStarted, eventStopped)
        return sid

    def unsubscribe(self, id):
        """Unsubscribe from event happenings in the scheduler.

        @param id: Subscription ID received from subscribe()
        """
        del self.subscribers[id]

    def _eventStarted(self, event):
        self.current.append(event)
        for started, _ in self.subscribers.values():
            started(event.content)

    def _eventStopped(self, event):
        self.current.remove(event)
        for _, stopped in self.subscribers.values():
            stopped(event.content)

    def _reschedule(self):
        def _getNextStart():
            for event in self.events:
                if event not in self.current:
                    return event
            return None

        def _getNextStop():
            t = None
            e = None
            for event in self.current:
                if not t or event.end < t:
                    t = event.end
                    e = event
            return e

        def doStart(e):
            self._eventStarted(e)
            self._reschedule()
            
        def doStop(e):
            self._eventStopped(e)
            self.events.delete(e)
            new = e.reschedule()
            if new:
                self.events.insert(new)
            self._reschedule()
            
        if self._delayedCall:
            self._delayedCall.cancel()
            self._delayedCall = None

        start = _getNextStart()
        stop = _getNextStop()
        now = datetime.now()

        if start and (not stop or start.start < stop.end):
            dc = reactor.callLater(max (start.start - now, 0), doStart,
                                   start)
        elif stop:
            dc = reactor.callLater(max (stop.end - now, 0), doStop,
                                   stop)
        else:
            dc = None

        self._delayedCall = dc


class ICalScheduler(Scheduler):
    """
    I am a scheduler that takes its data from an ical file.
    """

    def __init__(self, fileObj):
        from icalendar import Calendar

        Scheduler.__init__(self)
        cal = Calendar.from_string(fileObj.read())
        self.parseCalendar(cal)

    def parseCalendar(self, cal):
        for event in cal.walk('vevent'):
            start = event.decoded('dtstart', None)
            end = event.decoded('dtend', None)
            summary = event.decoded('summary', None)
            recur = event.get('rrule', None)
            if start and end:
                if recur:
                    self.addEvent(start, end, summary, recur.ical())
                else:
                    self.addEvent(start, end, summary)
            else:
                self.warning('ical has event without start or end: '
                             '%r', event)
