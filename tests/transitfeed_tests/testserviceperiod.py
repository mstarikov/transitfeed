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

# Unit tests for the serviceperiod module.
from __future__ import absolute_import

import datetime
from datetime import date
from tests import util
import time
import transitfeed


class ServicePeriodValidationTestCase(util.ValidationTestCase):
    def run_test(self):
        # success case
        period = transitfeed.ServicePeriod()
        repr(period)  # shouldn't crash
        period.service_id = 'WEEKDAY'
        period.start_date = '20070101'
        period.end_date = '20071231'
        period.day_of_week[0] = True
        repr(period)  # shouldn't crash
        period.Validate(self.problems)

        # missing start_date. If one of start_date or end_date is None then
        # ServicePeriod.Validate assumes the required column is missing and already
        # generated an error. Instead set it to an empty string, such as when the
        # csv cell is empty. See also comment in ServicePeriod.Validate.
        period.start_date = ''
        self.ValidateAndExpectmissing_value(period, 'start_date')
        period.start_date = '20070101'

        # missing end_date
        period.end_date = ''
        self.ValidateAndExpectmissing_value(period, 'end_date')
        period.end_date = '20071231'

        # invalid start_date
        period.start_date = '2007-01-01'
        self.ValidateAndExpectinvalid_value(period, 'start_date')
        period.start_date = '20070101'

        # impossible start_date
        period.start_date = '20070229'
        self.ValidateAndExpectinvalid_value(period, 'start_date')
        period.start_date = '20070101'

        # invalid end_date
        period.end_date = '2007/12/31'
        self.ValidateAndExpectinvalid_value(period, 'end_date')
        period.end_date = '20071231'

        # start & end dates out of order
        period.end_date = '20060101'
        self.ValidateAndExpectinvalid_value(period, 'end_date')
        period.end_date = '20071231'

        # no service in period
        period.day_of_week[0] = False
        self.ValidateAndExpectother_problem(period)
        period.day_of_week[0] = True

        # invalid exception date
        period.set_date_has_service('2007', False)
        self.ValidateAndExpectinvalid_value(period, 'date', '2007')
        period.ResetDateToNormalService('2007')

        period2 = transitfeed.ServicePeriod(
            field_list=['serviceid1', '20060101', '20071231', '1', '0', 'h', '1',
                        '1', '1', '1'])
        self.ValidateAndExpectinvalid_value(period2, 'wednesday', 'h')
        repr(period)  # shouldn't crash

    def test_has_exceptions(self):
        # A new ServicePeriod object has no exceptions
        period = transitfeed.ServicePeriod()
        self.assertFalse(period.HasExceptions())

        # Only regular service, no exceptions
        period.service_id = 'WEEKDAY'
        period.start_date = '20070101'
        period.end_date = '20071231'
        period.day_of_week[0] = True
        self.assertFalse(period.HasExceptions())

        # Regular service + removed service exception
        period.set_date_has_service('20070101', False)
        self.assertTrue(period.HasExceptions())

        # Regular service + added service exception
        period.set_date_has_service('20070101', True)
        self.assertTrue(period.HasExceptions())

        # Only added service exception
        period = transitfeed.ServicePeriod()
        period.set_date_has_service('20070101', True)
        self.assertTrue(period.HasExceptions())

        # Only removed service exception
        period = transitfeed.ServicePeriod()
        period.set_date_has_service('20070101', False)
        self.assertTrue(period.HasExceptions())

    def test_service_period_date_outside_valid_range(self):
        # regular service, no exceptions, start_date invalid
        period = transitfeed.ServicePeriod()
        period.service_id = 'WEEKDAY'
        period.start_date = '20070101'
        period.end_date = '21071231'
        period.day_of_week[0] = True
        self.ValidateAndExpectDateOutsideValidRange(period, 'end_date', '21071231')

        # regular service, no exceptions, start_date invalid
        period2 = transitfeed.ServicePeriod()
        period2.service_id = 'SUNDAY'
        period2.start_date = '18990101'
        period2.end_date = '19991231'
        period2.day_of_week[6] = True
        self.ValidateAndExpectDateOutsideValidRange(period2, 'start_date',
                                                    '18990101')

        # regular service, no exceptions, both start_date and end_date invalid
        period3 = transitfeed.ServicePeriod()
        period3.service_id = 'SATURDAY'
        period3.start_date = '18990101'
        period3.end_date = '29991231'
        period3.day_of_week[5] = True
        period3.Validate(self.problems)
        e = self.accumulator.PopDateOutsideValidRange('start_date')
        self.assertEquals('18990101', e.value)
        e.FormatProblem()  # should not throw any exceptions
        e.FormatContext()  # should not throw any exceptions
        e = self.accumulator.PopDateOutsideValidRange('end_date')
        self.assertEqual('29991231', e.value)
        e.FormatProblem()  # should not throw any exceptions
        e.FormatContext()  # should not throw any exceptions
        self.accumulator.AssertNoMoreExceptions()

    def test_service_period_exception_date_outside_valid_range(self):
        """ date exceptions of ServicePeriod must be in [1900,2100] """
        # regular service, 3 exceptions, date of 1st and 3rd invalid
        period = transitfeed.ServicePeriod()
        period.service_id = 'WEEKDAY'
        period.start_date = '20070101'
        period.end_date = '20071231'
        period.day_of_week[0] = True
        period.set_date_has_service('21070101', False)  # removed service exception
        period.set_date_has_service('20070205', False)  # removed service exception
        period.set_date_has_service('10070102', True)  # added service exception
        period.Validate(self.problems)

        # check for error from first date exception
        e = self.accumulator.PopDateOutsideValidRange('date')
        self.assertEqual('10070102', e.value)
        e.FormatProblem()  # should not throw any exceptions
        e.FormatContext()  # should not throw any exceptions

        # check for error from third date exception
        e = self.accumulator.PopDateOutsideValidRange('date')
        self.assertEqual('21070101', e.value)
        e.FormatProblem()  # should not throw any exceptions
        e.FormatContext()  # should not throw any exceptions
        self.accumulator.AssertNoMoreExceptions()


