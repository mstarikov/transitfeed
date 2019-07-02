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
from __future__ import print_function

import logging
import time
from functools import reduce

from . import util
from .errors import TYPE_ERROR, TYPE_WARNING, TYPE_NOTICE, ALL_TYPES

MAX_DISTANCE_FROM_STOP_TO_SHAPE = 1000
MAX_DISTANCE_BETWEEN_STOP_AND_PARENT_STATION_WARNING = 100.0
MAX_DISTANCE_BETWEEN_STOP_AND_PARENT_STATION_ERROR = 1000.0


class ProblemReporter(object):
    """Base class for problem reporters. Tracks the current context and creates
       an exception object for each problem. Exception objects are sent to a
       Problem Accumulator, which is responsible for handling them."""

    def __init__(self, accumulator=None):
        self.clear_context()
        if accumulator is None:
            self.accumulator = SimpleProblemAccumulator()
        else:
            self.accumulator = accumulator

    def set_accumulator(self, accumulator):
        self.accumulator = accumulator

    def get_accumulator(self):
        return self.accumulator

    def clear_context(self):
        """Clear any previous context."""
        self._context = None

    def set_file_context(self, file_name, row_num, row, headers):
        """Save the current context to be output with any errors.

        Args:
          file_name: string
          row_num: int
          row: list of strings
          headers: list of column headers, its order corresponding to row's
        """
        self._context = (file_name, row_num, row, headers)

    def get_file_context(self):
        return self._context

    def add_to_accumulator(self, e):
        """report an exception to the Problem Accumulator"""
        self.accumulator._report(e)

    def new_version_available(self, version):
        e = new_version_available(version=version, type=TYPE_NOTICE,
                                  url='https://github.com/google/transitfeed')
        self.add_to_accumulator(e)

    def feed_not_found(self, feed_name, context=None, type=TYPE_ERROR):
        e = feed_not_found(feed_name=feed_name, context=context,
                           context2=self._context, type=type)
        self.add_to_accumulator(e)

    def unknown_format(self, feed_name, context=None, type=TYPE_ERROR):
        e = unknown_format(feed_name=feed_name, context=context,
                           context2=self._context, type=type)
        self.add_to_accumulator(e)

    def file_format(self, problem, context=None, type=TYPE_ERROR):
        e = file_format(problem=problem, context=context,
                        context2=self._context, type=type)
        self.add_to_accumulator(e)

    def missing_file(self, file_name, context=None, type=TYPE_ERROR):
        e = missing_file(file_name=file_name, context=context,
                         context2=self._context, type=type)
        self.add_to_accumulator(e)

    def unknown_file(self, file_name, context=None, type=TYPE_WARNING):
        e = unknown_file(file_name=file_name, context=context,
                         context2=self._context, type=type)
        self.add_to_accumulator(e)

    def empty_file(self, file_name, context=None, type=TYPE_ERROR):
        e = empty_file(file_name=file_name, context=context,
                       context2=self._context, type=type)
        self.add_to_accumulator(e)

    def missing_column(self, file_name, column_name, context=None,
                       type=TYPE_ERROR):
        e = missing_column(file_name=file_name, column_name=column_name,
                           context=context, context2=self._context,
                           type=type)
        self.add_to_accumulator(e)

    def unrecognized_column(self, file_name, column_name, context=None,
                            type=TYPE_WARNING):
        e = unrecognized_column(file_name=file_name, column_name=column_name,
                                context=context, context2=self._context, type=type)
        self.add_to_accumulator(e)

    def deprecated_column(self, file_name, column_name, new_name, context=None,
                          type=TYPE_WARNING):
        reason = None
        if not util.IsEmpty(new_name):
            reason = 'Please use the new column "%s" instead.' % (new_name)
        e = deprecated_column(file_name=file_name, column_name=column_name,
                              reason=reason, context=context, context2=self._context,
                              type=type)
        self.add_to_accumulator(e)

    def csv_syntax(self, description=None, context=None, type=TYPE_ERROR):
        e = csv_syntax(description=description, context=context,
                       context2=self._context, type=type)
        self.add_to_accumulator(e)

    def duplicate_column(self, file_name, header, count, type=TYPE_ERROR,
                         context=None):
        e = duplicate_column(file_name=file_name,
                             header=header,
                             count=count,
                             type=type,
                             context=context,
                             context2=self._context)
        self.add_to_accumulator(e)

    def missing_value(self, column_name, reason=None, context=None,
                      type=TYPE_ERROR):
        e = missing_value(column_name=column_name, reason=reason, context=context,
                          context2=self._context, type=type)
        self.add_to_accumulator(e)

    def invalid_value(self, column_name, value, reason=None, context=None,
                      type=TYPE_ERROR):
        e = invalid_value(column_name=column_name, value=value, reason=reason,
                          context=context, context2=self._context, type=type)
        self.add_to_accumulator(e)

    def invalid_float_value(self, value, reason=None, context=None,
                            type=TYPE_WARNING):
        e = invalid_float_value(value=value, reason=reason, context=context,
                                context2=self._context, type=type)
        self.add_to_accumulator(e)

    def invalid_non_negative_integer_value(self, value, reason=None, context=None,
                                           type=TYPE_WARNING):
        e = invalid_non_negative_integer_value(value=value, reason=reason,
                                               context=context, context2=self._context,
                                               type=type)
        self.add_to_accumulator(e)

    def duplicate_i_d(self, column_names, values, context=None, type=TYPE_ERROR):
        if isinstance(column_names, (tuple, list)):
            column_names = '(' + ', '.join(column_names) + ')'
        if isinstance(values, tuple):
            values = '(' + ', '.join(values) + ')'
        e = duplicate_i_d(column_name=column_names, value=values,
                          context=context, context2=self._context, type=type)
        self.add_to_accumulator(e)

    def invalid_agency_i_d(self, column_name, value, relating_type, relating_id,
                           context=None, type=TYPE_ERROR):
        e = invalid_agency_i_d(column_name=column_name, value=value,
                               relating_type=relating_type, relating_id=relating_id,
                               context=context, context2=self._context, type=type)
        self.add_to_accumulator(e)

    def unused_stop(self, stop_id, stop_name, context=None, type=TYPE_WARNING):
        e = unused_stop(stop_id=stop_id, stop_name=stop_name,
                        context=context, context2=self._context, type=type)
        self.add_to_accumulator(e)

    def used_station(self, stop_id, stop_name, context=None, type=TYPE_ERROR):
        e = used_station(stop_id=stop_id, stop_name=stop_name,
                         context=context, context2=self._context, type=type)
        self.add_to_accumulator(e)

    def stop_too_far_from_parent_station(self, stop_id, stop_name, parent_stop_id,
                                         parent_stop_name, distance,
                                         type=TYPE_WARNING, context=None):
        e = stop_too_far_from_parent_station(
            stop_id=stop_id, stop_name=stop_name,
            parent_stop_id=parent_stop_id,
            parent_stop_name=parent_stop_name, distance=distance,
            context=context, context2=self._context, type=type)
        self.add_to_accumulator(e)

    def stops_too_close(self, stop_name_a, stop_id_a, stop_name_b, stop_id_b,
                        distance, type=TYPE_WARNING, context=None):
        e = stops_too_close(
            stop_name_a=stop_name_a, stop_id_a=stop_id_a, stop_name_b=stop_name_b,
            stop_id_b=stop_id_b, distance=distance, context=context,
            context2=self._context, type=type)
        self.add_to_accumulator(e)

    def stations_too_close(self, stop_name_a, stop_id_a, stop_name_b, stop_id_b,
                           distance, type=TYPE_WARNING, context=None):
        e = stations_too_close(
            stop_name_a=stop_name_a, stop_id_a=stop_id_a, stop_name_b=stop_name_b,
            stop_id_b=stop_id_b, distance=distance, context=context,
            context2=self._context, type=type)
        self.add_to_accumulator(e)

    def different_station_too_close(self, stop_name, stop_id,
                                    station_stop_name, station_stop_id,
                                    distance, type=TYPE_WARNING, context=None):
        e = different_station_too_close(
            stop_name=stop_name, stop_id=stop_id,
            station_stop_name=station_stop_name, station_stop_id=station_stop_id,
            distance=distance, context=context, context2=self._context, type=type)
        self.add_to_accumulator(e)

    def stop_too_far_from_shape_with_dist_traveled(self, trip_id, stop_name, stop_id,
                                                   shape_dist_traveled, shape_id,
                                                   distance, max_distance,
                                                   type=TYPE_WARNING):
        e = stop_too_far_from_shape_with_dist_traveled(
            trip_id=trip_id, stop_name=stop_name, stop_id=stop_id,
            shape_dist_traveled=shape_dist_traveled, shape_id=shape_id,
            distance=distance, max_distance=max_distance, type=type)
        self.add_to_accumulator(e)

    def expiration_date(self, expiration, expiration_origin_file, context=None):
        e = expiration_date(expiration=expiration,
                            expiration_origin_file=expiration_origin_file,
                            context=context, context2=self._context,
                            type=TYPE_WARNING)
        self.add_to_accumulator(e)

    def future_service(self, start_date, start_date_origin_file, context=None):
        e = future_service(start_date=start_date,
                           start_date_origin_file=start_date_origin_file,
                           context=context, context2=self._context,
                           type=TYPE_WARNING)
        self.add_to_accumulator(e)

    def date_outside_valid_range(self, column_name, value, range_start_year,
                                 range_end_year, reason=None, context=None,
                                 type=TYPE_ERROR):
        e = date_outside_valid_range(column_name=column_name, value=value,
                                     reason=reason, range_start_year=range_start_year,
                                     range_end_year=range_end_year, context=context,
                                     context2=self._context, type=type)
        self.add_to_accumulator(e)

    def no_service_exceptions(self, start, end, type=TYPE_WARNING, context=None):
        e = no_service_exceptions(start=start, end=end, context=context,
                                  context2=self._context, type=type);
        self.add_to_accumulator(e)

    def invalid_line_end(self, bad_line_end, context=None, type=TYPE_WARNING):
        """bad_line_end is a human readable string."""
        e = invalid_line_end(bad_line_end=bad_line_end, context=context,
                             context2=self._context, type=type)
        self.add_to_accumulator(e)

    def too_fast_travel(self, trip_id, prev_stop, next_stop, dist, time, speed,
                        type=TYPE_ERROR):
        e = too_fast_travel(trip_id=trip_id, prev_stop=prev_stop,
                            next_stop=next_stop, time=time, dist=dist, speed=speed,
                            context=None, context2=self._context, type=type)
        self.add_to_accumulator(e)

    def stop_with_multiple_route_types(self, stop_name, stop_id, route_id1, route_id2,
                                       context=None, type=TYPE_WARNING):
        e = stop_with_multiple_route_types(stop_name=stop_name, stop_id=stop_id,
                                           route_id1=route_id1, route_id2=route_id2,
                                           context=context, context2=self._context,
                                           type=type)
        self.add_to_accumulator(e)

    def duplicate_trip(self, trip_id1, route_id1, trip_id2, route_id2,
                       context=None, type=TYPE_WARNING):
        e = duplicate_trip(trip_id1=trip_id1, route_id1=route_id1, trip_id2=trip_id2,
                           route_id2=route_id2, context=context,
                           context2=self._context, type=type)
        self.add_to_accumulator(e)

    def overlapping_trips_in_same_block(self, trip_id1, trip_id2, block_id,
                                        context=None, type=TYPE_WARNING):
        e = overlapping_trips_in_same_block(trip_id1=trip_id1, trip_id2=trip_id2,
                                            block_id=block_id, context=context,
                                            context2=self._context, type=type);
        self.add_to_accumulator(e)

    def transfer_distance_too_big(self, from_stop_id, to_stop_id, distance,
                                  context=None, type=TYPE_ERROR):
        e = transfer_distance_too_big(from_stop_id=from_stop_id, to_stop_id=to_stop_id,
                                      distance=distance, context=context,
                                      context2=self._context, type=type)
        self.add_to_accumulator(e)

    def transfer_walking_speed_too_fast(self, from_stop_id, to_stop_id, distance,
                                        transfer_time, context=None,
                                        type=TYPE_WARNING):
        e = transfer_walking_speed_too_fast(from_stop_id=from_stop_id,
                                            transfer_time=transfer_time,
                                            distance=distance,
                                            to_stop_id=to_stop_id, context=context,
                                            context2=self._context, type=type)
        self.add_to_accumulator(e)

    def other_problem(self, description, context=None, type=TYPE_ERROR):
        e = other_problem(description=description,
                          context=context, context2=self._context, type=type)
        self.add_to_accumulator(e)

    def too_many_days_without_service(self,
                                      first_day_without_service,
                                      last_day_without_service,
                                      consecutive_days_without_service,
                                      context=None,
                                      type=TYPE_WARNING):
        e = too_many_days_without_service(
            first_day_without_service=first_day_without_service,
            last_day_without_service=last_day_without_service,
            consecutive_days_without_service=consecutive_days_without_service,
            context=context,
            context2=self._context,
            type=type)
        self.add_to_accumulator(e)

    def minimum_transfer_time_set_with_invalid_transfer_type(self,
                                                             transfer_type=None,
                                                             context=None,
                                                             type=TYPE_ERROR):
        e = minimum_transfer_time_set_with_invalid_transfer_type(context=context,
                                                                 context2=self._context, transfer_type=transfer_type,
                                                                 type=type)
        self.add_to_accumulator(e)

    def too_many_consecutive_stop_times_with_same_time(self,
                                                       trip_id,
                                                       number_of_stop_times,
                                                       time_in_secs,
                                                       type=TYPE_WARNING):
        e = too_many_consecutive_stop_times_with_same_time(trip_id=trip_id,
                                                           number_of_stop_times=number_of_stop_times,
                                                           stop_time=util.FormatSecondsSinceMidnight(time_in_secs),
                                                           context=None,
                                                           context2=self._context,
                                                           type=type)
        self.add_to_accumulator(e)


