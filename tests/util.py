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

# Code shared between tests.
from __future__ import absolute_import
from __future__ import print_function


import os
import os.path
import re
try:
    import io as StringIO
    import os as dircache
except ImportError:
    import cStringIO as StringIO
    import dircache
import shutil
import subprocess
import sys
import tempfile
import traceback
import unittest
import zipfile
import transitfeed
from transitfeed import problems


def check_call(cmd, expected_retcode=0, stdin_str="", **kwargs):
    """Convenience function that is in the docs for subprocess but not
    installed on my system. Raises an Exception if the return code is not
    expected_retcode. Returns a tuple of strings, (stdout, stderr)."""
    try:
        if 'stdout' in kwargs or 'stderr' in kwargs or 'stdin' in kwargs:
            raise Exception("Don't pass stdout or stderr")

        # If a custom 'env' is in kwargs this will be passed to subprocess.Popen and
        # will prevent the subprocess from inheriting the parent's 'env'.
        # On Windows 7 we have to make sure that our custom 'env' contains
        # 'SystemRoot' as some code here is using os.urandom() which requires this
        # system variable. See review at http://codereview.appspot.com/4240085/ and
        # thread "is this a bug? no environment variables" at
        # http://www.gossamer-threads.com/lists/python/dev/878941
        if 'SystemRoot' in os.environ:
            if 'env' in kwargs:
                kwargs['env'].setdefault('SystemRoot', os.environ['SystemRoot'])

        p = subprocess.Popen(cmd, stdout=subprocess.PIPE,
                             stderr=subprocess.PIPE, stdin=subprocess.PIPE,
                             **kwargs)
        (out, err) = p.communicate(stdin_str)
        retcode = p.returncode
    except Exception as e:
        raise Exception("When running %s: %s" % (cmd, e))
    if retcode < 0:
        raise Exception(
            "Child '%s' was terminated by signal %d. Output:\n%s\n%s\n" %
            (cmd, -retcode, out, err))
    elif retcode != expected_retcode:
        raise Exception(
            "Child '%s' returned %d. Output:\n%s\n%s\n" %
            (cmd, retcode, out, err))
    return out, err


def data_path(path):
    here = os.path.dirname(__file__)
    return os.path.join(here, 'data', path)


def getdata_path_contents():
    here = os.path.dirname(__file__)
    return dircache.listdir(os.path.join(here, 'data'))


class TestCase(unittest.TestCase):
    """Base of every TestCase class in this project.

    This adds some methods that perhaps should be in unittest.TestCase.
    """

    # Note from Tom, Dec 9 2009: Be careful about adding set_up or tear_down
    # because they will be run a few hundred times.

    def assert_matches_regex(self, regex, string):
        """Assert that regex is found in string."""
        if not re.search(regex, string):
            self.fail("string %r did not match regex %r" % (string, regex))


class RedirectStdOutTestCaseBase(TestCase):
    """Save stdout to the StringIO buffer self.this_stdout"""

    def set_up(self):
        self.saved_stdout = sys.stdout
        self.this_stdout = StringIO.StringIO()
        sys.stdout = self.this_stdout

    def tear_down(self):
        sys.stdout = self.saved_stdout
        self.this_stdout.close()


class GetPathTestCase(TestCase):
    """TestCase with method to get paths to files in the distribution."""
    def set_up(self):
        self._origcwd = os.getcwd()
        super(GetPathTestCase, self).set_up()

    def get_example_path(self, name):
        """Return the full path of a file in the examples directory"""
        return self.get_path('examples', name)

    def get_test_data_path(self, *path):
        """Return the full path of a file in the tests/data directory"""
        return self.get_path('tests', 'data', *path)

    def get_path(self, *path):
        try:
            self.set_up()
        except AttributeError:
            self._origcwd = os.getcwd()
        """Return absolute path of path. path is relative main source directory."""
        here = os.path.dirname(__file__)  # Relative to _origcwd
        return os.path.join(self._origcwd, here, '..', *path)


