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
# Foundation, Inc., 675 Mass Ave, Cambridge, MA 02139, USA.

from flumotion.server import component

class Converter(component.ParseLaunchComponent):
    kind = 'converter'

    def start(self, sources, feeds):
        self.setup_sources(sources)
        self.setup_feeds(feeds)
        
        self.pipeline_play()

    remote_start = start

def createComponent(config):
    name = config['name']
    feeds = config.get('feeds', [])
    sources = config.get('sources', [])
    pipeline = config['pipeline']

    # XXX: How can we do this properly?
    Converter.kind = config['kind']
    
    component = Converter(name, sources, feeds, pipeline)

    return component
