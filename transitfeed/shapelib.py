#!/usr/bin/python2.4
#
# Copyright 2007 Google Inc. All Rights Reserved.
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

"""A library for manipulating points and polylines.

This is a library for creating and manipulating points on the unit
sphere, as an approximate model of Earth.  The primary use of this
library is to make manipulation and matching of polylines easy in the
transitfeed library.

NOTE: in this library, Earth is modelled as a sphere, whereas
GTFS specifies that latitudes and longitudes are in WGS84.  For the
purpose of comparing and matching latitudes and longitudes that
are relatively close together on the surface of the earth, this
is adequate; for other purposes, this library may not be accurate
enough.
"""
from __future__ import print_function

__author__ = 'chris.harrelson.code@gmail.com (Chris Harrelson)'

import heapq
import math


class ShapeError(Exception):
    """Thrown whenever there is a shape parsing error."""
    pass


EARTH_RADIUS_METERS = 6371010.0


class Point(object):
    """
    A class representing a point on the unit sphere in three dimensions.
    """

    def __init__(self, x, y, z):
        self.x = x
        self.y = y
        self.z = z

    def __hash__(self):
        return hash((self.x, self.y, self.z))

    def __cmp__(self, other):
        if not isinstance(other, Point):
            raise TypeError('Point.__cmp__(x,y) requires y to be a "Point", '
                            'not a "%s"' % type(other).__name__)
        return(self.x, self.y, self.z), (other.x, other.y, other.z)

    def __str__(self):
        return "(%.15f, %.15f, %.15f) " % (self.x, self.y, self.z)

    def norm2(self):
        """
        Returns the L_2 (Euclidean) norm of self.
        """
        sum = self.x * self.x + self.y * self.y + self.z * self.z
        return math.sqrt(float(sum))

    def is_unit_length(self):
        return abs(self.norm2() - 1.0) < 1e-14

    def plus(self, other):
        """
        Returns a new point which is the pointwise sum of self and other.
        """
        return Point(self.x + other.x,
                     self.y + other.y,
                     self.z + other.z)

    def minus(self, other):
        """
        Returns a new point which is the pointwise subtraction of other from
        self.
        """
        return Point(self.x - other.x,
                     self.y - other.y,
                     self.z - other.z)

    def dot_prod(self, other):
        """
        Returns the (scalar) dot product of self with other.
        """
        return self.x * other.x + self.y * other.y + self.z * other.z

    def times(self, val):
        """
        Returns a new point which is pointwise multiplied by val.
        """
        return Point(self.x * val, self.y * val, self.z * val)

    def normalize(self):
        """
        Returns a unit point in the same direction as self.
        """
        return self.times(1 / self.norm2())

    def robust_cross_prod(self, other):
        """
        A robust version of cross product.  If self and other
        are not nearly the same point, returns the same value
        as cross_prod() modulo normalization.  Otherwise returns
        an arbitrary unit point orthogonal to self.
        """
        assert (self.is_unit_length() and other.is_unit_length())
        x = self.plus(other).cross_prod(other.minus(self))
        if abs(x.x) > 1e-15 or abs(x.y) > 1e-15 or abs(x.z) > 1e-15:
            return x.normalize()
        else:
            return self.ortho()

    def largest_component(self):
        """
        Returns (i, val) where i is the component index (0 - 2)
        which has largest absolute value and val is the value
        of the component.
        """
        if abs(self.x) > abs(self.y):
            if abs(self.x) > abs(self.z):
                return (0, self.x)
            else:
                return (2, self.z)
        else:
            if abs(self.y) > abs(self.z):
                return (1, self.y)
            else:
                return (2, self.z)

    def ortho(self):
        """Returns a unit-length point orthogonal to this point"""
        (index, val) = self.largest_component()
        index = index - 1
        if index < 0:
            index = 2
        temp = Point(0.012, 0.053, 0.00457)
        if index == 0:
            temp.x = 1
        elif index == 1:
            temp.y = 1
        elif index == 2:
            temp.z = 1
        return self.cross_prod(temp).normalize()

    def cross_prod(self, other):
        """
        Returns the cross product of self and other.
        """
        return Point(
            self.y * other.z - self.z * other.y,
            self.z * other.x - self.x * other.z,
            self.x * other.y - self.y * other.x)

    @staticmethod
    def _approx_eq(a, b):
        return abs(a - b) < 1e-11

    def equals(self, other):
        """
        Returns true of self and other are approximately equal.
        """
        return (self._approx_eq(self.x, other.x)
                and self._approx_eq(self.y, other.y)
                and self._approx_eq(self.z, other.z))

    def angle(self, other):
        """
        Returns the angle in radians between self and other.
        """
        return math.atan2(self.cross_prod(other).norm2(),
                          self.dot_prod(other))

    def to_lat_lng(self):
        """
        Returns that latitude and longitude that this point represents
        under a spherical Earth model.
        """
        rad_lat = math.atan2(self.z, math.sqrt(self.x * self.x + self.y * self.y))
        rad_lng = math.atan2(self.y, self.x)
        return (rad_lat * 180.0 / math.pi, rad_lng * 180.0 / math.pi)

    @staticmethod
    def from_lat_lng(lat, lng):
        """
        Returns a new point representing this latitude and longitude under
        a spherical Earth model.
        """
        phi = lat * (math.pi / 180.0)
        theta = lng * (math.pi / 180.0)
        cosphi = math.cos(phi)
        return Point(math.cos(theta) * cosphi,
                     math.sin(theta) * cosphi,
                     math.sin(phi))

    def get_distance_meters(self, other):
        assert (self.is_unit_length() and other.is_unit_length())
        return self.angle(other) * EARTH_RADIUS_METERS


