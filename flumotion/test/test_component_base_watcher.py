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

from twisted.internet import reactor, defer
from flumotion.common import testsuite
from flumotion.component.base import watcher
import tempfile
import os
import time


class WatcherTest(testsuite.TestCase):

    def testInstantiate(self):
        watcher.BaseWatcher(30)

    def testContiunePollingOnSubscriberError(self):

        def cleanUp(_):
            w.stop()

        def fileDeleted(_):
            d = defer.Deferred()
            d.addCallback(cleanUp)
            reactor.callLater(0, d.callback, _)
            return d

        def fileChanged(_):
            os.remove(tempFile)
            raise Exception("This exception shouldn't be raisen")

        fd, tempFile = tempfile.mkstemp()
        w = watcher.FilesWatcher([tempFile], 0.001)
        w.subscribe(fileChanged = fileChanged)
        d = defer.Deferred()
        d.addCallback(fileDeleted)
        w.subscribe(fileDeleted = d.callback)
        w.start()
        os.write(fd, "test")
        os.close(fd)
        return d
