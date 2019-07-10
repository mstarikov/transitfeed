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

from __future__ import absolute_import
from .gtfsobjectbase import GtfsObjectBase
from .problems import default_problem_reporter
from . import util


class FareAttribute(GtfsObjectBase):
    """Represents a fare type."""
    _REQUIRED_FIELD_NAMES = ['fare_id', 'price', 'currency_type',
                             'payment_method', 'transfers']
    _FIELD_NAMES = _REQUIRED_FIELD_NAMES + ['transfer_duration']
    _TABLE_NAME = "fare_attributes"

    def __init__(self,
                 fare_id=None, price=None, currency_type=None,
                 payment_method=None, transfers=None, transfer_duration=None,
                 field_dict=None):
        self._schedule = None
        (self.fare_id, self.price, self.currency_type, self.payment_method,
         self.transfers, self.transfer_duration) = \
            (fare_id, price, currency_type, payment_method,
             transfers, transfer_duration)

        if field_dict:
            if isinstance(field_dict, FareAttribute):
                # Special case so that we don't need to re-parse the attributes to
                # native types iteritems returns all attributes that don't start with _
                for k, v in field_dict.iteritems():
                    self.__dict__[k] = v
            else:
                self.__dict__.update(field_dict)
        self.rules = []

        try:
            self.price = float(self.price)
        except (TypeError, ValueError):
            pass
        try:
            self.payment_method = int(self.payment_method)
        except (TypeError, ValueError):
            pass
        if self.transfers == None or self.transfers == "":
            self.transfers = None
        else:
            try:
                self.transfers = int(self.transfers)
            except (TypeError, ValueError):
                pass
        if self.transfer_duration == None or self.transfer_duration == "":
            self.transfer_duration = None
        else:
            try:
                self.transfer_duration = int(self.transfer_duration)
            except (TypeError, ValueError):
                pass

    def get_fare_rule_list(self):
        return self.rules

    def clear_fare_rules(self):
        self.rules = []

    def get_field_values_tuple(self):
        return [getattr(self, fn) for fn in self._FIELD_NAMES]

    def __getitem__(self, name):
        return getattr(self, name)

    def __eq__(self, other):
        if not other:
            return False

        if id(self) == id(other):
            return True

        if self.get_field_values_tuple() != other.get_field_values_tuple():
            return False

        self_rules = [r.get_field_values_tuple() for r in self.get_fare_rule_list()]
        self_rules.sort()
        other_rules = [r.get_field_values_tuple() for r in other.get_fare_rule_list()]
        other_rules.sort()
        return self_rules == other_rules

    def __ne__(self, other):
        return not self.__eq__(other)

    def validate_fare_id(self, problems):
        if util.is_empty(self.fare_id):
            problems.missing_value("fare_id")

    def validate_price(self, problems):
        if self.price == None:
            problems.missing_value("price")
        elif not isinstance(self.price, float) and not isinstance(self.price, int):
            problems.invalid_value("price", self.price)
        elif self.price < 0:
            problems.invalid_value("price", self.price)

    def validate_currency_type(self, problems):
        if util.is_empty(self.currency_type):
            problems.missing_value("currency_type")
        elif self.currency_type not in util.ISO4217.codes:
            problems.invalid_value("currency_type", self.currency_type)

    def validate_payment_method(self, problems):
        if self.payment_method == "" or self.payment_method == None:
            problems.missing_value("payment_method")
        elif (not isinstance(self.payment_method, int) or
              self.payment_method not in range(0, 2)):
            problems.invalid_value("payment_method", self.payment_method)

    def validate_transfers(self, problems):
        if not ((self.transfers == None) or
                (isinstance(self.transfers, int) and
                 self.transfers in range(0, 3))):
            problems.invalid_value("transfers", self.transfers)

    def validate_transfer_duration(self, problems):
        if ((self.transfer_duration != None) and
                not isinstance(self.transfer_duration, int)):
            problems.invalid_value("transfer_duration", self.transfer_duration)
        if self.transfer_duration and (self.transfer_duration < 0):
            problems.invalid_value("transfer_duration", self.transfer_duration)

    def validate(self, problems=default_problem_reporter):
        self.validate_fare_id(problems)
        self.validate_price(problems)
        self.validate_currency_type(problems)
        self.validate_payment_method(problems)
        self.validate_transfers(problems)
        self.validate_transfer_duration(problems)

    def validate_before_add(self, problems):
        return True

    def validate_after_add(self, problems):
        return

    def add_to_schedule(self, schedule=None, problems=None):
        if schedule:
            schedule.AddFareAttributeObject(self, problems)
            self._schedule = schedule
