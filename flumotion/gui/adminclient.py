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

import os
import sys

import gobject
import gst
from gtk import gdk
import gtk
import gtk.glade
from twisted.internet import reactor

from flumotion import config
from flumotion.gui.admininterface import AdminInterface
from flumotion.server import admin   # Register types
from flumotion.twisted import errors
from flumotion.utils import log

COL_PIXBUF = 0
COL_TEXT   = 1

RESPONSE_FETCH = 0

class PropertyChangeDialog(gtk.Dialog):
    __gsignals__ = {
        'set': (gobject.SIGNAL_RUN_FIRST, None, (str, str, object)),
        'get': (gobject.SIGNAL_RUN_FIRST, None, (str, str)),
    }
    def __init__(self, name, parent):
        title = "Change element property on '%s'" % name
        dialog = gtk.Dialog.__init__(self, title, parent,
                            gtk.DIALOG_MODAL | gtk.DIALOG_DESTROY_WITH_PARENT)
        self.connect('response', self.response_cb)
        self.add_button('Close', gtk.RESPONSE_CLOSE)
        self.add_button('Set', gtk.RESPONSE_APPLY)
        self.add_button('Fetch current', RESPONSE_FETCH)

        hbox = gtk.HBox()
        hbox.show()
        
        label = gtk.Label('Element')
        label.show()
        hbox.pack_start(label, False, False)
        self.element_entry = gtk.Entry()
        self.element_entry.show()
        hbox.pack_start(self.element_entry, False, False)

        label = gtk.Label('Property')
        label.show()
        hbox.pack_start(label, False, False)
        self.property_entry = gtk.Entry()
        self.property_entry.show()
        hbox.pack_start(self.property_entry, False, False)
        
        label = gtk.Label('Value')
        label.show()
        hbox.pack_start(label, False, False)
        self.value_entry = gtk.Entry()
        self.value_entry.show()
        hbox.pack_start(self.value_entry, False, False)

        self.vbox.pack_start(hbox)
        
    def response_cb(self, dialog, response):
        if response == gtk.RESPONSE_APPLY:
            element = self.element_entry.get_text()
            property = self.property_entry.get_text()
            value = self.value_entry.get_text()
            self.emit('set', element, property, value)
        elif response == RESPONSE_FETCH:
            element = self.element_entry.get_text()
            property = self.property_entry.get_text()

            self.emit('get', element, property)
        elif response == gtk.RESPONSE_CLOSE:
            dialog.destroy()

    def update_value_entry(self, value):
        self.value_entry.set_text(str(value))
    
gobject.type_register(PropertyChangeDialog)

