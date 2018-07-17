#!/usr/bin/env python3
"""
.. module:: setup
   :platform: posix
   :synopsis: Build the mauzr package.

.. moduleauthor:: Alexander Sowitzki <dev@eqrx.net>
"""

import setuptools

setuptools.setup(
    version=0,
    author="Alexander Sowitzki",
    author_email="dev@eqrx.net",
    url="http://mauzr.eqrx.net",
    name="mauzr",
    keywords="agent cps distributed framework hardware iot mqtt smart",
    description="Framework for developing cyber-physical systems and"
                " IoT devices",
    packages=setuptools.find_packages(),
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Environment :: Console',
        'Environment :: No Input/Output (Daemon)',
        'Environment :: X11 Applications',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: '
        'GNU Affero General Public License v3 or later (AGPLv3+)',
        'Natural Language :: English',
        'Programming Language :: Python :: 3 :: Only',
        'Programming Language :: Python :: Implementation :: MicroPython',
        'Programming Language :: Python :: Implementation :: CPython',
        'Topic :: Home Automation',
        'Topic :: Software Development :: Embedded Systems',
        'Topic :: Software Development :: Libraries :: Application Frameworks',
        'Topic :: Software Development :: Libraries :: Python Modules',
        'Topic :: System :: Hardware :: Hardware Drivers'
    ],
    tests_require=['pytest', 'pylint', 'pytest-pylint'],
    extras_require={
        "build": ["sphinx", "pytest-runner"],
        "gui": ["pygame"],
        "images": ["numpy"]
    },
    entry_points={
        "console_scripts": ['mauzr=mauzr.shell:main',
                            'mauzr-cfg=mauzr.configurator:main']
    }
)
