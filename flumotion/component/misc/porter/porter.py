# -*- Mode: Python; test-case-name: flumotion.test.test_porter -*-
# vi:si:et:sw=4:sts=4:ts=4
#
# Flumotion - a streaming media server
# Copyright (C) 2004,2005,2006 Fluendo, S.L. (www.fluendo.com).
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

from urllib2 import urlparse

from twisted.internet import tcp, protocol, reactor, address, error, defer

from twisted.spread import pb
from twisted.cred import portal

from flumotion.common import medium, log, messages
from flumotion.twisted import credentials, fdserver, checkers
from flumotion.twisted import reflect 

from flumotion.component import component
from flumotion.component.component import moods

import socket, string, os, random

from flumotion.common.messages import N_
T_ = messages.gettexter('flumotion')

class PorterAvatar(pb.Avatar, log.Loggable):
    """
    An Avatar in the porter representing a streamer
    """
    def __init__(self, avatarId, porter, mind):
        self.avatarId = avatarId
        self.porter = porter

        # The underlying transport is now accessible as 
        # self.mind.broker.transport, on which we can call sendFileDescriptor
        self.mind = mind

    def isAttached(self):
        return self.mind != None

    def logout(self):
        self.mind = None

    def perspective_registerPath(self, path):
        self.log("Perspective called: registering path \"%s\"" % path)
        self.porter.registerPath(path, self)

    def perspective_deregisterPath(self, path):
        self.log("Perspective called: deregistering path \"%s\"" % path)
        self.porter.deregisterPath(path, self)

    def perspective_registerPrefix(self, prefix):
        self.log("Perspective called: registering default")
        self.porter.registerPrefix(prefix, self)

    def perspective_deregisterPrefix(self, prefix):
        self.log("Perspective called: deregistering default")
        self.porter.deregisterPrefix(prefix, self)

class PorterRealm(log.Loggable):
    """
    A Realm within the Porter that creates Avatars for streamers logging into
    the porter.
    """
    __implements__ = portal.IRealm

    def __init__(self, porter):
        """
        @param porter: The porter that avatars created from here should use.
        @type  porter: L{Porter}
        """
        self.porter = porter

    def requestAvatar(self, avatarId, mind, *interfaces):
        self.log("Avatar requested for avatarId %s, mind %r, interfaces %r" % 
            (avatarId, mind, interfaces))
        if pb.IPerspective in interfaces:
            avatar = PorterAvatar(avatarId, self.porter, mind)
            return pb.IPerspective, avatar, avatar.logout
        else:
            raise NotImplementedError("no interface")

class PorterMedium(component.BaseComponentMedium):

    def remote_getPorterDetails(self):
        """
        Return the location and login username/password for the porter
        as a tuple (path, username, password)
        """
        return (self.comp._socketPath, self.comp._username, self.comp._password)