class ProblemAccumulatorInterface(object):
    """The base class for Problem Accumulators, which defines their interface."""

    def _report(self, e):
        raise NotImplementedError("Please use a concrete Problem Accumulator that "
                                  "implements error and warning handling.")


class SimpleProblemAccumulator(ProblemAccumulatorInterface):
    """This is a basic problem accumulator that just prints to console."""

    def _report(self, e):
        context = e.format_context()
        if context:
            print(context)
        print(util.EncodeUnicode(self._line_wrap(e.format_problem(), 78)))

    @staticmethod
    def _line_wrap(text, width):
        """
        A word-wrap function that preserves existing line breaks
        and most spaces in the text. Expects that existing line
        breaks are posix newlines (\n).

        Taken from:
        http://aspn.activestate.com/ASPN/Cookbook/Python/Recipe/148061
        """
        return reduce(lambda line, word, width=width: '%s%s%s' %
                                                      (line,
                                                       ' \n'[(len(line) - line.rfind('\n') - 1 +
                                                              len(word.split('\n', 1)[0]) >= width)],
                                                       word),
                      text.split(' ')
                      )


class ExceptionWithContext(Exception):
    def __init__(self, context=None, context2=None, **kwargs):
        """Initialize an exception object, saving all keyword arguments in self.
        context and context2, if present, must be a tuple of (file_name, row_num,
        row, headers). context2 comes from ProblemReporter.set_file_context. context
        was passed in with the keyword arguments. context2 is ignored if context
        is present."""
        Exception.__init__(self)

        if context:
            self.__dict__.update(self.context_tuple_to_dict(context))
        elif context2:
            self.__dict__.update(self.context_tuple_to_dict(context2))
        self.__dict__.update(kwargs)

        if ('type' in kwargs) and (kwargs['type'] in ALL_TYPES):
            self._type = kwargs['type']
        else:
            self._type = TYPE_ERROR

    def get_type(self):
        return self._type

    def is_error(self):
        return self._type == TYPE_ERROR

    def is_warning(self):
        return self._type == TYPE_WARNING

    def is_notice(self):
        return self._type == TYPE_NOTICE

    CONTEXT_PARTS = ['file_name', 'row_num', 'row', 'headers']

    @staticmethod
    def context_tuple_to_dict(context):
        """Convert a tuple representing a context into a dict of (key, value) pairs
        """
        d = {}
        if not context:
            return d
        for k, v in zip(ExceptionWithContext.CONTEXT_PARTS, context):
            if v != '' and v != None:  # Don't ignore int(0), a valid row_num
                d[k] = v
        return d

    def __str__(self):
        return self.format_problem()

    def get_dict_to_format(self):
        """Return a copy of self as a dict, suitable for passing to format_problem"""
        d = {}
        for k, v in self.__dict__.items():
            # TODO: Better handling of unicode/utf-8 within Schedule objects.
            # Concatinating a unicode and utf-8 str object causes an exception such
            # as "UnicodeDecodeError: 'ascii' codec can't decode byte ..." as python
            # tries to convert the str to a unicode. To avoid that happening within
            # the problem reporter convert all unicode attributes to utf-8.
            # Currently valid utf-8 fields are converted to unicode in _ReadCsvDict.
            # Perhaps all fields should be left as utf-8.
            d[k] = util.EncodeUnicode(v)
        return d

    def format_problem(self, d=None):
        """Return a text string describing the problem.

        Args:
          d: map returned by get_dict_to_format with  with formatting added
        """
        if not d:
            d = self.get_dict_to_format()

        output_error_text = self.__class__.ERROR_TEXT % d
        if ('reason' in d) and d['reason']:
            return '%s\n%s' % (output_error_text, d['reason'])
        else:
            return output_error_text

    def format_context(self):
        """Return a text string describing the context"""
        text = ''
        if hasattr(self, 'feed_name'):
            text += "In feed '%s': " % self.feed_name
        if hasattr(self, 'file_name'):
            text += self.file_name
        if hasattr(self, 'row_num'):
            text += ":%i" % self.row_num
        if hasattr(self, 'column_name'):
            text += " column %s" % self.column_name
        return text

    def __cmp__(self, y):
        """Return an int <0/0/>0 when self is more/same/less significant than y.

        Subclasses should define this if exceptions should be listed in something
        other than the order they are reported.

        Args:
          y: object to compare to self

        Returns:
          An int which is negative if self is more significant than y, 0 if they
          are similar significance and positive if self is less significant than
          y. Returning a float won't work.

        Raises:
          TypeError by default, meaning objects of the type can not be compared.
        """
        raise TypeError("__cmp__ not defined")

    def get_order_key(self):
        """Return a tuple that can be used to sort problems into a consistent order.

        Returns:
          A list of values.
        """
        context_attributes = ['_type']
        context_attributes.extend(ExceptionWithContext.CONTEXT_PARTS)
        context_attributes.extend(self._get_extra_order_attributes())

        tokens = []
        for context_attribute in context_attributes:
            tokens.append(getattr(self, context_attribute, None))
        return tokens

    def _get_extra_order_attributes(self):
        """Return a list of extra attributes that should be used by get_order_key().

        The GetOrderkey method uses the list of class attributes defined in
        CONTEXT_PARTS to generate a list value that can be used as a comparison
        key for sorting problems in a consistent order.  Some specific problem
        types may which to define additional attributes that should be used
        when generating the order key.  They can override this method to do so.

        Returns:
          A list of class attribute names.
        """
        return []


