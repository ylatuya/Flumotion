#!/usr/bin/env python
#
# gst-python
# Copyright (C) 2005 Andy Wingo <wingo@pobox.com>
#
# This library is free software; you can redistribute it and/or
# modify it under the terms of the GNU Library General Public
# License as published by the Free Software Foundation; either
# version 2 of the License, or (at your option) any later version.
#
# This library is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# Library General Public License for more details.
#
# You should have received a copy of the GNU Library General Public
# License along with this library; if not, write to the
# Free Software Foundation, Inc., 59 Temple Place - Suite 330,
# Boston, MA 02111-1307, USA.


# A test more of gst-plugins than of gst-python.


import sys

import pygtk
pygtk.require('2.0')
import gtk
import gtk.gdk
import pango
import gobject

#import pygst
#pygst.require('0.10')
import gst

import debugslider

from twisted.internet import gtk2reactor
gtk2reactor.install(useGtk=False)
from twisted.internet import reactor


data = ("checkTVCard('/dev/video0')",
        "checkTVCard('/dev/video1')",
        "checkWebcam('/dev/video0')",
        "checkWebcam('/dev/video1')",
        "checkMixerTracks('alsasrc', 'hw:0')",
        "checkMixerTracks('osssrc', '/dev/dsp')",
        "check1394()")

def make_model():
    from flumotion.worker.checks import video

    m = gtk.ListStore(str, object)
    for s in data:
        i = m.append()
        m.set_value(i, 0, s)
        m.set_value(i, 1, eval('lambda: video.%s'%s, {'video': video}))
    return m


class Window(gtk.Window):
    def __init__(self):
        gtk.Window.__init__(self, gtk.WINDOW_TOPLEVEL)
        self.current_deferred = None
        self.prepare_ui()

    def prepare_ui(self):
        self.set_default_size(300, 400)
        self.set_title('Flumotion Check Checker')
        self.set_type_hint(gtk.gdk.WINDOW_TYPE_HINT_DIALOG)
        self.connect('delete-event', lambda *x: reactor.stop())
        self.set_border_width(18)
        b = gtk.VBox(False, 12)
        b.show()
        self.add(b)
        l = gtk.Label()
        l.set_markup('<big><b>Flumotion Check Checker</b></big>')
        l.show()
        b.pack_start(l, False, False, 6)
        l = gtk.Label('Choose a check to check.')
        l.show()
        b.pack_start(l, False, False, 0)
        sw = gtk.ScrolledWindow()
        sw.set_policy(gtk.POLICY_NEVER, gtk.POLICY_NEVER)
        sw.set_shadow_type(gtk.SHADOW_IN)
        sw.show()
        b.pack_start(sw, True, True, 6)
        tv = gtk.TreeView(make_model())
        tv.set_property('can-default', False)
        r = gtk.CellRendererText()
        r.set_property('xalign', 0.5)
        c = gtk.TreeViewColumn('System', r, text=0)
        tv.append_column(c)
        tv.set_headers_visible(False)
        tv.show()
        sw.add(tv)
        ds = debugslider.DebugSlider()
        ds.show()
        b.pack_start(ds, False, False, 0)
        bb = gtk.HButtonBox()
        bb.set_layout(gtk.BUTTONBOX_SPREAD)
        bb.show()
        b.pack_start(bb, False, False, 0)
        bu = gtk.Button(stock=gtk.STOCK_EXECUTE)
        bu.set_property('can-default', True)
        bu.set_focus_on_click(False)
        bu.show()
        bb.pack_start(bu, True, False, 0)
        bu.set_property('has-default', True)
        self.button = bu

        self.selection = tv.get_selection()

        tv.connect('row-activated', lambda *x: self.run_check())

        bu.connect('clicked', lambda *x: self.run_check())

    def error(self, message, secondary=None):
        m = gtk.MessageDialog(
            self,
            gtk.DIALOG_MODAL | gtk.DIALOG_DESTROY_WITH_PARENT,
            gtk.MESSAGE_ERROR,
            gtk.BUTTONS_OK,
            message)
        if secondary:
            m.format_secondary_text(secondary)
        m.run()
        m.destroy()

    def run_check(self):
        from twisted.internet.defer import Deferred

        m, i = self.selection.get_selected()
        if not i:
            return
        name, proc = m.get(i, 0, 1)

        def callback(res, d):
            if d != self.current_deferred:
                print '(got successful old result: %s->%s)' % (name, res)
            else:
                print '%s successful: %s' % (name, res)

        def errback(res, d):
            if d != self.current_deferred:
                print '(got failing old result: %s->%s)' % (name, res)
            else:
                print '%s failed, reason: %s' % (name, res)

        print name
        d = proc()
        if isinstance(d, Deferred):
            self.current_deferred = d
            d.addCallback(callback, d)
            d.addErrback(errback, d)
        else:
            print 'Check %s returned immediately with result %s' % (name, s)

try:
    from flumotion.common import errors
    from flumotion.common import setup
    w = Window()
    w.show()
    setup.setup()
    reactor.run()

except KeyboardInterrupt:
    print 'Interrupted'
