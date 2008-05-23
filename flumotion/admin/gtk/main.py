# -*- Mode: Python -*-
# vi:si:et:sw=4:sts=4:ts=4
#
# Flumotion - a streaming media server
# Copyright (C) 2004,2005,2006,2007,2008 Fluendo, S.L. (www.fluendo.com).
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
import sys

import gettext

from twisted.internet import reactor
from twisted.python import log as twistedlog

from flumotion.admin import connections
from flumotion.common import log
from flumotion.common.errors import ConnectionRefusedError, OptionError
from flumotion.configure import configure
from flumotion.common.options import OptionParser

__version__ = "$Rev$"
_ = gettext.gettext

_retval = 0

def _installGettext():
    import locale

    localedir = os.path.join(configure.localedatadir, 'locale')
    log.debug("locale", "Loading locales from %s" % localedir)
    gettext.bindtextdomain(configure.PACKAGE, localedir)
    gettext.textdomain(configure.PACKAGE)
    locale.bindtextdomain(configure.PACKAGE, localedir)
    locale.textdomain(configure.PACKAGE)

def _connectToManager(win, manager, ssl):
    try:
        info = connections.parsePBConnectionInfo(manager,
                                                 use_ssl=ssl)
    except OptionError, e:
        raise SystemExit("ERROR: %s" % (e,))

    d = win.openConnection(info)
    def errbackConnectionRefused(failure):
        global _retval
        failure.trap(ConnectionRefusedError)
        print >> sys.stderr, _(
            "ERROR: Could not connect to manager:\n"
            "       The connection to %r was refused.") % (
            manager,)
        _retval = 1
        reactor.stop()
    
    def errback(failure):
        global _retval
        print >> sys.stderr, "ERROR: %s" % (failure.value,)
        _retval = 1
        reactor.stop()
    d.addErrback(errbackConnectionRefused)
    d.addErrback(errback)
    return d

def main(args):
    global _retval

    parser = OptionParser(domain="flumotion-admin")
    parser.add_option('-m', '--manager',
                      action="store", type="string", dest="manager",
                      help="the manager to connect to, e.g. localhost:7531")
    parser.add_option('', '--no-ssl',
                      action="store_false", dest="ssl", default=True,
                      help="disable encryption when connecting to the manager")

    options, args = parser.parse_args(args)

    _installGettext()

    if len(args) > 1:
        log.error('flumotion-admin',
                  'too many arguments: %r' % (args[1:],))
        return 1

    from flumotion.ui.icons import register_icons
    register_icons()

    from flumotion.admin.gtk.client import AdminClientWindow
    win = AdminClientWindow()

    if options.verbose or (options.debug and options.debug > 3):
        win.setDebugEnabled(True)

    if options.manager:
        d = _connectToManager(win, options.manager, options.ssl)
    else:
        from flumotion.admin.gtk.greeter import Greeter
        greeter = Greeter(win)
        d = greeter.runAsync()

    # Printout unhandled exception to stderr
    d.addErrback(twistedlog.err)

    reactor.run()
    return _retval
