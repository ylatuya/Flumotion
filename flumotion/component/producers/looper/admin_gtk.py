# -*- Mode: Python -*-
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

__version__ = "$Rev$"

from gettext import gettext as _

import os
import gst
from twisted.internet import defer

from flumotion.common import errors

from flumotion.component.base.admin_gtk import BaseAdminGtk, BaseAdminGtkNode

from flumotion.ui.glade import GladeWidget

def time_to_string(value):
    sec = value / gst.SECOND
    mins = sec / 60
    sec = sec % 60
    hours = mins / 60
    mins = mins % 60
    return "%02d:%02d:%02d" % (hours, mins, sec)


class FileInfo(GladeWidget):
    glade_file = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                              'flufileinfo.glade')
    duration = 0

    def set_location(self, location):
        self.locationlabel.set_text(location)

    def set_duration(self, duration):
        self.duration = duration
        self.timelabel.set_text(time_to_string(duration))

    def set_audio(self, audio):
        self.audiolabel.set_markup(audio or "<i>No audio</i>")

    def set_video(self, video):
        self.videolabel.set_markup(video or "<i>No video</i>")

class LooperNode(BaseAdminGtkNode):
    logCategory = 'looper'

    uiStateHandlers = None
    glade_file = os.path.join('flumotion', 'component', 'producers',
                              'looper', 'looper.glade')

    def haveWidgetTree(self):
        self.widget = self.wtree.get_widget('looper-widget')
        self.fileinfowidget = self.wtree.get_widget('fileinfowidget')
        self.numiterlabel = self.wtree.get_widget('iterationslabel')
        self.curposlabel = self.wtree.get_widget('curposlabel')
        self.positionbar = self.wtree.get_widget('positionbar')
        self.restartbutton = self.wtree.get_widget('restartbutton')
        self.restartbutton.set_sensitive(False)

    def setUIState(self, state):
        BaseAdminGtkNode.setUIState(self, state)
        if not self.uiStateHandlers:
            self.uiStateHandlers = {'info-duration':
                                    self.fileinfowidget.set_duration,
                                    'info-location':
                                    self.fileinfowidget.set_location,
                                    'info-audio':
                                    self.fileinfowidget.set_audio,
                                    'info-video':
                                    self.fileinfowidget.set_video,
                                    'position': self.positionSet,
                                    'num-iterations': self.numIterationsSet}
        for k, handler in self.uiStateHandlers.items():
            handler(state.get(k))

    def positionSet(self, newposition):
        self.log("got new position : %d" % newposition)
        if self.fileinfowidget.duration:
            percent = float(newposition % self.fileinfowidget.duration) / float(self.fileinfowidget.duration)
            self.positionbar.set_fraction(percent)
            self.positionbar.set_text(time_to_string(newposition % self.fileinfowidget.duration))

    def numIterationsSet(self, numIterations):
        self.numiterlabel.set_text(str(numIterations))

    def _restart_callback(self, result):
        pass

    def _restart_failed(self, failure):
        self.warning("Failure %s getting pattern: %s" % (
            failure.type, failure.getErrorMessage()))
        return None

    def _reset_button_clicked(self, button):
        d = self.callRemote("gimme5", "ooooh yeah")
        d.addCallback(self._restart_callback)
        d.addErrback(self._restart_failed)

    def stateSet(self, state, key, value):
        handler = self.uiStateHandlers.get(key, None)
        if handler:
            handler(value)

class LooperAdminGtk(BaseAdminGtk):
    def setup(self):
        looper = LooperNode(self.state, self.admin, title=_("Looper"))
        self.nodes['Looper'] = looper

        return BaseAdminGtk.setup(self)

GUIClass = LooperAdminGtk
