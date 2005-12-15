# -*- Mode: Python -*-
# vi:si:et:sw=4:sts=4:ts=4
#
# Flumotion - a streaming media server
# Copyright (C) 2004,2005 Fluendo, S.L. (www.fluendo.com). All rights reserved.

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


from flumotion.twisted.defer import defer_generator
from flumotion.admin.command import utils


__all__ = ['commands']


# it's probably time to move this stuff into classes...

# command-list := (command-spec, command-spec...)
# command-spec := (command-name, command-desc, arguments, command-proc)
# command-name := str
# command-desc := str
# command-proc := f(model, quit, *args) -> None
# arguments := (arg-spec, arg-spec...)
# arg-spec := (arg-name, arg-parser)
# arg-name := str
# arg-parser := f(x) -> Python value or exception


def do_getprop(model, quit, avatarId, propname):
    d = utils.get_component_uistate(model, avatarId)
    yield d
    uistate = d.value()
    if uistate:
        if uistate.hasKey(propname):
            print uistate.get(propname)
        else:
            print ('Component %s in flow %s has no property called %s'
                   % (avatarId[1], avatarId[0], propname))
    quit()
do_getprop = defer_generator(do_getprop)

def do_listprops(model, quit, avatarId):
    d = utils.get_component_uistate(model, avatarId)
    yield d
    uistate = d.value()
    if uistate:
        for k in uistate.keys():
            print k
    quit()
do_listprops = defer_generator(do_listprops)

commands = (('getprop',
             'gets a property on a component',
             (('component-path', utils.avatarId),
              ('property-name', str)),
             do_getprop),
            ('listprops',
             'lists the properties a component has',
             (('component-path', utils.avatarId),
              ),
             do_listprops),
            )

