#!/usr/bin/python
# -*- coding: utf-8 -*-

import argparse
import blessed
import collections
import csv
import jinja2
import logging
import os
import re
import subprocess
import sys
from tempfile import NamedTemporaryFile

from dbbench import RunDbbench, DatabaseSpec, QueryStatistic, EnsureDbbenchInPath, CleanQuery

import statstest

logger = logging.getLogger(__name__)

# Ensure that we can output color escape characters and utf-8.
reload(sys)
sys.setdefaultencoding("utf-8")

term = blessed.Terminal()
_CONFIG_TEMPLATE = jinja2.Template(u"""
[setup]
{% if setupQueries %}
{% for sq in setupQueries %}
query={{ sq }}
{% endfor %}
{% endif %}
{% for _ in range(warmupIterations) %}
query-file={{ queryFile }}
{% endfor %}

[job "q"]
query-file={{ queryFile }}
count={{ iterations }}
""", trim_blocks=True)


def MakeDbbenchConfig(args, queryFile, setupQueries=None):
    """
    Generates a dbbench config to test the given query.

    Arguments:
        args: A python namespace object containing warmpup_iterations and
            iterations.
        queryFile: A file containg a single query to test
        setupQuery: An optional query to run during setup. This is run once
            and can set a session variable.

    Returns:
        A valid dbbench config as a string.
    """
    return _CONFIG_TEMPLATE.render(queryFile=queryFile,
                                   warmupIterations=args.warmup_iterations,
                                   iterations=args.iterations,
                                   setupQueries=setupQueries)


def RunQuery(args, dbspec, query, setupQueries=None):
    """
    Runs dbbench for the given config and returns an array of query statistics.

    Arguments:
        args: The command line arguments containing a `verbostity` level.
        dbspec: A DatabaseSpec object containing the database connection
            information.
        query: The query to run.
        setupQueries: An optional list of query to run during setup. They are
           run once and can set a session variable.

    Returns:
        A list of QueryStatistic tuples for the queries run by dbbench.

    Raises:
        subprocess.CalledProcessError: if `dbbench` returned a non-zero exit
            code. The exception object will have the return code in the
            `returncode` attribute and the combined output from stderr or
            stdout in the `output` attribute.
    """

    #
    # Write the query to a temp file so we do not have to worry about ini
    # escaping issues.
    #
    # If we will be logging the command executed, make sure to preserve the
    # temporary files.
    #
    keepTemporaryFiles = logger.getEffectiveLevel() <= logging.DEBUG
    with NamedTemporaryFile(delete=not keepTemporaryFiles,
                            suffix=".sql") as queryFile:
        queryFile.write(query)
        queryFile.flush()

        with NamedTemporaryFile(delete=not keepTemporaryFiles,
                                suffix=".ini") as configFile:
            configFile.write(MakeDbbenchConfig(args, queryFile.name,
                                               setupQueries=setupQueries))
            configFile.flush()

            return RunDbbench(dbspec, configFile.name)

def DoQuery(args, A_dbspec, B_dbspec, query):
    logger.info("testing query " + repr(query))
    queryPassed = True

    try:
        logger.debug("testing %s", args.A_name)
        aStats = RunQuery(args, A_dbspec, query,
                            setupQueries=args.A_setup_query)
        logger.debug("testing %s", args.B_name)
        bStats = RunQuery(args, B_dbspec, query,
                            setupQueries=args.B_setup_query)
    except subprocess.CalledProcessError as e:
        logger.error("Failed to execute dbbench with query %s: %s" %
                      (repr(query), e.output))
        if args.fatal_dbbench_errors:
            sys.exit("Exiting immediately due to --fatal-dbbench-errors")
        else:
            return False

    aExecutions = [float(s.elapsedMicros) / 1000.0 for s in aStats]
    bExecutions = [float(s.elapsedMicros) / 1000.0 for s in bStats]

    return statstest.DoTest(args, args.B_name, bExecutions,
                            args.A_name, aExecutions, unit="ms")

def main():
    EnsureDbbenchInPath()
    parser = argparse.ArgumentParser(
        description="Test query execution performance (old vs new codegen).",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument("-v", "--verbosity", action="count",
                        help="Increase output verbosity")

    def _add_config_to_group(group, name):
        group.add_argument("--%s-name" % name, default=name)
        group.add_argument("--%s-host" % name)
        group.add_argument("--%s-port" % name, type=int)
        group.add_argument("--%s-user" % name)
        group.add_argument("--%s-password" % name)
        group.add_argument("--%s-database" % name)
        group.add_argument("--%s-driver" % name)
        group.add_argument("--%s-setup-query" % name, action="append")

    _add_config_to_group(
        parser.add_argument_group("A test type configuration"), "A")
    _add_config_to_group(
        parser.add_argument_group("B test type configuration"), "B")

    dcg = parser.add_argument_group("Default test configuration")
    dcg.add_argument("--port", type=int, default=3306,
                     help="Database connection port")
    dcg.add_argument("--host", default="localhost",
                     help="Database connection host")
    dcg.add_argument("--user", default="root",
                     help="Database connection user")
    dcg.add_argument("--password", default="",
                     help="Database connection password")
    dcg.add_argument("--database", default="db",
                     help="Database connection database")
    dcg.add_argument("--driver", default="mysql",
                     help="Database connection driver")

    qg = parser.add_mutually_exclusive_group(required=True)
    qg.add_argument("--query", action="append",
                    help="Query to test. Can be specified " +
                         "multiple time to run multiple queries.")
    qg.add_argument("--query-file", type=argparse.FileType("r"),
                    help="SQL query file containing multiple queries to test.")

    dg = parser.add_mutually_exclusive_group()
    dg.add_argument("--fatal-dbbench-errors", dest="fatal_dbbench_errors",
                    action="store_true",
                    help="Stop immediately if dbbench exits non zero")
    dg.add_argument("--no-fatal-dbbench-errors", dest="fatal_dbbench_errors",
                    action="store_false")
    parser.set_defaults(fatal_dbbench_errors=True)

    statstest.AddStatsOptions(parser)

    parser.add_argument("--iterations", type=int, default=30,
                        help="Number of iterations to perform for each test.")
    parser.add_argument("--warmup-iterations", type=int, default=5,
                        help="Number of warmup iterations to perform for a " +
                        "query before recoring measurements.")

    args = parser.parse_args()

    A_dbspec = DatabaseSpec(
        args.A_host or args.host, args.A_port or args.port,
        args.A_user or args.user, args.A_password or args.password,
        args.A_database or args.database, args.A_driver or args.driver)
    B_dbspec = DatabaseSpec(
        args.B_host or args.host, args.B_port or args.port,
        args.B_user or args.user, args.B_password or args.password,
        args.B_database or args.database, args.B_driver or args.driver)

    if args.verbosity >= 1:
        logging.basicConfig(stream=sys.stdout, level=logging.DEBUG,
                            format='%(levelname)s:%(message)s')
    else:
        logging.basicConfig(stream=sys.stdout, level=logging.INFO,
                            format='%(levelname)s:%(message)s')

    if args.query is not None:
        queries = args.query
    else:
        queries = (CleanQuery(q) for q in args.query_file.read().split(";")
                   if CleanQuery(q))
    #
    # Make sure we materialize a list of all the DoQueries so that execute
    # all queries even if some regress.
    #
    results = [DoQuery(args, A_dbspec, B_dbspec, query) for query in queries]
    sys.exit(0 if all(results) else 1)

if __name__ == "__main__":
    main()