class Porter(component.BaseComponent, log.Loggable):
    """
    The porter optionally sits in front of a set of streamer components.
    The porter is what actually deals with incoming connections on a TCP socket.
    It decides which streamer to direct the connection to, then passes the FD
    (along with some amount of already-read data) to the appropriate streamer.
    """

    component_medium_class = PorterMedium

    def init(self):
        # We maintain a map of path -> avatar (the underlying transport is
        # accessible from the avatar, we need this for FD-passing)
        self._mappings = {}
        self._prefixes = {}

        self._socketlistener = None

        self._socketPath = None
        self._username = None
        self._password = None
        self._port = None
        self._porterProtocol = None

        self._interface = ''

    def registerPath(self, path, avatar):
        """
        Register a path as being served by a streamer represented by this 
        avatar. Will remove any previous registration at this path.

        @param path:   The path to register
        @type  path:   str
        @param avatar: The avatar representing the streamer to direct this path
                       to
        @type  avatar: L{PorterAvatar}
        """
        self.debug("Registering porter path \"%s\" to %r" % (path, avatar))
        if self._mappings.has_key(path):
            self.warning("Replacing existing mapping for path \"%s\"" % path)

        self._mappings[path] = avatar

    def deregisterPath(self, path, avatar):
        """
        Attempt to deregister the given path. A deregistration will only be
        accepted if the mapping is to the avatar passed.

        @param path:   The path to deregister
        @type  path:   str
        @param avatar: The avatar representing the streamer being deregistered
        @type  avatar: L{PorterAvatar}
        """
        if self._mappings.has_key(path):
            if self._mappings[path] == avatar:
                self.debug("Removing porter mapping for \"%s\"" % path)
                del self._mappings[path]
            else:
                self.warning("Mapping not removed: refers to a different avatar")
        else:
            self.warning("Mapping not removed: no mapping found")

    def registerPrefix(self, prefix, avatar):
        """
        Register a destination for all requests directed to anything beginning
        with a specified prefix. Where there are multiple matching prefixes, the
        longest is selected.

        @param avatar: The avatar being registered
        @type  avatar: L{PorterAvatar}
        """

        self.debug("Setting prefix \"%s\" for porter", prefix)
        if prefix in self._prefixes:
            self.warning("Overwriting prefix")

        self._prefixes[prefix] = avatar

    def deregisterPrefix(self, prefix, avatar):
        """
        Attempt to deregister a default destination for all requests not 
        directed to a specifically-mapped path. This will only succeed if the
        default is currently equal to this avatar.

        @param avatar: The avatar being deregistered
        @type  avatar: L{PorterAvatar}
        """
        if prefix not in self._prefixes:
            self.warning("Mapping not removed: no mapping found")
            return

        if self._prefixes[prefix] == avatar:
            self.debug("Removing prefix destination from porter")
            del self._prefixes[prefix]
        else:
            self.warning("Not removing prefix destination: expected avatar not found")

    def findPrefixMatch(self, path):
        found = None
        # TODO: Horribly inefficient. Figure out a smart algorithm
        for prefix in self._prefixes.keys():
            self.debug("Checking: %r, %r" % (type(prefix), type(path)))
            if (path.startswith(prefix) and (not found or len(found) < len(prefix))):
                found = prefix
        if found:
            return self._prefixes[found]
        else:
            return None

    def findDestination(self, path):
        """
        Find a destination Avatar for this path.
        @returns: The Avatar for this mapping, or None.
        """

        if self._mappings.has_key(path):
            return self._mappings[path]
        else:
            return self.findPrefixMatch(path)


    def generateSocketPath(self):
        """
        Generate a socket pathname in an appropriate location
        """
        # Also see worker/worker.py:_getSocketPath(), and note that this suffers
        # from the same potential race.
        import tempfile
        fd, name = tempfile.mkstemp('.%d' % os.getpid(), 'flumotion.porter.')
        os.close(fd)

        return name

    def generateRandomString(self, numchars):
        """
        Generate a random US-ASCII string of length numchars
        """
        str = ""
        chars = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz"
        for _ in range(numchars):
            str += chars[random.randint(0, len(chars)-1)]

        return str

    def do_setup(self):
        props = self.config['properties']
    
        # We can operate in two modes: explicitly configured (neccesary if you
        # want to handle connections from components in other managers), and
        # self-configured (which is sufficient for slaving only streamers
        # within this manager
        if props.has_key('socket_path'):
            # Explicitly configured
            self._socketPath = props['socket_path']
            self._username = props['username']
            self._password = props['password']
        else:
            # Self-configuring. Use a randomly create username/password, and
            # a socket with a random name.
            self._username = self.generateRandomString(12)
            self._password = self.generateRandomString(12)
            self._socketPath = self.generateSocketPath()

        self._port = int(props['port'])
        self._porterProtocol = props.get('protocol', 
            'flumotion.component.misc.porter.porter.HTTPPorterProtocol')
        self._interface = props.get('interface', '')

    def do_stop(self):
        if self._socketlistener:
            # stopListening() calls (via a callLater) connectionLost(), which
            # would normally unlink our socket. However, if we stop the reactor
            # before this happens, we leave a stale socket. So, we explicitly
            # unlink it below, as well. 
            self._socketlistener.stopListening()
        self._socketlistener = None

        try:
            os.unlink(self._socketPath)
        except:
            pass

        return component.BaseComponent.do_stop(self)
    
    def do_start(self, *args, **kwargs):
        # Create our combined PB-server/fd-passing channel

        realm = PorterRealm(self)
        checker = checkers.FlexibleCredentialsChecker()
        checker.addUser(self._username, self._password)
        
        p = portal.Portal(realm, [checker])
        serverfactory = pb.PBServerFactory(p)

        try:
            # Rather than a normal listenTCP() or listenUNIX(), we use 
            # listenWith so that we can specify our particular Port, which 
            # creates Transports that we know how to pass FDs over.
            try:
                os.unlink(self._socketPath)
            except:
                pass

            self._socketlistener = reactor.listenWith(
                fdserver.FDPort, self._socketPath, serverfactory)
            self.debug("Now listening on socketPath %s" % self._socketPath)
        except error.CannotListenError, e:
            self.warning("Failed to create socket %s" % self._socketPath)
            m = messages.Error(T_(N_(
                "Network error: socket path %s is not available."), 
                self._socketPath))
            self.addMessage(m)
            self.setMood(moods.sad)
            return defer.fail(e)

        # Create the class that deals with the specific protocol we're proxying
        # in this porter.
        try:
            proto = reflect.namedAny(self._porterProtocol)
            self.debug("Created proto %r" % proto)
        except:
            self.warning("Failed to import protocol '%s', defaulting to HTTP" % 
                self._porterProtocol)
            proto = HTTPPorterProtocol

        # And of course we also want to listen for incoming requests in the
        # appropriate protocol (HTTP, RTSP, etc.)
        factory = PorterProtocolFactory(self, proto)
        try:
            reactor.listenWith(
                PassableServerPort, self._port, factory, 
                    interface=self._interface)
            self.debug("Now listening on port %d" % self._port)
        except error.CannotListenError, e:
            self.warning("Failed to listen on port %d" % self._port)
            m = messages.Error(T_(N_(
                "Network error: TCP port %d is not available."), self._port))
            self.addMessage(m)
            self.setMood(moods.sad)
            return defer.fail(e)

        return component.BaseComponent.do_start(self, *args, **kwargs)

