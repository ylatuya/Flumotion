# -*- Mode: Python -*-
# vi:si:et:sw=4:sts=4:ts=4
#
# flumotion/component/base/converter.py: base Converter class
#
# Flumotion - a streaming media server
# Copyright (C) 2004 Fluendo, S.L. (www.fluendo.com). All rights reserved.

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

from flumotion.component import feedcomponent

__all__ = ['Converter']

class Converter(feedcomponent.ParseLaunchComponent):
    logCategory = 'conv-pipe'

def createComponent(config):
    name = config['name']
    feeders = config.get('feed', ['default'])
    eaters = config.get('source', [])
    pipeline = config['pipeline']

    component = Converter(name, eaters, feeders, pipeline)

    return component
