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

import gettext
import os

from flumotion.wizard.basesteps import VideoEncoderStep
from flumotion.wizard.models import VideoEncoder

__version__ = "$Rev$"
_ = gettext.gettext


def _fraction_from_float(number, denominator):
    """
    Return a string to be used in serializing to XML.
    """
    return "%d/%d" % (number * denominator, denominator)


class JPEGVideoEncoder(VideoEncoder):
    component_type = 'jpeg-encoder'

    def __init__(self):
        super(JPEGVideoEncoder, self).__init__()

        self.properties.framerate = 5.0
        self.properties.quality = 84

    def getProperties(self):
        properties = super(JPEGVideoEncoder, self).getProperties()
        properties['framerate'] = _fraction_from_float(properties['framerate'], 2)
        return properties


class JPEGStep(VideoEncoderStep):
    name = 'JPEG encoder'
    sidebar_name = 'JPEG'
    glade_file = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                              'jpeg-wizard.glade')
    section = _('Conversion')
    component_type = 'jpeg'

    # WizardStep

    def setup(self):
        self.framerate.data_type = float
        self.quality.data_type = int

        self.add_proxy(self.model.properties,
                       ['framerate', 'quality'])

    def worker_changed(self):
        self.model.worker = self.worker
        self.wizard.require_elements(self.worker, 'jpegenc')

    def get_next(self):
        return self.wizard.get_step('Encoding').get_audio_page()


class JPEGWizardPlugin(object):
    def __init__(self, wizard):
        self.wizard = wizard
        self.model = JPEGVideoEncoder()

    def getConversionStep(self):
        return JPEGStep(self.wizard, self.model)
