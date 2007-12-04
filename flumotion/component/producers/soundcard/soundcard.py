# -*- Mode: Python; test-case-name:flumotion.test.test_soundcard -*-
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

import gst
import gst.interfaces

from twisted.internet import defer

from flumotion.component import feedcomponent
from flumotion.component.effects.volume import volume
from flumotion.common import messages
from flumotion.common.messages import N_
T_ = messages.gettexter('flumotion')

class Soundcard(feedcomponent.ParseLaunchComponent):
    def do_check(self):
        self.debug('running PyGTK/PyGST checks')
        from flumotion.component.producers import checks
        d1 = checks.checkTicket347()
        d2 = checks.checkTicket348()
        dl = defer.DeferredList([d1, d2])
        dl.addCallback(self._checkCallback)
        return dl

    def _checkCallback(self, results):
        for (state, result) in results:
            for m in result.messages:
                self.addMessage(m)

    def get_pipeline_string(self, properties):
        element = properties.get('source-element', 'alsasrc')
        device = properties.get('device', 'hw:0')
        rate = properties.get('rate', 44100)
        depth = properties.get('depth', 16)
        channels = properties.get('channels', 2)
        self.inputTrackLabel = properties.get('input-track', None)
        d = self._change_monitor.add(gst.STATE_CHANGE_NULL_TO_READY)
        d.addCallback(self._set_input_track, self.inputTrackLabel)
        # FIXME: we should find a way to figure out what the card supports,
        # so we can add in correct elements on the fly
        # just adding audioscale and audioconvert always makes the soundcard
        # open in 1000 Hz, mono
        caps = 'audio/x-raw-int,rate=(int)%d,depth=%d,channels=%d' % (
            rate, depth, channels)
        pipeline = "%s device=%s name=src ! %s ! " \
            "level name=volumelevel message=true" % (
            element, device, caps)
        self._srcelement = None
        return pipeline

    def configure_pipeline(self, pipeline, properties):
        # add volume effect
        comp_level = pipeline.get_by_name('volumelevel')
        allowVolumeSet = True
        if gst.pygst_version < (0, 10, 7):
            allowVolumeSet = False
            m = messages.Info(T_(
                N_("The soundcard volume cannot be changed with this version of the 'gst-python' library.\n")), id = 'mixer-track-setting')
            m.add(T_(N_("Please upgrade '%s' to version %s or later if you desire this functionality."),
                'gst-python', '0.10.7'))
            self.addMessage(m)

        vol = volume.Volume('inputVolume', comp_level, pipeline,
            allowIncrease=False, allowVolumeSet=allowVolumeSet)
        self.addEffect(vol)
        self._srcelement = pipeline.get_by_name("src")

    def _set_input_track(self, result, trackLabel=None):
        element = self._srcelement
        for track in element.list_tracks():
            if trackLabel != None:
                self.debug("Setting track %s to record", trackLabel)
                # some low-end sound cards require the Capture track to be
                # set to recording to get any sound, so set that track and
                # the input track we selected
                element.set_record(track,
                    (track.get_property("label") == trackLabel or
                     track.get_property("label") == "Capture"))

    def setVolume(self, value):
        if gst.pygst_version < (0, 10, 7):
            self.warning(
                "Cannot set volume on soundcards with gst-python < 0.10.7")
            return
        self.debug("Volume set to: %f", value)
        if self.inputTrackLabel and self._srcelement:
            element = self._srcelement
            volumeSet = False
            for track in element.list_tracks():
                if track.get_property("label") == self.inputTrackLabel:
                    volumeVals = tuple(int(value/1.0 *
                        track.get_property("max-volume"))
                        for _ in xrange(0, track.get_property("num-channels")))
                    element.set_volume(track, volumeVals)
                    volumeSet = True
                    break
            if not volumeSet:
                self.warning("could not find track %s", self.inputTrackLabel)
        else:
            self.warning("no input track selected, cannot set volume")

    def getVolume(self):
        if gst.pygst_version < (0, 10, 7):
            self.warning(
                "Cannot query volume on soundcards with gst-python < 0.10.7")
            return 1.0
        if self.inputTrackLabel and self._srcelement:
            element = self._srcelement
            for track in element.list_tracks():
                if track.get_property("label") == self.inputTrackLabel:
                    volumeVals = element.get_volume(track)
                    vol = 0
                    nchannels = track.get_property("num-channels")
                    for k in range(0, track.get_property("num-channels")):
                        vol = vol + (volumeVals[k] / nchannels)
                    self.debug("vol: %f max vol: %d", vol, track.get_property("max-volume"))
                    v = vol / float(track.get_property("max-volume"))
                    self.debug("v: %f", v)
                    return v
            self.warning("could not find track %s", self.inputTrackLabel)
        else:
            self.warning("no input track selected, cannot set volume")
        return 1.0

__version__ = "$Rev$"
