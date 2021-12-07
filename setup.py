"""setup.py file."""
from setuptools import find_packages, setup

__author__ = 'Johan van den Dorpe'

with open("requirements.txt", "r") as fs:
    reqs = [r for r in fs.read().splitlines()]

setup(
    name="napalm-brocade-fastiron",
    version="0.16",
    packages=find_packages(),
    author="Johan van den Dorpe",
    description="Network Automation and Programmability Abstraction Layer with Multivendor support",
    classifiers=[
        'Topic :: Utilities',
         'Programming Language :: Python',
         'Programming Language :: Python :: 2.7',
        'Operating System :: POSIX :: Linux',
        'Operating System :: MacOS',
    ],
    url="https://github.com/vdltech/napalm-brocade-fastiron",
    include_package_data=True,
    install_requires=reqs,
)
