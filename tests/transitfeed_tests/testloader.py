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

# Unit tests for the loader module.
from __future__ import absolute_import

import re
try:
    from io import StringIO
except ImportError:
    from StringIO import StringIO
import tempfile
from tests import util
import transitfeed
import zipfile
import zlib


class unrecognized_columnRecorder(transitfeed.ProblemReporter):
    """Keeps track of unrecognized column errors."""

    def __init__(self, test_case):
        self.accumulator = util.RecordingProblemAccumulator(test_case,
                                                            ignore_types=("ExpirationDate",))
        self.column_errors = []

    def unrecognized_column(self, file_name, column_name, context=None):
        self.column_errors.append((file_name, column_name))


# ensure that there are no exceptions when attempting to load
# (so that the validator won't crash)
class NoExceptionTestCase(util.RedirectStdOutTestCaseBase):
    def run_test(self):
        for feed in util.GetDataPathContents():
            loader = transitfeed.Loader(util.DataPath(feed),
                                        problems=transitfeed.ProblemReporter(),
                                        extra_validation=True)
            schedule = loader.Load()
            schedule.Validate()


class EndOfLineCheckerTestCase(util.TestCase):
    def set_up(self):
        self.accumulator = util.RecordingProblemAccumulator(
            self, ("ExpirationDate"))
        self.problems = transitfeed.ProblemReporter(self.accumulator)

    def run_end_of_line_checker(self, end_of_line_checker):
        # Iterating using for calls end_of_line_checker.next() until a
        # StopIteration is raised. EndOfLineChecker does the final check for a mix
        # of CR LF and LF ends just before raising StopIteration.
        for line in end_of_line_checker:
            pass

    def test_invalid_line_end(self):
        f = transitfeed.EndOfLineChecker(StringIO("line1\r\r\nline2"),
                                         "<StringIO>",
                                         self.problems)
        self.run_end_of_line_checker(f)
        e = self.accumulator.PopException("InvalidLineEnd")
        self.assertEqual(e.file_name, "<StringIO>")
        self.assertEqual(e.row_num, 1)
        self.assertEqual(e.bad_line_end, r"\r\r\n")
        self.accumulator.AssertNoMoreExceptions()

    def test_invalid_line_endToo(self):
        f = transitfeed.EndOfLineChecker(
            StringIO("line1\nline2\r\nline3\r\r\r\n"),
            "<StringIO>", self.problems)
        self.run_end_of_line_checker(f)
        e = self.accumulator.PopException("InvalidLineEnd")
        self.assertEqual(e.file_name, "<StringIO>")
        self.assertEqual(e.row_num, 3)
        self.assertEqual(e.bad_line_end, r"\r\r\r\n")
        e = self.accumulator.PopException("other_problem")
        self.assertEqual(e.file_name, "<StringIO>")
        self.assertTrue(e.description.find("consistent line end") != -1)
        self.accumulator.AssertNoMoreExceptions()

    def test_embedded_cr(self):
        f = transitfeed.EndOfLineChecker(
            StringIO("line1\rline1b"),
            "<StringIO>", self.problems)
        self.run_end_of_line_checker(f)
        e = self.accumulator.PopException("other_problem")
        self.assertEqual(e.file_name, "<StringIO>")
        self.assertEqual(e.row_num, 1)
        self.assertEqual(e.FormatProblem(),
                         "Line contains ASCII Carriage Return 0x0D, \\r")
        self.accumulator.AssertNoMoreExceptions()

    def test_embedded_utf8_next_line(self):
        f = transitfeed.EndOfLineChecker(
            StringIO("line1b\xc2\x85"),
            "<StringIO>", self.problems)
        self.run_end_of_line_checker(f)
        e = self.accumulator.PopException("other_problem")
        self.assertEqual(e.file_name, "<StringIO>")
        self.assertEqual(e.row_num, 1)
        self.assertEqual(e.FormatProblem(),
                         "Line contains Unicode NEXT LINE SEPARATOR U+0085")
        self.accumulator.AssertNoMoreExceptions()

    def test_end_of_line_mix(self):
        f = transitfeed.EndOfLineChecker(
            StringIO("line1\nline2\r\nline3\nline4"),
            "<StringIO>", self.problems)
        self.run_end_of_line_checker(f)
        e = self.accumulator.PopException("other_problem")
        self.assertEqual(e.file_name, "<StringIO>")
        self.assertEqual(e.FormatProblem(),
                         "Found 1 CR LF \"\\r\\n\" line end (line 2) and "
                         "2 LF \"\\n\" line ends (lines 1, 3). A file must use a "
                         "consistent line end.")
        self.accumulator.AssertNoMoreExceptions()

    def test_end_of_line_many_mix(self):
        f = transitfeed.EndOfLineChecker(
            StringIO("1\n2\n3\n4\n5\n6\n7\r\n8\r\n9\r\n10\r\n11\r\n"),
            "<StringIO>", self.problems)
        self.run_end_of_line_checker(f)
        e = self.accumulator.PopException("other_problem")
        self.assertEqual(e.file_name, "<StringIO>")
        self.assertEqual(e.FormatProblem(),
                         "Found 5 CR LF \"\\r\\n\" line ends (lines 7, 8, 9, 10, "
                         "11) and 6 LF \"\\n\" line ends (lines 1, 2, 3, 4, 5, "
                         "...). A file must use a consistent line end.")
        self.accumulator.AssertNoMoreExceptions()

    def test_load(self):
        loader = transitfeed.Loader(
            util.DataPath("bad_eol.zip"),
            problems=self.problems,
            extra_validation=True)
        loader.Load()

        e = self.accumulator.PopException("other_problem")
        self.assertEqual(e.file_name, "calendar.txt")
        self.assertTrue(re.search(
            r"Found 1 CR LF.* \(line 2\) and 2 LF .*\(lines 1, 3\)",
            e.FormatProblem()))

        e = self.accumulator.PopException("InvalidLineEnd")
        self.assertEqual(e.file_name, "routes.txt")
        self.assertEqual(e.row_num, 5)
        self.assertTrue(e.FormatProblem().find(r"\r\r\n") != -1)

        e = self.accumulator.PopException("other_problem")
        self.assertEqual(e.file_name, "trips.txt")
        self.assertEqual(e.row_num, 1)
        self.assertTrue(re.search(
            r"contains ASCII Form Feed",
            e.FormatProblem()))
        # TODO(Tom): avoid this duplicate error for the same issue
        e = self.accumulator.PopException("CsvSyntax")
        self.assertEqual(e.row_num, 1)
        self.assertTrue(re.search(
            r"header row should not contain any space char",
            e.FormatProblem()))

        self.accumulator.AssertNoMoreExceptions()


