# -*- Mode: Python; test-case-name: flumotion.test.test_bouncers_ipbouncer -*-
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

"""
A bouncer that authenticates based on the IP address of the remote side,
as seen by the bouncer.
"""

from twisted.internet import defer

from flumotion.common import keycards, messages, errors, log, netutils
from flumotion.component.bouncers import bouncer
from flumotion.common.keycards import KeycardUACPP

N_ = messages.N_
T_ = messages.gettexter('flumotion')

__all__ = ['IPBouncer']

class IPBouncer(bouncer.Bouncer):

    logCategory = 'ip-bouncer'
    keycardClasses = (keycards.KeycardUACPCC, keycards.KeycardUACPP)

    def do_setup(self):
        conf = self.config
        props = conf['properties']

        self.deny_default = props.get('deny-default', True)

        self.allows = netutils.RoutingTable()
        self.denies = netutils.RoutingTable()
        for p, t in (('allow', self.allows), ('deny', self.denies)):
            for s in props.get(p, []):
                try:
                    ip, mask = s.split('/')
                    t.addSubnet(True, ip, int(mask))
                except Exception, e:
                    m = messages.Error(
                        T_(N_("Invalid value for property %r: %s"), p, s),
                        log.getExceptionMessage(e),
                        id='match-type')
                    self.addMessage(m)
                    raise errors.ComponentSetupHandledError()

        return defer.succeed(None)

    def do_authenticate(self, keycard):
        ip = keycard.getData()['address']
        self.debug('authenticating keycard from requester %s', ip)

        if ip is None:
            self.warning('could not get address of remote')
            allowed = False
        elif self.deny_default:
            allowed = (self.allows.route(ip)
                       and not self.denies.route(ip))
        else:
            allowed = (self.allows.route(ip)
                       or not self.denies.route(ip))

        if not allowed:
            self.info('denied login from ip address %s',
                      keycard.address)
            return None
        else:
            keycard.state = keycards.AUTHENTICATED
            self.addKeycard(keycard)
            self.debug('allowed login from ip address %s',
                       keycard.address)
            return keycard

__version__ = "$Rev$"
