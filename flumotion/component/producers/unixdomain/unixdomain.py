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

import os
import gst

from flumotion.component import feedcomponent
from flumotion.common import log, messages, errors
from twisted.internet.protocol import ServerFactory, Protocol
from twisted.internet import defer, reactor

# Fake Protocol
class DumbProtocol(Protocol):
    """ Dumb Protocol, doesn't do anything """

    def connectionMade(self):
        """ Stop reading/writing """
        if self.factory.component.currentTransport:

            self.transport.loseConnection()
            return
        self.transport.stopReading()
        self.transport.stopWriting()
        self.factory.component.setUnixTransport(self.transport)
        # FIXME : We should maybe lose connection here ....

# UnixDomainDumbFactory
class UnixDomainDumbFactory(ServerFactory):

    protocol = DumbProtocol

    def __init__(self, component):
        self.component = component

# Component
class UnixDomainProvider(feedcomponent.ParseLaunchComponent):

    def init(self):
        self.factory = None
        self.socketPath = None
        self.currentTransport = None

    def setUnixTransport(self, transport):
        self.debug("got transport %r [fd:%d]" % (transport, transport.fileno()))
        self.currentTransport = transport
        # we should set that fd on the fdsrc now

        fdsrc = self.pipeline.get_by_name("fdsrc")
        fdsrc.props.fd = transport.fileno()
        # create pipeline

        # call self.link()
        self.link()

    def get_pipeline_string(self, properties):
        """ return the pipeline """
        return 'fdsrc name=fdsrc ! gdpdepay'

    def do_setup(self):
        props = self.config['properties']
        self.socketPath = props.get('path')
        self.factory = UnixDomainDumbFactory(self)

        # We need to set the pipeline to READY so the multifdsink gets start'ed
        self.pipeline.set_state(gst.STATE_READY)

        # remove the existing socket
        if os.path.exists(self.socketPath):
            os.unlink(self.socketPath)

        self.log("Starting to listen on UNIX : %s" % self.socketPath)
        reactor.listenUNIX(self.socketPath, self.factory)
        # we will link once we have a valid FD
