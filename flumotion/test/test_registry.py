# -*- Mode: Python; test-case-name: flumotion.test.test_registry -*-
# vi:si:et:sw=4:sts=4:ts=4
#
# Flumotion - a streaming media server
# Copyright (C) 2004,2005,2006 Fluendo, S.L. (www.fluendo.com).
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

import common
from twisted.trial import unittest

import os
import warnings
import tempfile
warnings.filterwarnings('ignore', category=FutureWarning)

from flumotion.common import registry, fxml, common

class TestRegistry(unittest.TestCase):
    def setUp(self):
        self.reg = registry.ComponentRegistry()
        self.reg.clean()
        
    def testDefault(self):
        self.failUnless(hasattr(registry, 'getRegistry'))
        reg = registry.getRegistry()
        self.failUnless(isinstance(reg, registry.ComponentRegistry))
        
    def testIsTrue(self):
        self.failUnless(common.strToBool('True'))
        self.failUnless(common.strToBool('true'))
        self.failUnless(common.strToBool('1'))
        self.failUnless(common.strToBool('yes'))
        self.failIf(common.strToBool('False') )
        self.failIf(common.strToBool('false') )
        self.failIf(common.strToBool('0') )
        self.failIf(common.strToBool('no') )
        self.failIf(common.strToBool('I am a monkey') )

    def testgetMTime(self):
        mtime = registry._getMTime(__file__)
        self.failUnless(mtime)
        self.failUnless(isinstance(mtime, int))
        
    def testParseBasic(self):
        self.failUnless(self.reg.isEmpty())
        self.reg.addFromString('<root></root>')
        self.failUnless(self.reg.isEmpty())
        self.reg.addFromString('<registry><components></components></registry>')
        self.failUnless(self.reg.isEmpty())
        
    def testParseComponents(self):
        self.failUnless(self.reg.isEmpty())
        self.reg.addFromString("""
<registry>
  <components>
    <component type="bar">
    </component>
    <component type="baz">
    </component>
  </components>
</registry>""")

        self.failIf(self.reg.isEmpty())
        
        self.failUnless(self.reg.hasComponent('bar'))
        comp1 = self.reg.getComponent('bar')
        self.failUnless(isinstance(comp1, registry.RegistryEntryComponent))

        self.failUnless(self.reg.hasComponent('baz'))
        comp2 = self.reg.getComponent('baz')
        self.failUnless(isinstance(comp2, registry.RegistryEntryComponent))

        comps = self.reg.getComponents()
        comps.sort()
        self.assertEquals(len(comps), 2)
        self.failUnless(comp1 in comps)
        self.failUnless(comp2 in comps)
        
    def testParseComponentProperties(self):
        self.failUnless(self.reg.isEmpty())
        self.reg.addFromString("""
<registry>
  <components>
    <component type="component">
      <properties>
        <property name="source" type="string" required="yes" multiple="yes" description="a source property" />
      </properties>
    </component>
  </components>
</registry>""")

        comp = self.reg.getComponent('component')
        props = comp.getProperties()
        self.failUnless(props)
        self.assertEquals(len(props), 1)
        prop = props[0]
        self.assertEquals(prop.getName(), 'source')
        self.assertEquals(prop.getType(), 'string')
        self.assertEquals(prop.getDescription(), 'a source property')
        self.failUnless(prop.isRequired())
        self.failUnless(prop.isMultiple())

    def testParseComponentPropertiesErrors(self):
        template = """
<registry>
  <components>
    <component type="component">
      <properties>
        %s
      </properties>
    </component>
  </components>
</registry>"""

        property = "<base-name/>"
        self.assertRaises(fxml.ParserError,
                          self.reg.addFromString, template % property)

        property = '<property without-name=""/>'
        self.assertRaises(fxml.ParserError,
                          self.reg.addFromString, template % property)

        property = '<property name="bar" without-type=""/>'
        self.assertRaises(fxml.ParserError,
                          self.reg.addFromString, template % property)

    def testClean(self):
        xml = """
<registry>
  <components>
    <component type="bar">
    </component>
  </components>
</registry>"""
        reg = registry.ComponentRegistry()
        reg.addFromString(xml)
        reg.clean()
        self.failUnless(reg.isEmpty())

    def testComponentTypeError(self):
        reg = registry.ComponentRegistry()
        xml = """
<registry>
  <components>
    <component type="bar"></component>
  </components>
</registry>"""
        reg.addFromString(xml) 
       
    def testAddXmlParseError(self):
        reg = registry.ComponentRegistry()
        xml = """
<registry>
  <components>
    <component></component>
  </components>
</registry>"""
        self.assertRaises(fxml.ParserError, reg.addFromString, xml)
        xml = """<registry><components><foo></foo></components></registry>"""
        self.assertRaises(fxml.ParserError, reg.addFromString, xml)
        
    # addFromString does not parse <directory> toplevel entries since they
    # should not be in partial registry files
    def testDump(self):
        xml = """
<registry>
  <components>
    <component type="bar" base="base/dir"
               description="A bar component.">
      <entries>
        <entry type="test/test" location="loc" function="main"/>
      </entries>
    </component>
  </components>
  <plugs>
    <plug type="baz" socket="frogger">
      <entry location="loc" function="main"/>
      <properties>
        <property name="qux" type="string" description="a quxy property"/>
      </properties>
    </plug>
  </plugs>
  <bundles>
    <bundle name="test-bundle">
      <dependencies>
        <dependency name="test-dependency"/>
      </dependencies>
      <directories>
        <directory name="/tmp">
          <filename location="loc" relative="lob"/>
        </directory>
        <directory name="foobie">
          <filename location="barie"/>
        </directory>
      </directories>
    </bundle>
  </bundles>
</registry>"""
        reg = registry.ComponentRegistry()
        reg.clean()
        reg.addFromString(xml)
        import sys, StringIO
        s = StringIO.StringIO()
        reg.dump(s)
        s.seek(0, 0)
        data = s.read()
        target = """<registry>

  <components>

    <component type="bar" base="base/dir"
               description="A bar component.">
      <source location="None"/>
      <synchronization required="no" clock-priority="100"/>
      <properties>
      </properties>
      <entries>
        <entry type="test/test" location="loc" function="main"/>
      </entries>
    </component>

  </components>

  <plugs>

    <plug type="baz" socket="frogger">
      <entry location="loc" function="main"/>
      <properties>
        <property name="qux" type="string"
                  description="a quxy property"
                  required="False" multiple="False"/>
      </properties>
    </plug>

  </plugs>

  <bundles>
    <bundle name="test-bundle" under="pythondir" project="flumotion">
      <dependencies>
        <dependency name="test-dependency"/>
      </dependencies>
      <directories>
        <directory name="/tmp">
          <filename location="loc" relative="lob"/>
        </directory>
        <directory name="foobie">
          <filename location="barie" relative="foobie/barie"/>
        </directory>
      </directories>
    </bundle>

  </bundles>
</registry>
"""
        datalines = data.split("\n")
        targetlines = target.split("\n")
        datalines.reverse()
        targetlines.reverse()
        i = 0
        while targetlines:
            i = i + 1
            d = datalines.pop()
            t = targetlines.pop()
            self.assertEquals(t, d, "line %d: '%s' != expected '%s'" % (
                i, d, t))
            