class new_version_available(ExceptionWithContext):
    ERROR_TEXT = 'A new version %(version)s of transitfeed is available. ' \
                 'Please visit %(url)s and download the newest release.'


class missing_file(ExceptionWithContext):
    ERROR_TEXT = "File %(file_name)s is not found"


class empty_file(ExceptionWithContext):
    ERROR_TEXT = "File %(file_name)s is empty"


class unknown_file(ExceptionWithContext):
    ERROR_TEXT = 'The file named %(file_name)s was not expected.\n' \
                 'This may be a misspelled file name or the file may be ' \
                 'included in a subdirectory. Please check spellings and ' \
                 'make sure that there are no subdirectories within the feed'


class feed_not_found(ExceptionWithContext):
    ERROR_TEXT = 'Couldn\'t find a feed named %(feed_name)s'


class unknown_format(ExceptionWithContext):
    ERROR_TEXT = 'The feed named %(feed_name)s had an unknown format:\n' \
                 'feeds should be either .zip files or directories.'


class file_format(ExceptionWithContext):
    ERROR_TEXT = 'Files must be encoded in utf-8 and may not contain ' \
                 'any null bytes (0x00). %(file_name)s %(problem)s.'


class missing_column(ExceptionWithContext):
    ERROR_TEXT = 'Missing column %(column_name)s in file %(file_name)s'


