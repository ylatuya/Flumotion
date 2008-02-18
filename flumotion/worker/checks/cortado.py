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

from flumotion.common.messages import Result
from flumotion.component.misc.cortado.cortado_location import getCortadoFilename

__version__ = "$Rev$"

def checkCortado():
    """Check for cortado applet.
    @returns: a result containing the filename to the jar or None if it cannot be found
    @rtype: L{flumotion.common.messages.Result}
    """
    result = Result()
    result.succeed(getCortadoFilename())
    return result