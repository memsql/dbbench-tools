#!/usr/bin/python
# -*- coding: utf-8 -*-

import argparse
import logging
import os
import re
import subprocess
import sys
import time

from tempfile import NamedTemporaryFile

import matplotlib.pyplot as plt

from dbbench import RunDbbench, DatabaseSpec, humanize_count, humanize_us

# Ensure that we can output color escape characters and utf-8.
reload(sys)
sys.setdefaultencoding("utf-8")

logger = logging.getLogger(__name__)


def transform(param, level, line):
    m = re.match(re.compile('^(%s\s*=\s*)(\d+)' % param), line)
    if m:
        return "%s=%d" % (param, int(m.group(2)) * level)
    else:
        return line


def RunTest(args, param, level):
    """
    Runs dbbench for the given config and returns an array of query statistics.

    Arguments:
        args: The command line arguments containing a `verbosity` level.
        setupQueries: An optional list of query to run during setup. They are
           run once and can set a session variable.

    Returns:
        A list of QueryStatistic tuples for the queries run by dbbench for the
            matched job.
    """

    logger.info("Running at %s level %d for %d seconds",
                param, level, args.duration)

    #
    # If we will be logging the command executed, make sure to preserve the
    # temporary files.
    #
    keepTempFiles = logger.getEffectiveLevel() <= logging.DEBUG
    with NamedTemporaryFile(delete=not keepTempFiles,
                            suffix=".ini") as configFile:
        configFile.write("duration=%ds\n" % args.duration)
        with open(args.base_config_file) as baseConfigFile:
            for line in baseConfigFile:
                configFile.write(transform(param, level, line) + "\n")

        configFile.flush()

        try:
            ret = RunDbbench(
                DatabaseSpec(host=args.host, port=args.port,
                             user=args.user, password=args.password,
                             database=args.database, driver=args.driver),
                configFile.name,
                basedir=os.path.dirname(args.base_config_file))
        except subprocess.CalledProcessError as e:
            if args.fatal_dbbench_errors:
                logger.fatal(e.output)
                raise
            else:
                logger.error(e.output)
                time.sleep(1)
                return []

        if args.reported_job:
            ret = [qs for qs in data if qs.name == args.reported_job]

        matched_jobs = set(qs.name for qs in ret)
        if len(matched_jobs) == 0:
            logger.error("Reported job filter %s did not match any jobs",
                         repr(args.reported_job))
        elif len(matched_jobs) > 1:
            logger.error("Reported job filter %s matched multiple jobs: %s",
                         repr(args.reported_job), repr(matched_jobs))

        logger.info(
            "Finished run: avg latency=%s, tps=%s",
            humanize_us(sum(qs.elapsedMicros for qs in ret)/len(ret)),
            humanize_count(len(ret) / float(args.duration)))
        time.sleep(1)
        return ret


def MakeChart(args, axis_label, labels, allQueryStatistics):
    latencies = []
    tps = []
    for queryStatistics in allQueryStatistics:
        latencies.append(
            [qs.elapsedMicros / 1000000.0 for qs in queryStatistics])
        tps.append(len(queryStatistics) / args.duration)

    plt.subplot(2, 1, 1)
    plt.boxplot(latencies)
    plt.ylabel("Latency (seconds)")
    plt.xticks(range(1, len(labels)+1), labels)

    plt.subplot(2, 1, 2)
    plt.bar([i+.1 for i in xrange(len(tps))], tps, width=0.8)
    plt.xlabel(axis_label)
    plt.ylabel("TPS")
    plt.xticks([i+.5 for i in xrange(len(labels))], labels)

    if args.output:
        plt.savefig(args.output)
    else:
        plt.show()


def EnsureDbbenchInPath():
    "Ensure that dbbench is in the PATH"
    cur_dir = os.path.dirname(os.path.realpath(__file__))
    if not any(os.access(os.path.join(path, 'dbbench'), os.X_OK)
               for path in os.environ["PATH"].split(os.pathsep)):
        logger.warning("No dbbench found in PATH, adding %s to the PATH",
                       cur_dir)
        os.environ['PATH'] += os.pathsep + cur_dir


def main():
    EnsureDbbenchInPath()
    parser = argparse.ArgumentParser(
        description="Test accross different .",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument("-v", "--verbosity", action="count",
                        help="Increase output verbosity")

    parser.add_argument("--port", type=int, default=3306,
                        help="Database connection port")
    parser.add_argument("--host", default="localhost",
                        help="Database connection host")
    parser.add_argument("--user", default="root",
                        help="Database connection user")
    parser.add_argument("--password", default="",
                        help="Database connection password")
    parser.add_argument("--database", default="db",
                        help="Database connection database")
    parser.add_argument("--driver", default="mysql",
                        help="Database connection type (e.g mysql vs mssql).")

    dg = parser.add_mutually_exclusive_group()
    dg.add_argument("--fatal-dbbench-errors", dest="fatal_dbbench_errors",
                    action="store_true",
                    help="Stop immediately if dbbench exits non zero")
    dg.add_argument("--no-fatal-dbbench-errors", dest="fatal_dbbench_errors",
                    action="store_false")
    parser.set_defaults(fatal_dbbench_errors=True)

    parser.add_argument("--duration", type=int, default=10,
                        help="Duration of each test")
    parser.add_argument("base_config_file", help="Replace all concurrency=")

    parser.add_argument("--reported-job",
                        help="Which dbbench job to generate the report for.")

    tg = parser.add_mutually_exclusive_group(required=True)
    tg.add_argument('--concurrency',
                    help="Comma separated list of different concurrency levels"
                    " to test with dbbench.")
    tg.add_argument('--rate',
                    help="Comma separated list of different query start rates"
                    " to test with dbbench.")

    parser.add_argument("--output", help="Output file for chart")

    args = parser.parse_args()

    if args.verbosity >= 1:
        logging.basicConfig(stream=sys.stdout, level=logging.DEBUG,
                            format='%(levelname)s:%(message)s')
    else:
        logging.basicConfig(stream=sys.stdout, level=logging.INFO,
                            format='%(levelname)s:%(message)s')

    if args.concurrency:
        transform_param = "concurrency"
        transform_values = args.concurrency.split(",")
        transform_label = "Concurrency (# of connections)"
    else:
        transform_param = "rate"
        transform_values = args.rate.split(",")
        transform_label = "Rate of new queries (QPS)"

    data = (RunTest(args, transform_param, int(c)) for c in transform_values)
    MakeChart(args, transform_label, transform_values, data)

if __name__ == "__main__":
    main()