class unrecognized_column(ExceptionWithContext):
    ERROR_TEXT = 'Unrecognized column %(column_name)s in file %(file_name)s. ' \
                 'This might be a misspelled column name (capitalization ' \
                 'matters!). Or it could be extra information (such as a ' \
                 'proposed feed extension) that the validator doesn\'t know ' \
                 'about yet. Extra information is fine; this warning is here ' \
                 'to catch misspelled optional column names.'


class deprecated_column(ExceptionWithContext):
    ERROR_TEXT = 'Column %(column_name)s in file %(file_name)s is deprecated ' \
                 'and support for it will eventually be removed. As such, it  ' \
                 'should not be used in new feeds.'


class csv_syntax(ExceptionWithContext):
    ERROR_TEXT = '%(description)s'


class duplicate_column(ExceptionWithContext):
    ERROR_TEXT = 'Column %(header)s appears %(count)i times in file %(file_name)s'

    def _get_extra_order_attributes(self):
        return ['header']


class missing_value(ExceptionWithContext):
    ERROR_TEXT = 'Missing value for column %(column_name)s'


class invalid_value(ExceptionWithContext):
    ERROR_TEXT = 'Invalid value %(value)s in field %(column_name)s'

    def _get_extra_order_attributes(self):
        return ['column_name']


