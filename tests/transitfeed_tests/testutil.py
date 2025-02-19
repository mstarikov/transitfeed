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

# Unit tests for transitfeed/util.py

import datetime
import re
try:
    from io import StringIO
    from urllib import request as urllib2
    from urllib.error import HTTPError, URLError
except ImportError:
    import StringIO
    from urllib2 import HTTPError, URLError
    import urllib2
import tests.util as test_util
from transitfeed import problems
from transitfeed.problems import ProblemReporter
from transitfeed import stop
from transitfeed import util
from transitfeed import version
import unittest


class ColorLuminanceTestCase(test_util.TestCase):
    def run_test(self):
        self.assertEqual(util.ColorLuminance('000000'), 0,
                         "ColorLuminance('000000') should be zero")
        self.assertEqual(util.ColorLuminance('FFFFFF'), 255,
                         "ColorLuminance('FFFFFF') should be 255")
        RGBmsg = ("ColorLuminance('RRGGBB') should be "
                  "0.299*<Red> + 0.587*<Green> + 0.114*<Blue>")
        decimal_places_tested = 8
        self.assertAlmostEqual(util.ColorLuminance('640000'), 29.9,
                               decimal_places_tested, RGBmsg)
        self.assertAlmostEqual(util.ColorLuminance('006400'), 58.7,
                               decimal_places_tested, RGBmsg)
        self.assertAlmostEqual(util.ColorLuminance('000064'), 11.4,
                               decimal_places_tested, RGBmsg)
        self.assertAlmostEqual(util.ColorLuminance('1171B3'),
                               0.299 * 17 + 0.587 * 113 + 0.114 * 179,
                               decimal_places_tested, RGBmsg)


class find_unique_idTestCase(test_util.TestCase):
    def test_simple(self):
        d = {}
        for i in range(0, 5):
            d[util.find_unique_id(d)] = 1
        k = d.keys()
        k.sort()
        self.assertEqual(('0', '1', '2', '3', '4'), tuple(k))

    def test__avoid_collision(self):
        d = {'1': 1}
        d[util.find_unique_id(d)] = 1
        self.assertEqual(2, len(d))
        self.assertFalse('3' in d, "Ops, next statement should add something to d")
        d['3'] = None
        d[util.find_unique_id(d)] = 1
        self.assertEqual(4, len(d))


class ApproximateDistanceBetweenStopsTestCase(test_util.TestCase):
    def test_equator(self):
        stop1 = stop.Stop(lat=0, lng=100, name='Stop one', stop_id='1')
        stop2 = stop.Stop(lat=0.01, lng=100.01, name='Stop two', stop_id='2')
        self.assertAlmostEqual(
            util.ApproximateDistanceBetweenStops(stop1, stop2),
            1570, -1)  # Compare first 3 digits

    def test_whati(self):
        stop1 = stop.Stop(lat=63.1, lng=-117.2, name='whati one', stop_id='1')
        stop2 = stop.Stop(lat=63.102, lng=-117.201, name='whati two', stop_id='2')
        self.assertAlmostEqual(
            util.ApproximateDistanceBetweenStops(stop1, stop2),
            228, 0)


class TimeConversionHelpersTestCase(test_util.TestCase):
    def test_time_to_seconds_since_midnight(self):
        self.assertEqual(util.TimeToSecondsSinceMidnight("01:02:03"), 3723)
        self.assertEqual(util.TimeToSecondsSinceMidnight("00:00:00"), 0)
        self.assertEqual(util.TimeToSecondsSinceMidnight("25:24:23"), 91463)
        try:
            util.TimeToSecondsSinceMidnight("10:15:00am")
        except problems.Error:
            pass  # expected
        else:
            self.fail("Should have thrown Error")

    def test_format_seconds_since_midnight(self):
        self.assertEqual(util.FormatSecondsSinceMidnight(3723), "01:02:03")
        self.assertEqual(util.FormatSecondsSinceMidnight(0), "00:00:00")
        self.assertEqual(util.FormatSecondsSinceMidnight(91463), "25:24:23")

    def test_date_string_to_date_object(self):
        self.assertEqual(util.DateStringToDateObject("20080901"),
                         datetime.date(2008, 9, 1))
        self.assertEqual(util.DateStringToDateObject("20080841"), None)


