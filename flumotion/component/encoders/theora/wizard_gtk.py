# -*- Mode: Python -*-
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

import gettext
import os

from zope.interface import implements

from flumotion.common.fraction import fractionAsFloat
from flumotion.wizard.basesteps import VideoEncoderStep
from flumotion.wizard.interfaces import IEncoderPlugin
from flumotion.wizard.models import VideoEncoder

__version__ = "$Rev$"
_ = gettext.gettext


class TheoraVideoEncoder(VideoEncoder):
    """
    @ivar framerate: number of frames per second; to be set by view
    @type framerate: float
    """
    componentType = 'theora-encoder'

    def __init__(self):
        super(TheoraVideoEncoder, self).__init__()
        self.has_quality = True
        self.has_bitrate = False
        self.framerate = 25.0

        self.properties.noise_sensitivity = 0
        self.properties.keyframe_delta = 2.0
        self.properties.bitrate = 400
        self.properties.quality = 16
        self.properties.sharpness = 0

    def getProperties(self):
        properties = super(TheoraVideoEncoder, self).getProperties()
        if self.has_bitrate:
            del properties.quality
            properties.bitrate *= 1000
        elif self.has_quality:
            del properties.bitrate
        else:
            raise AssertionError

        properties.noise_sensitivity = max(
            int(properties.noise_sensitivity * (32768 / 100.)),  1)

        # convert the human-friendly delta to maxdistance
        # FIXME: I think the theora-encoder component should not expose
        # the theora element properties directly, but just have keyframe-delta
        # directly and calculate GStreamer element properties. But that's a
        # property change.
        properties.keyframe_maxdistance = int(properties.keyframe_delta *
            self.framerate)
        del properties.keyframe_delta

        self.debug('keyframe_maxdistance: %r',
            properties.keyframe_maxdistance)

        return properties


class TheoraStep(VideoEncoderStep):
    name = _('Theora encoder')
    sidebarName = _('Theora')
    gladeFile = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                              'wizard.glade')
    componentType = 'theora'
    icon = 'xiphfish.png'

    # WizardStep

    def setup(self):
        self.bitrate.data_type = int
        self.quality.data_type = int
        self.noise_sensitivity.data_type = int
        self.keyframe_delta.data_type = float
        self.sharpness.data_type = int
        self.has_quality.data_type = bool
        self.has_bitrate.data_type = bool

        self.add_proxy(self.model,
                       ['has_quality', 'has_bitrate'])
        self.add_proxy(self.model.properties,
                       ['bitrate', 'quality', 'keyframe_delta',
                        'noise_sensitivity', 'sharpness'])

        # we specify keyframe_delta in seconds, but theora expects
        # a number of frames, so we need the framerate and calculate
        # we need to go through the Step (which is the view) because models
        # don't have references to other models
        producer = self.wizard.getStep('Production').getVideoProducer()
        self.model.framerate = fractionAsFloat(producer.getFramerate())
        self.debug('Framerate of video producer: %r' % self.model.framerate)
        step = 1 / self.model.framerate
        page = 1.0
        self.keyframe_delta.set_increments(step, page)

    def workerChanged(self, worker):
        self.model.worker = worker

        def hasTheora(unused, worker):
            self.wizard.runInWorker(
                worker, 'flumotion.worker.checks.encoder', 'checkTheora')

        self.wizard.debug('running Theora checks')
        d = self.wizard.requireElements(worker, 'theoraenc')
        d.addCallback(hasTheora, worker)

    # Callbacks

    def on_radiobutton_toggled(self, button):
        # This is bound to both radiobutton_bitrate and radiobutton_quality
        self.bitrate.set_sensitive(self.has_bitrate.get_active())
        self.quality.set_sensitive(self.has_quality.get_active())


class TheoraWizardPlugin(object):
    implements(IEncoderPlugin)
    def __init__(self, wizard):
        self.wizard = wizard
        self.model = TheoraVideoEncoder()

    def getConversionStep(self):
        return TheoraStep(self.wizard, self.model)
