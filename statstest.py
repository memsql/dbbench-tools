#!/usr/bin/python
# -*- coding: utf-8 -*-

import argparse
import blessed
import collections
import csv
import logging
import numpy
import os
import re
from scipy import stats
import sys

# Ensure that we can output color escape characters and utf-8.
reload(sys)
sys.setdefaultencoding("utf-8")

term = blessed.Terminal()


def GetConfidenceIntervalWidth(values, confidence):
    return (stats.sem(values, ddof=len(values)-1) *
            stats.t.ppf(confidence, len(values)-1))


def GetMeanStr(values, confidence):
    """Returns a string representing a confidence interval around the mean."""
    error = GetConfidenceIntervalWidth(values, confidence)
    return "%.2f±%.2f" % (numpy.mean(values), error)


def GetBucketChar(count, maxCount):
    blocks = [' ', '▁', '▂', '▃', '▄', '▅', '▆', '▇', '█']
    bi = int(float(count)/float(maxCount)*(len(blocks) - 1))
    #
    # Deliberately show outliers, even if they would not have otherwise
    # appeared.
    #
    if count > 0 and bi == 0:
        bi = 1
    return blocks[bi]


def GetHistogramString(array, unit="", **kwargs):
    """
    Returns the values in array represented as a histogram.

    Summary:
        Generates a histogram using scipy.stats.histogram and renders it
        as a string.

    Arguments:
        array: A list of values.
        unit: The human readable string to be used as the unit for the values.
            For example, unit="us" would cause values to displayed as "10us".
        **kwargs: A dict containing parameters to be forwarded directly to
            scipy.stats.histogram as keyword args.
    """
    buckets, low_range, binsize, extrapoints = stats.histogram(array, **kwargs)
    hist = "%7.2f%s : " % (low_range, unit)
    for count in buckets:
        hist += GetBucketChar(count, max(buckets))
    hist += " : %7.2f%s" % ((low_range + binsize * (len(buckets) + 1)), unit)
    return hist


def LogPerformanceStats(args, oldGroup, oldExecutions, newGroup,
                        newExecutions, unit=""):
    """
    Logs detailed information for executions.

    Summary:
        Calculates detailed statistics (including histograms) for each of
        the input arrays and emits them to `logging.info`. Deliberately
        attempts to align the histograms and ensure the both execution
        histograms use the same scale to improve readability.

    Arguments:
        args: The command line arguments containing the histogram parameters
            and the confidence level.
        newGroup: The name of the new execution group.
        newExecutions: An array of floats containing new execution times in
            milliseconds.
        oldGroup: The name of the old execution group.
        oldExecutions: An array of floats containing old execution times in
            milliseconds.
    """

    #
    # We want might want more than default bins, and we  we take special care
    # to ensure that the histograms will line up (same size bucket at same
    # point on the screen).
    #
    minExecution = min(min(newExecutions), min(oldExecutions))
    maxExecution = max(max(newExecutions), max(oldExecutions))
    s = (1/2) * (maxExecution - minExecution) / (args.histogram_buckets - 1)

    newExecutionHist = GetHistogramString(
        newExecutions, unit,
        defaultlimits=(minExecution - s, maxExecution + s),
        numbins=args.histogram_buckets)
    oldExecutionHist = GetHistogramString(
        oldExecutions, unit,
        defaultlimits=(minExecution - s, maxExecution + s),
        numbins=args.histogram_buckets)

    newExecutionMeanStr = ("μ=%s%s" %
                           (GetMeanStr(newExecutions, args.confidence), unit))
    oldExecutionMeanStr = ("μ=%s%s" %
                           (GetMeanStr(oldExecutions, args.confidence), unit))
    maxMeanLen = max(len(newExecutionMeanStr), len(oldExecutionMeanStr))
    maxNameLen = max(len(newGroup), len(oldGroup))

    logging.info(term.cyan("%-*s execution time   : %-*s : %s"),
                 maxNameLen, newGroup,
                 maxMeanLen, newExecutionMeanStr, newExecutionHist)
    logging.info(term.blue("%-*s execution time   : %-*s : %s"),
                 maxNameLen, oldGroup,
                 maxMeanLen, oldExecutionMeanStr, oldExecutionHist)


