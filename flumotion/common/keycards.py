# -*- Mode: Python; test-case-name: flumotion.test.test_keycards -*-
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
serializable keycards used for authentication inside Flumotion
"""

from twisted.cred import credentials as tcredentials
from twisted.spread import pb
from zope.interface import implements

from flumotion.twisted import credentials
from flumotion.common import common

__version__ = "$Rev$"

_statesEnum = ['REFUSED', 'REQUESTING', 'AUTHENTICATED']
# state enum values
(REFUSED,
 REQUESTING,
 AUTHENTICATED) = range(3)

class Keycard(pb.Copyable, pb.RemoteCopy):
    """
    I am the base class for keycards which together with credentials are
    a serializable object used in authentication inside Flumotion.

    @ivar  bouncerName: name of the bouncer to authenticate against; set by
                        requester
    @type  bouncerName: str
    @ivar  requesterId: avatarId of the requester
    @type  requesterId: str
    @ivar  avatarId:    avatarId preferred by requester
    @type  avatarId:    str
    @ivar  id:          id of keycard decided by bouncer after authenticating
    @type  id:          object
    @ivar  duration:    duration for which the keycard is valid, or 0 for
                        unlimited
    @type  duration:    int
    @ivar  domain:      requester can pass a domain id to the bouncer
    @type  domain:      str
    @ivar  state:       state the keycard is in
    @type  state:       int
    """
    implements(common.mergeImplements(pb.Copyable, pb.RemoteCopy)
        + (tcredentials.ICredentials,))

    def __init__(self):
        self.bouncerName = None
        self.requesterId = None
        self.avatarId = None
        self.id = None
        self.duration = 0
        self.domain = None
        self.state = REQUESTING

    # F0.8
    def setDomain(self, domain):
        """
        Set the domain of the requester on the keycard.

        @type domain: string
        """
        import warnings
        warnings.warn('Set the domain on the keycard directly.',
            DeprecationWarning, stacklevel=2)

        self.domain = domain

    def getData(self):
        """
        Return a dictionary of the viewable data on the keycard that can be
        used to identify the keycard.
        It doesn't include sensitive information though.

        Subclasses should override to add additional information.
        """
        return {
            'id':        self.id,
            'requester': self.requesterId,
            'domain':    self.domain
        }

    def __repr__(self):
        return "<%s for requesterId %r in state %s>" % (self.__class__.__name__,
            self.requesterId, _statesEnum[self.state])

class KeycardGeneric(Keycard, object):
    pass

pb.setUnjellyableForClass(KeycardGeneric, KeycardGeneric)
# class KeycardUACCP: username, address, crypt password
#       from UsernameCryptPasswordCrypt

UCPP = credentials.UsernameCryptPasswordPlaintext
class KeycardUACPP(Keycard, UCPP):
    """
    I am a keycard with a username, plaintext password and IP address.
    I get authenticated against a crypt password.
    """
    implements(common.mergeImplements(Keycard, UCPP))
    def __init__(self, username, password, address):
        UCPP.__init__(self, username, password)
        Keycard.__init__(self)
        self.address = address

    def getData(self):
        d = Keycard.getData(self)
        d['username'] = self.username
        d['address'] = self.address
        return d

    def __repr__(self):
        return "<%s %s %s@%s for requesterId %r in state %s>" % (
            self.__class__.__name__, self.id, self.username, self.address,
            self.requesterId, _statesEnum[self.state])

pb.setUnjellyableForClass(KeycardUACPP, KeycardUACPP)

# username, address, crypt password
#       from UsernameCryptPasswordCrypt

UCPCC = credentials.UsernameCryptPasswordCryptChallenger
class KeycardUACPCC(Keycard, UCPCC):
    """
    I am a keycard with a username and IP address.
    I get authenticated through challenge/response on a crypt password.
    """
    implements(common.mergeImplements(Keycard, UCPCC))
    def __init__(self, username, address):
        UCPCC.__init__(self, username)
        Keycard.__init__(self)
        self.address = address

    def getData(self):
        d = Keycard.getData(self)
        d['username'] = self.username
        d['address'] = self.address
        return d

    def __repr__(self):
        return "<%s %s %s@%s for requesterId %r in state %s>" % (
            self.__class__.__name__, self.id, self.username, self.address,
            self.requesterId, _statesEnum[self.state])

pb.setUnjellyableForClass(KeycardUACPCC, KeycardUACPCC)

class KeycardToken(Keycard, credentials.Token):
    """
    I am a keycard with a token and IP address and a path (optional).
    I get authenticated by token and maybe IP address.
    """
    implements(common.mergeImplements(Keycard,credentials.Token))

    def __init__(self, token, address, path=None):
        credentials.Token.__init__(self, token)
        Keycard.__init__(self)
        self.address = address
        self.path = path

    def getData(self):
        d = Keycard.getData(self)
        d['token'] = self.token
        d['address'] = self.address
        d['path'] = self.path
        return d

    def __repr__(self):
        return "<%s %s token %s for path %s @%s for requesterId %r in state %s>" % (
            self.__class__.__name__, self.id, self.token, self.path,
            self.address, self.requesterId, _statesEnum[self.state])

pb.setUnjellyableForClass(KeycardToken, KeycardToken)

USPCC = credentials.UsernameSha256PasswordCryptChallenger
class KeycardUASPCC(Keycard, USPCC):
    """
    I am a keycard with a username and IP address.
    I get authenticated through challenge/response on a SHA-256 password.
    """
    implements(common.mergeImplements(Keycard, USPCC))
    def __init__(self, username, address):
        USPCC.__init__(self, username)
        Keycard.__init__(self)
        self.address = address

    def getData(self):
        d = Keycard.getData(self)
        d['username'] = self.username
        d['address'] = self.address
        return d

    def __repr__(self):
        return "<%s %s %s@%s for requesterId %r in state %s>" % (
            self.__class__.__name__, self.id, self.username, self.address,
            self.requesterId, _statesEnum[self.state])

pb.setUnjellyableForClass(KeycardUASPCC, KeycardUASPCC)

class KeycardHTTPDigest(Keycard, credentials.HTTPDigestChallenger):
    def __init__(self, username):
        credentials.HTTPDigestChallenger.__init__(self, username)
        Keycard.__init__(self)

    def getData(self):
        d = Keycard.getData(self)
        d['username'] = self.username
        # Realm? Uri?
        return d

    def __repr__(self):
        return "<%s %s %s for requesterId %r in state %s>" % (
            self.__class__.__name__, self.id, self.username,
            self.requesterId, _statesEnum[self.state])

pb.setUnjellyableForClass(KeycardHTTPDigest, KeycardHTTPDigest)

# F0.8
class HTTPDigestKeycard(KeycardHTTPDigest):
    def __init__(self, username):
        import warnings
        warnings.warn('Use KeycardHTTPDigest instead.', DeprecationWarning,
            stacklevel=2)
        KeycardHTTPDigest.__init__(self, username)

pb.setUnjellyableForClass(HTTPDigestKeycard, HTTPDigestKeycard)
