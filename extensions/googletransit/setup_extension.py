#!/usr/bin/python2.5

# Copyright (C) 2011 Google Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from __future__ import absolute_import
import transitfeed

from . import agency
from . import fareattribute
from . import route
from . import stop

def get_gtfs_factory(factory = None):
  if not factory:
    factory = transitfeed.get_gtfs_factory()

  # Agency class extension
  factory.update_class('Agency', agency.Agency)

  # FareAttribute class extension
  factory.update_class('FareAttribute', fareattribute.FareAttribute)

  # Route class extension
  factory.update_class('Route', route.Route)

  # Stop class extension
  factory.update_class('Stop', stop.Stop)

  return factory
