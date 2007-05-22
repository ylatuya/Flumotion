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

"""
Server functionality.
"""

import os

from twisted.internet import reactor
from zope.interface import Interface

from flumotion.common import log


class _ServerContextFactory(log.Loggable):

    logCategory = "SSLServer"
    
    def __init__(self, pemFile):
        self._pemFile = pemFile

    def getContext(self):
        """
        Create an SSL context.
        """
        from OpenSSL import SSL
        ctx = SSL.Context(SSL.SSLv23_METHOD)
        try:
            ctx.use_certificate_file(self._pemFile)
            ctx.use_privatekey_file(self._pemFile)
        except SSL.Error, e:
            self.warning('SSL error: %r' % e.args)
            self.error('Could not open certificate %s' % self._pemFile)
        return ctx

class IServable(Interface):
    """
    I am an interface for objects that want to be servable through a
    L{Server}.
    """
    def getFactory(self):
        """
        @rtype: L{twisted.spread.pb.PBServerFactory}
        """

    def setConnectionInfo(self, host, port, useSSL):
        """
        @param host:   the host to listen as
        @type  host:   str
        @param port:   the port to listen on
        @type  port:   int
        @param useSSL: whether this connection uses SSL
        @type  useSSL: bool
        """
    
class Server(log.Loggable):
    logCategory = "server"

    def __init__(self, servable):
        """
        I expose a servable to the network using TCP or SSL.
        
        @type servable: an implemtor of L{IServable}
        """
        self._servable = servable

    def startSSL(self, host, port, pemFile, configDir):
        """
        Listen as the given host and on the given port using SSL.
        Use the given .pem file, or look for it in the config directory.

        @returns: {twisted.internet.interfaces.IListeningPort} on which
        we are listening; call .stopListening() to stop.
        """
        # if no path in pemFile, then look for it in the config directory
        if not os.path.split(pemFile)[0]:
            pemFile = os.path.join(configDir, pemFile)
        if not os.path.exists(pemFile):
            self.error(".pem file %s does not exist.\n" \
                "For more information, see \n" \
                "http://www.flumotion.net/doc/flumotion/manual/html/" \
                "chapter-security.html" % pemFile)
        log.debug('manager', 'Using PEM certificate file %s' % pemFile)
        ctxFactory = _ServerContextFactory(pemFile)
        
        self.info('Starting on port %d using SSL' % port)
        if not host == "":
            self.info('Listening as host %s' % host)
        self._servable.setConnectionInfo(host, port, True)
        return reactor.listenSSL(port, self._servable.getFactory(),
                                 ctxFactory, interface=host)

    def startTCP(self, host, port):
        """
        Listen as the given host and on the given port using normal TCP.

        @returns: {twisted.internet.interfaces.IListeningPort} on which
        we are listening; call .stopListening() to stop.
        """
        self.info('Starting on port %d using TCP' % port)
        if not host == "":
            self.info('Listening as host %s' % host)
        self._servable.setConnectionInfo(host, port, False)
        return reactor.listenTCP(port, self._servable.getFactory(),
                                 interface=host)
