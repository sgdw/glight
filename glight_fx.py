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
import colorsys

import glight

app_version = "0.1"


class ColorUtils(object):

    @staticmethod
    def lerp(val, max_val, start_val, end_val):
        return start_val + (end_val - start_val) * val / max_val

    @staticmethod
    def lerp3(val, max_val, (s1, s2, s3), (e1, e2, e3)):
        r1 = ColorUtils.lerp(val, max_val, s1, e1)
        r2 = ColorUtils.lerp(val, max_val, s2, e2)
        r3 = ColorUtils.lerp(val, max_val, s3, e3)
        return r1, r2, r3

    @staticmethod
    def col_hex_to_triplet(col_hex):
        col_hex = col_hex or ""

        if len(col_hex) > 6:
            col_hex = col_hex[0:6]
        elif len(col_hex) < 6:
            col_hex = col_hex.ljust(6, "0")

        rgb = [0, 0, 0]
        for i in range(0, 3):
            col_int = float(int(col_hex[i*2:i*2+2], 16))
            rgb[i] = col_int/255.0

        return tuple(rgb)

    @staticmethod
    def col_triplet_to_hex(col_triplet):
        return "{:02x}{:02x}{:02x}".format(
            int(round(col_triplet[0] * 255)),
            int(round(col_triplet[1] * 255)),
            int(round(col_triplet[2] * 255)))

    @staticmethod
    def color_lerp(val, max_val, rgb_start, rgb_end):
        hsv_start = colorsys.rgb_to_hsv(rgb_start[0], rgb_start[1], rgb_start[2])
        hsv_end   = colorsys.rgb_to_hsv(rgb_end[0],   rgb_end[1],   rgb_end[2])

        hsv = ColorUtils.lerp3(val, max_val, hsv_start, hsv_end)
        rgb = colorsys.hsv_to_rgb(hsv[0], hsv[1], hsv[2])

        return rgb
        # rgb_triplet_to_display= hsv_to_rgb(transition3(value, maximum, start_triplet, end_triplet))


class ValueSource(object):

    def __init__(self):
        """"""

    def get_polling_timeout(self):
        return 2000  # milliseconds

    def get_value_range(self, dimension=0):
        return 0.0, 1.0

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

    def get_value_range(self, dimension=0):
        return 0.0, None

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

    def get_value_range(self, dimension=0):
        return 0.0, 100.0

    def get_value(self):
        return self.read_cpu_usage()

    def read_cpu_usage(self):
        return psutil.cpu_percent(interval=0.1, percpu=True)


class GlightEffect(object):

    def __init__(self, client):
        """"""
        self.client = client

class CpuxEffect(GlightEffect):

    def run(self):
        vsrc = CpuLoadSource()
        vsrc_range = vsrc.get_value_range()

        col_scale = [
            ColorUtils.col_hex_to_triplet("0000ff"), ColorUtils.col_hex_to_triplet("ff0000")
        ]

        vals = None
        while True:
            if vals is not None:
                sleep(vsrc.get_polling_timeout() / 1000)

            vals = vsrc.get_value()

            for device in args.device:
                colors = []
                for i, cpu_percent in enumerate(vals):
                    col3 = ColorUtils.color_lerp(cpu_percent, vsrc_range[1], col_scale[0], col_scale[1])
                    colors.append(ColorUtils.col_triplet_to_hex(col3))

                self.client.set_colors(device, colors)
                if args.verbose:
                    print "Colors updated {}".format(colors)

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

        argsparser.add_argument('-d', '--device', dest='device', nargs='*', action='store', help='set devices', metavar='device_name')
        argsparser.add_argument('-e', '--effect', dest='effect', nargs='?', action='store', help='show effect', metavar='name')

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
            GlightFxApp.handle_experiments(args=args, verbose=args.verbose)
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

        if args.device is None:
            raise "Need at least a device"

        if args.effect == "cpux":
            fx = CpuxEffect(client)

            state = client.get_state()
            try:
                fx.run()
            finally:
                client.set_state(state)


    @staticmethod
    def handle_experiments(args, verbose=False):
        if args.experimental == "test":
            src = CpuLoadSource()
            print src.read_cpu_usage()
        if args.experimental == "color":
            print ColorUtils.col_hex_to_triplet("abcdef")

            rgb = ColorUtils.color_lerp(
                0.5, 1.0,
                ColorUtils.col_hex_to_triplet("000000"),
                ColorUtils.col_hex_to_triplet("ffffff")
            )

            print ColorUtils.col_triplet_to_hex(rgb)


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
