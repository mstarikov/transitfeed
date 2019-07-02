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

import transitfeed
import transitfeed.util as util
import transitfeed.problems as problems_module

class Stop(transitfeed.Stop):
  """Extension of transitfeed.Stop:
  - Adding and validating new fields (see _FIELD_NAMES). See proposal at
    https://sites.google.com/site/gtfschanges/spec-changes-summary#stops
  - Overriding ValidateAfterAdd() in order to call new validation functions.
  - Overriding validate_stop_location_type(), adding location_type 2 (entrance).
  """

  _FIELD_NAMES = transitfeed.Stop._FIELD_NAMES + ['vehicle_type', 'platform_code']

  LOCATION_TYPE_ENTRANCE = 2

  # New validation function for field 'vehicle_type'.
  def validate_vehicle_type(self, problems):
    self.vehicle_type = util.ValidateAndReturnIntValue(
        self.vehicle_type, self._gtfs_factory.Route._ROUTE_TYPE_IDS, None, True,
        'vehicle_type', problems)
    # Entrances must not have a vehicle type, in general google transit does not
    # read vehicle types from stops with a parent station.
    if self.vehicle_type:
      if self.location_type == 2:
        problems.InvalidValue('vehicle_type', self.location_type,
              reason='an entrance must not have a vehicle type')
      elif not util.IsEmpty(self.parent_station):
        problems.InvalidValue('vehicle_type', self.location_type,
              reason='Google Transit does not read vehicle types for stops '
              'having a parent station', type=problems_module.TYPE_WARNING)

  # Overriding transitfeed.Stop.validate_before_add().
  def validate_before_add(self, problems):
    super(Stop, self).validate_before_add(problems)
    self.validate_vehicle_type(problems)
    return True # None of these checks are blocking

  # Overriding transitfeed.Stop.validate_stop_location_type().
  # Adding location_type 2 (entrance).
  def validate_stop_location_type(self, problems):
    self.location_type = util.ValidateAndReturnIntValue(
        self.location_type, [0, 1, 2], 0, True, 'location_type', problems)
    # Entrances must have a parent_station.
    if self.location_type == 2 and util.IsEmpty(self.parent_station):
      problems.InvalidValue('location_type', self.location_type,
          reason='an entrance must have a parent_station')

  # Overriding _report_missing_required_field() in order to allow empty stop_name
  # if location_type=2 (entrance).
  def _report_missing_required_field(self, problems, required):
    if required == 'stop_name':
      # stops of type 2 (entrance) may have an empty stop_name
      self.validate_stop_location_type(problems)
      if self.location_type == 2:
        return
    problems.MissingValue(required)
    setattr(self, required, None)
