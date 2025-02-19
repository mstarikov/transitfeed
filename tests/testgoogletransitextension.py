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

# Unit tests for the googletransit extension (extensions.googletransit)

from __future__ import absolute_import
import extensions.googletransit

import os
import re
import transitfeed
from tests.testfeedvalidator import FullTests
from tests.util import MemoryZipTestCase, ValidationTestCase


class ExtensionFullTests(FullTests):
    """Inherits FullTests from testfeedvalidator.py to test the extension
    executable feedvalidator_googletransit.py. Tests the extension executable with
    new good_feed test data which uses extension capabilities."""

    feedvalidator_executable = 'feedvalidator_googletransit.py'
    extension_name = 'extensions.googletransit'
    additional_arguments = ['--error_types_ignore_list',
                            'DeprecatedColumn']

    def test_google_transit_good_feed(self):
        (out, err) = self.check_call_with_path(
            [self.get_path(self.feedvalidator_executable), '-n', '--latest_version',
             transitfeed.__version__] + self.additional_arguments +
            [self.get_path('tests', 'data', 'googletransit', 'good_feed')])
        self.assertTrue(re.search(r'feed validated successfully', out))
        self.assertFalse(re.search(r'ERROR', out))
        htmlout = open('validation-results.html').read()
        self.assertMatchesRegex(
            self.extension_message + self.extension_name, htmlout)
        self.assertTrue(re.search(r'feed validated successfully', htmlout))
        self.assertFalse(re.search(r'ERROR', htmlout))
        self.assertFalse(os.path.exists('transitfeedcrash.txt'))


class ExtensionMemoryZipTestCase(MemoryZipTestCase):
    """ExtendMemoryZipTestCase to also ignore DeprecatedColumn errors.

       In this extension a couple of columns are set to be 'Deprecated'.
       The 'normal' transitfeed test data used in some of the test cases here
       however still uses these columns. As we can/should not modify the 'normal'
       test data we are adding the 'DeprecatedColumn' to the _IGNORE_TYPES list.
    """

    _IGNORE_TYPES = MemoryZipTestCase._IGNORE_TYPES + ["DeprecatedColumn"]


