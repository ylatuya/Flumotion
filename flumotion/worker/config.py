# -*- Mode: Python; test-case-name: flumotion.test.test_workerconfig -*-
# vi:si:et:sw=4:sts=4:ts=4
#
# flumotion/worker/config.py: parse worker configuration files
#
# Flumotion - a streaming media server
# Copyright (C) 2004 Fluendo (www.fluendo.com)

# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
# See "LICENSE.GPL" in the source distribution for more information.

# This program is also licensed under the Flumotion license.
# See "LICENSE.Flumotion" in the source distribution for more information.

"""
Parsing of configuration files.
"""

import os
from xml.dom import minidom, Node
from xml.parsers import expat

from flumotion.common.registry import registry
from flumotion.common import log

class ConfigError(Exception):
    pass

class ConfigEntryManager:
    "I represent a <manager> entry in a worker config file"
    def __init__(self, host, port, transport):
        self.host = host
        self.port = port
        self.transport = transport

class ConfigEntryAuthentication:
    "I represent a <authentication> entry in a worker config file"
    def __init__(self, username, password):
        self.username = username
        self.password = password

class WorkerConfigXML(log.Loggable):
    logCategory = 'config'

    def __init__(self, filename, string=None):
        self.name = 'default'
        self.manager = None
        self.authentication = None

        try:
            if filename is not None:
                self.debug('Loading configuration file `%s\'' % filename)
                self.doc = minidom.parse(filename)
            else:
                self.doc = minidom.parseString(string)
        except expat.ExpatError, e:
            raise ConfigError("XML parser error: %s" % e)
        
        if filename is not None:
            self.path = os.path.split(filename)[0]
        else:
            self.path = None
            
        self.parse()
        
    def parse(self):
        # <worker name="default">
        #     <manager>
        #     <authentication>
        #     ...
        # </worker>

        root = self.doc.documentElement
        
        if not root.nodeName == 'worker':
            raise ConfigError("unexpected root node': %s" % root.nodeName)

        if root.hasAttribute('name'):
            self.name = str(root.getAttribute('name'))

        for node in root.childNodes:
            if (node.nodeType == Node.TEXT_NODE or
                node.nodeType == Node.COMMENT_NODE):
                continue
            if node.nodeName == 'manager':
                self.manager = self.parseManager(node)
            elif node.nodeName == 'authentication':
                self.authentication = self.parseAuthentication(node)
            else:
                raise ConfigError("unexpected node under '%s': %s" % (root.nodeName, node.nodeName))

    def parseManager(self, node):
        # <manager>
        #   <host>...</host>
        #   <port>...</port>
        #   <transport>...</transport>
        # </manager>

        host = None
        port = None
        transport = None
        for child in node.childNodes:
            if (child.nodeType == Node.TEXT_NODE or
                child.nodeType == Node.COMMENT_NODE):
                continue

            if child.nodeName == "host":
                host = str(child.firstChild.nodeValue)
            elif child.nodeName == "port":
                try:
                    port = int(child.firstChild.nodeValue)
                except ValueError:
                    raise ConfigError("<port> value must be an integer")
            elif child.nodeName == "transport":
                transport = str(child.firstChild.nodeValue)
                if not transport in ('tcp', 'ssl'):
                    raise ConfigError("<transport> must be ssl or tcp")
                    
            else:
                raise ConfigError("unexpected '%s' node: %s" % (node.nodeName, child.nodeName))

        return ConfigEntryManager(host, port, transport)
     
    def parseAuthentication(self, node):
        # <authentication>
        #   <username>...</username>
        #   <password>...</password>
        # </authentication>

        username = None
        password = None
        for child in node.childNodes:
            if (child.nodeType == Node.TEXT_NODE or
                child.nodeType == Node.COMMENT_NODE):
                continue

            if child.nodeName == "username":
                username = str(child.firstChild.nodeValue)
            elif child.nodeName == "password":
                password = str(child.firstChild.nodeValue)
            else:
                raise ConfigError("unexpected '%s' node: %s" % (node.nodeName, child.nodeName))

        return ConfigEntryAuthentication(username, password)

