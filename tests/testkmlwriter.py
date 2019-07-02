#!/usr/bin/python2.4
#
# Copyright 2008 Google Inc. All Rights Reserved.
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

"""Unit tests for the kmlwriter module."""

from __future__ import absolute_import
import os
try:
    from io import StringIO
except ImportError:
    import StringIO
import tempfile
import unittest
import kmlparser
import kmlwriter
from tests import util
import transitfeed

try:
    import xml.etree.ElementTree as ET  # python 2.5
except ImportError as e:
    import elementtree.ElementTree as ET  # older pythons


def data_path(path):
    """Return the path to a given file in the test data directory.

    Args:
      path: The path relative to the test data directory.

    Returns:
      The absolute path.
    """
    here = os.path.dirname(__file__)
    return os.path.join(here, 'data', path)


def _element_to_string(root):
    """Returns the node as an XML string.

    Args:
      root: The ElementTree.Element instance.

    Returns:
      The XML string.
    """
    output = StringIO.StringIO()
    ET.ElementTree(root).write(output, 'utf-8')
    return output.getvalue()


class TestKMLStopsRoundtrip(util.TestCase):
    """Checks to see whether all stops are preserved when going to and from KML.
    """

    def set_up(self):
        fd, self.kml_output = tempfile.mkstemp('kml')
        os.close(fd)

    def tear_down(self):
        os.remove(self.kml_output)

    def run_test(self):
        gtfs_input = data_path('good_feed.zip')
        feed1 = transitfeed.Loader(gtfs_input).Load()
        kmlwriter.KMLWriter().Write(feed1, self.kml_output)
        feed2 = transitfeed.Schedule()
        kmlparser.KmlParser().Parse(self.kml_output, feed2)

        stop_name_mapper = lambda x: x.stop_name

        stops1 = set(map(stop_name_mapper, feed1.GetStopList()))
        stops2 = set(map(stop_name_mapper, feed2.GetStopList()))

        self.assertEqual(stops1, stops2)


class TestKMLGeneratorMethods(util.TestCase):
    """Tests the various KML element creation methods of KMLWriter."""

    def set_up(self):
        self.kmlwriter = kmlwriter.KMLWriter()
        self.parent = ET.Element('parent')

    def test_create_folder_visible(self):
        element = self.kmlwriter._CreateFolder(self.parent, 'folder_name')
        self.assertEqual(_element_to_string(element),
                         '<Folder><name>folder_name</name></Folder>')

    def test_create_folder_not_visible(self):
        element = self.kmlwriter._CreateFolder(self.parent, 'folder_name',
                                               visible=False)
        self.assertEqual(_element_to_string(element),
                         '<Folder><name>folder_name</name>'
                         '<visibility>0</visibility></Folder>')

    def test_create_folder_with_description(self):
        element = self.kmlwriter._CreateFolder(self.parent, 'folder_name',
                                               description='folder_desc')
        self.assertEqual(_element_to_string(element),
                         '<Folder><name>folder_name</name>'
                         '<description>folder_desc</description></Folder>')

    def test_create_placemark(self):
        element = self.kmlwriter._CreatePlacemark(self.parent, 'abcdef')
        self.assertEqual(_element_to_string(element),
                         '<Placemark><name>abcdef</name></Placemark>')

    def test_create_placemarkWithStyle(self):
        element = self.kmlwriter._CreatePlacemark(self.parent, 'abcdef',
                                                  style_id='ghijkl')
        self.assertEqual(_element_to_string(element),
                         '<Placemark><name>abcdef</name>'
                         '<styleUrl>#ghijkl</styleUrl></Placemark>')

    def test_create_placemarkNotVisible(self):
        element = self.kmlwriter._CreatePlacemark(self.parent, 'abcdef',
                                                  visible=False)
        self.assertEqual(_element_to_string(element),
                         '<Placemark><name>abcdef</name>'
                         '<visibility>0</visibility></Placemark>')

    def test_create_placemarkWithDescription(self):
        element = self.kmlwriter._CreatePlacemark(self.parent, 'abcdef',
                                                  description='ghijkl')
        self.assertEqual(_element_to_string(element),
                         '<Placemark><name>abcdef</name>'
                         '<description>ghijkl</description></Placemark>')

    def test_create_line_string(self):
        coord_list = [(2.0, 1.0), (4.0, 3.0), (6.0, 5.0)]
        element = self.kmlwriter._CreateLineString(self.parent, coord_list)
        self.assertEqual(_element_to_string(element),
                         '<LineString><tessellate>1</tessellate>'
                         '<coordinates>%f,%f %f,%f %f,%f</coordinates>'
                         '</LineString>' % (2.0, 1.0, 4.0, 3.0, 6.0, 5.0))

    def test_create_line_stringWithAltitude(self):
        coord_list = [(2.0, 1.0, 10), (4.0, 3.0, 20), (6.0, 5.0, 30.0)]
        element = self.kmlwriter._CreateLineString(self.parent, coord_list)
        self.assertEqual(_element_to_string(element),
                         '<LineString><tessellate>1</tessellate>'
                         '<altitudeMode>absolute</altitudeMode>'
                         '<coordinates>%f,%f,%f %f,%f,%f %f,%f,%f</coordinates>'
                         '</LineString>' %
                         (2.0, 1.0, 10.0, 4.0, 3.0, 20.0, 6.0, 5.0, 30.0))

    def test_create_line_stringForShape(self):
        shape = transitfeed.Shape('shape')
        shape.AddPoint(1.0, 1.0)
        shape.AddPoint(2.0, 4.0)
        shape.AddPoint(3.0, 9.0)
        element = self.kmlwriter._CreateLineStringForShape(self.parent, shape)
        self.assertEqual(_element_to_string(element),
                         '<LineString><tessellate>1</tessellate>'
                         '<coordinates>%f,%f %f,%f %f,%f</coordinates>'
                         '</LineString>' % (1.0, 1.0, 4.0, 2.0, 9.0, 3.0))