class LoadFromZipTestCase(util.TestCase):
    def run_test(self):
        loader = transitfeed.Loader(
            util.DataPath('good_feed.zip'),
            problems=util.GetTestFailureProblemReporter(self),
            extra_validation=True)
        loader.Load()

        # now try using Schedule.Load
        schedule = transitfeed.Schedule(
            problem_reporter=util.ExceptionProblemReporterNoExpiration())
        schedule.Load(util.DataPath('good_feed.zip'), extra_validation=True)


class LoadAndRewriteFromZipTestCase(util.TestCase):
    def run_test(self):
        schedule = transitfeed.Schedule(
            problem_reporter=util.ExceptionProblemReporterNoExpiration())
        schedule.Load(util.DataPath('good_feed.zip'), extra_validation=True)

        # Finally see if write crashes
        schedule.write_google_transit_feed(tempfile.TemporaryFile())


class BasicMemoryZipTestCase(util.MemoryZipTestCase):
    def run_test(self):
        self.make_loader_and_load()
        self.accumulator.AssertNoMoreExceptions()


class ZipCompressionTestCase(util.MemoryZipTestCase):
    def run_test(self):
        schedule = self.make_loader_and_load()
        self.zip.close()
        write_output = StringIO()
        schedule.write_google_transit_feed(write_output)
        recompressedzip = zlib.compress(write_output.getvalue())
        write_size = len(write_output.getvalue())
        recompressedzip_size = len(recompressedzip)
        # If zlib can compress write_output it probably wasn't compressed
        self.assertFalse(
            recompressedzip_size < write_size * 0.60,
            "Are you sure write_google_transit_feed wrote a compressed zip? "
            "Orginial size: %d  recompressed: %d" %
            (write_size, recompressedzip_size))


