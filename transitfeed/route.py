#!/usr/bin/python2.5

# Copyright (C) 2007 Google Inc.
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

from . import problems as problems_module
from . import util
from .gtfsobjectbase import GtfsObjectBase


class Route(GtfsObjectBase):
    """Represents a single route."""

    _REQUIRED_FIELD_NAMES = [
        'route_id', 'route_short_name', 'route_long_name', 'route_type'
    ]
    _FIELD_NAMES = _REQUIRED_FIELD_NAMES + [
        'agency_id', 'route_desc', 'route_url', 'route_color', 'route_text_color',
        'bikes_allowed'
    ]
    _ROUTE_TYPES = {
        0: {'name': 'Tram', 'max_speed': 100},
        1: {'name': 'Subway', 'max_speed': 150},
        2: {'name': 'Rail', 'max_speed': 300},
        3: {'name': 'Bus', 'max_speed': 100},
        4: {'name': 'Ferry', 'max_speed': 80},
        5: {'name': 'Cable Car', 'max_speed': 50},
        6: {'name': 'Gondola', 'max_speed': 50},
        7: {'name': 'Funicular', 'max_speed': 50},
    }
    # Create a reverse lookup dict of route type names to route types.
    _ROUTE_TYPE_IDS = set(_ROUTE_TYPES.keys())
    _ROUTE_TYPE_NAMES = dict((v['name'], k) for k, v in _ROUTE_TYPES.items())
    _TABLE_NAME = 'routes'

    def __init__(self, short_name=None, long_name=None, route_type=None,
                 route_id=None, agency_id=None, field_dict=None):
        self._schedule = None
        self._trips = []

        if not field_dict:
            field_dict = {}
            if short_name is not None:
                field_dict['route_short_name'] = short_name
            if long_name is not None:
                field_dict['route_long_name'] = long_name
            if route_type is not None:
                if route_type in self._ROUTE_TYPE_NAMES:
                    self.route_type = self._ROUTE_TYPE_NAMES[route_type]
                else:
                    field_dict['route_type'] = route_type
            if route_id is not None:
                field_dict['route_id'] = route_id
            if agency_id is not None:
                field_dict['agency_id'] = agency_id
        self.__dict__.update(field_dict)

    def add_trip(self, schedule=None, headsign=None, service_period=None,
                 trip_id=None):
        """Add a trip to this route.

        Args:
          schedule: a Schedule object which will hold the new trip or None to use
            the schedule of this route.
          headsign: headsign of the trip as a string
          service_period: a ServicePeriod object or None to use
            schedule.GetDefaultServicePeriod()
          trip_id: optional trip_id for the new trip

        Returns:
          a new Trip object
        """
        if schedule is None:
            assert self._schedule is not None
            schedule = self._schedule
        if trip_id is None:
            trip_id = util.find_unique_id(schedule.trips)
        if service_period is None:
            service_period = schedule.GetDefaultServicePeriod()
        trip_class = self.get_gtfs_factory().Trip
        trip_obj = trip_class(route=self, headsign=headsign,
                              service_period=service_period, trip_id=trip_id)
        schedule.add_tripObject(trip_obj)
        return trip_obj

    def _add_trip_object(self, trip):
        # Only class Schedule may call this. Users of the API should call
        # Route.add_trip or schedule.add_tripObject.
        self._trips.append(trip)

    def __getattr__(self, name):
        """Return None or the default value if name is a known attribute.

        This method overrides GtfsObjectBase.__getattr__ to provide backwards
        compatible access to trips.
        """
        if name == 'trips':
            return self._trips
        else:
            return GtfsObjectBase.__getattr__(self, name)

    def get_pattern_id_trip_dict(self):
        """Return a dictionary that maps pattern_id to a list of Trip objects."""
        d = {}
        for t in self._trips:
            d.setdefault(t.pattern_id, []).append(t)
        return d

    def validate_route_id_is_present(self, problems):
        if util.is_empty(self.route_id):
            problems.missing_value('route_id')

    def validate_route_type_is_present(self, problems):
        if util.is_empty(self.route_type):
            problems.missing_value('route_type')

    def validate_route_short_and_long_names_are_not_blank(self, problems):
        if util.is_empty(self.route_short_name) and \
                util.is_empty(self.route_long_name):
            problems.invalid_value('route_short_name',
                                  self.route_short_name,
                                  'Both route_short_name and '
                                  'route_long name are blank.')

    def validate_route_short_name_is_not_too_long(self, problems):
        if self.route_short_name and len(self.route_short_name) > 6:
            problems.invalid_value('route_short_name',
                                  self.route_short_name,
                                  'This route_short_name is relatively long, which '
                                  'probably means that it contains a place name.  '
                                  'You should only use this field to hold a short '
                                  'code that riders use to identify a route.  '
                                  'If this route doesn\'t have such a code, it\'s '
                                  'OK to leave this field empty.',
                                  type=problems_module.TYPE_WARNING)

    def validate_route_long_name_does_not_contain_short_name(self, problems):
        if self.route_short_name and self.route_long_name:
            short_name = self.route_short_name.strip().lower()
            long_name = self.route_long_name.strip().lower()
            if (long_name.startswith(short_name + ' ') or
                    long_name.startswith(short_name + '(') or
                    long_name.startswith(short_name + '-')):
                problems.invalid_value('route_long_name',
                                      self.route_long_name,
                                      'route_long_name shouldn\'t contain '
                                      'the route_short_name value, as both '
                                      'fields are often displayed '
                                      'side-by-side.',
                                      type=problems_module.TYPE_WARNING)

    def validate_route_short_and_long_names_are_not_equal(self, problems):
        if self.route_short_name and self.route_long_name:
            short_name = self.route_short_name.strip().lower()
            long_name = self.route_long_name.strip().lower()
            if long_name == short_name:
                problems.invalid_value('route_long_name',
                                      self.route_long_name,
                                      'route_long_name shouldn\'t be the same '
                                      'the route_short_name value, as both '
                                      'fields are often displayed '
                                      'side-by-side.  It\'s OK to omit either the '
                                      'short or long name (but not both).',
                                      type=problems_module.TYPE_WARNING)

    def validate_route_description_not_the_same_as_route_name(self, problems):
        if (self.route_desc and
                ((self.route_desc == self.route_short_name) or
                 (self.route_desc == self.route_long_name))):
            problems.invalid_value('route_desc',
                                  self.route_desc,
                                  'route_desc shouldn\'t be the same as '
                                  'route_short_name or route_long_name')

    def validate_route_type_has_valid_value(self, problems):
        if self.route_type is not None:
            try:
                if not isinstance(self.route_type, int):
                    self.route_type = util.non_neg_int_string_to_int(self.route_type, problems)
            except (TypeError, ValueError):
                problems.invalid_value('route_type', self.route_type)
            else:
                if self.route_type not in self._ROUTE_TYPE_IDS:
                    problems.invalid_value('route_type',
                                          self.route_type,
                                          type=problems_module.TYPE_WARNING)

    def validate_route_url(self, problems):
        if self.route_url:
            util.validateURL(self.route_url, 'route_url', problems)

    def validate_route_color(self, problems):
        if self.route_color:
            if not util.IsValidHexColor(self.route_color):
                problems.invalid_value('route_color', self.route_color,
                                      'route_color should be a valid color description '
                                      'which consists of 6 hexadecimal characters '
                                      'representing the RGB values. Example: 44AA06')
                self.route_color = None

    def validate_route_text_color(self, problems):
        if self.route_text_color:
            if not util.IsValidHexColor(self.route_text_color):
                problems.invalid_value('route_text_color', self.route_text_color,
                                      'route_text_color should be a valid color '
                                      'description, which consists of 6 hexadecimal '
                                      'characters representing the RGB values. '
                                      'Example: 44AA06')
                self.route_text_color = None

    def validate_route_and_text_colors(self, problems):
        if self.route_color:
            bg_lum = util.ColorLuminance(self.route_color)
        else:
            bg_lum = util.ColorLuminance('ffffff')  # white (default)
        if self.route_text_color:
            txt_lum = util.ColorLuminance(self.route_text_color)
        else:
            txt_lum = util.ColorLuminance('000000')  # black (default)
        if abs(txt_lum - bg_lum) < 510 / 7.:
            # http://www.w3.org/TR/2000/WD-AERT-20000426#color-contrast recommends
            # a threshold of 125, but that is for normal text and too harsh for
            # big colored logos like line names, so we keep the original threshold
            # from r541 (but note that weight has shifted between RGB components).
            problems.invalid_value('route_color', self.route_color,
                                  'The route_text_color and route_color should '
                                  'be set to contrasting colors, as they are used '
                                  'as the text and background color (respectively) '
                                  'for displaying route names.  When left blank, '
                                  'route_text_color defaults to 000000 (black) and '
                                  'route_color defaults to FFFFFF (white).  A common '
                                  'source of issues here is setting route_color to '
                                  'a dark color, while leaving route_text_color set '
                                  'to black.  In this case, route_text_color should '
                                  'be set to a lighter color like FFFFFF to ensure '
                                  'a legible contrast between the two.',
                                  type=problems_module.TYPE_WARNING)

    def validate_bikes_allowed(self, problems):
        if self.bikes_allowed:
            util.validateYesNoUnknown(self.bikes_allowed, 'bikes_allowed', problems)

    def validate_before_add(self, problems):
        self.validate_route_id_is_present(problems)
        self.validate_route_type_is_present(problems)
        self.validate_route_short_and_long_names_are_not_blank(problems)
        self.validate_route_short_name_is_not_too_long(problems)
        self.validate_route_long_name_does_not_contain_short_name(problems)
        self.validate_route_short_and_long_names_are_not_equal(problems)
        self.validate_route_description_not_the_same_as_route_name(problems)
        self.validate_route_type_has_valid_value(problems)
        self.validate_route_url(problems)
        self.validate_route_color(problems)
        self.validate_route_text_color(problems)
        self.validate_route_and_text_colors(problems)
        self.validate_bikes_allowed(problems)

        # None of these checks are blocking
        return True

    def validate_after_add(self, problems):
        return

    def add_to_schedule(self, schedule, problems):
        schedule.AddRouteObject(self, problems)

    def validate(self, problems=problems_module.default_problem_reporter):
        self.validate_before_add(problems)
        self.validate_after_add(problems)