def CheckVariance(args, newGroup, newExecutions, oldGroup, oldExecutions):
    """
    Ensure that neither execution has too much internal variance.
    """
    if len(newExecutions) <= 1 or len(oldExecutions) <= 1:
        logging.error(term.red("Insufficient samples to check variance."))
        return False

    newError = GetConfidenceIntervalWidth(newExecutions, args.confidence)
    oldError = GetConfidenceIntervalWidth(oldExecutions, args.confidence)
    newMean = numpy.mean(newExecutions)
    oldMean = numpy.mean(oldExecutions)
    passed = True

    if oldError > oldMean*args.max_interval_percent:
        logging.error(
            term.red("confidence interval width for %s (%.1f%%) is more "
                     "than %.1f%% of μ"),
            oldGroup, 100.0 * oldError / oldMean,
            100.0 * args.max_interval_percent)
        passed = False

    if newError > newMean*args.max_interval_percent:
        logging.error(
            term.red("confidence interval width for %s (%.1f%%) is more "
                     "than %.1f%% of μ"),
            newGroup, 100.0 * newError / newMean,
            100.0 * args.max_interval_percent)
        passed = False

    return passed


def CheckMean(args, newGroup, newExecutions, oldGroup, oldExecutions):
    """
    Run a Welch two sample t test to ensure that we have not regressed
    execution perf.

    While this test assumes normality, the Welch's variant does *not*
    assume homoscedasticity (i.e. both populations have the same
    variance). Other similar tests, such as the Mann-Whitney U test,
    are sensitive to this property:

    > If the distributions are heteroscedastic, the Kruskal–Wallis test
    won't help you; instead, you should use Welch's t–test for two groups, or
    Welch's anova for more than two groups.

    http://www.biostathandbook.com/kruskalwallis.html
    """

    (_, p) = stats.ttest_ind(newExecutions, oldExecutions,
                             equal_var=False)
    if p < 1 - args.confidence:
        newExecutionsMean = numpy.mean(newExecutions)
        oldExecutionsMean = numpy.mean(oldExecutions)

        if newExecutionsMean > oldExecutionsMean:
            regression = (newExecutionsMean - oldExecutionsMean)
            regressionPct = (regression / oldExecutionsMean) * 100
            logging.error(
                term.red("execution regressed by %.1f%%"), regressionPct)
            return False

        else:
            if newExecutionsMean == oldExecutionsMean:
                logging.error("Means equal with significant p value (%f)", p)

            improvement = (oldExecutionsMean - newExecutionsMean)
            improvementPct = (improvement / newExecutionsMean) * 100
            logging.info(
                term.green("execution improved by %.1f%%"), improvementPct)
    else:
        logging.debug("execution had too much variance to make conclusion")
    return True


def CheckP99(args, newGroup, newExecutions, oldGroup, oldExecutions):
    # TODO Test 99th percentile
    return True


def DoTest(args, newGroup, newExecutions, oldGroup, oldExecutions, unit=""):
    LogPerformanceStats(args, newGroup, newExecutions,
                        oldGroup, oldExecutions, unit)

    return all((
        CheckVariance(args, newGroup, newExecutions, oldGroup, oldExecutions),
        CheckMean(args, newGroup, newExecutions, oldGroup, oldExecutions),
        CheckP99(args, newGroup, newExecutions, oldGroup, oldExecutions),
    ))


def AddStatsOptions(parser):
    group = parser.add_argument_group("Statistical analysis options")
    group.add_argument("--confidence", type=float, default=0.999,
                       help="Confidence interval (e.g. be 99.9%% confident " +
                       "of all reported values.")
    group.add_argument("--max-regression", type=float, default=0.02,
                       help="Maximum allowed executionregression (e.g. " +
                       "B execution must within 2%% of A execution).")
    group.add_argument("--max-interval-percent", type=float, default=0.10,
                       help="Maximum allowed confidence interval width as a "
                       "percentage of the sample mean (e.g. "
                       "the interval cannot be more than 10%% of the sample "
                       "mean).")
    group.add_argument("--histogram-buckets", type=int, default=15,
                       help="Number of histogram buckets to use.")


def main():
    parser = argparse.ArgumentParser(
        description="A/B Test execution data (from <tag, score> csv file).",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument("-v", "--verbosity", action="count",
                        help="Increase output verbosity")

    AddStatsOptions(parser)
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

    if not DoTest(args, newGroup, newExecutions, oldGroup, oldExecutions,
                  args.display_unit):
        sys.exit(1)


if __name__ == "__main__":
    main()
