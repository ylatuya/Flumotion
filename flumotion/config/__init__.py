# -*- Mode: Python; test-case-name: flumotion.test.test_flumotion_config -*-
# vi:si:et:sw=4:sts=4:ts=4
#
# Flumotion - a video streaming server
#
# flumotion/config/__init__.py: module abstracting configure-time config.
#
# Copyright (C) 2004 Fluendo
# 
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
# 
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Street #330, Boston, MA 02111-1307, USA.

'''
Exports configure-time variables for installed and uninstalled operation.
\n
defines datadir, gladedir
'''

import os

global datadir

# where am I on the disk ?
__thisdir = os.path.dirname(os.path.abspath(__file__))

if os.path.exists(os.path.join(__thisdir, 'uninstalled.py')):
    from flumotion.config import uninstalled
    globals().update(uninstalled.get())
else:
    from flumotion.config import installed
    globals().update(installed.get())
