#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# Copyright (c) 2016 by MemSQL. All rights reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#

import argparse
import abstats
import collections
import csv
import logging
import sys

def main():
    parser = argparse.ArgumentParser(
        description="A/B Test execution data (from <tag, score> csv file).",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument("-v", "--verbosity", action="count",
                        help="Increase output verbosity")

    abstats.AddStatsOptions(parser)
    parser.add_argument("--display-unit", default="",
                        help="Unit to use when displaying values.")

    parser.add_argument("input_file", nargs='?', type=argparse.FileType('r'),
                        default=sys.stdin,
                        help="Input file: csv file with <tag, score>. Should"
                        "only be two tags. The first tag in the file is "
                        "considered the \"old\" tag when checking for a "
                        "regression.")

    args = parser.parse_args()

    if args.verbosity >= 1:
        logging.basicConfig(stream=sys.stdout, level=logging.DEBUG,
                            format='%(levelname)s:%(message)s')
    else:
        logging.basicConfig(stream=sys.stdout, level=logging.INFO,
                            format='%(levelname)s:%(message)s')

    oldGroup = None
    executions_dict = collections.defaultdict(list)
    for row in csv.reader(args.input_file):
        # Gracefully handle empty lines.
        if len(row) == 0:
            continue
        oldGroup = row[0] if oldGroup is None else oldGroup
        executions_dict[row[0]].append(float(row[1]))

    if len(executions_dict.keys()) != 2:
        logging.fatal("You must provide exactly two groups")
        sys.exit(1)

    for group, values in executions_dict.iteritems():
        if group == oldGroup:
                oldExecutions = values
        else:
                newGroup = group
                newExecutions = values

    if len(oldExecutions) != len(newExecutions):
        logging.error("Both groups do not have the same number of values: "
                      "got %d values for %s but %d values for %s",
                      len(oldExecutions), oldGroup, len(newExecutions),
                      newGroup)

    if not abstats.DoTest(args, newGroup, newExecutions, oldGroup, oldExecutions,
                  args.display_unit):
        sys.exit(1)


if __name__ == "__main__":
    main()
