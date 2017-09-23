#!/usr/bin/env python

'''
GLight controls LEDs of some Logitech devices

Copyright (C) 2017  Martin Feil aka. SGDW

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <http://www.gnu.org/licenses/>.


'''

# pylint: disable=C0326

import sys
import array
import json
import os

import argparse
from time import sleep
import traceback

import psutil  # http://pythonhosted.org/psutil/

import glight

app_version = "0.1"

class ColorUtils(object):

    @staticmethod
    def transition(value, maximum, start_point, end_point):
        return start_point + (end_point - start_point) * value / maximum

    @staticmethod
    def transition3(value, maximum, (s1, s2, s3), (e1, e2, e3)):
        r1 = ColorUtils.transition(value, maximum, s1, e1)
        r2 = ColorUtils.transition(value, maximum, s2, e2)
        r3 = ColorUtils.transition(value, maximum, s3, e3)
        return r1, r2, r3

    # import colorsys
    # rgb_triplet_to_display= hsv_to_rgb(transition3(value, maximum, start_triplet, end_triplet))


class ValueSource(object):

    def __init__(self):
        """"""

    def get_dimensions(self):
        """"""
        return 1

    def get_value(self):
        """"""
        return 0.0


class SysLoadSource(ValueSource):

    def __init__(self, load_field=None, initial_load_max=None):
        super(SysLoadSource, self).__init__()

        self.load_max = initial_load_max or 1.0
        self.load_field = load_field or 0

    def get_dimensions(self):
        return 1

    def get_value(self):
        load = os.getloadavg()
        load_val = load[self.load_field]
        if load_val > self.load_max:
            self.load_max = load_val

        return load_val/self.load_max


class CpuLoadSource(ValueSource):

    def __init__(self):
        super(CpuLoadSource, self).__init__()

    def get_dimensions(self):
        return psutil.cpu_count()

    def get_value(self):
        return self.read_cpu_usage()

    def read_cpu_usage(self):
        return psutil.cpu_percent(interval=0.1, percpu=True)


# App handling ----------------------------------------------------------------

class GlightFxApp(object):

    @staticmethod
    def get_val_at(values, index, default=None):
        if len(values) > index:
            return values[index]
        return default

    @staticmethod
    def get_num_at(values, index, default=None):
        if len(values) > index:
            return int(values[index])
        return default

    @staticmethod
    def get_argsparser():
        """"""
        argsparser = argparse.ArgumentParser(
            description='Some color effects using Glight (V' + app_version + ')', add_help=False)

        argsparser.add_argument('-d', '--device',  dest='device',  nargs='*', action='store', help='set device', metavar='device_name')

        argsparser.add_argument('--experimental', dest='experimental', nargs='?', action='store', help='call experimental function',
                                metavar='name')

        argsparser.add_argument('-C', '--client',  dest='client',  action='store_const', const=True, help='run as client')
        argsparser.add_argument('-l', '--list',    dest='do_list', action='store_const', const=True, help='list devices')
        argsparser.add_argument('-v', '--verbose', dest='verbose', action='store_const', const=True, help='be verbose')
        argsparser.add_argument('-h', '--help',    dest='help',    action='store_const', const=True, help='show help')

        return argsparser

    @staticmethod
    def get_args():
        return GlightFxApp.get_argsparser().parse_args()

    @staticmethod
    def handle_args(args=None, verbose=None):
        """"""
        if args is None:
            args=GlightFxApp.get_args()

        if args.help:
            GlightFxApp.get_argsparser().print_help()
            print()
            sys.exit(0)

        if verbose is None:
            verbose = args.verbose or False

        if args.experimental:
            if args.experimental == "test":
                src = CpuLoadSource()
                print src.read_cpu_usage()

        else:
            GlightFxApp.handle(args=args, verbose=args.verbose)

        return args

    @staticmethod
    def handle(args, verbose=False):
        """"""
        backend_type = glight.GlightController.BACKEND_LOCAL
        if args.client:
            backend_type = glight.GlightController.BACKEND_DBUS
        client = glight.GlightController(backend_type, verbose=verbose)


if __name__ == "__main__":

    # App -----------------------------------------
    # here we go ...

    try:

        args = GlightFxApp.get_args()
        GlightFxApp.handle_args(args=args)

    except Exception as ex:
        print("Exception: {}".format(ex))
        if args.verbose:
            print(traceback.format_exc())
        sys.exit(1)
    finally:
        pass
