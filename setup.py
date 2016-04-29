#!/usr/bin/env python

from setuptools import setup, Extension
from setuptools.command.build_ext import build_ext as _build_ext

import sys

def readme():
    with open('README.md') as f:
        return f.read()


#
# Amazingly, `pip install scipy` fails if numpy is not already installed.
# Since we cannot control the order that dependencies are installed via
# install_requires, use setup_requires to ensure that numpy is available
# before scipy is installed.
#
# Unfortunately, this is *still* not sufficient: numpy has a guard to
# check when it is in its setup process. It is possible to circumvent
# the guard, but then we still get scary error messages; its much
# easier to just require numpy before we can install.
#
try:
    import numpy
except ImportError:
    sys.stderr.write(
        "\n"
        "You *must* install numpy before installing dbbench-tools.\n" +
        "You might be able to install via one of the following:\n" +
        " - apt-get install python-numpy\n" +
        " - pip install numpy\n" +
        " - From the scipy website: http://www.scipy.org/scipylib/download.html\n"
    )
    sys.exit(1)

setup(
    name='dbbench_tools',
    version='0.0.2',
    description='A collection of tools for interacting with dbbench',
    long_description=readme(),
    author='Alex Reece',
    author_email='awreece' '@' 'gmail.com',
    license='Apache License',
    install_requires=[
        'matplotlib==1.4.3',
        'scipy',
        'blessed',
        'jinja2',
    ],
    packages=['DbbenchTools'],
    py_modules=['dbbench'],
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Environment :: Console',
        'Intended Audience :: Developers',
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 2.6',
        'Programming Language :: Python :: 2.7',
        'Topic :: Database',
        'Topic :: Software Development :: Testing',
        'Topic :: System :: Benchmark',
    ],
    scripts=['statstest.py'],
    entry_points={
        'console_scripts': [
            'autopoc.py=DbbenchTools.autopoc:main',
            'dbbench-abtest=DbbenchTools.abtest:main',
        ],
    }
)