class TempDirTestCaseBase(GetPathTestCase):
    """Make a temporary directory the current directory before running the test
    and remove it after the test.
    """

    def set_up(self):
        GetPathTestCase.set_up(self)
        self.tempdirpath = tempfile.mkdtemp()
        os.chdir(self.tempdirpath)

    def tear_down(self):
        os.chdir(self._origcwd)
        shutil.rmtree(self.tempdirpath)
        GetPathTestCase.tear_down(self)

    @staticmethod
    def check_call_with_path(cmd, expected_retcode=0, stdin_str=""):
        """Run python script cmd[0] with args cmd[1:], making sure 'import
        transitfeed' will use the module in this source tree. Raises an Exception
        if the return code is not expected_retcode. Returns a tuple of strings,
        (stdout, stderr)."""
        tf_path = transitfeed.__file__
        # Path of the directory containing transitfeed. When this is added to
        # sys.path importing transitfeed should work independent of if
        # transitfeed.__file__ is <parent>/transitfeed.py or
        # <parent>/transitfeed/__init__.py
        transitfeed_parent = tf_path[:tf_path.rfind("transitfeed")]
        transitfeed_parent = transitfeed_parent.replace("\\", "/").rstrip("/")
        script_path = cmd[0].replace("\\", "/")
        script_args = cmd[1:]

        # Propogate sys.path of this process to the subprocess. This is done
        # because I assume that if this process has a customized sys.path it is
        # meant to be used for all processes involved in the tests.  The downside
        # of this is that the subprocess is no longer a clean version of what you
        # get when running "python" after installing transitfeed. Hopefully if this
        # process uses a customized sys.path you know what you are doing.
        env = {"PYTHONPATH": ":".join(sys.path)}

        # Instead of directly running the script make sure that the transitfeed
        # module in this source directory is at the front of sys.path. Then
        # adjust sys.argv so it looks like the script was run directly. This lets
        # OptionParser use the correct value for %proj.
        cmd = [sys.executable, "-c",
               "import sys; "
               "sys.path.insert(0,'%s'); "
               "sys.argv = ['%s'] + sys.argv[1:]; "
               "exec(open('%s'))" %
               (transitfeed_parent, script_path, script_path)] + script_args
        return check_call(cmd, expected_retcode=expected_retcode, shell=False,
                          env=env, stdin_str=stdin_str)

    @staticmethod
    def convert_zip_to_dict(zip):
        """Converts a zip file into a dictionary.

        Arguments:
            zip: The zipfile whose contents are to be converted to a dictionary.

        Returns:
            A dictionary mapping filenames to file contents."""

        zip_dict = {}
        for archive_name in zip.namelist():
            zip_dict[archive_name] = zip.read(archive_name)
        zip.close()
        return zip_dict

    @staticmethod
    def convert_dict_to_zip(dict):
        """Converts a dictionary to an in-memory zipfile.

        Arguments:
            dict: A dictionary mapping file names to file contents

        Returns:
            The new file's in-memory contents as a file-like object."""
        zipfile_mem = StringIO.StringIO()
        zip = zipfile.ZipFile(zipfile_mem, 'a')
        for arcname, contents in dict.items():
            zip.writestr(arcname, contents)
        zip.close()
        return zipfile_mem


class TempFileTestCaseBase(TestCase):
    """
    Subclass of TestCase which sets self.tempfilepath to a valid temporary zip
    file name and removes the file if it exists when the test is done.
    """

    def set_up(self):
        (fd, self.tempfilepath) = tempfile.mkstemp(".zip")
        # Open file handle causes an exception during remove in Windows
        os.close(fd)

    def tear_down(self):
        if os.path.exists(self.tempfilepath):
            os.remove(self.tempfilepath)