def simple_c_c_w(a, b, c):
    """
    Returns true if the triangle abc is oriented counterclockwise.
    """
    return c.cross_prod(a).dot_prod(b) > 0


def get_closest_point(x, a, b):
    """
    Returns the point on the great circle segment ab closest to x.
    """
    assert (x.is_unit_length())
    assert (a.is_unit_length())
    assert (b.is_unit_length())

    a_cross_b = a.robust_cross_prod(b)
    # project to the great circle going through a and b
    p = x.minus(
        a_cross_b.times(
            x.dot_prod(a_cross_b) / a_cross_b.norm2()))

    # if p lies between a and b, return it
    if simple_c_c_w(a_cross_b, a, p) and simple_c_c_w(p, b, a_cross_b):
        return p.normalize()

    # otherwise return the closer of a or b
    if x.minus(a).norm2() <= x.minus(b).norm2():
        return a
    else:
        return b


class Poly(object):
    """
    A class representing a polyline.
    """

    def __init__(self, points=[], name=None):
        self._points = list(points)
        self._name = name

    def add_point(self, p):
        """
        Adds a new point to the end of the polyline.
        """
        assert (p.is_unit_length())
        self._points.append(p)

    def get_name(self):
        return self._name

    def get_point(self, i):
        return self._points[i]

    def get_points(self):
        return self._points

    def get_num_points(self):
        return len(self._points)

    def _get_point_safe(self, i):
        try:
            return self.get_point(i)
        except IndexError:
            return None

    def get_closest_point(self, p):
        """
        Returns (closest_p, closest_i), where closest_p is the closest point
        to p on the piecewise linear curve represented by the polyline,
        and closest_i is the index of the point on the polyline just before
        the polyline segment that contains closest_p.
        """
        assert (len(self._points) > 0)
        closest_point = self._points[0]
        closest_i = 0

        for i in range(0, len(self._points) - 1):
            (a, b) = (self._points[i], self._points[i + 1])
            cur_closest_point = get_closest_point(p, a, b)
            if p.angle(cur_closest_point) < p.angle(closest_point):
                closest_point = cur_closest_point.normalize()
                closest_i = i

        return (closest_point, closest_i)

    def length_meters(self):
        """Return length of this polyline in meters."""
        assert (len(self._points) > 0)
        length = 0
        for i in range(0, len(self._points) - 1):
            length += self._points[i].get_distance_meters(self._points[i + 1])
        return length

    def reversed(self):
        """Return a polyline that is the reverse of this polyline."""
        return Poly(reversed(self.get_points()), self.get_name())

    def cut_at_closest_point(self, p):
        """
        Let x be the point on the polyline closest to p.  Then
        cut_at_closest_point returns two new polylines, one representing
        the polyline from the beginning up to x, and one representing
        x onwards to the end of the polyline.  x is the first point
        returned in the second polyline.
        """
        (closest, i) = self.get_closest_point(p)

        tmp = [closest]
        tmp.extend(self._points[i + 1:])
        return (Poly(self._points[0:i + 1]),
                Poly(tmp))

    def greedy_poly_match_dist(self, shape):
        """
        Tries a greedy matching algorithm to match self to the
        given shape.  Returns the maximum distance in meters of
        any point in self to its matched point in shape under the
        algorithm.

        Args: shape, a Poly object.
        """
        tmp_shape = Poly(shape.get_points())
        max_radius = 0
        for (i, point) in enumerate(self._points):
            tmp_shape = tmp_shape.cut_at_closest_point(point)[1]
            dist = tmp_shape.get_point(0).get_distance_meters(point)
            max_radius = max(max_radius, dist)
        return max_radius

    @staticmethod
    def merge_polys(polys, merge_point_threshold=10):
        """
        Merge multiple polylines, in the order that they were passed in.
        Merged polyline will have the names of their component parts joined by ';'.
        Example: merging [a,b], [c,d] and [e,f] will result in [a,b,c,d,e,f].
        However if the endpoints of two adjacent polylines are less than
        merge_point_threshold meters apart, we will only use the first endpoint in
        the merged polyline.
        """
        name = ";".join((p.get_name(), '')[p.get_name() is None] for p in polys)
        merged = Poly([], name)
        if polys:
            first_poly = polys[0]
            for p in first_poly.get_points():
                merged.add_point(p)
            last_point = merged._get_point_safe(-1)
            for poly in polys[1:]:
                first_point = poly._get_point_safe(0)
                if (last_point and first_point and
                        last_point.get_distance_meters(first_point) <= merge_point_threshold):
                    points = poly.get_points()[1:]
                else:
                    points = poly.get_points()
                for p in points:
                    merged.add_point(p)
                last_point = merged._get_point_safe(-1)
        return merged

    def __str__(self):
        return self._to_string(str)

    def to_lat_lng_string(self):
        return self._to_string(lambda p: str(p.to_lat_lng()))

    def _to_string(self, pointto_stringFn):
        return "%s: %s" % (self.get_name() or "",
                           ", ".join([pointto_stringFn(p) for p in self._points]))


