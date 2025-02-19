#!/usr/bin/python2.4
#
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

"""Tests for transitfeed.shapelib.py"""
from __future__ import absolute_import
from __future__ import print_function

__author__ = 'chris.harrelson.code@gmail.com (Chris Harrelson)'

import math
from transitfeed import shapelib
from transitfeed.shapelib import Point
from transitfeed.shapelib import Poly
from transitfeed.shapelib import PolyCollection
from transitfeed.shapelib import PolyGraph
import unittest
from tests import util


def format_point(p, precision=12):
    formatString = "(%%.%df, %%.%df, %%.%df)" % (precision, precision, precision)
    return formatString % (p.x, p.y, p.z)


def format_points(points):
    return "[%s]" % ", ".join([format_point(p, precision=4) for p in points])


class ShapeLibTestBase(util.TestCase):
    def assert_approx_eq(self, a, b):
        self.assertAlmostEqual(a, b, 8)

    def assert_point_approx_eq(self, a, b):
        try:
            self.assert_approx_eq(a.x, b.x)
            self.assert_approx_eq(a.y, b.y)
            self.assert_approx_eq(a.z, b.z)
        except AssertionError:
            print('ERROR: %s != %s' % (format_point(a), format_point(b)))
            raise

    def assert_points_approx_eq(self, points1, points2):
        try:
            self.assertEqual(len(points1), len(points2))
        except AssertionError:
            print("ERROR: %s != %s" % (format_points(points1), format_points(points2)))
            raise
        for i in xrange(len(points1)):
            try:
                self.assert_point_approx_eq(points1[i], points2[i])
            except AssertionError:
                print('ERROR: points not equal in position %d\n%s != %s'
                      % (i, format_points(points1), format_points(points2)))
                raise


class TestPoints(ShapeLibTestBase):
    def test_points(self):
        p = Point(1, 1, 1)

        self.assert_approx_eq(p.DotProd(p), 3)

        self.assert_approx_eq(p.Norm2(), math.sqrt(3))

        self.assert_point_approx_eq(Point(1.5, 1.5, 1.5),
                                    p.Times(1.5))

        norm = 1.7320508075688772
        self.assert_point_approx_eq(p.Normalize(),
                                    Point(1 / norm,
                                          1 / norm,
                                          1 / norm))

        p2 = Point(1, 0, 0)
        self.assert_point_approx_eq(p2, p2.Normalize())

    def test_cross_prod(self):
        p1 = Point(1, 0, 0).Normalize()
        p2 = Point(0, 1, 0).Normalize()
        p1_cross_p2 = p1.CrossProd(p2)
        self.assert_approx_eq(p1_cross_p2.x, 0)
        self.assert_approx_eq(p1_cross_p2.y, 0)
        self.assert_approx_eq(p1_cross_p2.z, 1)

    def test_robust_cross_prod(self):
        p1 = Point(1, 0, 0)
        p2 = Point(1, 0, 0)
        self.assert_point_approx_eq(Point(0, 0, 0),
                                    p1.CrossProd(p2))
        # only needs to be an arbitrary vector perpendicular to (1, 0, 0)
        self.assert_point_approx_eq(
            Point(0.000000000000000, -0.998598452020993, 0.052925717957113),
            p1.RobustCrossProd(p2))

    def test_s2_lat_long(self):
        point = Point.FromLatLng(30, 40)
        self.assert_point_approx_eq(Point(0.663413948169,
                                          0.556670399226,
                                          0.5), point)
        (lat, lng) = point.ToLatLng()
        self.assert_approx_eq(30, lat)
        self.assert_approx_eq(40, lng)

    def test_ortho(self):
        point = Point(1, 1, 1)
        ortho = point.Ortho()
        self.assert_approx_eq(ortho.DotProd(point), 0)

    def test_angle(self):
        point1 = Point(1, 1, 0).Normalize()
        point2 = Point(0, 1, 0)
        self.assert_approx_eq(45, point1.Angle(point2) * 360 / (2 * math.pi))
        self.assert_approx_eq(point1.Angle(point2), point2.Angle(point1))

    def test_get_distance_meters(self):
        point1 = Point.FromLatLng(40.536895, -74.203033)
        point2 = Point.FromLatLng(40.575239, -74.112825)
        self.assert_approx_eq(8732.623770873237,
                              point1.GetDistanceMeters(point2))


class TestClosestPoint(ShapeLibTestBase):
    def test_get_closest_point(self):
        x = Point(1, 1, 0).Normalize()
        a = Point(1, 0, 0)
        b = Point(0, 1, 0)

        closest = shapelib.GetClosestPoint(x, a, b)
        self.assert_approx_eq(0.707106781187, closest.x)
        self.assert_approx_eq(0.707106781187, closest.y)
        self.assert_approx_eq(0.0, closest.z)


