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

import warnings

from . import problems as problems_module
from . import util
from .gtfsobjectbase import GtfsObjectBase


class Stop(GtfsObjectBase):
    """Represents a single stop. A stop must have a latitude, longitude and name.

    Callers may assign arbitrary values to instance attributes.
    Stop.parse_attributes validates attributes according to GTFS and converts some
    into native types. parse_attributes may delete invalid attributes.
    Accessing an attribute that is a column in GTFS will return None if this
    object does not have a value or it is ''.
    A Stop object acts like a dict with string values.

    Attributes:
      stop_lat: a float representing the latitude of the stop
      stop_lon: a float representing the longitude of the stop
      All other attributes are strings.
    """
    _REQUIRED_FIELD_NAMES = ['stop_id', 'stop_name', 'stop_lat', 'stop_lon']
    _FIELD_NAMES = _REQUIRED_FIELD_NAMES + \
                   ['stop_desc', 'zone_id', 'stop_url', 'stop_code',
                    'location_type', 'parent_station', 'stop_timezone',
                    'wheelchair_boarding']
    _TABLE_NAME = 'stops'

    LOCATION_TYPE_STATION = 1

    def __init__(self, lat=None, lng=None, name=None, stop_id=None,
                 field_dict=None, stop_code=None):
        """Initialize a new Stop object.

        Args:
          field_dict: A dictionary mapping attribute name to unicode string
          lat: a float, ignored when field_dict is present
          lng: a float, ignored when field_dict is present
          name: a string, ignored when field_dict is present
          stop_id: a string, ignored when field_dict is present
          stop_code: a string, ignored when field_dict is present
        """
        self.location_type = None
        self._schedule = None
        if field_dict:
            if isinstance(field_dict, self.__class__):
                # Special case so that we don't need to re-parse the attributes to
                # native types iteritems returns all attributes that don't start with _
                for k, v in field_dict.iteritems():
                    self.__dict__[k] = v
            else:
                self.__dict__.update(field_dict)
        else:
            if lat is not None:
                self.stop_lat = lat
            if lng is not None:
                self.stop_lon = lng
            if name is not None:
                self.stop_name = name
            if stop_id is not None:
                self.stop_id = stop_id
            if stop_code is not None:
                self.stop_code = stop_code

    def get_trips(self, schedule=None):
        """Return iterable containing trips that visit this stop."""
        return [trip for trip, ss in self._get_trip_sequence(schedule)]

    def _get_trip_sequence(self, schedule=None):
        """Return a list of (trip, stop_sequence) for all trips visiting this stop.

        A trip may be in the list multiple times with different index.
        stop_sequence is an integer.

        Args:
          schedule: Deprecated, do not use.
        """
        if schedule is None:
            schedule = getattr(self, "_schedule", None)
        if schedule is None:
            warnings.warn("No longer supported. _schedule attribute is  used to get "
                          "stop_times table", DeprecationWarning)
        cursor = schedule._connection.cursor()
        cursor.execute("SELECT trip_id,stop_sequence FROM stop_times "
                       "WHERE stop_id=?",
                       (self.stop_id,))
        return [(schedule.GetTrip(row[0]), row[1]) for row in cursor]

    def _get_trip_index(self, schedule=None):
        """Return a list of (trip, index).

        trip: a Trip object
        index: an offset in trip.GetStopTimes()
        """
        trip_index = []
        for trip, sequence in self._get_trip_sequence(schedule):
            for index, st in enumerate(trip.GetStopTimes()):
                if st.stop_sequence == sequence:
                    trip_index.append((trip, index))
                    break
            else:
                raise RuntimeError("stop_sequence %d not found in trip_id %s" %
                                   sequence, trip.trip_id)
        return trip_index

    def get_stop_time_trips(self, schedule=None):
        """Return a list of (time, (trip, index), is_timepoint).

        time: an integer. It might be interpolated.
        trip: a Trip object.
        index: the offset of this stop in trip.GetStopTimes(), which may be
          different from the stop_sequence.
        is_timepoint: a bool
        """
        time_trips = []
        for trip, index in self._get_trip_index(schedule):
            secs, stoptime, is_timepoint = trip.GetTimeInterpolatedStops()[index]
            time_trips.append((secs, (trip, index), is_timepoint))
        return time_trips

    def __getattr__(self, name):
        """Return None or the default value if name is a known attribute.

        This method is only called when name is not found in __dict__.
        """
        if name == "location_type":
            return 0
        elif name == "trip_index":
            return self._get_trip_index()
        else:
            return super(Stop, self).__getattr__(name)

    def validate_stop_latitude(self, problems):
        if self.stop_lat is not None:
            value = self.stop_lat
            try:
                if not isinstance(value, (float, int)):
                    self.stop_lat = util.float_string_to_float(value, problems)
            except (ValueError, TypeError):
                problems.invalid_value('stop_lat', value)
                del self.stop_lat
            else:
                if self.stop_lat > 90 or self.stop_lat < -90:
                    problems.invalid_value('stop_lat', value)

    def validate_stop_longitude(self, problems):
        if self.stop_lon is not None:
            value = self.stop_lon
            try:
                if not isinstance(value, (float, int)):
                    self.stop_lon = util.float_string_to_float(value, problems)
            except (ValueError, TypeError):
                problems.invalid_value('stop_lon', value)
                del self.stop_lon
            else:
                if self.stop_lon > 180 or self.stop_lon < -180:
                    problems.invalid_value('stop_lon', value)

    def validate_stop_url(self, problems):
        value = self.stop_url
        if value and not util.validateURL(value, 'stop_url', problems):
            del self.stop_url

    def validate_stop_location_type(self, problems):
        value = self.location_type
        if value == '':
            self.location_type = 0
        else:
            try:
                self.location_type = int(value)
            except (ValueError, TypeError):
                problems.invalid_value('location_type', value)
                del self.location_type
            else:
                if self.location_type not in (0, 1):
                    problems.invalid_value('location_type', value,
                                          type=problems_module.TYPE_WARNING)

    def validate_stop_required_fields(self, problems):
        for required in self._REQUIRED_FIELD_NAMES:
            if util.is_empty(getattr(self, required, None)):
                self._report_missing_required_field(problems, required)

    def _report_missing_required_field(self, problems, required):
        # TODO: For now we are keeping the API stable but it would be cleaner to
        # treat whitespace stop_id as invalid, instead of missing
        problems.missing_value(required)
        setattr(self, required, None)

    def validate_stop_not_too_close_to_origin(self, problems):
        if self.stop_lat is not None \
                and self.stop_lon is not None \
                and abs(self.stop_lat) < 1.0 \
                and abs(self.stop_lon) < 1.0:
            problems.invalid_value('stop_lat', self.stop_lat,
                                  'Stop location too close to 0, 0',
                                  type=problems_module.TYPE_WARNING)

    def validate_stop_description_and_name_are_different(self, problems):
        if (self.stop_desc and self.stop_name and
                not util.is_empty(self.stop_desc) and
                self.stop_name.strip().lower() == self.stop_desc.strip().lower()):
            problems.invalid_value('stop_desc', self.stop_desc,
                                  'stop_desc should not be the same as stop_name',
                                  type=problems_module.TYPE_WARNING)

    def validate_stop_is_not_station_with_parent(self, problems):
        if self.parent_station and self.location_type == 1:
            problems.invalid_value('parent_station', self.parent_station,
                                  'Stop row with location_type=1 (a station) must '
                                  'not have a parent_station')

    def validate_stop_timezone(self, problems):
        # Entrances or other child stops (having a parent station) must not have a
        # stop_timezone.
        util.validateTimezone(self.stop_timezone, 'stop_timezone', problems)
        if (not util.is_empty(self.parent_station) and
                not util.is_empty(self.stop_timezone)):
            problems.invalid_value('stop_timezone', self.stop_timezone,
                                  reason='a stop having a parent stop must not have a stop_timezone',
                                  type=problems_module.TYPE_WARNING)

    def validate_wheelchair_boarding(self, problems):
        if self.wheelchair_boarding:
            util.validateYesNoUnknown(
                self.wheelchair_boarding, 'wheelchair_boarding', problems)

    def validate_before_add(self, problems):
        # First check that all required fields are present because parse_attributes
        # may remove invalid attributes.
        self.validate_stop_required_fields(problems)

        # If value is valid for attribute name store it.
        # If value is not valid call problems. Return a new value of the correct type
        # or None if value couldn't be converted.
        self.validate_stop_latitude(problems)
        self.validate_stop_longitude(problems)
        self.validate_stop_url(problems)
        self.validate_stop_location_type(problems)
        self.validate_stop_timezone(problems)
        self.validate_wheelchair_boarding(problems)

        # Check that this object is consistent with itself
        self.validate_stop_not_too_close_to_origin(problems)
        self.validate_stop_description_and_name_are_different(problems)
        self.validate_stop_is_not_station_with_parent(problems)

        # None of these checks are blocking
        return True

    def validate_after_add(self, problems):
        return

    def validate(self, problems=problems_module.default_problem_reporter):
        self.validate_before_add(problems)
        self.validate_after_add(problems)

    def add_to_schedule(self, schedule, problems):
        schedule.AddStopObject(self, problems)