class PolyCollection(object):
    """
    A class representing a collection of polylines.
    """

    def __init__(self):
        self._name_to_shape = {}
        pass

    def add_poly(self, poly, smart_duplicate_handling=True):
        """
        Adds a new polyline to the collection.
        """
        inserted_name = poly.get_name()
        if poly.get_name() in self._name_to_shape:
            if not smart_duplicate_handling:
                raise ShapeError("Duplicate shape found: " + poly.get_name())

            print("Warning: duplicate shape id being added to collection: " +
                  poly.get_name())
            if poly.greedy_poly_match_dist(self._name_to_shape[poly.get_name()]) < 10:
                print("  (Skipping as it apears to be an exact duplicate)")
            else:
                print("  (Adding new shape variant with uniquified name)")
                inserted_name = "%s-%d" % (inserted_name, len(self._name_to_shape))
        self._name_to_shape[inserted_name] = poly

    def num_polys(self):
        return len(self._name_to_shape)

    def find_matching_polys(self, start_point, end_point, max_radius=150):
        """
        Returns a list of polylines in the collection that have endpoints
        within max_radius of the given start and end points.
        """
        matches = []
        for shape in self._name_to_shape.itervalues():
            if start_point.get_distance_meters(shape.get_point(0)) < max_radius and \
                    end_point.get_distance_meters(shape.get_point(-1)) < max_radius:
                matches.append(shape)
        return matches