class LoadUnknownFileInZipTestCase(util.MemoryZipTestCase):
    def run_test(self):
        self.set_archive_contents(
            "stpos.txt",
            "stop_id,stop_name,stop_lat,stop_lon,location_type,parent_station\n"
            "BEATTY_AIRPORT,Airport,36.868446,-116.784582,,STATION\n"
            "STATION,Airport,36.868446,-116.784582,1,\n"
            "BULLFROG,Bullfrog,36.88108,-116.81797,,\n"
            "STAGECOACH,Stagecoach Hotel,36.915682,-116.751677,,\n")
        schedule = self.make_loader_and_load()
        e = self.accumulator.PopException('UnknownFile')
        self.assertEquals('stpos.txt', e.file_name)
        self.accumulator.AssertNoMoreExceptions()


class TabDelimitedTestCase(util.MemoryZipTestCase):
    def run_test(self):
        # Create an extremely corrupt file by replacing each comma with a tab,
        # ignoring csv quoting.
        for arcname in self.GetArchiveNames():
            contents = self.GetArchiveContents(arcname)
            self.set_archive_contents(arcname, contents.replace(",", "\t"))
        schedule = self.make_loader_and_load()
        # Don't call self.accumulator.AssertNoMoreExceptions() because there are
        # lots of problems but I only care that the validator doesn't crash. In the
        # magical future the validator will stop when the csv is obviously hosed.


class LoadFromDirectoryTestCase(util.TestCase):
    def run_test(self):
        loader = transitfeed.Loader(
            util.DataPath('good_feed'),
            problems=util.GetTestFailureProblemReporter(self),
            extra_validation=True)
        loader.Load()


class LoadUnknownFeedTestCase(util.TestCase):
    def run_test(self):
        feed_name = util.DataPath('unknown_feed')
        loader = transitfeed.Loader(
            feed_name,
            problems=util.ExceptionProblemReporterNoExpiration(),
            extra_validation=True)
        try:
            loader.Load()
            self.fail('FeedNotFound exception expected')
        except transitfeed.FeedNotFound as e:
            self.assertEqual(feed_name, e.feed_name)


class LoadUnknownFormatTestCase(util.TestCase):
    def run_test(self):
        feed_name = util.DataPath('unknown_format.zip')
        loader = transitfeed.Loader(
            feed_name,
            problems=util.ExceptionProblemReporterNoExpiration(),
            extra_validation=True)
        try:
            loader.Load()
            self.fail('UnknownFormat exception expected')
        except transitfeed.UnknownFormat as e:
            self.assertEqual(feed_name, e.feed_name)


class LoadunrecognizedColumnsTestCase(util.TestCase):
    def run_test(self):
        problems = unrecognized_columnRecorder(self)
        loader = transitfeed.Loader(util.DataPath('unrecognized_columns'),
                                    problems=problems)
        loader.Load()
        found_errors = set(problems.column_errors)
        expected_errors = set([
            ('agency.txt', 'agency_lange'),
            ('stops.txt', 'stop_uri'),
            ('routes.txt', 'Route_Text_Color'),
            ('calendar.txt', 'leap_day'),
            ('calendar_dates.txt', 'leap_day'),
            ('trips.txt', 'sharpe_id'),
            ('stop_times.txt', 'shapedisttraveled'),
            ('stop_times.txt', 'drop_off_time'),
            ('fare_attributes.txt', 'transfer_time'),
            ('fare_rules.txt', 'source_id'),
            ('frequencies.txt', 'superfluous'),
            ('transfers.txt', 'to_stop')
        ])

        # Now make sure we got the unrecognized column errors that we expected.
        not_expected = found_errors.difference(expected_errors)
        self.failIf(not_expected, 'unexpected errors: %s' % str(not_expected))
        not_found = expected_errors.difference(found_errors)
        self.failIf(not_found, 'expected but not found: %s' % str(not_found))


class LoadExtraCellValidationTestCase(util.LoadTestCase):
    """Check that the validation detects too many cells in a row."""

    def run_test(self):
        self.Load('extra_row_cells')
        e = self.accumulator.PopException("other_problem")
        self.assertEquals("routes.txt", e.file_name)
        self.assertEquals(4, e.row_num)
        self.accumulator.AssertNoMoreExceptions()


class LoadMissingCellValidationTestCase(util.LoadTestCase):
    """Check that the validation detects missing cells in a row."""

    def run_test(self):
        self.Load('missing_row_cells')
        e = self.accumulator.PopException("other_problem")
        self.assertEquals("routes.txt", e.file_name)
        self.assertEquals(4, e.row_num)
        self.accumulator.AssertNoMoreExceptions()


