# -*- Mode: Python -*-
# vi:si:et:sw=4:sts=4:ts=4

# Flumotion - a video streaming server
# Copyright (C) 2004 Fluendo
# 
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
# 
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Street #330, Boston, MA 02111-1307, USA.

from flumotion.server import component

__all__ = ['Producer']

class Producer(component.ParseLaunchComponent):
    def __init__(self, name, feeds, pipeline):
        component.ParseLaunchComponent.__init__(self, name, [],
                                                feeds, pipeline)

def createComponent(config):
    name = config['name']
    feeds = config.get('feed', ['default'])
    pipeline = config['pipeline']

    component = Producer(name, feeds, pipeline)

    return component

    
