#!/usr/bin/env python3
"""
.. module:: setup
   :platform: posix
   :synopsis: Build the mauzr package.

.. moduleauthor:: Alexander Sowitzki <dev@eqrx.net>
"""

import setuptools
import mauzr.setup

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
    cmdclass={"espbuild": mauzr.setup.ESPBuildCommand,
              "espfetch": mauzr.setup.ESPFetchCommand,
              "espflash": mauzr.setup.ESPFlashCommand,
              "dockerize": mauzr.setup.DockerCommand},
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
    setup_requires=[],
    tests_require=['pytest', 'pylint', 'pytest-pylint'],
    install_requires=['paho-mqtt', 'PyYAML'],
    extras_require={
        "buildextra": ["sphinx", "pytest-runner"],
        "raspberry": ["RPi.GPIO"],
        "docker": ["gitpython"],
        "esp": ["esptool", "requests"],
        "gui": ["pygame"],
        "images": ["Pillow"],
        "logging": ["rrdtool"],
        "prometheus": ["prometheus_client"]
    },
    entry_points={
        "console_scripts": [
            'mauzr-camera=mauzr.platform.cpython.camera:main',
            'mauzr-linuxaudio=mauzr.platform.linux.audio.driver:main',
            'mauzr-imageviewer=mauzr.util.image.viewer:main',
            'mauzr-rrdlogger=mauzr.util.rrd.logger:main',
            'mauzr-rrdrenderer=mauzr.util.rrd.renderer:main'
        ]
    }
)