class invalid_float_value(ExceptionWithContext):
    ERROR_TEXT = (
        "Invalid numeric value %(value)s. "
        "Please ensure that the number includes an explicit whole "
        "number portion (ie. use 0.5 instead of .5), that you do not use the "
        "exponential notation (ie. use 0.001 instead of 1E-3), and "
        "that it is a properly formated decimal value.")


class invalid_non_negative_integer_value(ExceptionWithContext):
    ERROR_TEXT = (
        "Invalid numeric value %(value)s. "
        "Please ensure that the number does not have a leading zero (ie. use "
        "3 instead of 03), and that it is a properly formated integer value.")


class duplicate_i_d(ExceptionWithContext):
    ERROR_TEXT = 'Duplicate ID %(value)s in column %(column_name)s'


class invalid_agency_i_d(ExceptionWithContext):
    ERROR_TEXT = 'The %(relating_type)s with ID %(relating_id)s specifies ' \
                 '%(column_name)s %(value)s which does not exist.'


class unused_stop(ExceptionWithContext):
    ERROR_TEXT = "%(stop_name)s (ID %(stop_id)s) isn't used in any trips"


class used_station(ExceptionWithContext):
    ERROR_TEXT = "%(stop_name)s (ID %(stop_id)s) has location_type=1 " \
                 "(station) so it should not appear in stop_times"


