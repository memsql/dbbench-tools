#!/usr/bin/env python
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
        'blessed==1.14.1',
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
            'dbbench-scaler=DbbenchTools.autopoc:main',
            'dbbench-abtest=DbbenchTools.abtest:main',
        ],
    }
)