class TestRouteKML(util.TestCase):
    """Tests the routes folder KML generation methods of KMLWriter."""

    def set_up(self):
        self.feed = transitfeed.Loader(data_path('flatten_feed')).Load()
        self.kmlwriter = kmlwriter.KMLWriter()
        self.parent = ET.Element('parent')

    def test_create_route_patterns_folder_no_patterns(self):
        folder = self.kmlwriter._CreateRoutePatternsFolder(
            self.parent, self.feed.GetRoute('route_7'))
        self.assert_(folder is None)

    def test_create_route_patterns_folder_one_pattern(self):
        folder = self.kmlwriter._CreateRoutePatternsFolder(
            self.parent, self.feed.GetRoute('route_1'))
        placemarks = folder.findall('Placemark')
        self.assertEquals(len(placemarks), 1)

    def test_create_route_patterns_folder_two_patterns(self):
        folder = self.kmlwriter._CreateRoutePatternsFolder(
            self.parent, self.feed.GetRoute('route_3'))
        placemarks = folder.findall('Placemark')
        self.assertEquals(len(placemarks), 2)

    def test_create_route_pattern_folder_two_equal_patterns(self):
        folder = self.kmlwriter._CreateRoutePatternsFolder(
            self.parent, self.feed.GetRoute('route_4'))
        placemarks = folder.findall('Placemark')
        self.assertEquals(len(placemarks), 1)

    def test_create_route_shapes_folder_one_trip_one_shape(self):
        folder = self.kmlwriter._CreateRouteShapesFolder(
            self.feed, self.parent, self.feed.GetRoute('route_1'))
        self.assertEqual(len(folder.findall('Placemark')), 1)

    def test_create_route_shapes_folder_two_trips_two_shapes(self):
        folder = self.kmlwriter._CreateRouteShapesFolder(
            self.feed, self.parent, self.feed.GetRoute('route_2'))
        self.assertEqual(len(folder.findall('Placemark')), 2)

    def test_create_route_shapes_folder_two_trips_one_shape(self):
        folder = self.kmlwriter._CreateRouteShapesFolder(
            self.feed, self.parent, self.feed.GetRoute('route_3'))
        self.assertEqual(len(folder.findall('Placemark')), 1)

    def test_create_route_shapes_folder_two_trips_no_shapes(self):
        folder = self.kmlwriter._CreateRouteShapesFolder(
            self.feed, self.parent, self.feed.GetRoute('route_4'))
        self.assert_(folder is None)

    def assert_route_folder_contains_trips(self, tripids, folder):
        """Assert that the route folder contains exactly tripids"""
        actual_tripds = set()
        for placemark in folder.findall('Placemark'):
            actual_tripds.add(placemark.find('name').text)
        self.assertEquals(set(tripids), actual_tripds)

    def test_create_trips_folder_for_route_two_trips(self):
        route = self.feed.GetRoute('route_2')
        folder = self.kmlwriter._CreateRouteTripsFolder(self.parent, route)
        self.assert_route_folder_contains_trips(['route_2_1', 'route_2_2'], folder)

    def test_create_trips_folder_for_route_date_filter_none(self):
        self.kmlwriter.date_filter = None
        route = self.feed.GetRoute('route_8')
        folder = self.kmlwriter._CreateRouteTripsFolder(self.parent, route)
        self.assert_route_folder_contains_trips(['route_8_1', 'route_8_2'], folder)

    def test_create_trips_folder_for_route_date_filter_set(self):
        self.kmlwriter.date_filter = '20070604'
        route = self.feed.GetRoute('route_8')
        folder = self.kmlwriter._CreateRouteTripsFolder(self.parent, route)
        self.assert_route_folder_contains_trips(['route_8_2'], folder)

    def _get_trip_placemark(self, route_folder, trip_name):
        for trip_placemark in route_folder.findall('Placemark'):
            if trip_placemark.find('name').text == trip_name:
                return trip_placemark

    def test_create_route_trips_folder_altitude0(self):
        self.kmlwriter.altitude_per_sec = 0.0
        folder = self.kmlwriter._CreateRouteTripsFolder(
            self.parent, self.feed.GetRoute('route_4'))
        trip_placemark = self._get_trip_placemark(folder, 'route_4_1')
        self.assertEqual(_element_to_string(trip_placemark.find('LineString')),
                         '<LineString><tessellate>1</tessellate>'
                         '<coordinates>-117.133162,36.425288 '
                         '-116.784582,36.868446 '
                         '-116.817970,36.881080</coordinates></LineString>')

    def test_create_route_trips_folder_altitude1(self):
        self.kmlwriter.altitude_per_sec = 0.5
        folder = self.kmlwriter._CreateRouteTripsFolder(
            self.parent, self.feed.GetRoute('route_4'))
        trip_placemark = self._get_trip_placemark(folder, 'route_4_1')
        self.assertEqual(_element_to_string(trip_placemark.find('LineString')),
                         '<LineString><tessellate>1</tessellate>'
                         '<altitudeMode>absolute</altitudeMode>'
                         '<coordinates>-117.133162,36.425288,3600.000000 '
                         '-116.784582,36.868446,5400.000000 '
                         '-116.817970,36.881080,7200.000000</coordinates>'
                         '</LineString>')

    def test_create_route_trips_folder_no_trips(self):
        folder = self.kmlwriter._CreateRouteTripsFolder(
            self.parent, self.feed.GetRoute('route_7'))
        self.assert_(folder is None)

    def test_create_routes_folder_no_routes(self):
        schedule = transitfeed.Schedule()
        folder = self.kmlwriter._CreateRoutesFolder(schedule, self.parent)
        self.assert_(folder is None)

    def test_create_routes_folder_no_routesWithRouteType(self):
        folder = self.kmlwriter._CreateRoutesFolder(self.feed, self.parent, 999)
        self.assert_(folder is None)

    def _test_create_routes_folder(self, show_trips):
        self.kmlwriter.show_trips = show_trips
        folder = self.kmlwriter._CreateRoutesFolder(self.feed, self.parent)
        self.assertEquals(folder.tag, 'Folder')
        styles = self.parent.findall('Style')
        self.assertEquals(len(styles), len(self.feed.GetRouteList()))
        route_folders = folder.findall('Folder')
        self.assertEquals(len(route_folders), len(self.feed.GetRouteList()))

    def test_create_routes_folder(self):
        self._test_create_routes_folder(False)

    def test_create_routes_folderShowTrips(self):
        self._test_create_routes_folder(True)

    def test_create_routes_folderWithRouteType(self):
        folder = self.kmlwriter._CreateRoutesFolder(self.feed, self.parent, 1)
        route_folders = folder.findall('Folder')
        self.assertEquals(len(route_folders), 1)


