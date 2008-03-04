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

from zope.interface import implements

from flumotion.wizard.basesteps import AudioSourceStep
from flumotion.wizard.interfaces import IProducerPlugin
from flumotion.wizard.models import AudioProducer

__version__ = "$Rev$"
_ = gettext.gettext


class TestAudioProducer(AudioProducer):
    component_type = 'audiotest-producer'

    def __init__(self):
        super(TestAudioProducer, self).__init__()

        self.properties.rate = '44100'


class TestAudioSourceStep(AudioSourceStep):
    name = _('Test Audio Source')
    glade_file = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                              'audiotest-wizard.glade')
    icon = 'soundcard.png'

    # WizardStep

    def setup(self):
        self.rate.data_type = str
        self.volume.data_type = float

        self.rate.prefill(['8000',
                           '16000',
                           '32000',
                           '44100'])

        self.add_proxy(self.model.properties,
                       ['frequency', 'volume', 'rate'])

        self.rate.set_sensitive(True)

    def worker_changed(self, worker):
        self.model.worker = worker
        self.wizard.require_elements(worker, 'audiotestsrc')

    def get_next(self):
        return None


class AudioTestWizardPlugin(object):
    implements(IProducerPlugin)
    def __init__(self, wizard):
        self.wizard = wizard
        self.model = TestAudioProducer()

    def getProductionStep(self, type):
        return TestAudioSourceStep(self.wizard, self.model)
