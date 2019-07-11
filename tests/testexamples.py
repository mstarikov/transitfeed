#!/usr/bin/python2.5

# Test the examples to make sure they are not broken

from __future__ import absolute_import
import os
import re
from transitfeed import problems, loader
import unittest
import urllib
from tests import util


class WikiExample(util.TempDirTestCaseBase):
    # Download example from wiki and run it
    def run_test(self):
        wiki_source = urllib.urlopen(
            'https://raw.githubusercontent.com/wiki/google/transitfeed/TransitFeed.md'
        ).read()
        m = re.search(r'```\s*(import transitfeed.*)```', wiki_source, re.DOTALL)
        if not m:
            raise Exception("Failed to find source code on wiki page")
        wiki_code = m.group(1)
        exec(wiki_code)


class ShuttleFromXMLFeed(util.TempDirTestCaseBase):
    def run_test(self):
        self.check_call_with_path(
            [self.get_example_path('ShuttleFromXMLFeed.py'),
             '--input', 'file:' + self.get_example_path('ShuttleFromXMLFeed.xml'),
             '--output', 'shuttle-YYYYMMDD.zip',
             # save the path of the dated output to tempfilepath
             '--execute', 'echo %(path)s > outputpath'])

        dated_path = open('outputpath').read().strip()
        self.assertTrue(re.match(r'shuttle-20\d\d[01]\d[0123]\d.zip$', dated_path))
        if not os.path.exists(dated_path):
            raise Exception('did not create expected file')


class Table(util.TempDirTestCaseBase):
    def run_test(self):
        self.check_call_with_path(
            [self.get_example_path('table.py'),
             '--input', self.get_example_path('table.txt'),
             '--output', 'google_transit.zip'])
        if not os.path.exists('google_transit.zip'):
            raise Exception('should have created output')


class SmallBuilder(util.TempDirTestCaseBase):
    def run_test(self):
        self.check_call_with_path(
            [self.get_example_path('SmallBuilder.py'),
             '--output', 'google_transit.zip'])
        if not os.path.exists('google_transit.zip'):
            raise Exception('should have created output')


class GoogleRandomQueries(util.TempDirTestCaseBase):
    def test_normal_run(self):
        self.check_call_with_path(
            [self.get_example_path('GoogleRandomQueries.py'),
             '--output', 'queries.html',
             '--limit', '5',
             self.get_path('tests', 'data', 'good_feed')])
        if not os.path.exists('queries.html'):
            raise Exception('should have created output')

    def test_invalid_feed_still_works(self):
        self.check_call_with_path(
            [self.get_example_path('GoogleRandomQueries.py'),
             '--output', 'queries.html',
             '--limit', '5',
             self.get_path('tests', 'data', 'invalid_route_agency')])
        if not os.path.exists('queries.html'):
            raise Exception('should have created output')

    def test_bad_args(self):
        self.check_call_with_path(
            [self.get_example_path('GoogleRandomQueries.py'),
             '--output', 'queries.html',
             '--limit', '5'],
            expected_retcode=2)
        if os.path.exists('queries.html'):
            raise Exception('should not have created output')


class FilterUnusedStops(util.TempDirTestCaseBase):
    def test_normal_run(self):
        unused_stop_path = self.get_path('tests', 'data', 'unused_stop')
        # Make sure original data has an unused stop.
        accumulator = util.RecordingProblemAccumulator(self, ("ExpirationDate"))
        problem_reporter = problems.ProblemReporter(accumulator)
        loader.Loader(
            unused_stop_path,
            problems=problem_reporter, extra_validation=True).Load()
        accumulator.PopException("UnusedStop")
        accumulator.AssertNoMoreExceptions()

        (stdout, stderr) = self.check_call_with_path(
            [self.get_example_path('FilterUnusedStops.py'),
             '--list_removed',
             unused_stop_path, 'output.zip'])
        # Extra stop was listed on stdout
        self.assertNotEqual(stdout.find('Bogus Stop'), -1)

        # Make sure unused stop was removed and another stop still exists.
        schedule = transitfeed.Loader(
            'output.zip', problems=problem_reporter, extra_validation=True).Load()
        schedule.GetStop('STAGECOACH')
        accumulator.AssertNoMoreExceptions()


if __name__ == '__main__':
    unittest.main()