class PolyGraph(PolyCollection):
    """
    A class representing a graph where the edges are polylines.
    """

    def __init__(self):
        PolyCollection.__init__(self)
        self._nodes = {}

    def add_poly(self, poly, smart_duplicate_handling=True):
        PolyCollection.add_poly(self, poly, smart_duplicate_handling)
        start_point = poly.get_point(0)
        end_point = poly.get_point(-1)
        self._add_node_with_edge(start_point, poly)
        self._add_node_with_edge(end_point, poly)

    def _add_node_with_edge(self, point, edge):
        if point in self._nodes:
            self._nodes[point].add(edge)
        else:
            self._nodes[point] = set([edge])

    def shortest_path(self, start, goal):
        """Uses the A* algorithm to find a shortest path between start and goal.

        For more background see http://en.wikipedia.org/wiki/A-star_algorithm

        Some definitions:
        g(x): The actual shortest distance traveled from initial node to current
              node.
        h(x): The estimated (or "heuristic") distance from current node to goal.
              We use the distance on Earth from node to goal as the heuristic.
              This heuristic is both admissible and monotonic (see wikipedia for
              more details).
        f(x): The sum of g(x) and h(x), used to prioritize elements to look at.

        Arguments:
          start: Point that is in the graph, start point of the search.
          goal: Point that is in the graph, end point for the search.

        Returns:
          A Poly object representing the shortest polyline through the graph from
          start to goal, or None if no path found.
        """

        assert start in self._nodes
        assert goal in self._nodes
        closed_set = set()  # Set of nodes already evaluated.
        open_heap = [(0, start)]  # Nodes to visit, heapified by f(x).
        open_set = set([start])  # Same as open_heap, but a set instead of a heap.
        g_scores = {start: 0}  # Distance from start along optimal path
        came_from = {}  # Map to reconstruct optimal path once we're done.
        while open_set:
            (f_x, x) = heapq.heappop(open_heap)
            open_set.remove(x)
            if x == goal:
                return self._reconstruct_path(came_from, goal)
            closed_set.add(x)
            edges = self._nodes[x]
            for edge in edges:
                if edge.get_point(0) == x:
                    y = edge.get_point(-1)
                else:
                    y = edge.get_point(0)
                if y in closed_set:
                    continue
                tentative_g_score = g_scores[x] + edge.length_meters()
                tentative_is_better = False
                if y not in open_set:
                    h_y = y.get_distance_meters(goal)
                    f_y = tentative_g_score + h_y
                    open_set.add(y)
                    heapq.heappush(open_heap, (f_y, y))
                    tentative_is_better = True
                elif tentative_g_score < g_scores[y]:
                    tentative_is_better = True
                if tentative_is_better:
                    came_from[y] = (x, edge)
                    g_scores[y] = tentative_g_score
        return None

    def _reconstruct_path(self, came_from, current_node):
        """
        Helper method for shortest_path, to reconstruct path.

        Arguments:
          came_from: a dictionary mapping Point to (Point, Poly) tuples.
              This dictionary keeps track of the previous neighbor to a node, and
              the edge used to get from the previous neighbor to the node.
          current_node: the current Point in the path.

        Returns:
          A Poly that represents the path through the graph from the start of the
          search to current_node.
        """
        if current_node in came_from:
            (previous_node, previous_edge) = came_from[current_node]
            if previous_edge.get_point(0) == current_node:
                previous_edge = previous_edge.reversed()
            p = self._reconstruct_path(came_from, previous_node)
            return Poly.merge_polys([p, previous_edge], merge_point_threshold=0)
        else:
            return Poly([], '')

    def find_shortest_multi_point_path(self, points, max_radius=150, keep_best_n=10,
                                       verbosity=0):
        """
        Return a polyline, representing the shortest path through this graph that
        has edge endpoints on each of a given list of points in sequence.  We allow
        fuzziness in matching of input points to points in this graph.

        We limit ourselves to a view of the best keep_best_n paths at any time, as a
        greedy optimization.
        """
        assert len(points) > 1
        nearby_points = []
        paths_found = []  # A heap sorted by inverse path length.

        for i, point in enumerate(points):
            nearby = [p for p in self._nodes.iterkeys()
                      if p.get_distance_meters(point) < max_radius]
            if verbosity >= 2:
                print("Nearby points for point %d %s: %s"
                      % (i + 1,
                         str(point.to_lat_lng()),
                         ", ".join([str(n.to_lat_lng()) for n in nearby])))
            if nearby:
                nearby_points.append(nearby)
            else:
                print("No nearby points found for point %s" % str(point.to_lat_lng()))
                return None

        pathToStr = lambda start, end, path: ("  Best path %s -> %s: %s"
                                              % (str(start.to_lat_lng()),
                                                 str(end.to_lat_lng()),
                                                 path and path.get_name() or
                                                 "None"))
        if verbosity >= 3:
            print("Step 1")
        step = 2

        start_points = nearby_points[0]
        end_points = nearby_points[1]

        for start in start_points:
            for end in end_points:
                path = self.shortest_path(start, end)
                if verbosity >= 3:
                    print(pathToStr(start, end, path))
                PolyGraph._add_path_to_heap(paths_found, path, keep_best_n)

        for possible_points in nearby_points[2:]:
            if verbosity >= 3:
                print("\nStep %d" % step)
                step += 1
            new_paths_found = []

            start_end_paths = {}  # cache of shortest paths between (start, end) pairs
            for score, path in paths_found:
                start = path.get_point(-1)
                for end in possible_points:
                    if (start, end) in start_end_paths:
                        new_segment = start_end_paths[(start, end)]
                    else:
                        new_segment = self.shortest_path(start, end)
                        if verbosity >= 3:
                            print(pathToStr(start, end, new_segment))
                        start_end_paths[(start, end)] = new_segment

                    if new_segment:
                        new_path = Poly.merge_polys([path, new_segment],
                                                    merge_point_threshold=0)
                        PolyGraph._add_path_to_heap(new_paths_found, new_path, keep_best_n)
            paths_found = new_paths_found

        if paths_found:
            best_score, best_path = max(paths_found)
            return best_path
        else:
            return None

    @staticmethod
    def _add_path_to_heap(heap, path, keep_best_n):
        if path and path.get_num_points():
            new_item = (-path.length_meters(), path)
            if new_item not in heap:
                if len(heap) < keep_best_n:
                    heapq.heappush(heap, new_item)
                else:
                    heapq.heapreplace(heap, new_item)
