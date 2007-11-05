# -*- Mode: Python -*-
# vi:si:et:sw=4:sts=4:ts=4
#
# Flumotion - a streaming media server
# Copyright (C) 2007 Fluendo, S.L. (www.fluendo.com).
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

import common
import random

from twisted.trial import unittest

from flumotion.common import signals


class TestObject(signals.SignalMixin):
    __signals__ = ('foo', 'bar')

class TestSignalMixin(unittest.TestCase):
    def testEmitSelf(self):
        o = TestObject()

        emissions = []
        def trackEmission(*args, **kwargs):
            emissions.append((args[-1], args[:-1], kwargs))

        o.connect('foo', trackEmission, 'foo')
        o.emit('foo')

        self.assertEquals(emissions, [('foo', (o,), {})])

    def testMixin(self):
        o = TestObject()

        o.emit('foo')
        o.emit('bar')

        self.assertRaises(ValueError, o.emit, 'qux')

        emissions = []
        def trackEmission(*args, **kwargs):
            emissions.append((args[-1], args[:-1], kwargs))

        o.connect('foo', trackEmission, 'foo')
        o.connect('bar', trackEmission, 'bar', baz='qux')

        o.emit('foo')
        self.assertEquals(emissions, [('foo', (o,), {})])
        o.emit('foo', 1)
        self.assertEquals(emissions, [('foo', (o,), {}),
                                      ('foo', (o,1,), {})])
        o.emit('bar', 'xyzzy')
        self.assertEquals(emissions, [('foo', (o,), {}),
                                      ('foo', (o,1,), {}),
                                      ('bar', (o,'xyzzy',), {'baz':'qux'})])

    def testDisconnect(self):
        o = TestObject()

        sid = o.connect('foo', self.fail)
        o.disconnect(sid)
        o.emit('foo')