class LoadUnknownFileTestCase(util.TestCase):
    """Check that the validation detects unknown files."""

    def run_test(self):
        feed_name = util.DataPath('unknown_file')
        self.accumulator = util.RecordingProblemAccumulator(
            self, ("ExpirationDate"))
        self.problems = transitfeed.ProblemReporter(self.accumulator)
        loader = transitfeed.Loader(
            feed_name,
            problems=self.problems,
            extra_validation=True)
        loader.Load()
        e = self.accumulator.PopException('UnknownFile')
        self.assertEqual('frecuencias.txt', e.file_name)
        self.accumulator.AssertNoMoreExceptions()


class LoadMissingAgencyTestCase(util.LoadTestCase):
    def run_test(self):
        self.ExpectMissingFile('missing_agency', 'agency.txt')


class LoadMissingStopsTestCase(util.LoadTestCase):
    def run_test(self):
        self.ExpectMissingFile('missing_stops', 'stops.txt')


class LoadMissingRoutesTestCase(util.LoadTestCase):
    def run_test(self):
        self.ExpectMissingFile('missing_routes', 'routes.txt')


class LoadMissingTripsTestCase(util.LoadTestCase):
    def run_test(self):
        self.ExpectMissingFile('missing_trips', 'trips.txt')


class LoadMissingStopTimesTestCase(util.LoadTestCase):
    def run_test(self):
        self.ExpectMissingFile('missing_stop_times', 'stop_times.txt')


class LoadMissingCalendarTestCase(util.LoadTestCase):
    def run_test(self):
        self.ExpectMissingFile('missing_calendar', 'calendar.txt')


class EmptyFileTestCase(util.TestCase):
    def run_test(self):
        loader = transitfeed.Loader(
            util.DataPath('empty_file'),
            problems=util.ExceptionProblemReporterNoExpiration(),
            extra_validation=True)
        try:
            loader.Load()
            self.fail('EmptyFile exception expected')
        except transitfeed.EmptyFile as e:
            self.assertEqual('agency.txt', e.file_name)


class missing_columnTestCase(util.TestCase):
    def run_test(self):
        loader = transitfeed.Loader(
            util.DataPath('missing_column'),
            problems=util.ExceptionProblemReporterNoExpiration(),
            extra_validation=True)
        try:
            loader.Load()
            self.fail('missing_column exception expected')
        except transitfeed.missing_column as e:
            self.assertEqual('agency.txt', e.file_name)
            self.assertEqual('agency_name', e.column_name)


class LoadUTF8BOMTestCase(util.TestCase):
    def run_test(self):
        loader = transitfeed.Loader(
            util.DataPath('utf8bom'),
            problems=util.GetTestFailureProblemReporter(self),
            extra_validation=True)
        loader.Load()


class LoadUTF16TestCase(util.TestCase):
    def run_test(self):
        # utf16 generated by `recode utf8..utf16 *'
        accumulator = transitfeed.ExceptionProblemAccumulator()
        problem_reporter = transitfeed.ProblemReporter(accumulator)
        loader = transitfeed.Loader(
            util.DataPath('utf16'),
            problems=problem_reporter,
            extra_validation=True)
        try:
            loader.Load()
            # TODO: make sure processing proceeds beyond the problem
            self.fail('FileFormat exception expected')
        except transitfeed.FileFormat as e:
            # make sure these don't raise an exception
            self.assertTrue(re.search(r'encoded in utf-16', e.FormatProblem()))
            e.FormatContext()


class BadUtf8TestCase(util.LoadTestCase):
    def run_test(self):
        self.Load('bad_utf8')
        self.accumulator.PopException("unrecognized_column")
        self.accumulator.Popinvalid_value("agency_name", "agency.txt")
        self.accumulator.Popinvalid_value("route_long_name", "routes.txt")
        self.accumulator.Popinvalid_value("route_short_name", "routes.txt")
        self.accumulator.Popinvalid_value("stop_headsign", "stop_times.txt")
        self.accumulator.Popinvalid_value("stop_name", "stops.txt")
        self.accumulator.Popinvalid_value("trip_headsign", "trips.txt")
        self.accumulator.AssertNoMoreExceptions()


class LoadNullTestCase(util.TestCase):
    def run_test(self):
        accumulator = transitfeed.ExceptionProblemAccumulator()
        problem_reporter = transitfeed.ProblemReporter(accumulator)
        loader = transitfeed.Loader(
            util.DataPath('contains_null'),
            problems=problem_reporter,
            extra_validation=True)
        try:
            loader.Load()
            self.fail('FileFormat exception expected')
        except transitfeed.FileFormat as e:
            self.assertTrue(re.search(r'contains a null', e.FormatProblem()))
            # make sure these don't raise an exception
            e.FormatContext()


