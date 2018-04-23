"""setup.py file."""

import uuid

from setuptools import setup, find_packages

try:                    # for pip >= 10
    from pip._internal.req import parse_requirements
except ImportError:     # for pip <= 9.0.3
    from pip.req import parse_requirements

__author__ = 'Jesus Mendez <mendezj@staticoverride.us>'

install_reqs = parse_requirements('requirements.txt', session=uuid.uuid1())
reqs = [str(ir.req) for ir in install_reqs]

setup(
    name="napalm-ruckus-fastiron",
    version="1.0.21",
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
