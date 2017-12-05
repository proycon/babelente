#! /usr/bin/env python
# -*- coding: utf8 -*-

from __future__ import print_function

import os
from setuptools import setup

def read(fname):
    return open(os.path.join(os.path.dirname(__file__), fname)).read()

setup(
    name = "BabelEnte",
    version = "0.1.6",
    author = "Maarten van Gompel, Iris Hendrickx",
    author_email = "proycon@anaproy.nl",
    description = ("Entity extractioN, Translation and Evaluation using BabelFy"),
    license = "GPL",
    keywords = "nlp computational_linguistics entities wikipedia dbpedia linguistics tramooc",
    url = "https://github.com/proycon/babelente",
    packages=['babelente'],
    long_description=read('README.rst'),
    classifiers=[
        "Development Status :: 4 - Beta",
        "Topic :: Text Processing :: Linguistic",
        "Programming Language :: Python :: 3",
        "Operating System :: POSIX",
        "Intended Audience :: Science/Research",
        "License :: OSI Approved :: GNU General Public License v3 (GPLv3)",
    ],
    zip_safe=False,
    include_package_data=True,
    package_data = { },
    install_requires=[ 'babelpy >= 1.0', 'numpy'],
    entry_points = {    'console_scripts': [ 'babelente = babelente.babelente:main' ] }
)