class CsvDictTestCase(util.TestCase):
    def set_up(self):
        self.accumulator = util.RecordingProblemAccumulator(self)
        self.problems = transitfeed.ProblemReporter(self.accumulator)
        self.zip = zipfile.ZipFile(StringIO(), 'a')
        self.loader = transitfeed.Loader(
            problems=self.problems,
            zip=self.zip)

    def tear_down(self):
        self.accumulator.TearDownAssertNoMoreExceptions()

    def test_empty_file(self):
        self.zip.writestr("test.txt", "")
        results = list(self.loader._ReadCsvDict("test.txt", [], [], []))
        self.assertEquals([], results)
        self.accumulator.PopException("EmptyFile")
        self.accumulator.AssertNoMoreExceptions()

    def test_header_only(self):
        self.zip.writestr("test.txt", "test_id,test_name")
        results = list(self.loader._ReadCsvDict("test.txt",
                                                ["test_id", "test_name"], [], []))
        self.assertEquals([], results)
        self.accumulator.AssertNoMoreExceptions()

    def test_header_and_new_line_only(self):
        self.zip.writestr("test.txt", "test_id,test_name\n")
        results = list(self.loader._ReadCsvDict("test.txt",
                                                ["test_id", "test_name"], [], []))
        self.assertEquals([], results)
        self.accumulator.AssertNoMoreExceptions()

    def test_header_with_space_before(self):
        self.zip.writestr("test.txt", " test_id, test_name\n")
        results = list(self.loader._ReadCsvDict("test.txt",
                                                ["test_id", "test_name"], [], []))
        self.assertEquals([], results)
        self.accumulator.AssertNoMoreExceptions()

    def test_header_with_space_beforeAfter(self):
        self.zip.writestr("test.txt", "test_id , test_name\n")
        results = list(self.loader._ReadCsvDict("test.txt",
                                                ["test_id", "test_name"], [], []))
        self.assertEquals([], results)
        e = self.accumulator.PopException("CsvSyntax")
        self.accumulator.AssertNoMoreExceptions()

    def test_header_quoted(self):
        self.zip.writestr("test.txt", "\"test_id\", \"test_name\"\n")
        results = list(self.loader._ReadCsvDict("test.txt",
                                                ["test_id", "test_name"], [], []))
        self.assertEquals([], results)
        self.accumulator.AssertNoMoreExceptions()

    def test_header_space_after_quoted(self):
        self.zip.writestr("test.txt", "\"test_id\" , \"test_name\"\n")
        results = list(self.loader._ReadCsvDict("test.txt",
                                                ["test_id", "test_name"], [], []))
        self.assertEquals([], results)
        e = self.accumulator.PopException("CsvSyntax")
        self.accumulator.AssertNoMoreExceptions()

    def test_header_space_in_quotes_after_value(self):
        self.zip.writestr("test.txt", "\"test_id \",\"test_name\"\n")
        results = list(self.loader._ReadCsvDict("test.txt",
                                                ["test_id", "test_name"], [], []))
        self.assertEquals([], results)
        e = self.accumulator.PopException("CsvSyntax")
        self.accumulator.AssertNoMoreExceptions()

    def test_header_space_in_quotes_before_value(self):
        self.zip.writestr("test.txt", "\"test_id\",\" test_name\"\n")
        results = list(self.loader._ReadCsvDict("test.txt",
                                                ["test_id", "test_name"], [], []))
        self.assertEquals([], results)
        e = self.accumulator.PopException("CsvSyntax")
        self.accumulator.AssertNoMoreExceptions()

    def test_header_empty_column_name(self):
        self.zip.writestr("test.txt", 'test_id,test_name,\n')
        results = list(self.loader._ReadCsvDict("test.txt",
                                                ["test_id", "test_name"], [], []))
        self.assertEquals([], results)
        e = self.accumulator.PopException("CsvSyntax")
        self.accumulator.AssertNoMoreExceptions()

    def test_header_all_unknown_column_names(self):
        self.zip.writestr("test.txt", 'id,nam\n')
        results = list(self.loader._ReadCsvDict("test.txt",
                                                ["test_id", "test_name"], [], []))
        self.assertEquals([], results)
        e = self.accumulator.PopException("CsvSyntax")
        self.assertTrue(e.FormatProblem().find("missing the header") != -1)
        self.accumulator.AssertNoMoreExceptions()

    def test_field_with_spaces(self):
        self.zip.writestr("test.txt",
                          "test_id,test_name\n"
                          "id1 , my name\n")
        results = list(self.loader._ReadCsvDict("test.txt",
                                                ["test_id", "test_name"], [], []))
        self.assertEquals([({"test_id": "id1", "test_name": "my name"}, 2,
                            ["test_id", "test_name"], ["id1", "my name"])],
                          results)
        self.accumulator.AssertNoMoreExceptions()

    def test_field_with_only_spaces(self):
        self.zip.writestr("test.txt",
                          "test_id,test_name\n"
                          "id1,  \n")  # spaces are skipped to yield empty field
        results = list(self.loader._ReadCsvDict("test.txt",
                                                ["test_id", "test_name"], [], []))
        self.assertEquals([({"test_id": "id1", "test_name": ""}, 2,
                            ["test_id", "test_name"], ["id1", ""])], results)
        self.accumulator.AssertNoMoreExceptions()

    def test_quoted_field_with_spaces(self):
        self.zip.writestr("test.txt",
                          'test_id,"test_name",test_size\n'
                          '"id1" , "my name" , "234 "\n')
        results = list(self.loader._ReadCsvDict("test.txt",
                                                ["test_id", "test_name",
                                                 "test_size"], [], []))
        self.assertEquals(
            [({"test_id": "id1", "test_name": "my name", "test_size": "234"}, 2,
              ["test_id", "test_name", "test_size"], ["id1", "my name", "234"])],
            results)
        self.accumulator.AssertNoMoreExceptions()

    def test_quoted_field_with_commas(self):
        self.zip.writestr("test.txt",
                          'id,name1,name2\n'
                          '"1", "brown, tom", "brown, ""tom"""\n')
        results = list(self.loader._ReadCsvDict("test.txt",
                                                ["id", "name1", "name2"], [], []))
        self.assertEquals(
            [({"id": "1", "name1": "brown, tom", "name2": "brown, \"tom\""}, 2,
              ["id", "name1", "name2"], ["1", "brown, tom", "brown, \"tom\""])],
            results)
        self.accumulator.AssertNoMoreExceptions()

    def test_unknown_column(self):
        # A small typo (omitting '_' in a header name) is detected
        self.zip.writestr("test.txt", "test_id,testname\n")
        results = list(self.loader._ReadCsvDict("test.txt",
                                                ["test_id", "test_name"], [], []))
        self.assertEquals([], results)
        e = self.accumulator.PopException("unrecognized_column")
        self.assertEquals("testname", e.column_name)
        self.accumulator.AssertNoMoreExceptions()

    def test_deprecated_column(self):
        self.zip.writestr("test.txt", "test_id,test_old\n")
        results = list(self.loader._ReadCsvDict("test.txt",
                                                ["test_id", "test_new"],
                                                ["test_id"],
                                                [("test_old", "test_new")]))
        self.assertEquals([], results)
        e = self.accumulator.PopException("DeprecatedColumn")
        self.assertEquals("test_old", e.column_name)
        self.assertTrue("test_new" in e.reason)
        self.accumulator.AssertNoMoreExceptions()

    def test_deprecated_columnWithoutNewColumn(self):
        self.zip.writestr("test.txt", "test_id,test_old\n")
        results = list(self.loader._ReadCsvDict("test.txt",
                                                ["test_id", "test_new"],
                                                ["test_id"],
                                                [("test_old", None)]))
        self.assertEquals([], results)
        e = self.accumulator.PopException("DeprecatedColumn")
        self.assertEquals("test_old", e.column_name)
        self.assertTrue(not e.reason or "use the new column" not in e.reason)
        self.accumulator.AssertNoMoreExceptions()

    def test_deprecated_values_being_read(self):
        self.zip.writestr("test.txt",
                          "test_id,test_old\n"
                          "1,old_value1\n"
                          "2,old_value2\n")
        results = list(self.loader._ReadCsvDict("test.txt",
                                                ["test_id", "test_new"],
                                                ["test_id"],
                                                [("test_old", "test_new")]))
        self.assertEquals(2, len(results))
        self.assertEquals('old_value1', results[0][0]['test_old'])
        self.assertEquals('old_value2', results[1][0]['test_old'])
        e = self.accumulator.PopException("DeprecatedColumn")
        self.assertEquals('test_old', e.column_name)
        self.accumulator.AssertNoMoreExceptions()

    def test_missing_required_column(self):
        self.zip.writestr("test.txt", "test_id,test_size\n")
        results = list(self.loader._ReadCsvDict("test.txt",
                                                ["test_id", "test_size"],
                                                ["test_name"], []))
        self.assertEquals([], results)
        e = self.accumulator.PopException("missing_column")
        self.assertEquals("test_name", e.column_name)
        self.accumulator.AssertNoMoreExceptions()

    def test_required_not_in_all_cols(self):
        self.zip.writestr("test.txt", "test_id,test_name,test_size\n")
        results = list(self.loader._ReadCsvDict("test.txt",
                                                ["test_id", "test_size"],
                                                ["test_name"], []))
        self.assertEquals([], results)
        e = self.accumulator.PopException("unrecognized_column")
        self.assertEquals("test_name", e.column_name)
        self.accumulator.AssertNoMoreExceptions()

    def test_blank_line(self):
        # line_num is increased for an empty line
        self.zip.writestr("test.txt",
                          "test_id,test_name\n"
                          "\n"
                          "id1,my name\n")
        results = list(self.loader._ReadCsvDict("test.txt",
                                                ["test_id", "test_name"], [], []))
        self.assertEquals([({"test_id": "id1", "test_name": "my name"}, 3,
                            ["test_id", "test_name"], ["id1", "my name"])], results)
        self.accumulator.AssertNoMoreExceptions()

    def test_extra_comma(self):
        self.zip.writestr("test.txt",
                          "test_id,test_name\n"
                          "id1,my name,\n")
        results = list(self.loader._ReadCsvDict("test.txt",
                                                ["test_id", "test_name"], [], []))
        self.assertEquals([({"test_id": "id1", "test_name": "my name"}, 2,
                            ["test_id", "test_name"], ["id1", "my name"])],
                          results)
        e = self.accumulator.PopException("other_problem")
        self.assertTrue(e.FormatProblem().find("too many cells") != -1)
        self.accumulator.AssertNoMoreExceptions()

    def test_missing_comma(self):
        self.zip.writestr("test.txt",
                          "test_id,test_name\n"
                          "id1 my name\n")
        results = list(self.loader._ReadCsvDict("test.txt",
                                                ["test_id", "test_name"], [], []))
        self.assertEquals([({"test_id": "id1 my name"}, 2,
                            ["test_id", "test_name"], ["id1 my name"])], results)
        e = self.accumulator.PopException("other_problem")
        self.assertTrue(e.FormatProblem().find("missing cells") != -1)
        self.accumulator.AssertNoMoreExceptions()

    def test_detects_duplicate_headers(self):
        self.zip.writestr(
            "transfers.txt",
            "from_stop_id,from_stop_id,to_stop_id,transfer_type,min_transfer_time,"
            "min_transfer_time,min_transfer_time,min_transfer_time,unknown,"
            "unknown\n"
            "BEATTY_AIRPORT,BEATTY_AIRPORT,BULLFROG,3,,2,,,,\n"
            "BULLFROG,BULLFROG,BEATTY_AIRPORT,2,1200,1,,,,\n")

        list(self.loader._ReadCsvDict("transfers.txt",
                                      transitfeed.Transfer._FIELD_NAMES,
                                      transitfeed.Transfer._REQUIRED_FIELD_NAMES,
                                      transitfeed.Transfer._DEPRECATED_FIELD_NAMES))

        self.accumulator.PopDuplicateColumn("transfers.txt", "from_stop_id", 2)
        self.accumulator.PopDuplicateColumn("transfers.txt", "min_transfer_time", 4)
        self.accumulator.PopDuplicateColumn("transfers.txt", "unknown", 2)
        e = self.accumulator.PopException("unrecognized_column")
        self.assertEquals("unknown", e.column_name)
        self.accumulator.AssertNoMoreExceptions()


