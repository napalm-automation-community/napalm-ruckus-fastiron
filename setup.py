"""setup.py file."""

import uuid

from setuptools import setup, find_packages
from os import path

__author__ = 'Jesus Mendez <mendezj@staticoverride.us>'

with open("requirements.txt", "r") as fs:
    reqs = [r for r in fs.read().splitlines()]

setup(
    name="napalm-ruckus-fastiron",
    version="1.0.26",
    packages=find_packages(),
    author="Jesus Mendez",
    author_email="mendezj@staticoverride.us",
    description="Network Automation and Programmability Abstraction Layer with Multivendor support",
    classifiers=[
        'Topic :: Utilities',
         'Programming Language :: Python',
         'Programming Language :: Python :: 2',
         'Programming Language :: Python :: 2.7',
        'Operating System :: POSIX :: Linux',
        'Operating System :: MacOS',
    ],
    url="https://github.com/Static0verride/napalm-ruckus-fastiron",
    include_package_data=True,
    install_requires=reqs,
)