class FareAttributeAgencyIdTestCase(ExtensionMemoryZipTestCase):
    gtfs_factory = extensions.googletransit.get_gtfs_factory()

    def test_no_errors_with_one_agency_and_no_id_and_agency_id_column_not_present(self):
        self.set_archive_contents(
            "fare_attributes.txt",
            "fare_id,price,currency_type,payment_method,transfers\n"
            "fare1,1,EUR,1,0\n")
        self.set_archive_contents(
            "agency.txt",
            "agency_id,agency_name,agency_url,agency_timezone,agency_lang\n"
            ",Demo Agency,http://google.com,America/Los_Angeles,en\n")
        self.set_archive_contents(
            "routes.txt",
            "route_id,agency_id,route_short_name,route_long_name,route_type\n"
            "AB,,,Airport Bullfrog,3\n")
        self.make_loader_and_load(self.problems, gtfs_factory=self.gtfs_factory)
        self.accumulator.AssertNoMoreExceptions()

    def test_no_errors_with_one_agency_and_no_id_and_agency_id_column_present(self):
        self.set_archive_contents(
            "fare_attributes.txt",
            "fare_id,price,currency_type,payment_method,transfers,agency_id\n"
            "fare1,1,EUR,1,0,\n")
        self.set_archive_contents(
            "agency.txt",
            "agency_id,agency_name,agency_url,agency_timezone,agency_lang\n"
            ",Demo Agency,http://google.com,America/Los_Angeles,en\n")
        self.set_archive_contents(
            "routes.txt",
            "route_id,agency_id,route_short_name,route_long_name,route_type\n"
            "AB,,,Airport Bullfrog,3\n")
        self.make_loader_and_load(self.problems, gtfs_factory=self.gtfs_factory)
        self.accumulator.AssertNoMoreExceptions()

    def test_no_errors_with_several_agencies(self):
        self.set_archive_contents(
            "fare_attributes.txt",
            "fare_id,price,currency_type,payment_method,transfers,agency_id\n"
            "fare1,1,EUR,1,0,DTA\n"
            "fare2,2,EUR,0,0,ATD\n")
        self.set_archive_contents(
            "agency.txt",
            "agency_id,agency_name,agency_url,agency_timezone,agency_lang\n"
            "DTA,Demo Agency,http://google.com,America/Los_Angeles,en\n"
            "ATD,Another Demo Agency,http://example.com,America/Los_Angeles,en\n")
        self.make_loader_and_load(self.problems, gtfs_factory=self.gtfs_factory)
        self.accumulator.AssertNoMoreExceptions()

    def test_wrong_id_with_one_agency_with_no_id(self):
        self.set_archive_contents(
            "fare_attributes.txt",
            "fare_id,price,currency_type,payment_method,transfers,agency_id\n"
            "fare1,1,EUR,1,0,DOESNOTEXIST\n")
        self.set_archive_contents(
            "routes.txt",
            "route_id,agency_id,route_short_name,route_long_name,route_type\n"
            "AB,,,Airport Bullfrog,3\n")
        self.set_archive_contents(
            "agency.txt",
            "agency_id,agency_name,agency_url,agency_timezone,agency_lang\n"
            ",Demo Agency,http://google.com,America/Los_Angeles,en\n")
        self.make_loader_and_load(self.problems, gtfs_factory=self.gtfs_factory)
        e = self.accumulator.PopException("InvalidAgencyID")
        self.assertEquals('agency_id', e.column_name)
        self.accumulator.AssertNoMoreExceptions()

    def test_wrong_id_with_one_agency_with_id(self):
        self.set_archive_contents("fare_attributes.txt",
                                "fare_id,price,currency_type,payment_method,transfers,agency_id\n"
                                "fare1,1,EUR,1,0,DOESNOTEXIST\n")
        self.set_archive_contents(
            "agency.txt",
            "agency_id,agency_name,agency_url,agency_timezone,agency_lang\n"
            "DTA,Demo Agency,http://google.com,America/Los_Angeles,en\n")
        self.make_loader_and_load(self.problems, gtfs_factory=self.gtfs_factory)
        e = self.accumulator.PopException("InvalidAgencyID")
        self.assertEquals('agency_id', e.column_name)
        self.accumulator.AssertNoMoreExceptions()

    def test_wrong_id_with_several_agencies(self):
        self.set_archive_contents(
            "fare_attributes.txt",
            "fare_id,price,currency_type,payment_method,transfers,"
            "agency_id\n"
            "fare1,1,EUR,1,0,DTA\n"
            "fare2,2,EUR,0,1,ATD\n"
            "fare3,2,EUR,0,2,DOESNOTEXIST\n")
        self.set_archive_contents(
            "agency.txt",
            "agency_id,agency_name,agency_url,agency_timezone,agency_lang\n"
            "DTA,Demo Agency,http://google.com,America/Los_Angeles,en\n"
            "ATD,Another Demo Agency,http://example.com,America/Los_Angeles,en\n")
        self.make_loader_and_load(self.problems, gtfs_factory=self.gtfs_factory)
        e = self.accumulator.PopException("InvalidAgencyID")
        self.assertEquals('agency_id', e.column_name)
        self.accumulator.AssertNoMoreExceptions()


class StopExtensionIntegrationTestCase(ExtensionMemoryZipTestCase):
    gtfs_factory = extensions.googletransit.get_gtfs_factory()

    def test_no_errors(self):
        self.set_archive_contents("stops.txt",
                                "stop_id,stop_name,stop_lat,stop_lon,stop_timezone,location_type,"
                                "parent_station,vehicle_type\n"
                                "BEATTY,Beatty,36.868446,-116.784582,,1,,1100\n"
                                "BEATTY_AIRPORT,Airport West,36.868446,-116.784582,,2,BEATTY,\n"
                                "BULLFROG,Bullfrog,36.88108,-116.81797,,,,3\n"
                                "STAGECOACH,Stagecoach Hotel,36.915682,-116.751677,America/Los_Angeles,"
                                ",,204\n")
        self.make_loader_and_load(self.problems, gtfs_factory=self.gtfs_factory)
        self.accumulator.AssertNoMoreExceptions()

    def test_invalid_vehicle_type(self):
        self.set_archive_contents("stops.txt",
                                "stop_id,stop_name,stop_lat,stop_lon,stop_timezone,location_type,"
                                "parent_station,vehicle_type\n"
                                "BEATTY,Beatty,36.868446,-116.784582,,1,,2557\n"  # bad vehicle type
                                "BEATTY_AIRPORT,Airport West,36.868446,-116.784582,,2,BEATTY,\n"
                                "BULLFROG,Bullfrog,36.88108,-116.81797,,,,3\n"
                                "STAGECOACH,Stagecoach Hotel,36.915682,-116.751677,America/Los_Angeles,"
                                ",,204\n")
        self.make_loader_and_load(self.problems, gtfs_factory=self.gtfs_factory)
        self.accumulator.Popinvalid_value("vehicle_type")
        self.accumulator.AssertNoMoreExceptions()


