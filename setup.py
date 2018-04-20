import uuid
from setuptools import setup, find_packages
from pip.req import parse_requirements

install_reqs = parse_requirements('requirements.txt', session=uuid.uuid1())
reqs = [str(ir.req) for ir in install_reqs]

setup(name='napalm-ruckus-fastiron',
      description='Ruckus Fastiron Support for Napalm',
      author='Jesus Mendez',
      author_email='mendezj@staticoverride.us',
      version='1.0.1',
      package=find_packages(),
      classifiers=[
          'Topic :: Utilities',
          'Programming Language :: Python',
          'Programming Language :: Python :: 2',
          'Programming Language :: Python :: 2.7',
          'Operating System :: POSIX :: Linux',
          'Operating System :: MacOS',
      ],
      url='https://github.com/napalm-automation-community/napalm-ruckus-fastiron',
      include_package_data=True,
      install_requires=reqs,
      )
