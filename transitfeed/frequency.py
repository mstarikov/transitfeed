#!/usr/bin/python2.5

# Copyright (C) 2010 Google Inc.
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
from .gtfsobjectbase import GtfsObjectBase
from . import util


class Frequency(GtfsObjectBase):
    """This class represents a period of a trip during which the vehicle travels
    at regular intervals (rather than specifying exact times for each stop)."""

    _REQUIRED_FIELD_NAMES = ['trip_id', 'start_time', 'end_time',
                             'headway_secs']
    _FIELD_NAMES = _REQUIRED_FIELD_NAMES + ['exact_times']
    _TABLE_NAME = "frequencies"

    def __init__(self, field_dict=None):
        self._schedule = None
        if field_dict:
            if isinstance(field_dict, self.__class__):
                for k, v in field_dict.iteritems():
                    self.__dict__[k] = v
            else:
                self.__dict__.update(field_dict)

    def start_time(self):
        return self.start_time

    def end_time(self):
        return self.end_time

    def trip_id(self):
        return self.trip_id

    def headway_secs(self):
        return self.headway_secs

    def exact_times(self):
        return self.exact_times

    def validateexact_times(self, problems):
        if util.IsEmpty(self.exact_times):
            self.exact_times = 0
            return
        try:
            self.exact_times = int(self.exact_times)
        except (ValueError, TypeError):
            problems.InvalidValue('exact_times', self.exact_times,
                                  'Should be 0 (no fixed schedule) or 1 (fixed and ' \
                                  'regular schedule, shortcut for a repetitive ' \
                                  'stop_times file).')
            del self.exact_times
            return
        if self.exact_times not in (0, 1):
            problems.InvalidValue('exact_times', self.exact_times,
                                  'Should be 0 (no fixed schedule) or 1 (fixed and ' \
                                  'regular schedule, shortcut for a repetitive ' \
                                  'stop_times file).')

    def validate_before_add(self, problems):
        self.validateexact_times(problems)
        return True

    def validate_after_add(self, problems):
        return

    def validate(self, problems=None):
        return

    def add_to_schedule(self, schedule=None, problems=None):
        if schedule is None:
            return
        self._schedule = schedule
        try:
            trip = schedule.GetTrip(self.trip_id)
        except KeyError:
            problems.InvalidValue('trip_id', self.trip_id)
            return
        trip.AddFrequencyObject(self, problems)