class StopExtensionTestCase(ValidationTestCase):
    gtfs_factory = extensions.googletransit.get_gtfs_factory()

    def set_up(self):
        super(StopExtensionTestCase, self).set_up()

        self._stop = self.gtfs_factory.Stop(
            lng=1.00, lat=48.1, name="a stop", stop_id="stop")
        self._stop._gtfs_factory = self.gtfs_factory

        self._parent_stop = self.gtfs_factory.Stop(
            lng=1.00, lat=48.2, name="parent stop", stop_id="parent_stop")
        self._parent_stop._gtfs_factory = self.gtfs_factory

        self._child_stop = self.gtfs_factory.Stop(
            lng=1.00, lat=48.2, name="child stop", stop_id="child stop")
        self._child_stop.parent_station = self._parent_stop.stop_id
        self._child_stop._gtfs_factory = self.gtfs_factory

        self._entrance = self.gtfs_factory.Stop(
            lng=1.00, lat=48.2, name="an entrance", stop_id="entrance")
        self._entrance.location_type = 2
        self._entrance.parent_station = self._parent_stop.stop_id
        self._entrance._gtfs_factory = self.gtfs_factory

    def test_validate_vehicle_type(self):
        # Test with non-integer value
        self._stop.vehicle_type = 'abc'
        self._stop.Validate(self.problems)
        self.accumulator.Popinvalid_value('vehicle_type')
        self.accumulator.AssertNoMoreExceptions()

        # Test with not known value
        self._stop.vehicle_type = 2547
        self._stop.Validate(self.problems)
        self.accumulator.Popinvalid_value('vehicle_type')
        self.accumulator.AssertNoMoreExceptions()

    def test_entrance_exceptions(self):
        # There should be no error validating _entrance
        self._entrance.Validate(self.problems)
        self.accumulator.AssertNoMoreExceptions()

        # An entrance must not have a stop_timezone
        self._entrance.stop_timezone = 'America/Los_Angeles'
        self._entrance.Validate(self.problems)
        e = self.accumulator.Popinvalid_value('stop_timezone')
        self.assertMatchesRegex(r'stop_timezone', e.FormatProblem())
        self.accumulator.AssertNoMoreExceptions()
        self._entrance.stop_timezone = None

        # An entrance must not have a vehicle type
        self._entrance.vehicle_type = 200
        self._entrance.Validate(self.problems)
        e = self.accumulator.Popinvalid_value('vehicle_type')
        self.accumulator.AssertNoMoreExceptions()
        self._entrance.vehicle_type = None

        # An entrance should have a parent station
        self._entrance.parent_station = None
        self._entrance.Validate(self.problems)
        e = self.accumulator.Popinvalid_value('location_type')
        self.assertMatchesRegex(r'parent_station', e.FormatProblem())
        self.accumulator.AssertNoMoreExceptions()

    def test_child_exceptions(self):
        # There should be no error validating _child_stop
        self._child_stop.Validate(self.problems)
        self.accumulator.AssertNoMoreExceptions()

        # A _child_stop must not have a stop_timezone
        self._child_stop.stop_timezone = 'America/Los_Angeles'
        self._child_stop.Validate(self.problems)
        e = self.accumulator.Popinvalid_value('stop_timezone')
        self.assertMatchesRegex(r'stop_timezone', e.FormatProblem())
        self.assertTrue(e.IsWarning())
        self.accumulator.AssertNoMoreExceptions()
        self._child_stop.stop_timezone = None

        # Adding vehicle_type, Google transit doesn't read child stop vehicle types
        self._child_stop.vehicle_type = 200
        self._child_stop.Validate(self.problems)
        e = self.accumulator.Popinvalid_value('vehicle_type')
        self.assertTrue(e.IsWarning())
        self.accumulator.AssertNoMoreExceptions()
        self._child_stop.vehicle_type = None

    def test_allow_empty_stop_name_if_entrance(self):
        # Empty stop_name with default location_type=0 should report missing_value
        self._stop.stop_name = ''
        self._stop.Validate(self.problems)
        self.accumulator.Popmissing_value('stop_name')
        self.accumulator.AssertNoMoreExceptions()

        # Empty stop_name in a child stop should report missing_value
        self._child_stop.stop_name = ''
        self._child_stop.Validate(self.problems)
        self.accumulator.Popmissing_value('stop_name')
        self.accumulator.AssertNoMoreExceptions()

        # Empty stop_name with location_type=2 should report no errors
        self._entrance.stop_name = ''
        self._entrance.Validate(self.problems)
        self.accumulator.AssertNoMoreExceptions()