class TestPoly(ShapeLibTestBase):
    def test_get_closest_pointShape(self):
        poly = Poly()

        poly.add_point(Point(1, 1, 0).Normalize())
        self.assert_point_approx_eq(Point(
            0.707106781187, 0.707106781187, 0), poly.GetPoint(0))

        point = Point(0, 1, 1).Normalize()
        self.assert_point_approx_eq(Point(1, 1, 0).Normalize(),
                                    poly.GetClosestPoint(point)[0])

        poly.add_point(Point(0, 1, 1).Normalize())

        self.assert_point_approx_eq(
            Point(0, 1, 1).Normalize(),
            poly.GetClosestPoint(point)[0])

    def test_cut_at_closest_point(self):
        poly = Poly()
        poly.add_point(Point(0, 1, 0).Normalize())
        poly.add_point(Point(0, 0.5, 0.5).Normalize())
        poly.add_point(Point(0, 0, 1).Normalize())

        (before, after) = \
            poly.CutAtClosestPoint(Point(0, 0.3, 0.7).Normalize())

        self.assert_(2 == before.GetNumPoints())
        self.assert_(2 == before.GetNumPoints())
        self.assert_point_approx_eq(
            Point(0, 0.707106781187, 0.707106781187), before.GetPoint(1))

        self.assert_point_approx_eq(
            Point(0, 0.393919298579, 0.919145030018), after.GetPoint(0))

        poly = Poly()
        poly.add_point(Point.FromLatLng(40.527035999999995, -74.191265999999999))
        poly.add_point(Point.FromLatLng(40.526859999999999, -74.191140000000004))
        poly.add_point(Point.FromLatLng(40.524681000000001, -74.189579999999992))
        poly.add_point(Point.FromLatLng(40.523128999999997, -74.188467000000003))
        poly.add_point(Point.FromLatLng(40.523054999999999, -74.188676000000001))
        pattern = Poly()
        pattern.add_point(Point.FromLatLng(40.52713,
                                          -74.191146000000003))
        self.assert_approx_eq(14.564268281551, pattern.GreedyPolyMatchDist(poly))

    def test_merge_polys(self):
        poly1 = Poly(name="Foo")
        poly1.add_point(Point(0, 1, 0).Normalize())
        poly1.add_point(Point(0, 0.5, 0.5).Normalize())
        poly1.add_point(Point(0, 0, 1).Normalize())
        poly1.add_point(Point(1, 1, 1).Normalize())

        poly2 = Poly()
        poly3 = Poly(name="Bar")
        poly3.add_point(Point(1, 1, 1).Normalize())
        poly3.add_point(Point(2, 0.5, 0.5).Normalize())

        merged1 = Poly.MergePolys([poly1, poly2])
        self.assert_points_approx_eq(poly1.GetPoints(), merged1.GetPoints())
        self.assertEqual("Foo;", merged1.GetName())

        merged2 = Poly.MergePolys([poly2, poly3])
        self.assert_points_approx_eq(poly3.GetPoints(), merged2.GetPoints())
        self.assertEqual(";Bar", merged2.GetName())

        merged3 = Poly.MergePolys([poly1, poly2, poly3], merge_point_threshold=0)
        mergedPoints = poly1.GetPoints()[:]
        mergedPoints.append(poly3.GetPoint(-1))
        self.assert_points_approx_eq(mergedPoints, merged3.GetPoints())
        self.assertEqual("Foo;;Bar", merged3.GetName())

        merged4 = Poly.MergePolys([poly2])
        self.assertEqual("", merged4.GetName())
        self.assertEqual(0, merged4.GetNumPoints())

        # test merging two nearby points
        newPoint = poly1.GetPoint(-1).Plus(Point(0.000001, 0, 0)).Normalize()
        poly1.add_point(newPoint)
        distance = poly1.GetPoint(-1).GetDistanceMeters(poly3.GetPoint(0))
        self.assertTrue(distance <= 10)
        self.assertTrue(distance > 5)

        merged5 = Poly.MergePolys([poly1, poly2, poly3], merge_point_threshold=10)
        mergedPoints = poly1.GetPoints()[:]
        mergedPoints.append(poly3.GetPoint(-1))
        self.assert_points_approx_eq(mergedPoints, merged5.GetPoints())
        self.assertEqual("Foo;;Bar", merged5.GetName())

        merged6 = Poly.MergePolys([poly1, poly2, poly3], merge_point_threshold=5)
        mergedPoints = poly1.GetPoints()[:]
        mergedPoints += poly3.GetPoints()
        self.assert_points_approx_eq(mergedPoints, merged6.GetPoints())
        self.assertEqual("Foo;;Bar", merged6.GetName())

    def test_reversed(self):
        p1 = Point(1, 0, 0).Normalize()
        p2 = Point(0, 0.5, 0.5).Normalize()
        p3 = Point(0.3, 0.8, 0.5).Normalize()
        poly1 = Poly([p1, p2, p3])
        self.assert_points_approx_eq([p3, p2, p1], poly1.Reversed().GetPoints())

    def test_length_meters(self):
        p1 = Point(1, 0, 0).Normalize()
        p2 = Point(0, 0.5, 0.5).Normalize()
        p3 = Point(0.3, 0.8, 0.5).Normalize()
        poly0 = Poly([p1])
        poly1 = Poly([p1, p2])
        poly2 = Poly([p1, p2, p3])
        try:
            poly0.LengthMeters()
            self.fail("Should have thrown AssertionError")
        except AssertionError:
            pass

        p1_p2 = p1.GetDistanceMeters(p2)
        p2_p3 = p2.GetDistanceMeters(p3)
        self.assertEqual(p1_p2, poly1.LengthMeters())
        self.assertEqual(p1_p2 + p2_p3, poly2.LengthMeters())
        self.assertEqual(p1_p2 + p2_p3, poly2.Reversed().LengthMeters())