class stop_too_far_from_parent_station(ExceptionWithContext):
    ERROR_TEXT = (
        "%(stop_name)s (ID %(stop_id)s) is too far from its parent station "
        "%(parent_stop_name)s (ID %(parent_stop_id)s) : %(distance).2f meters.")

    def __cmp__(self, y):
        # Sort in decreasing order because more distance is more significant.
        return y.distance, self.distance


class stops_too_close(ExceptionWithContext):
    ERROR_TEXT = (
        "The stops \"%(stop_name_a)s\" (ID %(stop_id_a)s) and \"%(stop_name_b)s\""
        " (ID %(stop_id_b)s) are %(distance)0.2fm apart and probably represent "
        "the same location.")

    def __cmp__(self, y):
        # Sort in increasing order because less distance is more significant.
        return self.distance, y.distance


class stations_too_close(ExceptionWithContext):
    ERROR_TEXT = (
        "The stations \"%(stop_name_a)s\" (ID %(stop_id_a)s) and "
        "\"%(stop_name_b)s\" (ID %(stop_id_b)s) are %(distance)0.2fm apart and "
        "probably represent the same location.")

    def __cmp__(self, y):
        # Sort in increasing order because less distance is more significant.
        return self.distance, y.distance


class different_station_too_close(ExceptionWithContext):
    ERROR_TEXT = (
        "The parent_station of stop \"%(stop_name)s\" (ID %(stop_id)s) is not "
        "station \"%(station_stop_name)s\" (ID %(station_stop_id)s) but they are "
        "only %(distance)0.2fm apart.")

    def __cmp__(self, y):
        # Sort in increasing order because less distance is more significant.
        return self.distance, y.distance