class MemoryZipTestCase(TestCase):
    """Base for TestCase classes which read from an in-memory zip file.

    A test that loads data from this zip file exercises almost all the code used
    when the feedvalidator runs, but does not touch disk. Unfortunately it is very
    difficult to add new stops to the default stops.txt because a new stop will
    break tests in StopHierarchyTestCase and StopsNearEachOther."""

    _IGNORE_TYPES = ["expiration_date"]

    def set_up(self):
        self.accumulator = RecordingProblemAccumulator(self, self._IGNORE_TYPES)
        self.problems = transitfeed.ProblemReporter(self.accumulator)
        self.zip_contents = {}
        self.set_archive_contents(
            "agency.txt",
            "agency_id,agency_name,agency_url,agency_timezone\n"
            "DTA,Demo Agency,http://google.com,America/Los_Angeles\n")
        self.set_archive_contents(
            "calendar.txt",
            "service_id,monday,tuesday,wednesday,thursday,friday,saturday,sunday,"
            "start_date,end_date\n"
            "FULLW,1,1,1,1,1,1,1,20070101,20101231\n"
            "WE,0,0,0,0,0,1,1,20070101,20101231\n")
        self.set_archive_contents(
            "calendar_dates.txt",
            "service_id,date,exception_type\n"
            "FULLW,20070101,1\n")
        self.set_archive_contents(
            "routes.txt",
            "route_id,agency_id,route_short_name,route_long_name,route_type\n"
            "AB,DTA,,Airport Bullfrog,3\n")
        self.set_archive_contents(
            "trips.txt",
            "route_id,service_id,trip_id\n"
            "AB,FULLW,AB1\n")
        self.set_archive_contents(
            "stops.txt",
            "stop_id,stop_name,stop_lat,stop_lon\n"
            "BEATTY_AIRPORT,Airport,36.868446,-116.784582\n"
            "BULLFROG,Bullfrog,36.88108,-116.81797\n"
            "STAGECOACH,Stagecoach Hotel,36.915682,-116.751677\n")
        self.set_archive_contents(
            "stop_times.txt",
            "trip_id,arrival_time,departure_time,stop_id,stop_sequence\n"
            "AB1,10:00:00,10:00:00,BEATTY_AIRPORT,1\n"
            "AB1,10:20:00,10:20:00,BULLFROG,2\n"
            "AB1,10:25:00,10:25:00,STAGECOACH,3\n")

    def make_loader_and_load(self,
                             problems=None,
                             extra_validation=True,
                             gtfs_factory=None):
        """Returns a Schedule loaded with the contents of the file dict."""

        if gtfs_factory is None:
            gtfs_factory = transitfeed.get_gtfs_factory()
        if problems is None:
            problems = self.problems
        self.create_zip()
        self.loader = transitfeed.loader(
            problems=problems,
            extra_validation=extra_validation,
            zip=self.zip,
            gtfs_factory=gtfs_factory)
        return self.loader.load()

    def append_to_archive_contents(self, arcname, s):
        """Append string s to file arcname in the file dict.

        All calls to this function, if any, should be made before calling
        make_loader_and_load."""
        current_contents = self.zip_contents[arcname]
        self.zip_contents[arcname] = current_contents + s

    def set_archive_contents(self, arcname, contents):
        """Set the contents of file arcname in the file dict.

        All calls to this function, if any, should be made before calling
        make_loader_and_load."""
        self.zip_contents[arcname] = contents

    def get_archive_contents(self, arcname):
        """Get the contents of file arcname in the file dict."""
        return self.zip_contents[arcname]

    def remove_archive(self, arcname):
        """Remove file arcname from the file dict.

        All calls to this function, if any, should be made before calling
        make_loader_and_load."""
        del self.zip_contents[arcname]

    def get_archive_names(self):
        """Get a list of all the archive names in the file dict."""
        return self.zip_contents.keys()

    def create_zip(self):
        """Create an in-memory GTFS zipfile from the contents of the file dict."""
        self.zipfile = StringIO.StringIO()
        self.zip = zipfile.ZipFile(self.zipfile, 'a')
        for (arcname, contents) in self.zip_contents.items():
            try:
                self.zip.writestr(arcname, contents)
            except TypeError:
                self.zip.write(arcname, contents)

    def dump_zip_file(self, zf):
        """Print the contents of something zipfile can open, such as a StringIO."""
        # Handy for debugging
        z = zipfile.ZipFile(zf)
        for n in z.namelist():
            print("--\n%s\n%s" % (n, z.read(n)))


