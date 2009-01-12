# -*- Mode: Python -*-
# vi:si:et:sw=4:sts=4:ts=4
#
# Flumotion - a streaming media server
# Copyright (C) 2006 Fluendo, S.L. (www.fluendo.com).
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

from flumotion.common import log

__version__ = "$Rev$"


class Plug(log.Loggable):
    """
    Base class for plugs. Provides an __init__ method that receives the
    plug args and sets them to the 'args' attribute.
    """

    def __init__(self, args):
        """
        @param args: The plug args
        @type args:  dict with keys 'socket', 'type', and 'properties'.
                     'properties' has the same format as component
                     properties.
        """
        self.args = args

    def getProperties(self):
        return self.args['properties']


class ComponentPlug(Plug):
    """
    Base class for plugs that live in a component. Subclasses can
    implement the start and stop vmethods, which will be called with the
    component as an argument.
    """

    def start(self, component):
        pass

    def stop(self, component):
        pass

    def restart(self, component):
        self.stop(component)
        self.start(component)


class ManagerPlug(Plug):
    """
    Base class for plugs that live in the manager. Subclasses can
    implement the start and stop vmethods, which will be called with the
    manager vishnu as an argument.
    """

    def start(self, vishnu):
        pass

    def stop(self, vishnu):
        pass

    def restart(self, vishnu):
        self.stop(vishnu)
        self.start(vishnu)


class ManagerExamplePlug(ManagerPlug):
    """
    Example implementation of the ManagerLifecyle socket, just prints
    things on the console. Pretty stupid!
    """

    def start(self, vishnu):
        info = vishnu.connectionInfo
        print ('started manager running on %s:%d (%s)'
               % (info['host'], info['port'],
                  info['using_ssl'] and 'with ssl' or 'without ssl'))

    def stop(self, vishnu):
        info = vishnu.connectionInfo
        print ('stopped manager running on %s:%d (%s)'
               % (info['host'], info['port'],
                  info['using_ssl'] and 'with ssl' or 'without ssl'))


class ComponentExamplePlug(ComponentPlug):
    """
    Example implementation of the ComponentLifecyle socket, just prints
    things on the console. Pretty stupid!
    """

    def start(self, component):
        print 'Component has been started'

    def stop(self, component):
        print 'Component is stopping'