class TestCollection(ShapeLibTestBase):
    def test_poly_match(self):
        poly = Poly()
        poly.add_point(Point(0, 1, 0).Normalize())
        poly.add_point(Point(0, 0.5, 0.5).Normalize())
        poly.add_point(Point(0, 0, 1).Normalize())

        collection = PolyCollection()
        collection.AddPoly(poly)
        match = collection.FindMatchingPolys(Point(0, 1, 0),
                                             Point(0, 0, 1))
        self.assert_(len(match) == 1 and match[0] == poly)

        match = collection.FindMatchingPolys(Point(0, 1, 0),
                                             Point(0, 1, 0))
        self.assert_(len(match) == 0)

        poly = Poly()
        poly.add_point(Point.FromLatLng(45.585212, -122.586136))
        poly.add_point(Point.FromLatLng(45.586654, -122.587595))
        collection = PolyCollection()
        collection.AddPoly(poly)

        match = collection.FindMatchingPolys(
            Point.FromLatLng(45.585212, -122.586136),
            Point.FromLatLng(45.586654, -122.587595))
        self.assert_(len(match) == 1 and match[0] == poly)

        match = collection.FindMatchingPolys(
            Point.FromLatLng(45.585219, -122.586136),
            Point.FromLatLng(45.586654, -122.587595))
        self.assert_(len(match) == 1 and match[0] == poly)

        self.assert_approx_eq(0.0, poly.GreedyPolyMatchDist(poly))

        match = collection.FindMatchingPolys(
            Point.FromLatLng(45.587212, -122.586136),
            Point.FromLatLng(45.586654, -122.587595))
        self.assert_(len(match) == 0)


class TestGraph(ShapeLibTestBase):
    def test_reconstruct_path(self):
        p1 = Point(1, 0, 0).Normalize()
        p2 = Point(0, 0.5, 0.5).Normalize()
        p3 = Point(0.3, 0.8, 0.5).Normalize()
        poly1 = Poly([p1, p2])
        poly2 = Poly([p3, p2])
        came_from = {
            p2: (p1, poly1),
            p3: (p2, poly2)
        }

        graph = PolyGraph()
        reconstructed1 = graph._ReconstructPath(came_from, p1)
        self.assertEqual(0, reconstructed1.GetNumPoints())

        reconstructed2 = graph._ReconstructPath(came_from, p2)
        self.assert_points_approx_eq([p1, p2], reconstructed2.GetPoints())

        reconstructed3 = graph._ReconstructPath(came_from, p3)
        self.assert_points_approx_eq([p1, p2, p3], reconstructed3.GetPoints())

    def test_shortest_path(self):
        p1 = Point(1, 0, 0).Normalize()
        p2 = Point(0, 0.5, 0.5).Normalize()
        p3 = Point(0.3, 0.8, 0.5).Normalize()
        p4 = Point(0.7, 0.7, 0.5).Normalize()
        poly1 = Poly([p1, p2, p3], "poly1")
        poly2 = Poly([p4, p3], "poly2")
        poly3 = Poly([p4, p1], "poly3")
        graph = PolyGraph()
        graph.AddPoly(poly1)
        graph.AddPoly(poly2)
        graph.AddPoly(poly3)
        path = graph.ShortestPath(p1, p4)
        self.assert_(path is not None)
        self.assert_points_approx_eq([p1, p4], path.GetPoints())

        path = graph.ShortestPath(p1, p3)
        self.assert_(path is not None)
        self.assert_points_approx_eq([p1, p4, p3], path.GetPoints())

        path = graph.ShortestPath(p3, p1)
        self.assert_(path is not None)
        self.assert_points_approx_eq([p3, p4, p1], path.GetPoints())

    def test_find_shortest_multi_point_path(self):
        p1 = Point(1, 0, 0).Normalize()
        p2 = Point(0.5, 0.5, 0).Normalize()
        p3 = Point(0.5, 0.5, 0.1).Normalize()
        p4 = Point(0, 1, 0).Normalize()
        poly1 = Poly([p1, p2, p3], "poly1")
        poly2 = Poly([p4, p3], "poly2")
        poly3 = Poly([p4, p1], "poly3")
        graph = PolyGraph()
        graph.AddPoly(poly1)
        graph.AddPoly(poly2)
        graph.AddPoly(poly3)
        path = graph.FindShortestMultiPointPath([p1, p3, p4])
        self.assert_(path is not None)
        self.assert_points_approx_eq([p1, p2, p3, p4], path.GetPoints())


if __name__ == '__main__':
    unittest.main()