class LoadTestCase(TestCase):
    def set_up(self):
        self.accumulator = RecordingProblemAccumulator(self, ("expiration_date",))
        self.problems = transitfeed.ProblemReporter(self.accumulator)

    def load(self, feed_name):
        loader = transitfeed.loader(
            data_path(feed_name), problems=self.problems, extra_validation=True)
        loader.load()

    def expect_invalid_value(self, feed_name, column_name):
        self.load(feed_name)
        self.accumulator.pop_invalid_value(column_name)
        self.accumulator.assert_no_more_exceptions()

    def expect_missing_file(self, feed_name, file_name):
        self.load(feed_name)
        e = self.accumulator.pop_exception("MissingFile")
        self.assertEqual(file_name, e.file_name)
        # Don't call assert_no_more_exceptions() because a missing file causes
        # many errors.


INVALID_VALUE = Exception()


class ValidationTestCase(TestCase):
    def set_up(self):
        self.accumulator = RecordingProblemAccumulator(
            self, ("expiration_date", "NoServiceExceptions"))
        self.problems = transitfeed.ProblemReporter(self.accumulator)

    def tear_down(self):
        self.accumulator.tear_down_assert_no_more_exceptions()

    def expect_no_problems(self, object):
        self.accumulator.assert_no_more_exceptions()
        object.Validate(self.problems)
        self.accumulator.assert_no_more_exceptions()

    # TODO: think about Expect*Closure methods. With the
    # RecordingProblemAccumulator it is now possible to replace
    # self.expect_missing_value_in_closure(lambda: o.method(...), foo)
    # with
    # o.method(...)
    # self.expect_missing_value_in_closure(foo)
    # because problems don't raise an exception. This has the advantage of
    # making it easy and clear to test the return value of o.method(...) and
    # easier to test for a sequence of problems caused by one call.
    # neun@ 2011-01-18: for the moment I don't remove the Expect*InClosure methods
    # as they allow enforcing an assert_no_more_exceptions() before validation.
    # When removing them we do have to make sure that each "logical test block"
    # before an Expect*InClosure usage really ends with assert_no_more_exceptions.
    # See http://codereview.appspot.com/4020041/
    def validate_and_expect_missing_value(self, object, column_name):
        self.accumulator.assert_no_more_exceptions()
        object.Validate(self.problems)
        self.expect_exception('missing_value', column_name)

    def expect_missing_value_in_closure(self, column_name, c):
        self.accumulator.assert_no_more_exceptions()
        rv = c()
        self.expect_exception('missing_value', column_name)

    def validate_andexpect_invalid_value(self, object, column_name,
                                         value=INVALID_VALUE):
        self.accumulator.assert_no_more_exceptions()
        object.Validate(self.problems)
        self.expect_exception('invalid_value', column_name, value)

    def expect_invalid_value_in_closure(self, column_name, value=INVALID_VALUE,
                                        c=None):
        self.accumulator.assert_no_more_exceptions()
        rv = c()
        self.expect_exception('invalid_value', column_name, value)

    def validate_and_expect_invalid_float_value(self, object, value):
        self.accumulator.assert_no_more_exceptions()
        object.Validate(self.problems)
        self.expect_exception('InvalidFloatValue', None, value)

    def validate_and_expect_other_problem(self, object):
        self.accumulator.assert_no_more_exceptions()
        object.Validate(self.problems)
        self.expect_exception('other_problem')

    def expect_other_problem_in_closure(self, c):
        self.accumulator.assert_no_more_exceptions()
        rv = c()
        self.expect_exception('other_problem')

    def validate_and_expect_date_outside_valid_range(self, object, column_name,
                                                     value=INVALID_VALUE):
        self.accumulator.assert_no_more_exceptions()
        object.Validate(self.problems)
        self.expect_exception('DateOutsideValidRange', column_name, value)

    def expect_exception(self, type_name, column_name=None, value=INVALID_VALUE):
        e = self.accumulator.pop_exception(type_name)
        if column_name:
            self.assertEqual(column_name, e.column_name)
        if value != INVALID_VALUE:
            self.assertEqual(value, e.value)
        # these should not throw any exceptions
        e.FormatProblem()
        e.FormatContext()
        self.accumulator.assert_no_more_exceptions()

    def simple_schedule(self):
        """Return a minimum schedule that will load without warnings."""
        schedule = transitfeed.Schedule(problem_reporter=self.problems)
        schedule.AddAgency("Fly Agency", "http://iflyagency.com",
                           "America/Los_Angeles")
        service_period = transitfeed.ServicePeriod("WEEK")
        service_period.SetWeekdayService(True)
        service_period.SetStartDate("20091203")
        service_period.SetEndDate("20111203")
        service_period.set_date_has_service("20091203")
        schedule.add_service_period_object(service_period)
        stop1 = schedule.add_stop(lng=1.00, lat=48.2, name="Stop 1", stop_id="stop1")
        stop2 = schedule.add_stop(lng=1.01, lat=48.2, name="Stop 2", stop_id="stop2")
        stop3 = schedule.add_stop(lng=1.03, lat=48.2, name="Stop 3", stop_id="stop3")
        route = schedule.AddRoute("54C", "", "Bus", route_id="054C")
        trip = route.AddTrip(schedule, "bus trip", trip_id="CITY1")
        trip.AddStopTime(stop1, stop_time="12:00:00")
        trip.AddStopTime(stop2, stop_time="12:00:45")
        trip.AddStopTime(stop3, stop_time="12:02:30")
        return schedule