class ReadCsvTestCase(util.TestCase):
    def set_up(self):
        self.accumulator = util.RecordingProblemAccumulator(self)
        self.problems = transitfeed.ProblemReporter(self.accumulator)
        self.zip = zipfile.ZipFile(StringIO(), 'a')
        self.loader = transitfeed.Loader(
            problems=self.problems,
            zip=self.zip)

    def tear_down(self):
        self.accumulator.TearDownAssertNoMoreExceptions()

    def test_detects_duplicate_headers(self):
        self.zip.writestr(
            "calendar.txt",
            "service_id,monday,tuesday,wednesday,thursday,friday,saturday,sunday,"
            "start_date,end_date,end_date,end_date,tuesday,unknown,unknown\n"
            "FULLW,1,1,1,1,1,1,1,20070101,20101231,,,,,\n")

        list(self.loader._ReadCSV("calendar.txt",
                                  transitfeed.ServicePeriod._FIELD_NAMES,
                                  transitfeed.ServicePeriod._REQUIRED_FIELD_NAMES,
                                  transitfeed.ServicePeriod._DEPRECATED_FIELD_NAMES
                                  ))

        self.accumulator.PopDuplicateColumn("calendar.txt", "end_date", 3)
        self.accumulator.PopDuplicateColumn("calendar.txt", "tuesday", 2)
        self.accumulator.PopDuplicateColumn("calendar.txt", "unknown", 2)
        e = self.accumulator.PopException("unrecognized_column")
        self.assertEquals("unknown", e.column_name)
        self.accumulator.AssertNoMoreExceptions()

    def test_deprecated_column(self):
        self.zip.writestr("test.txt", "test_id,test_old\n")
        results = list(self.loader._ReadCSV("test.txt",
                                            ["test_id", "test_new"],
                                            ["test_id"],
                                            [("test_old", "test_new")]))
        self.assertEquals([], results)
        e = self.accumulator.PopException("DeprecatedColumn")
        self.assertEquals("test_old", e.column_name)
        self.assertTrue("test_new" in e.reason)
        self.accumulator.AssertNoMoreExceptions()

    def test_deprecated_columnWithoutNewColumn(self):
        self.zip.writestr("test.txt", "test_id,test_old\n")
        results = list(self.loader._ReadCSV("test.txt",
                                            ["test_id", "test_new"],
                                            ["test_id"],
                                            [("test_old", None)]))
        self.assertEquals([], results)
        e = self.accumulator.PopException("DeprecatedColumn")
        self.assertEquals("test_old", e.column_name)
        self.assertTrue(not e.reason or "use the new column" not in e.reason)
        self.accumulator.AssertNoMoreExceptions()


