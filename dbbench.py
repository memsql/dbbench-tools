#!/usr/bin/env python

import csv
import logging
import subprocess
import os

from tempfile import NamedTemporaryFile

logger = logging.getLogger(__name__)


def humanize_us(micros):
    for (fmt, scale) in [('%.3fh', 60*60*1000000.0), ('%.3fm', 60*1000000.0),
                         ('%.3fs', 1000000.0), ('%.3fms', 1000.0),
                         ('%dus', 1)]:
        if micros >= scale:
            return fmt % (micros/scale)
    return "0us"


def humanize_count(count):
    for (fmt, scale) in [('%.3fG', 2.0**30), ('%.3fM', 2.0**20),
                         ('%.3K', 2.0**10), ('%d', 1)]:
        if count >= scale:
            return fmt % (count/scale)
    return "0"


class QueryStatistic(object):
    __slots__ = 'name', 'startMicros', 'elapsedMicros', 'rowsAffected'

    def __init__(self, name, startMicros, elapsedMicros, rowsAffected):
        self.name = name
        self.startMicros = int(startMicros)
        self.elapsedMicros = int(elapsedMicros)
        self.rowsAffected = int(rowsAffected)

    def __repr__(self):
        return "QueryStatistic(" + ",".join((
            "name=%s" % repr(self.name),
            "start=%s" % humanize_us(self.startMicros),
            "elapsed=%s" % humanize_us(self.elapsedMicros),
            "rowsAffected=%s" % humanize_count(self.rowsAffected)
        )) + ")"


class DatabaseSpec(object):
    def __init__(self, host="localhost", port=3306, user="root", password="",
                 database="", driver="mysql"):
        self.host = host if host else "localhost"
        self.port = int(port) if port else 3306
        self.user = user if user else "root"
        self.password = password if password else ""
        self.database = database if database else ""
        self.driver = driver if driver else "mysql"

    def __repr__(self):
        return "DatabaseSpec(%s::%s:%s@%s:%d/%s)" % (
            self.driver, self.user, self.password,
            self.host, self.port, self.database)


def RunDbbench(dbspec, configFileName, basedir=None):
    """
    Runs dbbench for the given config and returns an array of query statistics.

    Arguments:
        dbspec: A DatabaseSpec object containing the database connection
            information.
        configFileName: The path to a config file to execute.
        basedir: An optional argument. If not none, is used as the base for
            for the dbbench run.

    Returns:
        A list of QueryStatistic tuples for the queries run by dbbench.

    Raises:
        subprocess.CalledProcessError: if `dbbench` returned a non-zero exit
            code. The exception object will have the return code in the
            `returncode` attribute and the combined output from stderr or
            stdout in the `output` attribute.
    """

    if basedir is None:
        basedir = os.path.dirname(configFileName)
    #
    # If we will be logging the command executed, make sure to preserve the
    # temporary files.
    #
    keepTemporaryFiles = logger.getEffectiveLevel() <= logging.DEBUG
    with NamedTemporaryFile(delete=not keepTemporaryFiles,
                            suffix=".csv") as statsFile:
        command = [
            "dbbench",
            "--database", dbspec.database,
            "--host", dbspec.host,
            "--port", str(dbspec.port),
            "--username", dbspec.user,
            "--password", dbspec.password,
            "--intermediate-stats=false",
            "--query-stats-file", statsFile.name,
            "--base-dir", basedir,
            configFileName]
        logger.debug(" ".join(a if a else repr(a) for a in command))
        subprocess.check_output(command, stderr=subprocess.STDOUT)

        return [QueryStatistic(*row) for row in csv.reader(statsFile)]