# TODO(anog): Revisit this after we implement proper per-exception level change
class RecordingProblemAccumulator(problems.ProblemAccumulatorInterface):
    """Save all problems for later inspection.

    Args:
      test_case: a unittest.TestCase object on which to report problems
      ignore_types: sequence of string type names that will be ignored by the
      ProblemAccumulator
    """

    def __init__(self, test_case, ignore_types=None):
        self.exceptions = []
        self._test_case = test_case
        self._ignore_types = ignore_types or set()
        self._sorted = False

    def _report(self, e):
        # Ensure that these don't crash
        e.FormatProblem()
        e.FormatContext()
        if e.__class__.__name__ in self._ignore_types:
            return
        # Keep the 7 nearest stack frames. This should be enough to identify
        # the code path that created the exception while trimming off most of the
        # large test framework's stack.
        traceback_list = traceback.format_list(traceback.extract_stack()[-7:-1])
        self.exceptions.append((e, ''.join(traceback_list)))

    def pop_exception(self, type_name):
        """Return the first exception, which must be a type_name."""
        if not self._sorted:
            self._sort_exception_groups()
            self._sorted = True
        e = self.exceptions.pop(0)
        e_name = e[0].__class__.__name__
        self._test_case.assertEqual(e_name, type_name,
                                    "%s != %s\n%s" %
                                    (e_name, type_name, self.format_exception(*e)))
        return e[0]

    @staticmethod
    def format_exception(exce, tb):
        return ("%s\nwith gtfs file context %s\nand traceback\n%s" %
                (exce.FormatProblem(), exce.FormatContext(), tb))

    def tear_down_assert_no_more_exceptions(self):
        """Assert that there are no unexpected problems left after a test has run.

           This function should be called on a test's tear_down. For more information
           please see assert_no_more_exceptions"""
        assert len(self.exceptions) == 0, \
            "see util.RecordingProblemAccumulator.assert_no_more_exceptions"

    def assert_no_more_exceptions(self):
        """Check that no unexpected problems were reported.

        Every test that uses a RecordingProblemReporter should end with a call to
        this method. If set_up creates a RecordingProblemReporter it is good for
        tear_down to double check that the exceptions list was emptied.
        """
        exceptions_as_text = []
        for e, tb in self.exceptions:
            exceptions_as_text.append(self.format_exception(e, tb))
        # If the assertFalse below fails the test will abort and tear_down is
        # called. Some tear_down methods assert that self.exceptions is empty as
        # protection against a test that doesn't end with assert_no_more_exceptions
        # and has exceptions remaining in the RecordingProblemReporter. It would
        # be nice to trigger a normal test failure in tear_down but the idea was
        # rejected (http://bugs.python.org/issue5531).
        self.exceptions = []
        self._test_case.assertFalse(exceptions_as_text,
                                    "\n".join(exceptions_as_text))

    def pop_column_specific_exception(self, type_name, column_name, file_name=None):
        """Pops and validates column-specific exceptions from the accumulator.

        Asserts that the exception is of the given type, and originated in the
        specified file and column.

        Arguments:
            type_name: the type of the exception as string, e.g. 'invalid_value'
            column_name: the name of the field (column) which caused the exception
            file_name: optional, the name of the file containing the bad field

        Returns:
            the exception object
        """
        e = self.pop_exception(type_name)
        self._test_case.assertEquals(column_name, e.column_name)
        if file_name:
            self._test_case.assertEquals(file_name, e.file_name)
        return e

    def pop_invalid_value(self, column_name, file_name=None):
        return self.pop_column_specific_exception("invalid_value", column_name,
                                                  file_name)

    def pop_missing_value(self, column_name, file_name=None):
        return self.pop_column_specific_exception("missing_value", column_name,
                                                  file_name)

    def pop_date_outside_valid_range(self, column_name, file_name=None):
        return self.pop_column_specific_exception("DateOutsideValidRange", column_name,
                                                  file_name)

    def pop_duplicate_column(self, file_name, header, count):
        e = self.pop_exception("DuplicateColumn")
        self._test_case.assertEquals(file_name, e.file_name)
        self._test_case.assertEquals(header, e.header)
        self._test_case.assertEquals(count, e.count)
        return e

    def _sort_exception_groups(self):
        """Applies a consistent order to exceptions for repeatable testing.

        Exceptions are only sorted when multiple exceptions of the same type appear
        consecutively within the full exception list.  For example, if the exception
        list is ['B2', 'B1', 'A2', 'A1', 'A3', 'B3'], where A B and C are distinct
        exception types, the resulting order is ['B1', 'B2', 'A1', 'A2', 'A3', 'B3']
        Notice the order of exception types does not change, but grouped exceptions
        of the same type are sorted within their group.

        The ExceptionWithContext.GetOrderKey method id used for generating the sort
        key for exceptions.
        """
        sorted_exceptions = []
        exception_group = []
        current_exception_type = None

        def process_exception_group():
            exception_group.sort(key=lambda x: x[0].GetOrderKey())
            sorted_exceptions.extend(exception_group)

        for e_tuple in self.exceptions:
            e = e_tuple[0]
            if e.__class__ != current_exception_type:
                current_exception_type = e.__class__
                process_exception_group()
                exception_group = []
            exception_group.append(e_tuple)
        process_exception_group()
        self.exceptions = sorted_exceptions


