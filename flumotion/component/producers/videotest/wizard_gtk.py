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

from flumotion.admin.assistant.interfaces import IProducerPlugin
from flumotion.admin.assistant.models import VideoProducer
from flumotion.admin.gtk.basesteps import VideoProducerStep
from flumotion.configure import configure

__version__ = "$Rev$"
_ = gettext.gettext


class TestVideoProducer(VideoProducer):
    componentType = 'videotest-producer'

    def __init__(self):
        super(TestVideoProducer, self).__init__()

        self.properties.pattern = 0


class TestVideoProducerStep(VideoProducerStep):
    name = 'Test Video Producer'
    title = _('Test Video Producer')
    icon = 'testsource.png'
    gladeFile = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                              'wizard.glade')
    componentType = 'videotestsrc'
    docSection = 'help-configuration-assistant-producer-video-test'
    docAnchor = ''
    docVersion = 'local'

    # WizardStep

    def setup(self):
        self.pattern.data_type = int
        self.framerate.data_type = float

        patterns = [('SMPTE Color bars', 0, 'pattern_smpte.png'),
                    ('Random (television snow)', 1, 'pattern_snow.png'),
                    ('100% Black', 2, 'pattern_black.png'),
                    ('Blink', 12, 'pattern_blink.png')]
        self.pattern_icons = dict()

        for description, id, image in patterns:
            self.pattern.append_item(_(description), id)
            if image:
                self.pattern_icons[id] = os.path.join(configure.imagedir,
                                                      'wizard', image)

        self.pattern.connect('changed', self._change_image)

        self.add_proxy(self.model.properties,
                       ['pattern', 'width', 'height',
                        'framerate'])

        sizegroup = gtk.SizeGroup(gtk.SIZE_GROUP_HORIZONTAL)
        sizegroup.add_widget(self.width)
        sizegroup.add_widget(self.height)
        sizegroup.add_widget(self.framerate)

    def workerChanged(self, worker):
        self.model.worker = worker
        self.wizard.requireElements(worker, 'videotestsrc', 'level')

    def _change_image(self, combo):
        self.pattern_image.set_from_file(
            self.pattern_icons.get(combo.get_selected_data(), None))


class VideoTestWizardPlugin(object):
    implements(IProducerPlugin)

    def __init__(self, wizard):
        self.wizard = wizard
        self.model = TestVideoProducer()

    def getProductionStep(self, type):
        return TestVideoProducerStep(self.wizard, self.model)
