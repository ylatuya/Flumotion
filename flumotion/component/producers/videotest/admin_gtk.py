# -*- Mode: Python -*-
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

from gettext import gettext as _

import gtk

from twisted.internet import defer

from flumotion.common import errors
from flumotion.component.base.admin_gtk import BaseAdminGtk, BaseAdminGtkNode
from flumotion.ui import fgtk
from flumotion.wizard import enums

class PatternNode(BaseAdminGtkNode):
    uiStateHandlers = None

    def render(self):
        # FIXME: gladify
        self.widget = gtk.Table(1, 2)
        label = gtk.Label(_("Pattern:"))
        self.widget.attach(label, 0, 1, 0, 1, 0, 0, 6, 6)
        label.show()
        self.combobox_pattern = fgtk.FComboBox()
        self.combobox_pattern.set_enum(enums.VideoTestPattern)
        self.pattern_changed_id = self.combobox_pattern.connect('changed',
            self.cb_pattern_changed)
        self.widget.attach(self.combobox_pattern, 1, 2, 0, 1, 0, 0, 6, 6)
        self.combobox_pattern.show()
        return BaseAdminGtkNode.render(self)

    def setUIState(self, state):
        BaseAdminGtkNode.setUIState(self, state)
        if not self.uiStateHandlers:
            self.uiStateHandlers = {'pattern': self.patternSet}
        for k, handler in self.uiStateHandlers.items():
            handler(state.get(k))

    def cb_pattern_changed(self, combobox):
        def _setPatternErrback(failure):
            self.warning("Failure %s setting pattern: %s" % (
                failure.type, failure.getErrorMessage()))
            return None

        pattern = combobox.get_value()
        d = self.callRemote("setElementProperty", "source", "pattern", pattern)
        d.addErrback(_setPatternErrback)

    def patternSet(self, value):
        self.debug("pattern changed to %r" % value)
        c = self.combobox_pattern
        id = self.pattern_changed_id
        c.handler_block(id)
        c.set_active(value)
        c.handler_unblock(id)

    def stateSet(self, state, key, value):
        handler = self.uiStateHandlers.get(key, None)
        if handler:
            handler(value)

class VideoTestAdminGtk(BaseAdminGtk):
    def setup(self):
        # FIXME: have constructor take self instead ?
        pattern = PatternNode(self.state, self.admin, title=_("Pattern"))
        self.nodes['Pattern'] = pattern
        return BaseAdminGtk.setup(self)

GUIClass = VideoTestAdminGtk