class ServicePeriodDateRangeTestCase(util.ValidationTestCase):
    def run_test(self):
        period = transitfeed.ServicePeriod()
        period.service_id = 'WEEKDAY'
        period.start_date = '20070101'
        period.end_date = '20071231'
        period.SetWeekdayService(True)
        period.set_date_has_service('20071231', False)
        period.Validate(self.problems)
        self.assertEqual(('20070101', '20071231'), period.GetDateRange())

        period2 = transitfeed.ServicePeriod()
        period2.service_id = 'HOLIDAY'
        period2.set_date_has_service('20071225', True)
        period2.set_date_has_service('20080101', True)
        period2.set_date_has_service('20080102', False)
        period2.Validate(self.problems)
        self.assertEqual(('20071225', '20080101'), period2.GetDateRange())

        period2.start_date = '20071201'
        period2.end_date = '20071225'
        period2.Validate(self.problems)
        self.assertEqual(('20071201', '20080101'), period2.GetDateRange())

        period3 = transitfeed.ServicePeriod()
        self.assertEqual((None, None), period3.GetDateRange())

        period4 = transitfeed.ServicePeriod()
        period4.service_id = 'halloween'
        period4.set_date_has_service('20051031', True)
        self.assertEqual(('20051031', '20051031'), period4.GetDateRange())
        period4.Validate(self.problems)

        schedule = transitfeed.Schedule(problem_reporter=self.problems)
        self.assertEqual((None, None), schedule.GetDateRange())
        schedule.add_service_period_object(period)
        self.assertEqual(('20070101', '20071231'), schedule.GetDateRange())
        schedule.add_service_period_object(period2)
        self.assertEqual(('20070101', '20080101'), schedule.GetDateRange())
        schedule.add_service_period_object(period4)
        self.assertEqual(('20051031', '20080101'), schedule.GetDateRange())
        self.accumulator.AssertNoMoreExceptions()


