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

# Unit tests for the shapepoint module.
from __future__ import absolute_import

from tests import util
import transitfeed


class ShapeValidationTestCase(util.ValidationTestCase):
    def expect_failed_add(self, shape, lat, lon, dist, column_name, value):
        self.Expectinvalid_valueInClosure(
            column_name, value,
            lambda: shape.AddPoint(lat, lon, dist, self.problems))

    def run_test(self):
        shape = transitfeed.Shape('TEST')
        repr(shape)  # shouldn't crash
        self.ValidateAndExpectother_problem(shape)  # no points!

        self.expect_failed_add(shape, 36.905019, -116.763207, -1,
                               'shape_dist_traveled', -1)

        shape.AddPoint(36.915760, -116.751709, 0, self.problems)
        shape.AddPoint(36.905018, -116.763206, 5, self.problems)
        shape.Validate(self.problems)

        shape.shape_id = None
        self.ValidateAndExpectmissing_value(shape, 'shape_id')
        shape.shape_id = 'TEST'

        self.expect_failed_add(shape, 91, -116.751709, 6, 'shape_pt_lat', 91)
        self.expect_failed_add(shape, -91, -116.751709, 6, 'shape_pt_lat', -91)

        self.expect_failed_add(shape, 36.915760, -181, 6, 'shape_pt_lon', -181)
        self.expect_failed_add(shape, 36.915760, 181, 6, 'shape_pt_lon', 181)

        self.expect_failed_add(shape, 0.5, -0.5, 6, 'shape_pt_lat', 0.5)
        self.expect_failed_add(shape, 0, 0, 6, 'shape_pt_lat', 0)

        # distance decreasing is bad, but staying the same is OK
        shape.AddPoint(36.905019, -116.763206, 4, self.problems)
        e = self.accumulator.PopException('invalid_value')
        self.assertMatchesRegex('Each subsequent point', e.FormatProblem())
        self.assertMatchesRegex('distance was 5.000000.', e.FormatProblem())
        self.accumulator.AssertNoMoreExceptions()

        shape.AddPoint(36.925019, -116.764206, 6, self.problems)
        self.accumulator.AssertNoMoreExceptions()

        shapepoint = transitfeed.ShapePoint('TEST', 36.915760, -116.7156, 6, 8)
        shape.add_shape_point_object_unsorted(shapepoint, self.problems)
        shapepoint = transitfeed.ShapePoint('TEST', 36.915760, -116.7156, 5, 10)
        shape.add_shape_point_object_unsorted(shapepoint, self.problems)
        e = self.accumulator.PopException('invalid_value')
        self.assertMatchesRegex('Each subsequent point', e.FormatProblem())
        self.assertMatchesRegex('distance was 8.000000.', e.FormatProblem())
        self.accumulator.AssertNoMoreExceptions()

        shapepoint = transitfeed.ShapePoint('TEST', 36.915760, -116.7156, 6, 11)
        shape.add_shape_point_object_unsorted(shapepoint, self.problems)
        e = self.accumulator.PopException('invalid_value')
        self.assertMatchesRegex('The sequence number 6 occurs ', e.FormatProblem())
        self.assertMatchesRegex('once in shape TEST.', e.FormatProblem())
        self.accumulator.AssertNoMoreExceptions()


class ShapePointValidationTestCase(util.ValidationTestCase):
    def run_test(self):
        shapepoint = transitfeed.ShapePoint('', 36.915720, -116.7156, 0, 0)
        self.Expectmissing_valueInClosure('shape_id',
                                         lambda: shapepoint.parse_attributes(self.problems))

        shapepoint = transitfeed.ShapePoint('T', '36.9151', '-116.7611', '00', '0')
        shapepoint.parse_attributes(self.problems)
        e = self.accumulator.PopException('InvalidNonNegativeIntegerValue')
        self.assertMatchesRegex('not have a leading zero', e.FormatProblem())
        self.accumulator.AssertNoMoreExceptions()

        shapepoint = transitfeed.ShapePoint('T', '36.9151', '-116.7611', -1, '0')
        shapepoint.parse_attributes(self.problems)
        e = self.accumulator.PopException('invalid_value')
        self.assertMatchesRegex('Value should be a number', e.FormatProblem())
        self.accumulator.AssertNoMoreExceptions()

        shapepoint = transitfeed.ShapePoint('T', '0.1', '0.1', '1', '0')
        shapepoint.parse_attributes(self.problems)
        e = self.accumulator.PopException('invalid_value')
        self.assertMatchesRegex('too close to 0, 0,', e.FormatProblem())
        self.accumulator.AssertNoMoreExceptions()

        shapepoint = transitfeed.ShapePoint('T', '36.9151', '-116.7611', '0', '')
        shapepoint.parse_attributes(self.problems)
        shapepoint = transitfeed.ShapePoint('T', '36.9151', '-116.7611', '0', '-1')
        shapepoint.parse_attributes(self.problems)
        e = self.accumulator.PopException('invalid_value')
        self.assertMatchesRegex('Invalid value -1.0', e.FormatProblem())
        self.assertMatchesRegex('should be a positive number', e.FormatProblem())
        self.accumulator.AssertNoMoreExceptions()
