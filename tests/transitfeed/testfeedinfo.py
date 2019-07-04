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

# Unit tests for the feedinfo module.
from __future__ import absolute_import

from datetime import date
from tests import util
import transitfeed


class FeedInfoTestCase(util.MemoryZipTestCase):

    def set_up(self):
        super(FeedInfoTestCase, self).set_up()
        # Modify agency.txt for all tests in this test case
        self.set_archive_contents("agency.txt",
                                "agency_id,agency_name,agency_url,agency_timezone,agency_lang\n"
                                "DTA,Demo Agency,http://google.com,America/Los_Angeles,en\n")

    def test_no_errors(self):
        self.set_archive_contents("feed_info.txt",
                                "feed_publisher_name,feed_publisher_url,feed_lang\n"
                                "DTA,http://google.com,en")
        self.make_loader_and_load(self.problems)
        self.accumulator.AssertNoMoreExceptions()

    def test_different_language(self):
        self.set_archive_contents("feed_info.txt",
                                "feed_publisher_name,feed_publisher_url,feed_lang\n"
                                "DTA,http://google.com,pt")
        self.make_loader_and_load(self.problems)
        self.accumulator.PopInvalidValue("feed_lang")
        self.accumulator.AssertNoMoreExceptions()

    def test_invalid_publisher_url(self):
        self.set_archive_contents("feed_info.txt",
                                "feed_publisher_name,feed_publisher_url,feed_lang\n"
                                "DTA,htttp://google.com,en")
        self.make_loader_and_load(self.problems)
        self.accumulator.PopInvalidValue("feed_publisher_url")
        self.accumulator.AssertNoMoreExceptions()

    def test_validity_dates_no_errors(self):
        self.set_archive_contents("feed_info.txt",
                                "feed_publisher_name,feed_publisher_url,feed_lang,"
                                "feed_start_date,feed_end_date\n"
                                "DTA,http://google.com,en,20101201,20101231")
        self.make_loader_and_load(self.problems)
        self.accumulator.AssertNoMoreExceptions()

    def test_validity_dates_invalid(self):
        self.set_archive_contents("feed_info.txt",
                                "feed_publisher_name,feed_publisher_url,feed_lang,"
                                "feed_start_date,feed_end_date\n"
                                "DTA,http://google.com,en,10/01/12,10/31/12")
        self.make_loader_and_load(self.problems)
        self.accumulator.PopInvalidValue("feed_end_date")
        self.accumulator.PopInvalidValue("feed_start_date")
        self.accumulator.AssertNoMoreExceptions()

    def test_validity_dates_inverted(self):
        self.set_archive_contents("feed_info.txt",
                                "feed_publisher_name,feed_publisher_url,feed_lang,"
                                "feed_start_date,feed_end_date\n"
                                "DTA,http://google.com,en,20101231,20101201")
        self.make_loader_and_load(self.problems)
        self.accumulator.PopInvalidValue("feed_end_date")
        self.accumulator.AssertNoMoreExceptions()

    def test_deprectated_field_names(self):
        self.set_archive_contents("feed_info.txt",
                                "feed_publisher_name,feed_publisher_url,feed_timezone,feed_lang,"
                                "feed_valid_from,feed_valid_until\n"
                                "DTA,http://google.com,America/Los_Angeles,en,20101201,20101231")
        self.make_loader_and_load(self.problems)
        e = self.accumulator.PopException("DeprecatedColumn")
        self.assertEquals("feed_valid_from", e.column_name)
        e = self.accumulator.PopException("DeprecatedColumn")
        self.assertEquals("feed_valid_until", e.column_name)
        e = self.accumulator.PopException("DeprecatedColumn")
        self.assertEquals("feed_timezone", e.column_name)
        self.accumulator.AssertNoMoreExceptions()


class FeedInfoServiceGapsTestCase(util.MemoryZipTestCase):
    """Test for service gaps introduced by feed_info.txt start end dates."""

    def set_up(self):
        super(FeedInfoServiceGapsTestCase, self).set_up()
        self.set_archive_contents("calendar.txt",
                                "service_id,monday,tuesday,wednesday,thursday,friday,"
                                "saturday,sunday,start_date,end_date\n"
                                "FULLW,1,1,1,1,1,1,1,20090601,20090610\n")
        self.set_archive_contents("trips.txt",
                                "route_id,service_id,trip_id\n"
                                "AB,FULLW,AB1\n")
        self.set_archive_contents(
            "stop_times.txt",
            "trip_id,arrival_time,departure_time,stop_id,stop_sequence\n"
            "AB1,10:00:00,10:00:00,BEATTY_AIRPORT,1\n"
            "AB1,10:20:00,10:20:00,BULLFROG,2\n"
            "AB1,10:25:00,10:25:00,STAGECOACH,3\n")
        self.set_archive_contents("feed_info.txt",
                                "feed_publisher_name,feed_publisher_url,feed_lang,"
                                "feed_start_date,feed_end_date\n"
                                "DTA,http://google.com,en,20090515,20090620")

        self.schedule = self.make_loader_and_load(extra_validation=False)

    # If there is a service gap starting before today, and today has no service,
    # it should be found - even if tomorrow there is service
    def test_service_gap_before_today_is_discovered(self):
        self.schedule.Validate(today=date(2009, 6, 5),
                               service_gap_interval=7)
        exception = self.accumulator.PopException("TooManyDaysWithoutService")
        self.assertEquals(date(2009, 6, 11),
                          exception.first_day_without_service)
        self.assertEquals(date(2009, 6, 19),
                          exception.last_day_without_service)
        self.accumulator.AssertNoMoreExceptions()