class stop_too_far_from_shape_with_dist_traveled(ExceptionWithContext):
    ERROR_TEXT = (
        "For trip %(trip_id)s the stop \"%(stop_name)s\" (ID %(stop_id)s) is "
        "%(distance).0f meters away from the corresponding point "
        "(shape_dist_traveled: %(shape_dist_traveled)f) on shape %(shape_id)s. "
        "It should be closer than %(max_distance).0f meters.")

    def __cmp__(self, y):
        # Sort in decreasing order because more distance is more significant.
        return y.distance, self.distance


class too_many_days_without_service(ExceptionWithContext):
    ERROR_TEXT = "There are %(consecutive_days_without_service)i consecutive" \
                 " days, from %(first_day_without_service)s to" \
                 " %(last_day_without_service)s, without any scheduled service." \
                 " Please ensure this is intentional."


class minimum_transfer_time_set_with_invalid_transfer_type(ExceptionWithContext):
    ERROR_TEXT = "The field min_transfer_time should only be set when " \
                 "transfer_type is set to 2, but it is set to %(transfer_type)s."


class expiration_date(ExceptionWithContext):
    def format_problem(self, d=None):
        if not d:
            d = self.get_dict_to_format()
        expiration_origin_file = d['expiration_origin_file']
        expiration = d['expiration']
        formatted_date = time.strftime("%B %d, %Y",
                                       time.localtime(expiration))
        if expiration < time.mktime(time.localtime()):
            return "This feed expired on %s (%s)" % (formatted_date,
                                                     expiration_origin_file)
        else:
            return "This feed will soon expire, on %s (%s)" % (formatted_date,
                                                               expiration_origin_file)


class future_service(ExceptionWithContext):
    def format_problem(self, d=None):
        if not d:
            d = self.get_dict_to_format()
        start_date_origin_file = d['start_date_origin_file']
        formatted_date = time.strftime("%B %d, %Y", time.localtime(d['start_date']))
        return ("The %s in this feed is in the future, on %s. "
                "Published feeds must always include the current date." %
                (start_date_origin_file, formatted_date))


class date_outside_valid_range(ExceptionWithContext):
    ERROR_TEXT = "The date %(value)s in field %(column_name)s is not between " \
                 "the years %(range_start_year)d and %(range_end_year)d. It is " \
                 "advisable to create feeds with shorter validity periods to " \
                 "give feed consumers more confidence in their correctness."

    def _get_extra_order_attributes(self):
        return ['value']


class no_service_exceptions(ExceptionWithContext):
    ERROR_TEXT = "All services are defined on a weekly basis from %(start)s " \
                 "to %(end)s with no single day variations. If there are " \
                 "exceptions such as holiday service dates please ensure they " \
                 "are listed in calendar_dates.txt"