class TestComponentEntry(unittest.TestCase):
    def setUp(self):
        self.file = registry.RegistryEntryFile('gui-filename', 'type')
        rec = registry.RegistryEntryComponent
        self.entry = rec('filename', 'type', 'source', 'description', 'base', 
                         ['prop'], [self.file], {}, [], [], False, 100, [])
        self.empty_entry = rec('filename', 'type', 'source', 'description', 'base',
                               ['prop'], [], {}, [], [], True, 130, [])
        self.multiple_entry = rec('filename', 'type', 'source', 'description', 'base', ['prop'],
                                  [self.file, self.file], {}, [], [],
                                  False, 100, [])

    def testThings(self):
        self.assertEquals(self.entry.getType(), 'type')
        self.assertEquals(self.entry.getSource(), 'source')
        self.assertEquals(self.entry.getFiles(), [self.file])
        self.assertEquals(self.entry.getGUIEntry(), 'gui-filename')
        self.assertEquals(self.empty_entry.getGUIEntry(), None)
        self.assertEquals(self.multiple_entry.getGUIEntry(), None)
        self.assertEquals(self.empty_entry.getNeedsSynchronization(), True) 
        self.assertEquals(self.empty_entry.getClockPriority(), 130)
        self.assertEquals(self.multiple_entry.getNeedsSynchronization(), False)
        self.assertEquals(self.multiple_entry.getClockPriority(), 100)
        self.assertEquals(self.multiple_entry.getSockets(), [])

def rmdir(root):
    for file in os.listdir(root):
        filename = os.path.join(root, file)
        if os.path.isdir(filename):
            rmdir(filename)
        else:
            os.remove(filename)
    os.rmdir(root)
            
class TestFindComponents(unittest.TestCase):
    def setUp(self):
        self.reg = registry.ComponentRegistry()
        self.reg.clean()

        # override the registry's filename so make distcheck works
        fd, self.reg.filename = tempfile.mkstemp()
        os.close(fd)
        os.unlink(self.reg.filename)

        self.tempdir = tempfile.mkdtemp()
        self.cwd = os.getcwd()
        os.chdir(self.tempdir) 
        os.makedirs('subdir')
        os.makedirs('subdir/foo')
        os.makedirs('subdir/bar')
        self.writeComponent('subdir/first.xml', 'first')
        self.writeComponent('subdir/foo/second.xml', 'second')
        self.writeComponent('subdir/bar/third.xml', 'third')

    def tearDown(self):
        rmdir('subdir')
        os.chdir(self.cwd)
        self.reg.clean()
        rmdir(self.tempdir)

        if os.path.exists(self.reg.filename):
            os.unlink(self.reg.filename)

    def writeComponent(self, filename, name):
        open(filename, 'w').write("""
<registry>
  <components>
    <component type="%s">
      <properties>
      </properties>
    </component>
  </components>
</registry>""" % name)
    
    def testSimple(self):
        self.reg.addRegistryPath('.', prefix='subdir')
        components = self.reg.getComponents()
        self.assertEquals(len(components), 3)
        types = [c.getType() for c in components]
        types.sort()
        self.assertEquals(types, ['first', 'second', 'third']) # alpha order
