#!/usr/bin/env python3

try:
    from setuptools import setup
except ImportError:
    from distutils.core import setup

setup(name='glight',
    version='0.1',
    description='GLight a library for setting led colors on some Logitech devices',
    author='Martin Feil',
    author_email='foss2017@sgdw.de',
    url='https://github.com/sgdw/glight',
    classifiers=[ # https://pypi.python.org/pypi?:action=list_classifiers
        'Development Status :: 4 - Beta',
        'Environment :: Console',
        'Environment :: X11 Applications :: GTK',
        'Intended Audience :: End Users/Desktop',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: GNU General Public License v3 or later (GPLv3+)',
        'Operating System :: POSIX :: Linux',
        'Programming Language :: Python :: 2.7',
        'Topic :: Utilities',
    ],
    install_requires=['gi', 'libusb1', 'pydbus'],
    extras_require={'legacy': ['libusb', 'glib']},
    package_dir={'glight': 'glight'},
    package_data={
        'glight': ['*.glade'],
    },
    packages=['glight'],
    scripts=['scripts/install-glight'],
    data_files=[],
    entry_points={
        'console_scripts': [
            'glight = glight.glight:main',
            'glight_ui = glight.glight_ui:main',
            'glight_fx = glight.glight_fx:main',
        ]
    }
)