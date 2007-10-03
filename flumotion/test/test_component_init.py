# -*- Mode: Python; test-case-name: flumotion.test.test_component_init -*-
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

from twisted.trial import unittest

import common


# test importing modules for every component in the registry

from flumotion.common import registry, log, reflectcall
from flumotion.job import job

class TestInit(unittest.TestCase):
    def testInit(self):
        r = registry.getRegistry()
        components = [c.getType() for c in r.getComponents()]
        for type in components:
            # skip test components - see test_config.py
            if type.startswith('test-'):
                continue
                
            log.debug('test', 'testing component type %s' % type)
            defs = r.getComponent(type)
            try:
                entry = defs.getEntryByType('component')
            except KeyError, e:
                self.fail(
                    'KeyError while trying to get component entry for %s' %
                        type)
            moduleName = defs.getSource()
            methodName = entry.getFunction()
            # call __init__ without the config arg; this will load
            # modules, get the entry point, then fail with too-few
            # arguments. would be nice to __init__ with the right
            # config, but that is component-specific...
            self.assertRaises(TypeError,
                              reflectcall.reflectCall,
                              moduleName, methodName)

if __name__ == '__main__':
    unittest.main()
