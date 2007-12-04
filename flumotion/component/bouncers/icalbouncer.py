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

__version__ = "$Rev$"

"""
A bouncer that only lets in during an event scheduled with an ical file.
"""

from twisted.internet import defer

from flumotion.common import keycards, config
from flumotion.component.bouncers import bouncer
from flumotion.common.keycards import KeycardGeneric
from datetime import datetime
from flumotion.component.base import scheduler

__all__ = ['IcalBouncer']

try:
    # icalendar and dateutil modules needed for ical parsing
    from icalendar import Calendar
    from dateutil import rrule
    HAS_ICAL = True
except:
    HAS_ICAL = False

class IcalBouncer(bouncer.Bouncer):

    logCategory = 'icalbouncer'
    keycardClasses = (KeycardGeneric)
    events = []

    def do_setup(self):
        if not HAS_ICAL:
            return defer.fail(
                config.ConfigError(
                    "Please install icalendar and dateutil modules"))
        props = self.config['properties']
        self._icsfile = props['file']
        self.icalScheduler = scheduler.ICalScheduler(open(
            self._icsfile, 'r'))

        return True

    def do_authenticate(self, keycard):
        self.debug('authenticating keycard')

        # need to check if inside an event time
        # FIXME: think of a strategy for handling overlapping events
        currentEvents = self.icalScheduler.getCurrentEvents()
        if currentEvents:
            event = currentEvents[0]
            keycard.state = keycards.AUTHENTICATED
            duration = event.end - datetime.now()
            durationSecs = duration.days * 86400 + duration.seconds
            keycard.duration = durationSecs
            self.addKeycard(keycard)
            self.info("autheticated login")
            return keycard
        self.info("failed in authentication, outside hours")
        return None