class ServicePeriodTestCase(util.TestCase):
    def test_active(self):
        """Test IsActiveOn and ActiveDates"""
        period = transitfeed.ServicePeriod()
        period.service_id = 'WEEKDAY'
        period.start_date = '20071226'
        period.end_date = '20071231'
        period.SetWeekdayService(True)
        period.set_date_has_service('20071230', True)
        period.set_date_has_service('20071231', False)
        period.set_date_has_service('20080102', True)
        #      December  2007
        #  Su Mo Tu We Th Fr Sa
        #  23 24 25 26 27 28 29
        #  30 31

        # Some tests have named arguments and others do not to ensure that any
        # (possibly unwanted) changes to the API get caught

        # calendar_date exceptions near start date
        self.assertFalse(period.IsActiveOn(date='20071225'))
        self.assertFalse(period.IsActiveOn(date='20071225',
                                           date_object=date(2007, 12, 25)))
        self.assertTrue(period.IsActiveOn(date='20071226'))
        self.assertTrue(period.IsActiveOn(date='20071226',
                                          date_object=date(2007, 12, 26)))

        # calendar_date exceptions near end date
        self.assertTrue(period.IsActiveOn('20071230'))
        self.assertTrue(period.IsActiveOn('20071230', date(2007, 12, 30)))
        self.assertFalse(period.IsActiveOn('20071231'))
        self.assertFalse(period.IsActiveOn('20071231', date(2007, 12, 31)))

        # date just outside range, both weekday and an exception
        self.assertFalse(period.IsActiveOn('20080101'))
        self.assertFalse(period.IsActiveOn('20080101', date(2008, 1, 1)))
        self.assertTrue(period.IsActiveOn('20080102'))
        self.assertTrue(period.IsActiveOn('20080102', date(2008, 1, 2)))

        self.assertEquals(period.ActiveDates(),
                          ['20071226', '20071227', '20071228', '20071230',
                           '20080102'])

        # Test of period without start_date, end_date
        period_dates = transitfeed.ServicePeriod()
        period_dates.set_date_has_service('20071230', True)
        period_dates.set_date_has_service('20071231', False)

        self.assertFalse(period_dates.IsActiveOn(date='20071229'))
        self.assertFalse(period_dates.IsActiveOn(date='20071229',
                                                 date_object=date(2007, 12, 29)))
        self.assertTrue(period_dates.IsActiveOn('20071230'))
        self.assertTrue(period_dates.IsActiveOn('20071230', date(2007, 12, 30)))
        self.assertFalse(period_dates.IsActiveOn('20071231'))
        self.assertFalse(period_dates.IsActiveOn('20071231', date(2007, 12, 31)))
        self.assertEquals(period_dates.ActiveDates(), ['20071230'])

        # Test with an invalid ServicePeriod; one of start_date, end_date is set
        period_no_end = transitfeed.ServicePeriod()
        period_no_end.start_date = '20071226'
        self.assertFalse(period_no_end.IsActiveOn(date='20071231'))
        self.assertFalse(period_no_end.IsActiveOn(date='20071231',
                                                  date_object=date(2007, 12, 31)))
        self.assertEquals(period_no_end.ActiveDates(), [])
        period_no_start = transitfeed.ServicePeriod()
        period_no_start.end_date = '20071230'
        self.assertFalse(period_no_start.IsActiveOn('20071229'))
        self.assertFalse(period_no_start.IsActiveOn('20071229', date(2007, 12, 29)))
        self.assertEquals(period_no_start.ActiveDates(), [])

        period_empty = transitfeed.ServicePeriod()
        self.assertFalse(period_empty.IsActiveOn('20071231'))
        self.assertFalse(period_empty.IsActiveOn('20071231', date(2007, 12, 31)))
        self.assertEquals(period_empty.ActiveDates(), [])


class OnlyCalendarDatesTestCase(util.LoadTestCase):
    def run_test(self):
        self.Load('only_calendar_dates'),
        self.accumulator.AssertNoMoreExceptions()


class DuplicateServiceIdDateWarningTestCase(util.MemoryZipTestCase):
    def run_test(self):
        # Two lines with the same value of service_id and date.
        # Test for the warning.
        self.set_archive_contents(
            'calendar_dates.txt',
            'service_id,date,exception_type\n'
            'FULLW,20100604,1\n'
            'FULLW,20100604,2\n')
        schedule = self.make_loader_and_load()
        e = self.accumulator.PopException('duplicate_id')
        self.assertEquals('(service_id, date)', e.column_name)
        self.assertEquals('(FULLW, 20100604)', e.value)


class ExpirationDateTestCase(util.TestCase):
    def run_test(self):
        accumulator = util.RecordingProblemAccumulator(
            self, ("NoServiceExceptions"))
        problems = transitfeed.ProblemReporter(accumulator)
        schedule = transitfeed.Schedule(problem_reporter=problems)

        now = time.mktime(time.localtime())
        seconds_per_day = 60 * 60 * 24
        two_weeks_ago = time.localtime(now - 14 * seconds_per_day)
        two_weeks_from_now = time.localtime(now + 14 * seconds_per_day)
        two_months_from_now = time.localtime(now + 60 * seconds_per_day)
        date_format = "%Y%m%d"

        service_period = schedule.GetDefaultServicePeriod()
        service_period.SetWeekdayService(True)
        service_period.SetStartDate("20070101")

        service_period.SetEndDate(time.strftime(date_format, two_months_from_now))
        schedule.Validate()  # should have no problems
        accumulator.AssertNoMoreExceptions()

        service_period.SetEndDate(time.strftime(date_format, two_weeks_from_now))
        schedule.Validate()
        e = accumulator.PopException('ExpirationDate')
        self.assertTrue(e.FormatProblem().index('will soon expire'))
        accumulator.AssertNoMoreExceptions()

        service_period.SetEndDate(time.strftime(date_format, two_weeks_ago))
        schedule.Validate()
        e = accumulator.PopException('ExpirationDate')
        self.assertTrue(e.FormatProblem().index('expired'))
        accumulator.AssertNoMoreExceptions()