class TestFailureProblemAccumulator(problems.ProblemAccumulatorInterface):
    """Causes a test failure immediately on any problem."""

    def __init__(self, test_case, ignore_types=("expiration_date",)):
        self.test_case = test_case
        self._ignore_types = ignore_types or set()

    def _report(self, e):
        # These should never crash
        formatted_problem = e.FormatProblem()
        formatted_context = e.FormatContext()
        exception_class = e.__class__.__name__
        if exception_class in self._ignore_types:
            return
        self.test_case.fail(
            "%s: %s\n%s" % (exception_class, formatted_problem, formatted_context))


def get_test_failure_problem_reporter(test_case,
                                      ignore_types=("expiration_date",)):
    accumulator = TestFailureProblemAccumulator(test_case, ignore_types)
    problems = transitfeed.ProblemReporter(accumulator)
    return problems


class ExceptionProblemReporterNoExpiration(problems.ProblemReporter):
    """Ignores feed expiration problems.

    Use TestFailureProblemReporter in new code because it fails more cleanly, is
    easier to extend and does more thorough checking.
    """

    def __init__(self):
        accumulator = transitfeed.ExceptionProblemAccumulator(raise_warnings=True)
        transitfeed.ProblemReporter.__init__(self, accumulator)

    def expiration_date(self, expiration, context=None):
        pass  # We don't want to give errors about our test data