class invalid_line_end(ExceptionWithContext):
    ERROR_TEXT = "Each line must end with CR LF or LF except for the last line " \
                 "of the file. This line ends with \"%(bad_line_end)s\"."


class stop_with_multiple_route_types(ExceptionWithContext):
    ERROR_TEXT = "Stop %(stop_name)s (ID=%(stop_id)s) belongs to both " \
                 "subway (ID=%(route_id1)s) and bus line (ID=%(route_id2)s)."


class too_fast_travel(ExceptionWithContext):
    def format_problem(self, d=None):
        if not d:
            d = self.get_dict_to_format()
        if not d['speed']:
            return "High speed travel detected in trip %(trip_id)s: %(prev_stop)s" \
                   " to %(next_stop)s. %(dist).0f meters in %(time)d seconds." % d
        else:
            return "High speed travel detected in trip %(trip_id)s: %(prev_stop)s" \
                   " to %(next_stop)s. %(dist).0f meters in %(time)d seconds." \
                   " (%(speed).0f km/h)." % d

    def __cmp__(self, y):
        # Sort in decreasing order because more distance is more significant. We
        # can't sort by speed because not all too_fast_travel objects have a speed.
        return y.dist, self.dist


class duplicate_trip(ExceptionWithContext):
    ERROR_TEXT = "Trip %(trip_id1)s of route %(route_id1)s might be duplicated " \
                 "with trip %(trip_id2)s of route %(route_id2)s. They go " \
                 "through the same stops with same service."


class overlapping_trips_in_same_block(ExceptionWithContext):
    ERROR_TEXT = "Trip %(trip_id1)s and trip %(trip_id2)s both are in the " \
                 "same block %(block_id)s and have overlapping arrival times."


class transfer_distance_too_big(ExceptionWithContext):
    ERROR_TEXT = "Transfer from stop %(from_stop_id)s to stop " \
                 "%(to_stop_id)s has a distance of %(distance)s meters."


class transfer_walking_speed_too_fast(ExceptionWithContext):
    ERROR_TEXT = "Riders transfering from stop %(from_stop_id)s to stop " \
                 "%(to_stop_id)s would need to walk %(distance)s meters in " \
                 "%(transfer_time)s seconds."


class too_many_consecutive_stop_times_with_same_time(ExceptionWithContext):
    ERROR_TEXT = "Trip %(trip_id)s has %(number_of_stop_times)d consecutive " \
                 "stop times all with the same arrival/departure time: " \
                 "%(stop_time)s."


class other_problem(ExceptionWithContext):
    ERROR_TEXT = '%(description)s'


class ExceptionProblemAccumulator(ProblemAccumulatorInterface):
    """A problem accumulator that handles errors and optionally warnings by
       raising exceptions."""

    def __init__(self, raise_warnings=False):
        """Initialise.

        Args:
          raise_warnings: If this is True then warnings are also raised as
                          exceptions.
                          If it is false, warnings are printed to the console using
                          SimpleProblemAccumulator.
        """
        self.raise_warnings = raise_warnings
        self.accumulator = SimpleProblemAccumulator()

    def _report(self, e):
        if self.raise_warnings or e.is_error():
            raise e
        else:
            self.accumulator._report(e)


default_accumulator = ExceptionProblemAccumulator()
default_problem_reporter = ProblemReporter(default_accumulator)

# Add a default handler to send log messages to console
console = logging.StreamHandler()
console.setLevel(logging.WARNING)
log = logging.getLogger("schedule_builder")
log.addHandler(console)


# Below are the exceptions related to loading and setting up Feed Validator
# extensions

class ExtensionException(Exception):
    pass


class InvalidMapping(ExtensionException):
    def __init__(self, missing_field):
        self.missing_field = missing_field


class NonexistentMapping(ExtensionException):
    def __init__(self, name):
        self.name = name


class DuplicateMapping(ExtensionException):
    def __init__(self, name):
        self.name = name


class NonStandardMapping(ExtensionException):
    def __init__(self, name):
        self.name = name
