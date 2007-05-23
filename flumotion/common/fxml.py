# -*- Mode: Python; test-case-name: flumotion.test.test_registry -*-
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

"""
Common routines to parsing XML.

Flumotion deals with two basic kinds of XML: config and registry. They
correspond to data and schema, more or less. This file defines some base
parsing routines shared between both kinds of XML.
"""

import sets

from xml.dom import minidom, Node
from xml.parsers import expat

from flumotion.common import log, common

class Box:
    """
    Object designed to wrap, or "box", any value. Useful mostly in the
    context of the table-driven XML parser, so that a handler that wants
    to set a scalar value can do so, getting around the limitations of
    Python's lexical scoping.
    """
    def __init__(self, val=None):
        self.set(val)

    def set(self, val):
        self.val = val

    def unbox(self):
        return self.val


class ParserError(Exception):
    """
    Error during parsing of XML.

    args[0]: str
    """

class Parser(log.Loggable):
    """
    XML parser base class.

    I add some helper functions for specialized XML parsers, mostly the
    parseFromTable method.

    I am here so that the config parser and the registry parser can
    share code.
    """
    
    parserError = ParserError

    def getRoot(self, file):
        """
        Return the root of the XML tree for the the string or filename
        passed as an argument. Raises fxml.ParserError if the XML could
        not be parsed.

        @param file: An open file object, or the name of a file. Note
        that if you pass a file object, this function will leave the
        file open.
        @type  file: File object; can be a duck file like StringIO.
        Alternately, the path of a file on disk.
        """
        self.debug('Parsing XML from %r', file)
        try:
            return minidom.parse(file)
        except expat.ExpatError, e:
            raise self.parserError('Error parsing XML from %r: %s' % (
                file, log.getExceptionMessage(e)))
        
    def checkAttributes(self, node, required=None, optional=None):
        """
        Checks that a given XML node has all of the required attributes,
        and no unknown attributes. Raises fxml.ParserError if unknown
        or missing attributes are detected. An empty attribute (e.g.
        'foo=""') is treated as a missing attribute.

        @param node: An XML DOM node.
        @type node: L{xml.dom.Node}
        @param required: Set of required attributes, or None.
        @type required: Sequence (list, tuple, ...) of strings.
        @param optional: Set of optional attributes, or None.
        @type optional: Sequence (list, tuple, ...) of strings.
        """
        attrs = sets.Set([k for k in node.attributes.keys()
                          if str(node.getAttribute(k))])
        required = sets.Set(required or ())
        optional = sets.Set(optional or ())
        for x in attrs - required.union(optional):
            raise self.parserError("Unknown attribute in <%s>: %s"
                                   % (node.nodeName, x))
        for x in required - attrs:
            raise self.parserError("Missing attribute in <%s>: %s"
                                   % (node.nodeName, x))

    def parseAttributes(self, node, required=None, optional=None):
        """
        Checks the validity of the attributes on an XML node, via
        Parser.checkAttributes, then parses them out and returns them
        all as a tuple.

        @param node: An XML DOM node.
        @type node: L{xml.dom.Node}
        @param required: Set of required attributes, or None.
        @type required: Sequence (list, tuple, ...) of strings.
        @param optional: Set of optional attributes, or None.
        @type optional: Sequence (list, tuple, ...) of strings.

        @returns: List of all attributes as a tuple. The first element
        of the returned tuple will be the value of the first required
        attribute, the second the value of the second required
        attribute, and so on. The optional attributes follow, with None
        as the value if the optional attribute was not present.
        @rtype: tuple of string or None, as long as the combined length
        of the required and optional attributes.
        """
        self.checkAttributes(node, required, optional)
        out = []
        for k in (required or ()) + (optional or ()):
            if node.hasAttribute(k):
                # expat always gives us unicode; we always want str
                a = node.getAttribute(k)
                if a:
                    out.append(str(a))
                else:
                    out.append(None)
            else:
                out.append(None)
        return out

    def parseFromTable(self, parent, parsers):
        """
        A data-driven verifying XML parser. Raises fxml.ParserError if
        an unexpected child node is encountered.

        @param parent: An XML node whose child nodes you are interested
        in parsing.
        @type parent: L{xml.dom.Node}
        @param parsers: A parse table defining how to parse the child
        nodes. The keys are the possible child nodes, and the value is a
        two-tuple of how to parse them consisting of a parser and a
        value handler. The parser is a one-argument function that will
        be called with the child node as an argument, and the handler is
        a one-argument function that will be called with the result of
        calling the parser.
        @type parsers: dict of string -> (function, function)
        """
        for child in parent.childNodes:
            if (child.nodeType == Node.TEXT_NODE or
                child.nodeType == Node.COMMENT_NODE):
                continue
            try:
                parser, handler = parsers[child.nodeName]
            except KeyError:
                raise self.parserError("unexpected node in <%s>: %s"
                                       % (parent.nodeName, child))
            handler(parser(child))

    def parseTextNode(self, node, type=str):
        """Parse a text-containing XML node.

        The node is expected to contain only text children. Recognized
        node types are L{xml.dom.Node.TEXT_NODE} and
        L{xml.dom.Node.CDATA_SECTION_NODE}.

        @param node: the node to parse
        @type  node: L{xml.dom.Node}
        @param type: a function to call on the resulting text
        @type  type: function of type unicode -> object

        @returns: The result of calling type on the unicode text. By
        default, type is L{str}.
        """
        ret = []
        for child in node.childNodes:
            if (child.nodeType == Node.TEXT_NODE
                or child.nodeType == Node.CDATA_SECTION_NODE):
                ret.append(child.data)
            elif child.nodeType == Node.COMMENT_NODE:
                continue
            else:
                raise ConfigError('unexpected non-text content of %r: %r'
                                  % (node, child))
        try:
            return type(''.join(ret))
        except Exception, e:
            raise ConfigError('failed to parse %s as %s: %s', node,
                              type, log.getExceptionMessage(e))