class TestShapesKML(util.TestCase):
    """Tests the shapes folder KML generation methods of KMLWriter."""

    def set_up(self):
        self.flatten_feed = transitfeed.Loader(data_path('flatten_feed')).Load()
        self.good_feed = transitfeed.Loader(data_path('good_feed.zip')).Load()
        self.kmlwriter = kmlwriter.KMLWriter()
        self.parent = ET.Element('parent')

    def test_create_shapes_folder_no_shapes(self):
        folder = self.kmlwriter._CreateShapesFolder(self.good_feed, self.parent)
        self.assertEquals(folder, None)

    def test_create_shapes_folder(self):
        folder = self.kmlwriter._CreateShapesFolder(self.flatten_feed, self.parent)
        placemarks = folder.findall('Placemark')
        self.assertEquals(len(placemarks), 3)
        for placemark in placemarks:
            self.assert_(placemark.find('LineString') is not None)


class TestStopsKML(util.TestCase):
    """Tests the stops folder KML generation methods of KMLWriter."""

    def set_up(self):
        self.feed = transitfeed.Loader(data_path('flatten_feed')).Load()
        self.kmlwriter = kmlwriter.KMLWriter()
        self.parent = ET.Element('parent')

    def test_create_stops_folder_no_stops(self):
        schedule = transitfeed.Schedule()
        folder = self.kmlwriter._CreateStopsFolder(schedule, self.parent)
        self.assert_(folder is None)

    def test_create_stops_folder(self):
        folder = self.kmlwriter._CreateStopsFolder(self.feed, self.parent)
        placemarks = folder.findall('Placemark')
        self.assertEquals(len(placemarks), len(self.feed.GetStopList()))