class BasicParsingTestCase(util.TestCase):
    """Checks that we're getting the number of child objects that we expect."""

    def assert_loaded_correctly(self, schedule):
        """Check that the good_feed looks correct"""
        self.assertEqual(1, len(schedule._agencies))
        self.assertEqual(5, len(schedule.routes))
        self.assertEqual(2, len(schedule.service_periods))
        self.assertEqual(10, len(schedule.stops))
        self.assertEqual(11, len(schedule.trips))
        self.assertEqual(0, len(schedule.fare_zones))

    def assert_loaded_stop_times_correctly(self, schedule):
        self.assertEqual(5, len(schedule.GetTrip('CITY1').GetStopTimes()))
        self.assertEqual('to airport', schedule.GetTrip('STBA').GetStopTimes()[0].stop_headsign)
        self.assertEqual(2, schedule.GetTrip('CITY1').GetStopTimes()[1].pickup_type)
        self.assertEqual(3, schedule.GetTrip('CITY1').GetStopTimes()[1].drop_off_type)

    def test__memory_db(self):
        loader = transitfeed.Loader(
            util.DataPath('good_feed.zip'),
            problems=util.GetTestFailureProblemReporter(self),
            extra_validation=True,
            memory_db=True)
        schedule = loader.Load()
        self.assert_loaded_correctly(schedule)
        self.assert_loaded_stop_times_correctly(schedule)

    def test__temporary_file(self):
        loader = transitfeed.Loader(
            util.DataPath('good_feed.zip'),
            problems=util.GetTestFailureProblemReporter(self),
            extra_validation=True,
            memory_db=False)
        schedule = loader.Load()
        self.assert_loaded_correctly(schedule)
        self.assert_loaded_stop_times_correctly(schedule)

    def test__no_load_stop_times(self):
        problems = util.GetTestFailureProblemReporter(
            self, ignore_types=("ExpirationDate", "UnusedStop", "other_problem"))
        loader = transitfeed.Loader(
            util.DataPath('good_feed.zip'),
            problems=problems,
            extra_validation=True,
            load_stop_times=False)
        schedule = loader.Load()
        self.assert_loaded_correctly(schedule)
        self.assertEqual(0, len(schedule.GetTrip('CITY1').GetStopTimes()))


class UndefinedStopAgencyTestCase(util.LoadTestCase):
    def run_test(self):
        self.Expectinvalid_value('undefined_stop', 'stop_id')