class ValidationUtilsTestCase(test_util.TestCase):
    def test_is_valid_u_r_l(self):
        self.assertTrue(util.IsValidURL("http://www.example.com"))
        self.assertFalse(util.IsValidURL("ftp://www.example.com"))
        self.assertFalse(util.IsValidURL(""))

    def test_validate_url(self):
        accumulator = test_util.RecordingProblemAccumulator(self)
        problems = ProblemReporter(accumulator)
        self.assertTrue(util.validate_url("", "col", problems))
        accumulator.AssertNoMoreExceptions()
        self.assertTrue(util.validate_url("http://www.example.com", "col",
                                         problems))
        accumulator.AssertNoMoreExceptions()
        self.assertFalse(util.validate_url("ftp://www.example.com", "col",
                                          problems))
        e = accumulator.Popinvalid_value("col")
        accumulator.AssertNoMoreExceptions()

    def test_is_valid_hex_color(self):
        self.assertTrue(util.IsValidHexColor("33FF00"))
        self.assertFalse(util.IsValidHexColor("blue"))
        self.assertFalse(util.IsValidHexColor(""))

    def test_is_valid_language_code(self):
        self.assertTrue(util.IsValidLanguageCode("de"))
        self.assertFalse(util.IsValidLanguageCode("Swiss German"))
        self.assertFalse(util.IsValidLanguageCode(""))

    def test_validate_language_code(self):
        accumulator = test_util.RecordingProblemAccumulator(self)
        problems = ProblemReporter(accumulator)
        self.assertTrue(util.validate_language_code("", "col", problems))
        accumulator.AssertNoMoreExceptions()
        self.assertTrue(util.validate_language_code("de", "col", problems))
        accumulator.AssertNoMoreExceptions()
        self.assertFalse(util.validate_language_code("Swiss German", "col",
                                                   problems))
        e = accumulator.Popinvalid_value("col")
        accumulator.AssertNoMoreExceptions()

    def test_is_valid_timezone(self):
        self.assertTrue(util.IsValidTimezone("America/Los_Angeles"))
        self.assertFalse(util.IsValidTimezone("Switzerland/Wil"))
        self.assertFalse(util.IsValidTimezone(""))

    def test_validate_timezone(self):
        accumulator = test_util.RecordingProblemAccumulator(self)
        problems = ProblemReporter(accumulator)
        self.assertTrue(util.ValidateTimezone("", "col", problems))
        accumulator.AssertNoMoreExceptions()
        self.assertTrue(util.ValidateTimezone("America/Los_Angeles", "col",
                                              problems))
        accumulator.AssertNoMoreExceptions()
        self.assertFalse(util.ValidateTimezone("Switzerland/Wil", "col",
                                               problems))
        e = accumulator.Popinvalid_value("col")
        accumulator.AssertNoMoreExceptions()

    def test_is_valid_date(self):
        self.assertTrue(util.IsValidDate("20100801"))
        self.assertFalse(util.IsValidDate("20100732"))
        self.assertFalse(util.IsValidDate(""))

    def test_validate_date(self):
        accumulator = test_util.RecordingProblemAccumulator(self)
        problems = ProblemReporter(accumulator)
        self.assertTrue(util.validate_date("", "col", problems))
        accumulator.AssertNoMoreExceptions()
        self.assertTrue(util.validate_date("20100801", "col", problems))
        accumulator.AssertNoMoreExceptions()
        self.assertFalse(util.validate_date("20100732", "col", problems))
        e = accumulator.Popinvalid_value("col")
        accumulator.AssertNoMoreExceptions()


class float_string_to_floatTestCase(test_util.TestCase):
    def run_test(self):
        accumulator = test_util.RecordingProblemAccumulator(self)
        problems = ProblemReporter(accumulator)

        self.assertAlmostEqual(0, util.float_string_to_float("0", problems))
        self.assertAlmostEqual(0, util.float_string_to_float(u"0", problems))
        self.assertAlmostEqual(1, util.float_string_to_float("1", problems))
        self.assertAlmostEqual(1, util.float_string_to_float("1.00000", problems))
        self.assertAlmostEqual(1.5, util.float_string_to_float("1.500", problems))
        self.assertAlmostEqual(-2, util.float_string_to_float("-2.0", problems))
        self.assertAlmostEqual(-2.5, util.float_string_to_float("-2.5", problems))
        self.assertRaises(ValueError, util.float_string_to_float, ".", problems)
        self.assertRaises(ValueError, util.float_string_to_float, "0x20", problems)
        self.assertRaises(ValueError, util.float_string_to_float, "-0x20", problems)
        self.assertRaises(ValueError, util.float_string_to_float, "0b10", problems)

        # These should issue a warning, but otherwise parse successfully
        self.assertAlmostEqual(0.001, util.float_string_to_float("1E-3", problems))
        e = accumulator.PopException("InvalidFloatValue")
        self.assertAlmostEqual(0.001, util.float_string_to_float(".001", problems))
        e = accumulator.PopException("InvalidFloatValue")
        self.assertAlmostEqual(-0.001, util.float_string_to_float("-.001", problems))
        e = accumulator.PopException("InvalidFloatValue")
        self.assertAlmostEqual(0, util.float_string_to_float("0.", problems))
        e = accumulator.PopException("InvalidFloatValue")

        accumulator.AssertNoMoreExceptions()


