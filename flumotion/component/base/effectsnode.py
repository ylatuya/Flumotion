# -*- Mode: Python; test-case-name: flumotion.test.test_feedcomponent010 -*-
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

"""
Base class for effect ui nodes
"""

from flumotion.component.base.baseadminnode import BaseAdminGtkNode


class EffectAdminGtkNode(BaseAdminGtkNode):
    """
    I am a base class for all GTK+-based component effect Admin UI nodes.
    I am a view on a set of properties for an effect on a component.
    """
    def __init__(self, state, admin, effectName, title=None):
        """
        @param state: state of component this is a UI for
        @type  state: L{flumotion.common.planet.AdminComponentState}
        @param admin: the admin model that interfaces with the manager for us
        @type  admin: L{flumotion.admin.admin.AdminModel}
        """
        BaseAdminGtkNode.__init__(self, state, admin, title)
        self.effectName = effectName

    def effectCallRemote(self, methodName, *args, **kwargs):
        return self.admin.componentCallRemote(self.state,
            "effect", self.effectName, methodName, *args, **kwargs)