class RouteExtensionIntegrationTestCase(ExtensionMemoryZipTestCase):
    gtfs_factory = extensions.googletransit.get_gtfs_factory()

    def test_no_errors(self):
        self.set_archive_contents(
            "routes.txt",
            "route_id,agency_id,route_short_name,route_long_name,route_type,"
            "co2_per_km\n"
            "AB,DTA,,Airport Bullfrog,201,15.5\n")
        self.make_loader_and_load(self.problems, gtfs_factory=self.gtfs_factory)
        self.accumulator.AssertNoMoreExceptions()

    def test_invalid_co2_per_km(self):
        self.set_archive_contents(
            "routes.txt",
            "route_id,route_short_name,route_long_name,route_type,co2_per_km\n"
            "AB,,Airport Bullfrog,201,15.5mg\n")
        self.make_loader_and_load(self.problems, gtfs_factory=self.gtfs_factory)
        self.accumulator.Popinvalid_value("co2_per_km")
        self.accumulator.AssertNoMoreExceptions()

    def test_invalid_route_type(self):
        self.set_archive_contents(
            "routes.txt",
            "route_id,route_short_name,route_long_name,route_type,co2_per_km\n"
            "AB,,Airport Bullfrog,2557,15.5\n")
        self.make_loader_and_load(self.problems, gtfs_factory=self.gtfs_factory)
        self.accumulator.Popinvalid_value("route_type")
        self.accumulator.AssertNoMoreExceptions()


class AgencyLangTestCase(ExtensionMemoryZipTestCase):
    gtfs_factory = extensions.googletransit.get_gtfs_factory()

    def test_not_well_formed_agency_lang(self):
        self.set_archive_contents(
            "agency.txt",
            "agency_id,agency_name,agency_url,agency_timezone,agency_lang\n"
            "DTA,Demo Agency,http://google.com,America/Los_Angeles,lang123456789\n")
        self.make_loader_and_load(self.problems,
                               gtfs_factory=self.gtfs_factory)
        e = self.accumulator.Popinvalid_value("agency_lang")
        e_msg = e.FormatProblem()
        self.assertTrue(e_msg.find('not well-formed') != -1,
                        '%s should not be well-formed, is: %s' % (e.value, e_msg))
        self.accumulator.AssertNoMoreExceptions()

    def test_not_valid_agency_lang(self):
        self.set_archive_contents(
            "agency.txt",
            "agency_id,agency_name,agency_url,agency_timezone,agency_lang\n"
            "DTA,Demo Agency,http://google.com,America/Los_Angeles,fra-XY\n")

        self.make_loader_and_load(self.problems,
                               gtfs_factory=self.gtfs_factory)
        e = self.accumulator.Popinvalid_value("agency_lang")
        e_msg = e.FormatProblem()
        self.assertTrue(e_msg.find('not valid') != -1,
                        '%s should not be valid, is: %s' % (e.value, e_msg))
        self.accumulator.AssertNoMoreExceptions()
