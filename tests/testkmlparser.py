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

# Unit tests for the kmlparser module.

from __future__ import absolute_import
import kmlparser
import os.path
import shutil
import transitfeed
try:
    from io import StringIO
except ImportError:
    from StringIO import StringIO
from tests import util
import unittest


class TestStopsParsing(util.GetPathTestCase):
    def test_single_stop(self):
        feed = transitfeed.Schedule()
        kmlFile = self.get_test_data_path('one_stop.kml')
        kmlparser.KMLParser().parse(kmlFile, feed)
        stops = feed.get_stop_list()
        self.assertEqual(1, len(stops))
        stop = stops[0]
        self.assertEqual(u'Stop Name', stop.stop_name)
        self.assertAlmostEqual(-93.239037, stop.stop_lon)
        self.assertAlmostEqual(44.854164, stop.stop_lat)
        write_output = StringIO()
        feed.write_google_transit_feed(write_output)

    def test_single_shape(self):
        feed = transitfeed.Schedule()
        kmlFile = self.get_test_data_path('one_line.kml')
        kmlparser.KMLParser().parse(kmlFile, feed)
        shapes = feed.get_shape_list()
        self.assertEqual(1, len(shapes))
        shape = shapes[0]
        self.assertEqual(3, len(shape.points))
        self.assertAlmostEqual(44.854240, shape.points[0][0])
        self.assertAlmostEqual(-93.238861, shape.points[0][1])
        self.assertAlmostEqual(44.853081, shape.points[1][0])
        self.assertAlmostEqual(-93.238708, shape.points[1][1])
        self.assertAlmostEqual(44.852638, shape.points[2][0])
        self.assertAlmostEqual(-93.237923, shape.points[2][1])
        write_output = StringIO()
        feed.write_google_transit_feed(write_output)


class FullTests(util.TempDirTestCaseBase):
    def test_normal_run(self):
        shutil.copyfile(self.get_test_data_path('one_stop.kml'), 'one_stop.kml')
        out, err = self.check_call_with_path([self.get_path('kmlparser.py'), 'one_stop.kml', 'one_stop.zip'])
        # There will be lots of problems, but ignore them
        accumulator = util.RecordingProblemAccumulator(self)
        problems = transitfeed.ProblemReporter(accumulator)
        schedule = transitfeed.Loader('one_stop.zip', problems=problems).Load()
        self.assertEquals(len(schedule.get_stop_list()), 1)
        self.assertFalse(os.path.exists('transitfeedcrash.txt'))

    def test_command_line_error(self):
        (out, err) = self.check_call_with_path([self.get_path('kmlparser.py')], expected_retcode=2)
        self.assertMatchesRegex(r'did not provide .+ arguments', err)
        self.assertMatchesRegex(r'[Uu]sage:', err)
        self.assertFalse(os.path.exists('transitfeedcrash.txt'))

    def test_crash_handler(self):
        (out, err) = self.check_call_with_path(
            [self.get_path('kmlparser.py'), 'IWantMyCrash', 'output.zip'],
            stdin_str="\n", expected_retcode=127)
        self.assertMatchesRegex(r'Yikes', out)
        crashout = open('transitfeedcrash.txt').read()
        self.assertMatchesRegex(r'For test_crash_handler', crashout)


if __name__ == '__main__':
    unittest.main()