class FutureServiceStartDateTestCase(util.TestCase):
    def run_test(self):
        accumulator = util.RecordingProblemAccumulator(self)
        problems = transitfeed.ProblemReporter(accumulator)
        schedule = transitfeed.Schedule(problem_reporter=problems)

        today = datetime.date.today()
        yesterday = today - datetime.timedelta(days=1)
        tomorrow = today + datetime.timedelta(days=1)
        two_months_from_today = today + datetime.timedelta(days=60)

        service_period = schedule.GetDefaultServicePeriod()
        service_period.SetWeekdayService(True)
        service_period.SetWeekendService(True)
        service_period.SetEndDate(two_months_from_today.strftime("%Y%m%d"))

        service_period.SetStartDate(yesterday.strftime("%Y%m%d"))
        schedule.Validate()
        accumulator.AssertNoMoreExceptions()

        service_period.SetStartDate(today.strftime("%Y%m%d"))
        schedule.Validate()
        accumulator.AssertNoMoreExceptions()

        service_period.SetStartDate(tomorrow.strftime("%Y%m%d"))
        schedule.Validate()
        accumulator.PopException('FutureService')
        accumulator.AssertNoMoreExceptions()


class CalendarTxtIntegrationTestCase(util.MemoryZipTestCase):
    def test_bad_end_date_format(self):
        # A badly formatted end_date used to generate an invalid_value report from
        # Schedule.Validate and ServicePeriod.Validate. Test for the bug.
        self.set_archive_contents(
            "calendar.txt",
            "service_id,monday,tuesday,wednesday,thursday,friday,saturday,sunday,"
            "start_date,end_date\n"
            "FULLW,1,1,1,1,1,1,1,20070101,20101232\n"
            "WE,0,0,0,0,0,1,1,20070101,20101231\n")
        schedule = self.make_loader_and_load()
        e = self.accumulator.Popinvalid_value('end_date')
        self.accumulator.AssertNoMoreExceptions()

    def test_bad_start_date_format(self):
        self.set_archive_contents(
            "calendar.txt",
            "service_id,monday,tuesday,wednesday,thursday,friday,saturday,sunday,"
            "start_date,end_date\n"
            "FULLW,1,1,1,1,1,1,1,200701xx,20101231\n"
            "WE,0,0,0,0,0,1,1,20070101,20101231\n")
        schedule = self.make_loader_and_load()
        e = self.accumulator.Popinvalid_value('start_date')
        self.accumulator.AssertNoMoreExceptions()

    def test_no_start_date_and_end_date(self):
        """Regression test for calendar.txt with empty start_date and end_date.

        See https://github.com/google/transitfeed/issues/41
        """
        self.set_archive_contents(
            "calendar.txt",
            "service_id,monday,tuesday,wednesday,thursday,friday,saturday,sunday,"
            "start_date,end_date\n"
            "FULLW,1,1,1,1,1,1,1,    ,\t\n"
            "WE,0,0,0,0,0,1,1,20070101,20101231\n")
        schedule = self.make_loader_and_load()
        e = self.accumulator.PopException("missing_value")
        self.assertEquals(2, e.row_num)
        self.assertEquals("start_date", e.column_name)
        e = self.accumulator.PopException("missing_value")
        self.assertEquals(2, e.row_num)
        self.assertEquals("end_date", e.column_name)
        self.accumulator.AssertNoMoreExceptions()

    def test_no_start_date_and_bad_end_date(self):
        self.set_archive_contents(
            "calendar.txt",
            "service_id,monday,tuesday,wednesday,thursday,friday,saturday,sunday,"
            "start_date,end_date\n"
            "FULLW,1,1,1,1,1,1,1,,abc\n"
            "WE,0,0,0,0,0,1,1,20070101,20101231\n")
        schedule = self.make_loader_and_load()
        e = self.accumulator.PopException("missing_value")
        self.assertEquals(2, e.row_num)
        self.assertEquals("start_date", e.column_name)
        e = self.accumulator.Popinvalid_value("end_date")
        self.assertEquals(2, e.row_num)
        self.accumulator.AssertNoMoreExceptions()

    def test_missing_end_date_column(self):
        self.set_archive_contents(
            "calendar.txt",
            "service_id,monday,tuesday,wednesday,thursday,friday,saturday,sunday,"
            "start_date\n"
            "FULLW,1,1,1,1,1,1,1,20070101\n"
            "WE,0,0,0,0,0,1,1,20070101\n")
        schedule = self.make_loader_and_load()
        e = self.accumulator.PopException("missing_column")
        self.assertEquals("end_date", e.column_name)
        self.accumulator.AssertNoMoreExceptions()

    def test_date_outside_valid_range(self):
        """ start_date and end_date values must be in [1900,2100] """
        self.set_archive_contents(
            "calendar.txt",
            "service_id,monday,tuesday,wednesday,thursday,friday,saturday,sunday,"
            "start_date,end_date\n"
            "FULLW,1,1,1,1,1,1,1,20070101,21101231\n"
            "WE,0,0,0,0,0,1,1,18990101,20101231\n")
        schedule = self.make_loader_and_load()
        e = self.accumulator.PopDateOutsideValidRange('end_date', 'calendar.txt')
        self.assertEquals('21101231', e.value)
        e = self.accumulator.PopDateOutsideValidRange('start_date', 'calendar.txt')
        self.assertEquals('18990101', e.value)
        self.accumulator.AssertNoMoreExceptions()