class Window(log.Loggable):
    '''
    Creates the GtkWindow for the user interface.
    Also connects to the controller on the given host and port.
    '''
    def __init__(self, host, port):
        self.gladedir = config.gladedir
        self.imagedir = config.imagedir
        self.connect(host, port)
        self.create_ui()
        
    def create_ui(self):
        wtree = gtk.glade.XML(os.path.join(self.gladedir, 'admin.glade'))
        self.window = wtree.get_widget('main_window')
        iconfile = os.path.join(self.imagedir, 'fluendo.png')
        gtk.window_set_default_icon_from_file(iconfile)
        self.window.set_icon_from_file(iconfile)
        
        self.hpaned = wtree.get_widget('hpaned')
        self.window.connect('delete-event', self.close)
        self.window.show_all()
        
        self.component_model = gtk.ListStore(gdk.Pixbuf, str)
        self.component_view = wtree.get_widget('component_view')
        self.component_view.connect('row-activated',
                                    self.component_view_row_activated_cb)
        self.component_view.set_model(self.component_model)
        self.component_view.set_headers_visible(True)

        col = gtk.TreeViewColumn(' ', gtk.CellRendererPixbuf(),
                                 pixbuf=COL_PIXBUF)
        self.component_view.append_column(col)

        col = gtk.TreeViewColumn('Component', gtk.CellRendererText(),
                                 text=COL_TEXT)
        self.component_view.append_column(col)
        
        wtree.signal_autoconnect(self)

    def get_selected_component(self):
        selection = self.component_view.get_selection()
        sel = selection.get_selected()
        if not sel:
            return
        model, iter = sel
        return model.get(iter, COL_TEXT)[0]

    def show_component(self, name, data):
        sub = None
        if data:
            namespace = {}
            exec (data, globals(), namespace)
            klass = namespace.get('GUIClass')

            if klass:
                instance = klass(name, self.admin)
                sub = instance.render()

        old = self.hpaned.get_child2()
        self.hpaned.remove(old)
        
        if not sub:
            sub = gtk.Label('%s does not have a UI yet' % name)
            
        self.hpaned.add2(sub)
        sub.show()
        
    def component_view_row_activated_cb(self, *args):
        name = self.get_selected_component()

        if not name:
            self.warning('Select a component')
            return

        def cb_gotUI(data):
            self.show_component(name, data)
            
        cb = self.admin.getUIEntry(name)
        cb.addCallback(cb_gotUI)

    def error_dialog(self, message, parent=None):
        """
        Show an error message dialog.
        """
        if not parent:
            parent = self.window
        d = gtk.MessageDialog(parent, gtk.DIALOG_MODAL, gtk.MESSAGE_ERROR,
            gtk.BUTTONS_OK, message)
        d.connect("response", lambda self, response: self.destroy())
        d.show_all()

    def admin_connected_cb(self, admin):
        self.update(admin.clients)

    def admin_update_cb(self, admin, clients):
        self.update(clients)

    def admin_connection_refused_later(self, host, port):
        message = "Connection to controller on %s:%d was refused." % (host, port)
        d = self.error_dialog(message)
        d.run()
        self.close()

    def admin_connection_refused_cb(self, admin, host, port):
        log.debug('adminclient', "handling connection-refused")
        reactor.callLater(0, self.admin_connection_refused_later, host, port)
        log.debug('adminclient', "handled connection-refused")

    def connect(self, host, port):
        'connect to controller on given host and port.  Called by __init__'
        self.admin = AdminInterface()
        self.admin.connect('connected', self.admin_connected_cb)
        self.admin.connect('update', self.admin_update_cb)
        self.admin.connect('connection-refused',
                           self.admin_connection_refused_cb, host, port)
        reactor.connectTCP(host, port, self.admin.factory)
        
    def update(self, orig_clients):
        model = self.component_model
        model.clear()

        # Make a copy
        clients = orig_clients[:]
        clients.sort()
        
        for client in clients:
            iter = model.append()
            #model.set(iter, 0, client.name)
            model.set(iter, 1, client.name)
            #model.set(iter, 1, client.options['pid'])
            #model.set(iter, 2, gst.element_state_get_name(client.state))
            #model.set(iter, 3, client.options['ip'])

    def close(self, *args):
        reactor.stop()

    # menubar/toolbar callbacks
    def file_open_cb(self, button):
        raise NotImplementedError
    
    def file_save_cb(self, button):
        raise NotImplementedError

    def file_quit_cb(self, button):
        self.close()

    def edit_properties_cb(self, button):
        raise NotImplementedError

    def debug_reload_controller_cb(self, button):
        cb = self.admin.reloadController()

    def debug_reload_all_cb(self, button):
        cb = self.admin.reload()
 
    def debug_modify_cb(self, button):
        name = self.get_selected_component()
        if not name:
            self.warning('Select a component')
            return

        def propertyErrback(failure):
            failure.trap(errors.PropertyError)
            self.error_dialog("%s." % failure.getErrorMessage())
            return None

        def after_getProperty(value, dialog):
            print 'got value', value
            dialog.update_value_entry(value)
            
        def dialog_set_cb(dialog, element, property, value):
            cb = self.admin.setProperty(name, element, property, value)
            cb.addErrback(propertyErrback)
        def dialog_get_cb(dialog, element, property):
            cb = self.admin.getProperty(name, element, property)
            cb.addCallback(after_getProperty, dialog)
            cb.addErrback(propertyErrback)
        
        d = PropertyChangeDialog(name, self.window)
        d.connect('get', dialog_get_cb)
        d.connect('set', dialog_set_cb)
        d.run()

    def help_about_cb(self, button):
        raise NotImplemenedError
    
def main(args):
    try:
        host = args[1]
        port = int(args[2])
    except IndexError:
        print "Please specify a host and a port number"
        sys.exit(1)

    win = Window(host, port)
    reactor.run()
    
if __name__ == '__main__':
    sys.exit(main(sys.argv))
