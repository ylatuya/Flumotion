# -*- Mode: Python -*-
# vi:si:et:sw=4:sts=4:ts=4
#
# Flumotion - a streaming media server
# Copyright (C) 2004,2005 Fluendo, S.L. (www.fluendo.com). All rights reserved.

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

from flumotion.component import feedcomponent
from vorbisutils import get_max_sample_rate

class Vorbis(feedcomponent.ParseLaunchComponent):
    def __init__(self, name, eaters, bitrate, quality, channels):
        self.bitrate = bitrate
        self.quality = quality
        self.channels = channels
        

        feedcomponent.ParseLaunchComponent.__init__(self, name, eaters,
            ['default'],
            'audioresample name=ar ! audioconvert ! capsfilter name=cf ! '
            'vorbisenc name=enc')

        enc = self.pipeline.get_by_name('enc')
        cf = self.pipeline.get_by_name('cf')
        ar = self.pipeline.get_by_name('ar')

        assert enc and cf and ar

        if self.bitrate > -1:
            enc.set_property('bitrate', self.bitrate)
        else:
            enc.set_property('quality', self.quality)

        pad = ar.get_pad('sink')
        handle = None

        def buffer_probe(pad, buffer):
            # this comes from another thread
            caps = buffer.get_caps()
            in_rate = caps[0]['rate']

            # now do necessary filtercaps
            rate = in_rate
            if self.bitrate > -1:
                maxsamplerate = get_max_sample_rate(self.bitrate, self.channels)
                if in_rate > maxsamplerate:
                    self.debug(
                        'rate %d > max rate %d (for %d kbit/sec), clamping' % (
                            in_rate, maxsamplerate, self.bitrate))
                    rate = maxsamplerate

            caps_str = 'audio/x-raw-float, rate=%d' % rate
            cf.set_property('caps',
                            gst.caps_from_string(caps_str))
            pad.remove_buffer_probe(handle)
            return True

        handle = pad.add_buffer_probe(buffer_probe)