class CalendarDatesTxtIntegrationTestCase(util.MemoryZipTestCase):
    def test_date_outside_valid_range(self):
        """ exception date values in must be in [1900,2100] """
        self.set_archive_contents("calendar_dates.txt",
                                "service_id,date,exception_type\n"
                                "WE,18990815,2\n")
        schedule = self.make_loader_and_load()
        e = self.accumulator.PopDateOutsideValidRange('date', 'calendar_dates.txt')
        self.assertEquals('18990815', e.value)
        self.accumulator.AssertNoMoreExceptions()


class DefaultServicePeriodTestCase(util.TestCase):
    def test__set_default(self):
        schedule = transitfeed.Schedule()
        service1 = transitfeed.ServicePeriod()
        service1.set_date_has_service('20070101', True)
        service1.service_id = 'SERVICE1'
        schedule.SetDefaultServicePeriod(service1)
        self.assertEqual(service1, schedule.GetDefaultServicePeriod())
        self.assertEqual(service1, schedule.GetServicePeriod(service1.service_id))

    def test__new_default(self):
        schedule = transitfeed.Schedule()
        service1 = schedule.NewDefaultServicePeriod()
        self.assertTrue(service1.service_id)
        schedule.GetServicePeriod(service1.service_id)
        service1.set_date_has_service('20070101', True)  # Make service1 different
        service2 = schedule.NewDefaultServicePeriod()
        schedule.GetServicePeriod(service2.service_id)
        self.assertTrue(service1.service_id)
        self.assertTrue(service2.service_id)
        self.assertNotEqual(service1, service2)
        self.assertNotEqual(service1.service_id, service2.service_id)

    def test__no_services_makes_new_default(self):
        schedule = transitfeed.Schedule()
        service1 = schedule.GetDefaultServicePeriod()
        self.assertEqual(service1, schedule.GetServicePeriod(service1.service_id))

    def test__assume_single_service_is_default(self):
        schedule = transitfeed.Schedule()
        service1 = transitfeed.ServicePeriod()
        service1.set_date_has_service('20070101', True)
        service1.service_id = 'SERVICE1'
        schedule.add_service_period_object(service1)
        self.assertEqual(service1, schedule.GetDefaultServicePeriod())
        self.assertEqual(service1.service_id, schedule.GetDefaultServicePeriod().service_id)

    def test__multiple_services_causes_no_default(self):
        schedule = transitfeed.Schedule()
        service1 = transitfeed.ServicePeriod()
        service1.service_id = 'SERVICE1'
        service1.set_date_has_service('20070101', True)
        schedule.add_service_period_object(service1)
        service2 = transitfeed.ServicePeriod()
        service2.service_id = 'SERVICE2'
        service2.set_date_has_service('20070201', True)
        schedule.add_service_period_object(service2)
        service_d = schedule.GetDefaultServicePeriod()
        self.assertEqual(service_d, None)
