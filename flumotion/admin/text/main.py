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

import optparse

from twisted.internet import reactor
from twisted.python import rebuild

from flumotion.common import log, errors, worker, planet, common

# make Message proxyable
from flumotion.common import messages

from flumotion.configure import configure
from flumotion.twisted import flavors, reflect

#from flumotion.admin import connections

from flumotion.admin.text import connection
from flumotion.admin.text.greeter import AdminTextGreeter

import curses

def cleanup_curses(stdscr):
    curses.nocbreak()
    stdscr.keypad(0)
    curses.echo()
    curses.endwin()

def _runInterface(options):
    # initialise curses
       
    stdscr = curses.initscr()
    curses.noecho()
    curses.cbreak()
    stdscr.nodelay(1)
    stdscr.keypad(1)

    reactor.addSystemEventTrigger('after','shutdown', cleanup_curses, stdscr)


    # first lets sort out logging in
    username = 'user'
    password = 'test'
    hostname = 'localhost'
    insecure = False
    port = 7531
    if options.username and options.password and options.hostname:
        username = options.username
        password = options.password
        hostname = options.hostname
        if options.port:
            try:
                port = int(options.port)
            except ValueError:
                pass
        if options.insecure:
            insecure = True
        connection.connect_to_manager(stdscr, hostname, port, insecure, username, password)
                   
    else:
        # do greeter
        # get recent connections
        greeter = AdminTextGreeter(stdscr)
        reactor.addReader(greeter)
        greeter.show()
    
def main(args):
    parser = optparse.OptionParser()
    parser.add_option('-d', '--debug',
                      action="store", type="string", dest="debug",
                      help="set debug levels")
    parser.add_option('-v', '--verbose',
                      action="store_true", dest="verbose",
                      help="be verbose")
    parser.add_option('', '--version',
                      action="store_true", dest="version",
                      default=False,
                      help="show version information")
    parser.add_option('-u', '--username',
                      action="store", type="string", dest="username",
                      help="set username to connect to manager")
    parser.add_option('-P', '--password',
                      action="store", type="string", dest="password",
                      help="set password to connect to manager")
    parser.add_option('-H', '--hostname',
                      action="store", type="string", dest="hostname",
                      help="set hostname of manager to connect to")
    parser.add_option('-p', '--port',
                      action="store", type="string", dest="port",
                      help="set port of manager to connect to")
    parser.add_option('', '--insecure',
                      action="store_true", dest="insecure",
                      help="make insecure connection")
    
    options, args = parser.parse_args(args)

    if options.version:
        from flumotion.common import common
        print common.version("flumotion-admin-text")
        return 0

    if options.verbose:
        log.setFluDebug("*:3")

    if options.debug:
        log.setFluDebug(options.debug)


    _runInterface(options)
    
    reactor.run()
