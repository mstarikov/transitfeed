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


class Trip(GtfsObjectBase):
    _REQUIRED_FIELD_NAMES = ['route_id', 'service_id', 'trip_id']
    _FIELD_NAMES = _REQUIRED_FIELD_NAMES + [
        'trip_headsign', 'trip_short_name', 'direction_id', 'block_id', 'shape_id',
        'bikes_allowed', 'wheelchair_accessible', 'original_trip_id'
    ]
    _TABLE_NAME = "trips"

    def __init__(self, headsign=None, service_period=None,
                 route=None, trip_id=None, field_dict=None):
        self._schedule = None
        self._headways = []  # [(start_time, end_time, headway_secs)]
        if not field_dict:
            field_dict = {}
            if headsign is not None:
                field_dict['trip_headsign'] = headsign
            if route:
                field_dict['route_id'] = route.route_id
            if trip_id is not None:
                field_dict['trip_id'] = trip_id
            if service_period is not None:
                field_dict['service_id'] = service_period.service_id
            # Earlier versions of transitfeed.py assigned self.service_period here
            # and allowed the caller to set self.service_id. Schedule.validate
            # checked the service_id attribute if it was assigned and changed it to a
            # service_period attribute. Now only the service_id attribute is used and
            # it is validated by Trip.validate.
            if service_period is not None:
                # For backwards compatibility
                self.service_id = service_period.service_id
        self.__dict__.update(field_dict)

    def get_field_values_tuple(self):
        return [getattr(self, fn) or '' for fn in self._FIELD_NAMES]

    def add_stop_time(self, stop, problems=None, schedule=None, **kwargs):
        """Add a stop to this trip. Stops must be added in the order visited.

        Args:
          stop: A Stop object
          kwargs: remaining keyword args passed to StopTime.__init__

        Returns:
          None
        """
        if problems is None:
            # TODO: delete this branch when StopTime.__init__ doesn't need a
            # ProblemReporter
            problems = problems_module.default_problem_reporter
        stoptime = self.get_gtfs_factory().StopTime(
            problems=problems, stop=stop, **kwargs)
        self.add_stop_time_object(stoptime, schedule)

    def _add_stop_time_object_unordered(self, stoptime, schedule):
        """Add StopTime object to this trip.

        The trip isn't checked for duplicate sequence numbers so it must be
        validated later."""
        stop_time_class = self.get_gtfs_factory().StopTime
        cursor = schedule._connection.cursor()
        insert_query = "INSERT INTO stop_times (%s) VALUES (%s);" % (
            ','.join(stop_time_class._SQL_FIELD_NAMES),
            ','.join(['?'] * len(stop_time_class._SQL_FIELD_NAMES)))
        cursor = schedule._connection.cursor()
        cursor.execute(
            insert_query, stoptime.GetSqlValuesTuple(self.trip_id))

    def replace_stop_time_object(self, stoptime, schedule=None):
        """Replace a StopTime object from this trip with the given one.

        Keys the StopTime object to be replaced by trip_id, stop_sequence
        and stop_id as 'stoptime', with the object 'stoptime'.
        """

        if schedule is None:
            schedule = self._schedule

        new_secs = stoptime.GetTimeSecs()
        cursor = schedule._connection.cursor()
        cursor.execute("DELETE FROM stop_times WHERE trip_id=? and "
                       "stop_sequence=? and stop_id=?",
                       (self.trip_id, stoptime.stop_sequence, stoptime.stop_id))
        if cursor.rowcount == 0:
            raise problems_module.Error('Attempted replacement of StopTime object which does not exist')
        self._add_stop_time_object_unordered(stoptime, schedule)

    def add_stop_time_object(self, stoptime, schedule=None, problems=None):
        """Add a StopTime object to the end of this trip.

        Args:
          stoptime: A StopTime object. Should not be reused in multiple trips.
          schedule: Schedule object containing this trip which must be
          passed to Trip.__init__ or here
          problems: ProblemReporter object for validating the StopTime in its new
          home

        Returns:
          None
        """
        if schedule is None:
            schedule = self._schedule
        if schedule is None:
            warnings.warn("No longer supported. _schedule attribute is used to get "
                          "stop_times table", DeprecationWarning)
        if problems is None:
            problems = schedule.problem_reporter

        new_secs = stoptime.GetTimeSecs()
        cursor = schedule._connection.cursor()
        cursor.execute("SELECT max(stop_sequence), max(arrival_secs), "
                       "max(departure_secs) FROM stop_times WHERE trip_id=?",
                       (self.trip_id,))
        row = cursor.fetchone()
        if row[0] is None:
            # This is the first stop_time of the trip
            stoptime.stop_sequence = 1
            if new_secs == None:
                problems.other_problem(
                    'No time for first StopTime of trip_id "%s"' % (self.trip_id,))
        else:
            stoptime.stop_sequence = row[0] + 1
            prev_secs = max(row[1], row[2])
            if new_secs != None and new_secs < prev_secs:
                problems.other_problem(
                    'out of order stop time for stop_id=%s trip_id=%s %s < %s' %
                    (util.encode_str(stoptime.stop_id),
                     util.encode_str(self.trip_id),
                     util.FormatSecondsSinceMidnight(new_secs),
                     util.FormatSecondsSinceMidnight(prev_secs)))
        self._add_stop_time_object_unordered(stoptime, schedule)

    def get_time_stops(self):
        """Return a list of (arrival_secs, departure_secs, stop) tuples.

        Caution: arrival_secs and departure_secs may be 0, a false value meaning a
        stop at midnight or None, a false value meaning the stop is untimed."""
        return [(st.arrival_secs, st.departure_secs, st.stop) for st in
                self.get_stop_times()]

    def get_count_stop_times(self):
        """Return the number of stops made by this trip."""
        cursor = self._schedule._connection.cursor()
        cursor.execute(
            'SELECT count(*) FROM stop_times WHERE trip_id=?', (self.trip_id,))
        return cursor.fetchone()[0]

    def get_time_interpolated_stops(self):
        """Return a list of (secs, stoptime, is_timepoint) tuples.

        secs will always be an int. If the StopTime object does not have explict
        times this method guesses using distance. stoptime is a StopTime object and
        is_timepoint is a bool.

        Raises:
          ValueError if this trip does not have the times needed to interpolate
        """
        rv = []

        stoptimes = self.get_stop_times()
        # If there are no stoptimes [] is the correct return value but if the start
        # or end are missing times there is no correct return value.
        if not stoptimes:
            return []
        if (stoptimes[0].GetTimeSecs() is None or
                stoptimes[-1].GetTimeSecs() is None):
            raise ValueError("%s must have time at first and last stop" % (self))

        cur_timepoint = None
        next_timepoint = None
        distance_between_timepoints = 0
        distance_traveled_between_timepoints = 0

        for i, st in enumerate(stoptimes):
            if st.GetTimeSecs() != None:
                cur_timepoint = st
                distance_between_timepoints = 0
                distance_traveled_between_timepoints = 0
                if i + 1 < len(stoptimes):
                    k = i + 1
                    distance_between_timepoints += util.ApproximateDistanceBetweenStops(stoptimes[k - 1].stop,
                                                                                        stoptimes[k].stop)
                    while stoptimes[k].GetTimeSecs() == None:
                        k += 1
                        distance_between_timepoints += util.ApproximateDistanceBetweenStops(stoptimes[k - 1].stop,
                                                                                            stoptimes[k].stop)
                    next_timepoint = stoptimes[k]
                rv.append((st.GetTimeSecs(), st, True))
            else:
                distance_traveled_between_timepoints += util.ApproximateDistanceBetweenStops(stoptimes[i - 1].stop,
                                                                                             st.stop)
                distance_percent = distance_traveled_between_timepoints / distance_between_timepoints
                total_time = next_timepoint.GetTimeSecs() - cur_timepoint.GetTimeSecs()
                time_estimate = distance_percent * total_time + cur_timepoint.GetTimeSecs()
                rv.append((int(round(time_estimate)), st, False))

        return rv

    def clear_stop_times(self):
        """Remove all stop times from this trip.

        StopTime objects previously returned by get_stop_times are unchanged but are
        no longer associated with this trip.
        """
        cursor = self._schedule._connection.cursor()
        cursor.execute('DELETE FROM stop_times WHERE trip_id=?', (self.trip_id,))

    def get_stop_times(self, problems=None):
        """Return a sorted list of StopTime objects for this trip."""
        # In theory problems=None should be safe because data from database has been
        # validated. See comment in _LoadStopTimes for why this isn't always true.
        cursor = self._schedule._connection.cursor()
        cursor.execute(
            'SELECT arrival_secs,departure_secs,stop_headsign,pickup_type,'
            'drop_off_type,shape_dist_traveled,stop_id,stop_sequence,timepoint '
            'FROM stop_times '
            'WHERE trip_id=? '
            'ORDER BY stop_sequence', (self.trip_id,))
        stop_times = []
        stoptime_class = self.get_gtfs_factory().StopTime
        if problems is None:
            # TODO: delete this branch when StopTime.__init__ doesn't need a
            # ProblemReporter
            problems = problems_module.default_problem_reporter
        for row in cursor.fetchall():
            stop = self._schedule.GetStop(row[6])
            stop_times.append(stoptime_class(problems=problems,
                                             stop=stop,
                                             arrival_secs=row[0],
                                             departure_secs=row[1],
                                             stop_headsign=row[2],
                                             pickup_type=row[3],
                                             drop_off_type=row[4],
                                             shape_dist_traveled=row[5],
                                             stop_sequence=row[7],
                                             timepoint=row[8]))
        return stop_times

    def get_headway_stop_times(self, problems=None):
        """Deprecated. Please use get_frequency_stop_times instead."""
        warnings.warn("No longer supported. The HeadwayPeriod class was renamed to "
                      "Frequency, and all related functions were renamed "
                      "accordingly.", DeprecationWarning)
        return self.get_frequency_stop_times(problems)

    def get_frequency_stop_times(self, problems=None):
        """Return a list of StopTime objects for each headway-based run.

        Returns:
          a list of list of StopTime objects. Each list of StopTime objects
          represents one run. If this trip doesn't have headways returns an empty
          list.
        """
        stoptimes_list = []  # list of stoptime lists to be returned
        stoptime_pattern = self.get_stop_times()
        first_secs = stoptime_pattern[0].arrival_secs  # first time of the trip
        stoptime_class = self.get_gtfs_factory().StopTime
        # for each start time of a headway run
        for run_secs in self.get_frequency_start_times():
            # stop time list for a headway run
            stoptimes = []
            # go through the pattern and generate stoptimes
            for st in stoptime_pattern:
                arrival_secs, departure_secs = None, None  # default value if the stoptime is not timepoint
                if st.arrival_secs != None:
                    arrival_secs = st.arrival_secs - first_secs + run_secs
                if st.departure_secs != None:
                    departure_secs = st.departure_secs - first_secs + run_secs
                # append stoptime
                stoptimes.append(stoptime_class(problems=problems, stop=st.stop,
                                                arrival_secs=arrival_secs,
                                                departure_secs=departure_secs,
                                                stop_headsign=st.stop_headsign,
                                                pickup_type=st.pickup_type,
                                                drop_off_type=st.drop_off_type,
                                                shape_dist_traveled= \
                                                    st.shape_dist_traveled,
                                                stop_sequence=st.stop_sequence,
                                                timepoint=st.timepoint))
            # add stoptimes to the stoptimes_list
            stoptimes_list.append(stoptimes)
        return stoptimes_list

    def get_start_time(self, problems=problems_module.default_problem_reporter):
        """Return the first time of the trip. TODO: For trips defined by frequency
        return the first time of the first trip."""
        cursor = self._schedule._connection.cursor()
        cursor.execute(
            'SELECT arrival_secs,departure_secs FROM stop_times WHERE '
            'trip_id=? ORDER BY stop_sequence LIMIT 1', (self.trip_id,))
        (arrival_secs, departure_secs) = cursor.fetchone()
        if arrival_secs != None:
            return arrival_secs
        elif departure_secs != None:
            return departure_secs
        else:
            problems.invalid_value('departure_time', '',
                                  'The first stop_time in trip %s is missing '
                                  'times.' % self.trip_id)

    def get_headway_start_times(self):
        """Deprecated. Please use get_frequency_start_times instead."""
        warnings.warn("No longer supported. The HeadwayPeriod class was renamed to "
                      "Frequency, and all related functions were renamed "
                      "accordingly.", DeprecationWarning)
        return self.get_frequency_start_times()

    def get_frequency_start_times(self):
        """Return a list of start time for each headway-based run.

        Returns:
          a sorted list of seconds since midnight, the start time of each run. If
          this trip doesn't have headways returns an empty list."""
        start_times = []
        # for each headway period of the trip
        for freq_tuple in self.get_frequency_tuples():
            (start_secs, end_secs, headway_secs) = freq_tuple[0:3]
            # reset run secs to the start of the timeframe
            run_secs = start_secs
            while run_secs < end_secs:
                start_times.append(run_secs)
                # increment current run secs by headway secs
                run_secs += headway_secs
        return start_times

    def get_end_time(self, problems=problems_module.default_problem_reporter):
        """Return the last time of the trip. TODO: For trips defined by frequency
        return the last time of the last trip."""
        cursor = self._schedule._connection.cursor()
        cursor.execute(
            'SELECT arrival_secs,departure_secs FROM stop_times WHERE '
            'trip_id=? ORDER BY stop_sequence DESC LIMIT 1', (self.trip_id,))
        (arrival_secs, departure_secs) = cursor.fetchone()
        if departure_secs != None:
            return departure_secs
        elif arrival_secs != None:
            return arrival_secs
        else:
            problems.invalid_value('arrival_time', '',
                                  'The last stop_time in trip %s is missing '
                                  'times.' % self.trip_id)

    def _generate_stop_times_tuples(self):
        """Generator for rows of the stop_times file"""
        stoptimes = self.get_stop_times()
        for i, st in enumerate(stoptimes):
            yield st.get_field_values_tuple(self.trip_id)

    def get_stop_times_tuples(self):
        results = []
        for time_tuple in self._generate_stop_times_tuples():
            results.append(time_tuple)
        return results

    def get_pattern(self):
        """Return a tuple of Stop objects, in the order visited"""
        stoptimes = self.get_stop_times()
        return tuple(st.stop for st in stoptimes)

    def add_headway_period_object(self, headway_period, problem_reporter):
        """Deprecated. Please use add_frequency_object instead."""
        warnings.warn("No longer supported. The HeadwayPeriod class was renamed to "
                      "Frequency, and all related functions were renamed "
                      "accordingly.", DeprecationWarning)
        self.add_frequency_object(headway_period, problem_reporter)

    def add_frequency_object(self, frequency, problem_reporter):
        """Add a Frequency object to this trip's list of Frequencies."""
        if frequency is not None:
            self.add_frequency(frequency.StartTime(),
                               frequency.EndTime(),
                               frequency.HeadwaySecs(),
                               frequency.ExactTimes(),
                               problem_reporter)

    def add_headway_period(self, start_time, end_time, headway_secs,
                           problem_reporter=problems_module.default_problem_reporter):
        """Deprecated. Please use add_frequency instead."""
        warnings.warn("No longer supported. The HeadwayPeriod class was renamed to "
                      "Frequency, and all related functions were renamed "
                      "accordingly.", DeprecationWarning)
        self.add_frequency(start_time, end_time, headway_secs, problem_reporter)

    def add_frequency(self, start_time, end_time, headway_secs, exact_times=0,
                      problem_reporter=problems_module.default_problem_reporter):
        """Adds a period to this trip during which the vehicle travels
        at regular intervals (rather than specifying exact times for each stop).

        Args:
          start_time: The time at which this headway period starts, either in
              numerical seconds since midnight or as "HH:MM:SS" since midnight.
          end_time: The time at which this headway period ends, either in
              numerical seconds since midnight or as "HH:MM:SS" since midnight.
              This value should be larger than start_time.
          headway_secs: The amount of time, in seconds, between occurences of
              this trip.
          exact_times: If 1, indicates that frequency trips should be scheduled
              exactly as determined by their start time and headway.  Default is 0.
          problem_reporter: Optional parameter that can be used to select
              how any errors in the other input parameters will be reported.
        Returns:
          None
        """
        if not start_time or start_time == '':  # 0 is OK
            problem_reporter.missing_value('start_time')
            return
        if isinstance(start_time, str):
            try:
                start_time = util.TimeToSecondsSinceMidnight(start_time)
            except problems_module.Error:
                problem_reporter.invalid_value('start_time', start_time)
                return
        elif start_time < 0:
            problem_reporter.invalid_value('start_time', start_time)

        if not end_time or end_time == '':
            problem_reporter.missing_value('end_time')
            return
        if isinstance(end_time, str):
            try:
                end_time = util.TimeToSecondsSinceMidnight(end_time)
            except problems_module.Error:
                problem_reporter.invalid_value('end_time', end_time)
                return
        elif end_time < 0:
            problem_reporter.invalid_value('end_time', end_time)
            return

        if not headway_secs:
            problem_reporter.missing_value('headway_secs')
            return
        try:
            headway_secs = int(headway_secs)
        except ValueError:
            problem_reporter.invalid_value('headway_secs', headway_secs)
            return

        if headway_secs <= 0:
            problem_reporter.invalid_value('headway_secs', headway_secs)
            return

        if end_time <= start_time:
            problem_reporter.invalid_value('end_time', end_time,
                                          'should be greater than start_time')

        if not exact_times:
            exact_times = 0
        if exact_times not in (0, 1):
            problem_reporter.invalid_value('exact_times', exact_times,
                                          'Should be 0 (no fixed schedule) or 1 (fixed and regular schedule)')

        self._headways.append((start_time, end_time, headway_secs, exact_times))

    def clear_frequencies(self):
        self._headways = []

    def _headway_output_tuple(self, headway):
        try:
            headway2 = str(headway[2])
            headway3 = str(headway[3])
        except NameError:
            headway2 = str(headway2, 'utf-8')
            headway3 = str(headway3, 'utf-8')
        return (self.trip_id,
                util.FormatSecondsSinceMidnight(headway[0]),
                util.FormatSecondsSinceMidnight(headway[1]),
                headway2,
                headway3)

    def get_frequency_output_tuples(self):
        tuples = ()
        for headway in self._headways:
            tuples.append(self._headway_output_tuple(headway))
        return tuples

    def get_frequency_tuples(self):
        return self._headways

    def __getattr__(self, name):
        if name == 'service_period':
            assert self._schedule, "Must be in a schedule to get service_period"
            return self._schedule.GetServicePeriod(self.service_id)
        elif name == 'pattern_id':
            if '_pattern_id' not in self.__dict__:
                self.__dict__['_pattern_id'] = hash(self.get_pattern())
            return self.__dict__['_pattern_id']
        else:
            return GtfsObjectBase.__getattr__(self, name)

    def validate_route_id(self, problems):
        if util.is_empty(self.route_id):
            problems.missing_value('route_id')

    def validate_service_period(self, problems):
        if 'service_period' in self.__dict__:
            # Some tests assign to the service_period attribute. Patch up self before
            # proceeding with validation. See also comment in Trip.__init__.
            self.service_id = self.__dict__['service_period'].service_id
            del self.service_period
        if util.is_empty(self.service_id):
            problems.missing_value('service_id')

    def validate_trip_id(self, problems):
        if util.is_empty(self.trip_id):
            problems.missing_value('trip_id')

    def validate_direction_id(self, problems):
        if hasattr(self, 'direction_id') and (not util.is_empty(self.direction_id)) \
                and (self.direction_id != '0') and (self.direction_id != '1'):
            problems.invalid_value('direction_id', self.direction_id,
                                  'direction_id must be "0" or "1"')

    def validate_shape_ids_exist_in_shape_list(self, problems):
        if self._schedule:
            if self.shape_id and self.shape_id not in self._schedule._shapes:
                problems.invalid_value('shape_id', self.shape_id)

    def validate_route_id_exists_in_route_list(self, problems):
        if self._schedule:
            if self.route_id and self.route_id not in self._schedule.routes:
                problems.invalid_value('route_id', self.route_id)

    def validate_service_id_exists_in_service_list(self, problems):
        if self._schedule:
            if (self.service_id and
                    self.service_id not in self._schedule.service_periods):
                problems.invalid_value('service_id', self.service_id)

    def validate_bikes_allowed(self, problems):
        if self.bikes_allowed:
            util.validateYesNoUnknown(self.bikes_allowed, 'bikes_allowed', problems)

    def validate_wheelchair_accessible(self, problems):
        if self.wheelchair_accessible:
            util.validateYesNoUnknown(
                self.wheelchair_accessible, 'wheelchair_accessible', problems)

    def validate(self, problems, validate_children=True):
        """validate attributes of this object.

        Check that this object has all required values set to a valid value without
        reference to the rest of the schedule. If the _schedule attribute is set
        then check that references such as route_id and service_id are correct.

        Args:
          problems: A ProblemReporter object
          validate_children: if True and the _schedule attribute is set than call
                             validate_children
        """
        self.validate_route_id(problems)
        self.validate_service_period(problems)
        self.validate_direction_id(problems)
        self.validate_trip_id(problems)
        self.validate_shape_ids_exist_in_shape_list(problems)
        self.validate_route_id_exists_in_route_list(problems)
        self.validate_service_id_exists_in_service_list(problems)
        self.validate_bikes_allowed(problems)
        self.validate_wheelchair_accessible(problems)
        if self._schedule and validate_children:
            self.validate_children(problems)

    def validate_no_duplicate_stop_sequences(self, problems):
        cursor = self._schedule._connection.cursor()
        cursor.execute("SELECT COUNT(stop_sequence) AS a, stop_sequence "
                       "FROM stop_times "
                       "WHERE trip_id=? GROUP BY stop_sequence HAVING a > 1",
                       (self.trip_id,))
        for row in cursor:
            problems.invalid_value('stop_sequence', row[1],
                                  'Duplicate stop_sequence in trip_id %s' %
                                  self.trip_id)

    def validate_trip_start_and_end_times(self, problems, stoptimes):
        if stoptimes:
            if stoptimes[0].arrival_time is None and stoptimes[0].departure_time is None:
                problems.other_problem(
                    'No time for start of trip_id "%s""' % (self.trip_id))
            if stoptimes[-1].arrival_time is None and stoptimes[-1].departure_time is None:
                problems.other_problem(
                    'No time for end of trip_id "%s""' % (self.trip_id))

    def validate_stop_times_sequence_has_increasing_time_and_distance(self,
                                                                      problems,
                                                                      stoptimes):
        if stoptimes:
            route_class = self.get_gtfs_factory().Route
            # Checks that the arrival time for each time point is after the departure
            # time of the previous. Assumes a stoptimes sorted by sequence
            prev_departure = 0
            prev_stop = None
            prev_distance = None
            try:
                route_type = self._schedule.GetRoute(self.route_id).route_type
                max_speed = route_class._ROUTE_TYPES[route_type]['max_speed']
            except KeyError as e:
                # If route_type cannot be found, assume it is 0 (Tram) for checking
                # speeds between stops.
                max_speed = route_class._ROUTE_TYPES[0]['max_speed']
            for timepoint in stoptimes:
                # Distance should be a nonnegative float number, so it should be
                # always larger than None.
                distance = timepoint.shape_dist_traveled
                if distance is not None:
                    if distance > prev_distance and distance >= 0:
                        prev_distance = distance
                    else:
                        if distance == prev_distance:
                            type = problems_module.TYPE_WARNING
                        else:
                            type = problems_module.TYPE_ERROR
                        problems.invalid_value('stoptimes.shape_dist_traveled', distance,
                                              'For the trip %s the stop %s has shape_dist_traveled=%s, '
                                              'which should be larger than the previous ones. In this '
                                              'case, the previous distance was %s.' %
                                              (self.trip_id, timepoint.stop_id, distance, prev_distance),
                                              type=type)

                if timepoint.arrival_secs is not None:
                    self._check_speed(prev_stop, timepoint.stop, prev_departure,
                                      timepoint.arrival_secs, max_speed, problems)

                    if timepoint.arrival_secs >= prev_departure:
                        prev_departure = timepoint.departure_secs
                        prev_stop = timepoint.stop
                    else:
                        problems.other_problem('Timetravel detected! Arrival time '
                                              'is before previous departure '
                                              'at sequence number %s in trip %s' %
                                              (timepoint.stop_sequence, self.trip_id))

    def validate_shape_dist_traveled_smaller_than_max_shape_distance(self,
                                                                     problems,
                                                                     stoptimes):
        if stoptimes:
            if self.shape_id and self.shape_id in self._schedule._shapes:
                shape = self._schedule.GetShape(self.shape_id)
                max_shape_dist = shape.max_distance
                st = stoptimes[-1]
                if (st.shape_dist_traveled and
                        st.shape_dist_traveled > max_shape_dist):
                    problems.other_problem(
                        'In stop_times.txt, the stop with trip_id=%s and '
                        'stop_sequence=%d has shape_dist_traveled=%f, which is larger '
                        'than the max shape_dist_traveled=%f of the corresponding '
                        'shape (shape_id=%s)' %
                        (self.trip_id, st.stop_sequence, st.shape_dist_traveled,
                         max_shape_dist, self.shape_id),
                        type=problems_module.TYPE_WARNING)

    def validate_distance_from_stop_to_shape(self, problems, stoptimes):
        if stoptimes:
            if self.shape_id and self.shape_id in self._schedule._shapes:
                shape = self._schedule.GetShape(self.shape_id)
                max_shape_dist = shape.max_distance
                st = stoptimes[-1]
                # shape_dist_traveled is valid in shape if max_shape_dist larger than 0.
                if max_shape_dist > 0:
                    for st in stoptimes:
                        if st.shape_dist_traveled is None:
                            continue
                        pt = shape.GetPointWithDistanceTraveled(st.shape_dist_traveled)
                        if pt:
                            stop = self._schedule.GetStop(st.stop_id)
                            if stop.stop_lat and stop.stop_lon:
                                distance = util.ApproximateDistance(stop.stop_lat,
                                                                    stop.stop_lon,
                                                                    pt[0], pt[1])
                                if distance > problems_module.MAX_DISTANCE_FROM_STOP_TO_SHAPE:
                                    problems.StopTooFarFromShapeWithDistTraveled(
                                        self.trip_id, stop.stop_name, stop.stop_id, pt[2],
                                        self.shape_id, distance,
                                        problems_module.MAX_DISTANCE_FROM_STOP_TO_SHAPE)

    def validate_frequencies(self, problems):
        # O(n^2), but we don't anticipate many headway periods per trip
        for headway_index, headway in enumerate(self._headways[0:-1]):
            for other in self._headways[headway_index + 1:]:
                if (other[0] < headway[1]) and (other[1] > headway[0]):
                    problems.other_problem('Trip contains overlapping headway periods '
                                          '%s and %s' %
                                          (self._headway_output_tuple(headway),
                                           self._headway_output_tuple(other)))

    def validate_children(self, problems):
        """validate StopTimes and headways of this trip."""
        assert self._schedule, "Trip must be in a schedule to validate_children"
        # TODO: validate distance values in stop times (if applicable)

        self.validate_no_duplicate_stop_sequences(problems)
        stoptimes = self.get_stop_times(problems)
        stoptimes.sort(key=lambda x: x.stop_sequence)
        self.validate_trip_start_and_end_times(problems, stoptimes)
        self.validate_stop_times_sequence_has_increasing_time_and_distance(problems,
                                                                           stoptimes)
        self.validate_shape_dist_traveled_smaller_than_max_shape_distance(problems,
                                                                          stoptimes)
        self.validate_distance_from_stop_to_shape(problems, stoptimes)
        self.validate_frequencies(problems)

    def validate_before_add(self, problems):
        return True

    def validate_after_add(self, problems):
        self.validate(problems)

    def _check_speed(self, prev_stop, next_stop, depart_time,
                     arrive_time, max_speed, problems):
        # Checks that the speed between two stops is not faster than max_speed
        if prev_stop != None:
            try:
                time_between_stops = arrive_time - depart_time
            except TypeError:
                return

            dist_between_stops = \
                util.ApproximateDistanceBetweenStops(next_stop, prev_stop)
            if dist_between_stops is None:
                return

            if time_between_stops == 0:
                # HASTUS makes it hard to output GTFS with times to the nearest second;
                # it rounds times to the nearest minute. Therefore stop_times at the
                # same time ending in :00 are fairly common. These times off by no more
                # than 30 have not caused a problem. See
                # https://github.com/google/transitfeed/issues/193
                # Show a warning if times are not rounded to the nearest minute or
                # distance is more than max_speed for one minute.
                if depart_time % 60 != 0 or dist_between_stops / 1000 * 60 > max_speed:
                    problems.TooFastTravel(self.trip_id,
                                           prev_stop.stop_name,
                                           next_stop.stop_name,
                                           dist_between_stops,
                                           time_between_stops,
                                           speed=None,
                                           type=problems_module.TYPE_WARNING)
                return
            # This needs floating point division for precision.
            speed_between_stops = ((float(dist_between_stops) / 1000) /
                                   (float(time_between_stops) / 3600))
            if speed_between_stops > max_speed:
                problems.TooFastTravel(self.trip_id,
                                       prev_stop.stop_name,
                                       next_stop.stop_name,
                                       dist_between_stops,
                                       time_between_stops,
                                       speed_between_stops,
                                       type=problems_module.TYPE_WARNING)

    def add_to_schedule(self, schedule, problems):
        schedule.AddTripObject(self, problems)

    def sort_list_of_trip_by_time(self, trips):
        trips.sort(key=self.get_start_time)
