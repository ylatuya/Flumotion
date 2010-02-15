# -*- Mode: Python; test-case-name: flumotion.test.test_component_providers -*-
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

from flumotion.component.misc.httpserver import fileprovider
from flumotion.component.misc.httpserver import mimetypes
from flumotion.component.misc.httpserver.fileprovider import InsecureError
from flumotion.component.misc.httpserver.fileprovider import NotFoundError


class LocalPath(fileprovider.FilePath):

    contentTypes = mimetypes.MimeTypes()

    # Override parent class property by an attribute
    mimeType = None

    def __init__(self, path):
        self._path = path
        self.mimeType = self.contentTypes.fromPath(path)

    def __str__(self):
        return "<%s '%s'>" % (type(self).__name__, self._path)

    def child(self, name):
        childpath = self._getChildPath(name)
        return type(self)(childpath)

    def open(self):
        raise NotImplementedError()


    ## Protected Methods ##

    def _getChildPath(self, name):
        """
        @param name: the name of a child of the pointed directory
        @type  name: str

        @return: the path of the child
        @rtype:  str
        @raises InsecureError: if the specified name compromise security
        """
        norm = os.path.normpath(name)
        if os.sep in norm:
            raise InsecureError("Child name '%s' contains one or more "
                                "directory separators" % (name, ))
        childpath = os.path.abspath(os.path.join(self._path, norm))
        if not childpath.startswith(self._path):
            raise InsecureError("Path '%s' is not a child of '%s'"
                                % (childpath, self._path))
        return childpath