class TestShapePointsKML(util.TestCase):
    """Tests the shape points folder KML generation methods of KMLWriter."""

    def set_up(self):
        self.flatten_feed = transitfeed.Loader(data_path('flatten_feed')).Load()
        self.kmlwriter = kmlwriter.KMLWriter()
        self.kmlwriter.shape_points = True
        self.parent = ET.Element('parent')

    def test_create_shape_points_folder(self):
        folder = self.kmlwriter._CreateShapesFolder(self.flatten_feed, self.parent)
        shape_point_folder = folder.find('Folder')
        self.assertEquals(shape_point_folder.find('name').text,
                          'shape_1 Shape Points')
        placemarks = shape_point_folder.findall('Placemark')
        self.assertEquals(len(placemarks), 4)
        for placemark in placemarks:
            self.assert_(placemark.find('Point') is not None)


class FullTests(util.TempDirTestCaseBase):
    def test_normal_run(self):
        (out, err) = self.CheckCallWithPath(
            [self.GetPath('kmlwriter.py'), self.GetTestdata_path('good_feed.zip'),
             'good_feed.kml'])
        self.assertFalse(os.path.exists('transitfeedcrash.txt'))
        self.assertTrue(os.path.exists('good_feed.kml'))

    def test_command_line_error(self):
        (out, err) = self.CheckCallWithPath(
            [self.GetPath('kmlwriter.py'), '--bad_flag'], expected_retcode=2)
        self.assertMatchesRegex(r'no such option.*--bad_flag', err)
        self.assertMatchesRegex(r'--showtrips', err)
        self.assertFalse(os.path.exists('transitfeedcrash.txt'))

    def test_crash_handler(self):
        (out, err) = self.CheckCallWithPath(
            [self.GetPath('kmlwriter.py'), 'IWantMyCrash', 'output.zip'],
            stdin_str="\n", expected_retcode=127)
        self.assertMatchesRegex(r'Yikes', out)
        crashout = open('transitfeedcrash.txt').read()
        self.assertMatchesRegex(r'For test_crash_handler', crashout)


if __name__ == '__main__':
    unittest.main()
