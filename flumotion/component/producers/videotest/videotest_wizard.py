# -*- Mode: Python -*-
# vi:si:et:sw=4:sts=4:ts=4
#
# Flumotion - a streaming media server
# Copyright (C) 2008 Fluendo, S.L. (www.fluendo.com).
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

import gtk
from zope.interface import implements

from flumotion.wizard.basesteps import VideoProducerStep
from flumotion.wizard.interfaces import IProducerPlugin
from flumotion.wizard.models import VideoProducer

__version__ = "$Rev$"
_ = gettext.gettext


class TestVideoProducer(VideoProducer):
    component_type = 'videotest-producer'

    def __init__(self):
        super(TestVideoProducer, self).__init__()

        self.properties.pattern = 0
        self.properties.format = 'video/x-raw-yuv'


class TestVideoProducerStep(VideoProducerStep):
    name = _('Test Video Producer')
    glade_file = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                              'videotest-wizard.glade')
    component_type = 'videotestsrc'
    icon = 'testsource.png'

    # WizardStep

    def setup(self):
        self.pattern.data_type = int
        self.format.data_type = str
        self.framerate.data_type = float

        self.pattern.prefill([
            (_('SMPTE Color bars'), 0),
            (_('Random (television snow)'), 1),
            (_('Totally black'), 2)])
        self.format.prefill([
            (_('YUV'), 'video/x-raw-yuv'),
            (_('RGB'), 'video/x-raw-rgb')])

        self.add_proxy(self.model.properties,
                       ['pattern', 'width', 'height',
                        'framerate', 'format'])

        sizegroup = gtk.SizeGroup(gtk.SIZE_GROUP_HORIZONTAL)
        sizegroup.add_widget(self.width)
        sizegroup.add_widget(self.height)
        sizegroup.add_widget(self.framerate)

    def worker_changed(self, worker):
        self.model.worker = worker
        self.wizard.require_elements(worker, 'videotestsrc')


class VideoTestWizardPlugin(object):
    implements(IProducerPlugin)
    def __init__(self, wizard):
        self.wizard = wizard
        self.model = TestVideoProducer()

    def getProductionStep(self, type):
        return TestVideoProducerStep(self.wizard, self.model)