class non_neg_int_string_to_intTestCase(test_util.TestCase):
    def run_test(self):
        accumulator = test_util.RecordingProblemAccumulator(self)
        problems = ProblemReporter(accumulator)

        self.assertEqual(0, util.non_neg_int_string_to_int("0", problems))
        self.assertEqual(0, util.non_neg_int_string_to_int(u"0", problems))
        self.assertEqual(1, util.non_neg_int_string_to_int("1", problems))
        self.assertEqual(2, util.non_neg_int_string_to_int("2", problems))
        self.assertEqual(10, util.non_neg_int_string_to_int("10", problems))
        self.assertEqual(1234567890123456789,
                         util.non_neg_int_string_to_int("1234567890123456789",
                                                   problems))
        self.assertRaises(ValueError, util.non_neg_int_string_to_int, "", problems)
        self.assertRaises(ValueError, util.non_neg_int_string_to_int, "-1", problems)
        self.assertRaises(ValueError, util.non_neg_int_string_to_int, "0x1", problems)
        self.assertRaises(ValueError, util.non_neg_int_string_to_int, "1.0", problems)
        self.assertRaises(ValueError, util.non_neg_int_string_to_int, "1e1", problems)
        self.assertRaises(ValueError, util.non_neg_int_string_to_int, "0x20", problems)
        self.assertRaises(ValueError, util.non_neg_int_string_to_int, "0b10", problems)
        self.assertRaises(TypeError, util.non_neg_int_string_to_int, 1, problems)
        self.assertRaises(TypeError, util.non_neg_int_string_to_int, None, problems)

        # These should issue a warning, but otherwise parse successfully
        self.assertEqual(1, util.non_neg_int_string_to_int("+1", problems))
        e = accumulator.PopException("InvalidNonNegativeIntegerValue")

        self.assertEqual(1, util.non_neg_int_string_to_int("01", problems))
        e = accumulator.PopException("InvalidNonNegativeIntegerValue")

        self.assertEqual(0, util.non_neg_int_string_to_int("00", problems))
        e = accumulator.PopException("InvalidNonNegativeIntegerValue")

        accumulator.AssertNoMoreExceptions()


class CheckVersionTestCase(test_util.TempDirTestCaseBase):
    def set_up(self):
        self.orig_urlopen = urllib2.urlopen
        self.mock = MockURLOpen()
        self.accumulator = test_util.RecordingProblemAccumulator(self)
        self.problems = ProblemReporter(self.accumulator)

    def tear_down(self):
        self.mock = None
        urllib2.urlopen = self.orig_urlopen

    def test_assigned_different_version(self):
        util.check_version(self.problems, '100.100.100')
        e = self.accumulator.PopException('new_version_available')
        self.assertEqual(e.version, '100.100.100')
        self.assertEqual(e.url, 'https://github.com/google/transitfeed')
        self.accumulator.AssertNoMoreExceptions()

    def test_assigned_same_version(self):
        util.check_version(self.problems, version.__version__)
        self.accumulator.AssertNoMoreExceptions()

    def test_get_correct_returns(self):
        urllib2.urlopen = self.mock.mocked_connect_success
        util.check_version(self.problems)
        self.accumulator.PopException('new_version_available')

    def test_page_not_found(self):
        urllib2.urlopen = self.mock.mocked_page_not_found
        util.check_version(self.problems)
        e = self.accumulator.PopException('other_problem')
        self.assertTrue(re.search(r'we failed to reach', e.description))
        self.assertTrue(re.search(r'Reason: Not Found \[404\]', e.description))

    def test_connection_time_out(self):
        urllib2.urlopen = self.mock.mocked_connection_time_out
        util.check_version(self.problems)
        e = self.accumulator.PopException('other_problem')
        self.assertTrue(re.search(r'we failed to reach', e.description))
        self.assertTrue(re.search(r'Reason: Connection timed', e.description))

    def test_get_addr_info_failed(self):
        urllib2.urlopen = self.mock.mocked_get_addr_info_failed
        util.check_version(self.problems)
        e = self.accumulator.PopException('other_problem')
        self.assertTrue(re.search(r'we failed to reach', e.description))
        self.assertTrue(re.search(r'Reason: Getaddrinfo failed', e.description))

    def test_empty_is_returned(self):
        urllib2.urlopen = self.mock.mocked_empty_is_returned
        util.check_version(self.problems)
        e = self.accumulator.PopException('other_problem')
        self.assertTrue(re.search(r'we had trouble parsing', e.description))


class MockURLOpen:
    """Pretend to be a urllib2.urlopen suitable for testing."""

    def mocked_connect_success(self, request):
        return StringIO.StringIO('latest_version=100.0.1')

    def mocked_page_not_found(self, request):
        raise HTTPError(request.get_full_url(), 404, 'Not Found',
                        request.header_items(), None)

    def mocked_connection_time_out(self, request):
        raise URLError('Connection timed out')

    def mocked_get_addr_info_failed(self, request):
        raise URLError('Getaddrinfo failed')

    def mocked_empty_is_returned(self, request):
        return StringIO.StringIO()


if __name__ == '__main__':
    unittest.main()