class PorterProtocolFactory(protocol.Factory):
    def __init__(self, porter, protocol):
        self._porter = porter
        self.protocol = protocol

    def buildProtocol(self, addr):
        p = self.protocol(self._porter)
        p.factory = self
        return p

class PassableServerConnection(tcp.Server):
    """
    A subclass of tcp.Server that permits passing the FDs used to other 
    processes (by just calling close(2) rather than shutdown(2) on them)
    """

    def __init__(self, sock, protocol, client, server, sessionno):
        tcp.Server.__init__(self, sock, protocol, client, server, sessionno)
        self.keepSocketAlive = False

    def _closeSocket(self):
        # We override this (from tcp._SocketCloser) so that we can close sockets
        # properly in the normal case, but once we've passed our socket on via
        # the FD-channel, we just close() it (not calling shutdown() which will
        # close the TCP channel without closing the FD itself)
        if self.keepSocketAlive:
            try:
                self.socket.close()
            except socket.error:
                pass
        else:
            tcp.Server._closeSocket(self)

class PassableServerPort(tcp.Port):
    transport = PassableServerConnection

class PorterProtocol(protocol.Protocol, log.Loggable):
    """
    The base porter is capable of accepting HTTP-like protocols (including 
    RTSP) - it reads the first line of a request, and makes the decision
    solely on that.

    We can't guarantee that we read precisely a line, so the buffer we 
    accumulate will actually be larger than what we actually parse.

    @cvar MAX_SIZE:   the maximum number of bytes allowed for the first line
    @cvar delimiters: a list of valid line delimiters I check for
    """
    # Don't permit a first line longer than this.
    MAX_SIZE = 4096

    # In fact, because we check \r, we'll never need to check for \r\n - we
    # leave this in as \r\n is the more correct form. At the other end, this
    # gets processed by a full protocol implementation, so being flexible hurts
    # us not at all
    delimiters = ['\r\n', '\n', '\r']

    def __init__(self, porter):
        self._buffer = ''
        self._porter = porter

    def dataReceived(self, data):
        self._buffer = self._buffer + data
        self.log("Got data, buffer now \"%s\"" % self._buffer)
        # We accept more than just '\r\n' (the true HTTP line end) in the 
        # interests of compatibility.
        for delim in self.delimiters:
            try:
                line, remaining = self._buffer.split(delim, 1)
                break
            except ValueError:
                self.log("No line break found yet")
                pass
        else:
            # Failed to find a valid delimiter. 
            self.log("No valid delimiter found")
            if len(self._buffer) > self.MAX_SIZE:
                self.log("Dropping connection!")
                return self.transport.loseConnection()
            else:
                # TODO: Should we return anything?
                return

        # Got a line. self._buffer is still our entire buffer, should be
        # provided to the slaved process.
        identifier = self.parseLine(line)
        
        if not identifier:
            self.log("Couldn't find identifier in first line")
            return self.transport.loseConnection()

        # Ok, we have an identifier. Is it one we know about, or do we have
        # a default destination?
        destinationAvatar = self._porter.findDestination(identifier)

        if not destinationAvatar or not destinationAvatar.isAttached():
            if destinationAvatar:
                self.log("There was an avatar, but it logged out?")
            self.log("No destination avatar found for \"%s\"" % identifier)
            self.writeNotFoundResponse()
            return self.transport.loseConnection()

        # Transfer control over this FD. Pass all the data so-far received
        # along in the same message. The receiver will push that data into
        # the Twisted Protocol object as if it had been normally received,
        # so it looks to the receiver like it has read the entire data stream
        # itself. 

        # TODO: Check out blocking characteristics of sendFileDescriptor, fix
        # if it blocks.
        self.debug("Attempting to send FD: %d" % self.transport.fileno())
        destinationAvatar.mind.broker.transport.sendFileDescriptor(
            self.transport.fileno(), self._buffer)

        # After this, we don't want to do anything with the FD, other than
        # close our reference to it - but not close the actual TCP connection.
        # We set keepSocketAlive to make loseConnection() only call close() 
        # rather than shutdown() then close()
        self.transport.keepSocketAlive = True
        self.transport.loseConnection()

    def parseLine(self, line):
        """
        Parse the initial line of the response. Return a string usable for
        uniquely identifying the stream being requested, or None if the request
        is unreadable.

        Subclasses should override this.
        """
        raise NotImplementedError

    def writeNotFoundResponse(self):
        """
        Write a response indicating that the requested resource was not found
        in this protocol.

        Subclasses should override this to use the correct protocol.
        """
        raise NotImplementedError

class HTTPPorterProtocol(PorterProtocol):
    scheme = 'http'
    protos = ["HTTP/1.0", "HTTP/1.1"]

    def parseLine(self, line):
        try:
            (method, location, proto) = map(string.strip, line.split(' ', 2))
            
            if proto not in self.protos:
                return None

            # Currently, we just return the path part of the URL.
            # Use the URL parsing from urllib2. 
            location = urlparse.urlparse(location, 'http')[2]
            self.log('parsed %s %s %s' % (method, location, proto))
            if not location or location == '':
                return None

            return location

        except ValueError:
            return None

    def writeNotFoundResponse(self):
        self.transport.write("HTTP/1.0 404 Not Found\r\n\r\nResource unknown")
    
class RTSPPorterProtocol(HTTPPorterProtocol):
    scheme = 'rtsp'
    protos = ["RTSP/1.0"]

    def writeNotFoundResponse(self):
        self.transport.write("RTSP/1.0 404 Not Found\r\n\r\nResource unknown")

