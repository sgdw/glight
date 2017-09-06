#!/usr/bin/env python

'''
  *  The MIT License (MIT)
  *
  *  g2x3 v0.1 Copyright (c) 2016 SGDW
  *
  *  Permission is hereby granted, free of charge, to any person obtaining a copy
  *  of this software and associated documentation files (the "Software"), to deal
  *  in the Software without restriction, including without limitation the rights
  *  to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
  *  copies of the Software, and to permit persons to whom the Software is
  *  furnished to do so, subject to the following conditions:
  *
  *  The above copyright notice and this permission notice shall be included in all
  *  copies or substantial portions of the Software.
  *
  *  THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
  *  IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
  *  FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
  *  AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
  *  LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
  *  OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
  *  SOFTWARE.
  *
  *
  *
  * This software was inspired by:
  *
  * G213Colors by SebiTimeWaster
  * https://github.com/SebiTimeWaster/G213Colors
  *
  * Thank you!
'''

# pylint: disable=C0326

import sys
import array
import json

# PyUSB
import usb.core
import usb.control
import usb.util

# PyUSB
import usb1

import binascii
import argparse
from time import sleep
import traceback

from pydbus import SystemBus, SessionBus
from pydbus.generic import signal
try:
    from gi.repository import GLib
except ImportError:
    import glib as GLib

from threading import Semaphore

app_version = "0.1"

default_time = 1000

# /usr/lib/python2.7/dist-packages/

class UsbConstants(object):
    HID_REQ_SET_REPORT=0x09


class UsbBackend(object):

    TYPE_PYUSB = 'pyusb'
    TYPE_USB1  = 'usb1'

    TYPE_DEFAULT = TYPE_USB1

    def __init__(self, vendor_id, product_id, w_index):
        """"""
        self.verbose = False

        self.device = None  # device resource
        self.is_detached = True

        self.vendor_id  = vendor_id   # The vendor id
        self.product_id = product_id  # The product id
        self.w_index    = w_index     # Interface

        self.supports_interrupts = False

        self.is_detached = False  # If kernel driver needs to be reattached

    def get_usb_device(self):
        """"""
        raise NotImplemented()

    def connect(self, device=None):
        """"""
        raise NotImplemented()

    def disconnect(self):
        """"""
        raise NotImplemented()

    def send_data(self, bm_request_type, bm_request, w_value, data):
        """"""
        pass

    def read_interrupt(self, endpoint, length, callback=None, user_data=None, timeout=0):
        """"""
        pass

    def handle_events(self):
        pass

    def _log(self, msg):
        if self.verbose:
            print(msg)


class UsbBackendPyUsb(UsbBackend):

    def __init__(self, vendor_id, product_id, w_index):
        """"""
        super(UsbBackendPyUsb, self).__init__(vendor_id, product_id, w_index)

    def get_usb_device(self):
        """"""
        return usb.core.find(idVendor = self.vendor_id, idProduct = self.product_id)

    def connect(self, device=None):
        # find G product
        if device is None:
            self.device = self.get_usb_device()
        else:
            self.device = device

        # if not found exit
        if self.device is None:
            raise ValueError("USB device not found!")

        self.digg_info()

        # if a kernel driver is attached to the interface detach it, otherwise no data can be send
        if self.device.is_kernel_driver_active(self.w_index):
            self.device.detach_kernel_driver(self.w_index)
            self.is_detached = True

        return self.device

    def disconnect(self):
        # free device resource to be able to reattach kernel driver
        usb.util.dispose_resources(self.device)
        # reattach kernel driver, otherwise special key will not work
        if self.is_detached:
            self.device.attach_kernel_driver(self.w_index)

    def send_data(self, bm_request_type, bm_request, w_value, data):
        # decode data to binary and send it
        self._log(">> '{}'".format(data))
        self.device.ctrl_transfer(bm_request_type, bm_request, w_value, self.w_index, binascii.unhexlify(data), 1000)

    def read_interrupt(self, endpoint, length, callback=None, user_data=None, timeout=0):
        """"""
        pass

    def digg_info(self):
        print("**digg_info**")
        # set the active configuration. With no arguments, the first
        # configuration will be the active one
        # self.device.set_configuration()

        # get an endpoint instance
        cfg = self.device.get_active_configuration()
        intf = cfg[(0, 0)]

        ep = usb.util.find_descriptor(
            intf,
            # match the first OUT endpoint
            custom_match= \
                lambda e: \
                    usb.util.endpoint_direction(e.bEndpointAddress) == \
                    usb.util.ENDPOINT_OUT)

        print("Config:")
        print(cfg)

        print("Endpoint OUT:")
        print(ep)


class UsbBackendUsb1(UsbBackend):

    def __init__(self, vendor_id, product_id, w_index):
        """"""
        super(UsbBackendUsb1, self).__init__(vendor_id, product_id, w_index)
        self.context = None
        self.interface = None
        self.supports_interrupts = True

    def get_usb_device(self):
        """"""
        self._assert_valid_usb_context()
        return self.context.openByVendorIDAndProductID(
            vendor_id=self.vendor_id,
            product_id=self.product_id,
            skip_on_error=True)

    def connect(self, device=None):
        self._assert_valid_usb_context()

        # find G product
        if device is None:
            self.device = self.get_usb_device()
        else:
            self.device = device

        # if not found exit
        if self.device is None:
            raise ValueError("USB device not found!")

        # if a kernel driver is attached to the interface detach it, otherwise no data can be send
        if self.device.kernelDriverActive(self.w_index):
            self._log("Detaching kernel on interface {}".format(self.w_index))
            self.device.detachKernelDriver(self.w_index)
            self.is_detached = True
        else:
            self._log("Kernel not active on interface {}".format(self.w_index))

        self.interface = self.get_interface()

        return self.device

    def disconnect(self):
        # free device resource to be able to reattach kernel driver
        # usb.util.dispose_resources(self.device)

        try:
            if self.interface is not None:
                self.device.releaseInterface(self.w_index)
        except Exception as ex:
            self._log("Exception while releasing interface: {}".format(ex))
        finally:
            # self.context.
            # self.device.close()
            pass

        # reattach kernel driver, otherwise special key will not work
        if self.is_detached:
            self._log("Attaching kernel on interface {}".format(self.w_index))
            self.device.attachKernelDriver(self.w_index)

        if self.device is not None:
            self.device.close()
            self.device = None

        if self.context is not None:
            self.context.close()
            self.context = None

    def get_interface(self):
        """"""
        return self.device.claimInterface(self.w_index)

    def send_data(self, bm_request_type, bm_request, w_value, data):
        # decode data to binary and send it
        self._log("Send >> '{}'".format(data))
        self.device.controlWrite(bm_request_type, bm_request, w_value, self.w_index, binascii.unhexlify(data), 1000)

    def read_interrupt(self, endpoint, length, callback=None, user_data=None, timeout=0):
        """"""
        transfer = self.device.getTransfer() # type: usb1.USBTransfer
        transfer.setInterrupt(endpoint=endpoint, buffer_or_len=length, callback=callback, user_data=user_data, timeout=timeout)
        transfer.submit()
        return transfer

    def handle_events(self, timeout=0):
        self.context.handleEventsTimeout(timeout)

    def _assert_valid_usb_context(self):
        if self.context is None:
            self.context = usb1.USBContext()


class GDeviceRegistry(object):
    """Enumerates the available G-Devices"""

    STATE_FILE_EXTENSION = ".gstate"

    def __init__(self, backend_type=UsbBackend.TYPE_DEFAULT, verbose=False, strict_filenames=True):
        """"""
        self.verbose = verbose
        self.strict_filenames = strict_filenames
        self.backend_type = backend_type
        self.known_devices = []
        self.init_known_devices()

    def init_known_devices(self):
        self.known_devices = [G203(self.backend_type), G213(self.backend_type)]
        for known_device in self.known_devices:
            known_device.verbose = self.verbose

    def find_devices(self):
        """
        :return: GDevice[]
        """

        found_devices = []
        for known_device in self.known_devices:
            if known_device.exists():
                found_devices.append(known_device)

        return found_devices

    def get_device(self, short_name_filter=None):
        found_devices = self.find_devices()
        for found_device in found_devices:
            if found_device.device_name_short == short_name_filter:
                return found_device
        return None

    def get_state_of_devices(self):
        states = {}
        for known_device in self.known_devices:
            states[known_device.device_name_short] = known_device.device_state.as_dict()
        return states

    def set_state_of_devices(self, states):
        states = {}
        for known_device in self.known_devices:
            if known_device.device_name_short in states:
                known_device.device_state.import_dict(states[known_device.device_name_short])

    def restore_states_of_devices(self):
        for known_device in self.known_devices:
            device_name = known_device.device_name_short
            try:
                known_device.restore_state()
            except Exception as ex:
                print("Could not restore state of device '{}'".format(device_name))
                print("Exception: {}".format(ex))
                if self.verbose:
                    print(traceback.format_exc())

    def load_state_of_devices(self, filename):
        """"""
        state = self.get_state_of_devices()

        fh = open(filename, "r")
        state_json = fh.read()
        fh.close()

        state_data = json.loads(state_json)
        for known_device in self.known_devices:
            device_name = known_device.device_name_short
            if device_name in state_data:
                try:
                    known_device.device_state.import_dict(state_data[device_name])
                except Exception as ex:
                    print("Could not restore state of device '{}'".format(device_name))
                    print("Exception: {}".format(ex))
                    if self.verbose:
                        print(traceback.format_exc())

    def write_state_of_devices(self, filename):
        """"""
        self._assert_valid_state_filename(filename)
        state = self.get_state_of_devices()
        state_json = json.dumps(state, indent=4)

        fh = open(filename, "w")
        fh.write(state_json)
        fh.close()

    def _assert_valid_state_filename(self, filename):
        if self.strict_filenames:
            if not filename.endswith(self.STATE_FILE_EXTENSION):
                raise GDeviceException("Invalid filename! Must end with '{}'".format(self.STATE_FILE_EXTENSION))


class GDeviceState(object):

    def __init__(self):
        """"""
        self.attrs = ["colors", "static", "breathing", "cycling", "brightness", "speed"]
        self.colors = None
        self.static = False
        self.breathing = False
        self.cycling = False
        self.brightness = None
        self.speed = None

    def reset(self):
        self.colors = None
        self.static = False
        self.breathing = False
        self.cycling = False
        self.brightness = None
        self.speed = None

    def resize_colors(self, size):
        if self.colors is None:
            self.colors = []

        clrs_len = len(self.colors)
        if clrs_len < size:
            self.colors.extend([None]*(size-clrs_len))
            clrs_len = len(self.colors)
        return clrs_len

    def set_color_at(self, color, index=0):
        self.resize_colors(index+1)
        self.colors[index] = color

    def import_dict(self, values):
        data = {}
        for attr in self.attrs:
            if attr in values:
                self.__setattr__(attr, values[attr])

    def as_dict(self):
        data = {}
        for attr in self.attrs:
            data[attr] = self.__getattribute__(attr)
        return data

class GValueSpec(object):

    def __init__(self, format, min_value, max_value, default_value=None):
        self.format = format
        self.min_value = min_value
        self.max_value = max_value
        self.default_value = default_value

    def format_color_hex(self, value):
        if value is None:
            value = self.default_value
        value = int(value, 16)
        return self.format_num(value)

    def format_num(self, value):
        if value is None:
            value = self.default_value

        if self.min_value is not None and value < self.min_value:
            value = self.min_value
        elif self.max_value is not None and value > self.max_value:
            value = self.max_value

        return format(value, self.format)


class GDeviceException(Exception):
    """"""


class GDevice(object):
    """Abstract G-Device"""

    def __init__(self, backend_type=UsbBackend.TYPE_DEFAULT):
        """"""
        self.verbose = False;

        self.backend_type = backend_type
        self.backend = None # type: UsbBackend

        self.device_name_short = ""
        self.device_name = ""
        self.device_state = GDeviceState()

        self.id_vendor   = 0x0000  # The vendor id
        self.id_product  = 0x0000  # The product id
        self.w_index     = 0x0000  # Interface
        self.ep_inter    = None    # Interrupt Endpoint (e.g. 0x82)

        self.is_detached = False    # If kernel driver needs to be reattached

        self.bm_request_type = 0x00   # Device specific
        self.bm_request      = 0x00   # Device specific
        self.w_value         = 0x0000 # Device specific

        # capabilities
        self.max_color_fields = 0
        self.can_breathe = False
        self.can_cycle   = False

        # timings
        self.timeout_after_prepare = 0
        self.timeout_after_cmd = 0

        # mutexes
        self.wait_on_interrupt = False
        self.wait_lock = None

        # value specs
        self.field_spec  = GValueSpec("02x", 0, self.max_color_fields, 0)
        self.color_spec  = GValueSpec("06x", 0x000000, 0xffffff, 0xffffff)
        self.speed_spec  = GValueSpec("04x", 0x03e8,   0x4e20,   0x2af8)
        self.bright_spec = GValueSpec("02x", 0x01,     0x64,     0x64)

        # binary commands in hex format
        self.cmd_prepare = None
        self.cmd_color   = "{field}{color}"
        self.cmd_breathe = "{color}{speed}{bright}"
        self.cmd_cycle   = "{speed}{bright}"

        self.interrupt_length = 20

    def _init_backend(self):
        """"""
        if self.backend is None:
            if self.backend_type == UsbBackend.TYPE_PYUSB:
                self.backend = UsbBackendPyUsb(self.id_vendor, self.id_product, self.w_index)
            elif self.backend_type == UsbBackend.TYPE_USB1:
                self.backend = UsbBackendUsb1(self.id_vendor, self.id_product, self.w_index)
            else:
                raise ValueError("Unknown Backend {}".format(self.backend_type))

    def restore_state(self):
        """"""
        if self.exists():
            if self.device_state is not None:
                has_state = self.device_state.static or self.device_state.breathing or self.device_state.cycling

                if has_state:
                    if self.device_state.static and self.device_state.colors is not None:
                        self.connect()
                        try:
                            for i, color in enumerate(self.device_state.colors):
                                if color is not None:
                                    self.send_color_command(color, i)
                        finally:
                            self.disconnect()

                    elif self.device_state.breathing:
                        self.connect()
                        try:
                            if self.device_state.colors is not None and len(self.device_state.colors) > 0:
                                self.send_breathe_command(
                                        self.device_state.colors[0],
                                        self.device_state.speed,
                                        self.device_state.brightness)
                        finally:
                            self.disconnect()

                    elif self.device_state.cycling:
                        self.connect()
                        try:
                            self.send_cycle_command(
                                    self.device_state.speed,
                                    self.device_state.brightness)
                        finally:
                            self.disconnect()

    def exists(self):
        """"""
        self._init_backend()
        return self.backend.get_usb_device() is not None

    def connect(self):
        """"""
        self._init_backend()
        self.backend.connect()

    def disconnect(self):
        """"""
        self.backend.disconnect()

    def on_interrupt(self, sender):
        self.wait_on_interrupt = False
        self._log("Received interrupt from sender: {}".format(sender))

    def _can_do_interrup(self):
        return self.backend.supports_interrupts and self.ep_inter is not None

    def begin_interrupt(self):
        if self._can_do_interrup():
            self.backend.read_interrupt(endpoint=self.ep_inter, length=self.interrupt_length, callback=self.on_interrupt,
                                        user_data=None, timeout=5000)
            self.wait_on_interrupt = True

    def end_interrupt(self): # ChangeMe: stupid busy wait ...
        if self._can_do_interrup():
            max_iter = 10000
            while self.wait_on_interrupt:
                max_iter = max_iter-1
                self.backend.handle_events()
                if max_iter == 0:
                    self._log("Did not get a interrupt response in time")
                    # yield # hack ... works but why?
                    return

    def send_data(self, data):
        if self.cmd_prepare is not None:
            self.begin_interrupt()
            self.backend.send_data(self.bm_request_type, self.bm_request, self.w_value, self.cmd_prepare)
            sleep(self.timeout_after_prepare)
            self.end_interrupt()

        self.begin_interrupt()
        self.backend.send_data(self.bm_request_type, self.bm_request, self.w_value, data)
        sleep(self.timeout_after_cmd)
        self.end_interrupt()

    def send_colors_command(self, colors):
        """"""
        if len(colors) <= 1:
            if len(colors) == 1:
                color = colors[0]
            else:
                color = "FFFFFF"

            self.send_color_command(color, 0)

        elif len(colors) > 1:
            for i in range(0, min(len(colors), self.max_color_fields)):
                self.send_color_command(colors[i], i + 1)

    def send_color_command(self, color_hex, field=0):
        GDevice.assert_valid_color(color_hex)
        self._log("Set color '{}' at slot {}".format(color_hex, field))
        self.send_data(self.cmd_color.format(
                            field=self.field_spec.format_num(field),
                            color=self.color_spec.format_color_hex(color_hex)))

        self.device_state.reset()
        self.device_state.static = True
        self.device_state.set_color_at(color_hex, field)

    def send_breathe_command(self, color_hex, speed, brightness=None):
        if not self.can_breathe:
            raise GDeviceException("Device does not support the breathe effect")

        if brightness is None:
            brightness = self.bright_spec.max_value
        GDevice.assert_valid_color(color_hex)

        self.send_data(self.cmd_breathe.format(
                            color=self.color_spec.format_color_hex(color_hex),
                            speed=self.speed_spec.format_num(speed),
                            bright=self.bright_spec.format_num(brightness)))

        self.device_state.reset()
        self.device_state.breathing = True
        self.device_state.speed = speed
        self.device_state.brightness = brightness
        self.device_state.set_color_at(color_hex)

    def send_cycle_command(self, speed, brightness=None):
        if not self.can_cycle:
            raise GDeviceException("Device does not support the cycle effect")

        if brightness is None:
            brightness = self.bright_spec.max_value

        self.send_data(self.cmd_cycle.format(
                                speed=self.speed_spec.format_num(speed),
                                bright=self.bright_spec.format_num(brightness)))

        self.device_state.reset()
        self.device_state.cycling = True
        self.device_state.speed = speed
        self.device_state.brightness = brightness

    def _log(self, msg):
        if self.verbose:
            print(msg)

    @staticmethod
    def assert_valid_color(color_hex):
        if not GDevice.is_valid_color(color_hex):
            raise ValueError("Color '{}' is not a valid color string in hex representation (e.g. 'F0D3AA')".format(color_hex))

    @staticmethod
    def is_valid_color(data):
        """"""
        if len(data) != 6:
            return False

        try:
            binascii.unhexlify(data)
        except:
            return False

        return True


class G203(GDevice):
    """Logitech G203 Mouse Support"""

    def __init__(self, backend_type=UsbBackend.TYPE_DEFAULT):
        """"""
        super(G203, self).__init__(backend_type)

        self.device_name_short = "g203"
        self.device_name = "G203 Mouse"

        self.id_vendor   = 0x046d  # The id of the Logitech company
        self.id_product  = 0xc084  # The id of the G203
        self.w_index     = 0x0001  # Interface 1
        self.ep_inter    = 0x82    # Interrupt Endpoint

        self.is_detached = False    # If kernel driver needs to be reattached

        self.bm_request_type = usb.util.CTRL_OUT | usb.util.CTRL_RECIPIENT_INTERFACE | usb.util.CTRL_TYPE_CLASS # 0x21
        self.bm_request      = UsbConstants.HID_REQ_SET_REPORT # 0x09
        self.w_value         = 0x0211 # ???

        # capabilities
        self.max_color_fields = 0
        self.can_breathe = True
        self.can_cycle   = True

        # timings
        self.timeout_after_prepare = 0.01
        self.timeout_after_cmd = 0.01

        # value specs
        self.field_spec  = GValueSpec("02x", 0, self.max_color_fields, 0)
        self.color_spec  = GValueSpec("06x", 0x000000, 0xffffff, 0xffffff)
        self.speed_spec  = GValueSpec("04x", 0x03e8,   0x4e20,   0x2af8)
        self.bright_spec = GValueSpec("02x", 0x01,     0x64,     0x64)

        # binary commands in hex format
        self.cmd_prepare = "10ff0e0d000000"
        #                   10ff0e0d000000
        #                   10ff0f4d000000 # another prepare command?
        self.cmd_color   = "11ff0e3d{field}01{color}0200000000000000000000"
        #                   11ff0e3d00018000ff0200000000000000000000 # similar to G213
        #                           []  RRGGBB
        #                           field
        self.cmd_breathe = "11ff0e3d0003{color}{speed}00{bright}00000000000000"
        #                   11ff0e3d00038000ff2af8000100000000000000 # darkest
        #                   11ff0e3d00038000ff2af8006400000000000000 # brightest
        #                               RRGGBB[..]  []
        #                                     speed brightness
        self.cmd_cycle   = "11ff0e3d00020000000000{speed}{bright}000000000000"
        #                   11ff0e3d00020000000000000fa064000000000000
        #                   11ff0e3d000200000000002af864000000000000
        #                                         [..][]
        #                                         |   brightness
        #                                         speed
        #                   11ff0e3d000200000000002af801000000000000 # darkest
        #                   11ff0e3d0002000000000003e864000000000000 # fastest
        #                   11ff0e3d000200000000004e2064000000000000 # slowest


class G213(GDevice):
    """Logitech G213 Keyboard Support"""

    def __init__(self, backend_type=UsbBackend.TYPE_DEFAULT):
        """"""
        super(G213, self).__init__(backend_type)

        self.device_name_short = "g213"
        self.device_name = "G213 Keyboard"

        self.id_vendor   = 0x046d  # The id of the Logitech company
        self.id_product  = 0xc336  # The id of the G213
        self.w_index     = 0x0001  # Interface 1
        self.ep_inter    = 0x82    # Interrupt Endpoint

        self.is_detached = False    # If kernel driver needs to be reattached

        self.bm_request_type = usb.util.CTRL_OUT | usb.util.CTRL_RECIPIENT_INTERFACE | usb.util.CTRL_TYPE_CLASS # 0x21
        self.bm_request      = UsbConstants.HID_REQ_SET_REPORT # 0x09
        self.w_value         = 0x0211 # ???

        # capabilities
        self.max_color_fields = 6
        self.can_breathe = True
        self.can_cycle   = True

        # timings
        self.timeout_after_prepare = 0.01
        self.timeout_after_cmd = 0.01

        # value specs
        self.field_spec  = GValueSpec("02x", 0, self.max_color_fields, 0)
        self.color_spec  = GValueSpec("06x", 0x000000, 0xffffff, 0xffffff)
        self.speed_spec  = GValueSpec("04x", 0x03e8,   0x4e20,   0x2af8)
        self.bright_spec = GValueSpec("02x", 0x01,     0x64,     0x64)

        # binary commands in hex format
        self.cmd_prepare = "11ff0c0a00000000000000000000000000000000"
        self.cmd_color   = "11ff0c3a{field}01{color}0200000000000000000000"
        #                   11ff0e3a00018000ff0200000000000000000000 # similar to G203
        #                           []  RRGGBB
        #                           field
        self.cmd_breathe = "11ff0c3a0002{color}{speed}00{bright}00000000000000"
        #                   11ff0e3d00038000ff2af8006400000000000000 # brightest
        #                               RRGGBB[..]  []
        #                                     speed brightness
        self.cmd_cycle   = "11ff0c3a0003ffffff0000{speed}{bright}000000000000"
        #                   11ff0e3d000200000000002af864000000000000
        #                                         [..][]
        #                                         |   brightness
        #                                         speed


class GlightCommon(object):

    ARRAY_DELIM = ","

    def get_bus(self):
        return SystemBus()
        # return SessionBus()

    def load_state(self):
        pass

    def save_state(self):
        pass

    def list_devices(self):
        pass

    def set_color_at(self, device, color, field):
        pass

    def set_colors(self, device, colors):
        pass

    def set_breathe(self, device, color, speed, brightness):
        pass

    def set_cycle(self, device, speed, brightness):
        pass

    def echo(self, s):
        pass

    def quit(self):
        pass


class GlightService(GlightCommon):
    """
      <node>
        <interface name='de.sgdw.linux.glight'>
          <method name='list_devices'>
            <arg type='as' name='resp'  direction='out'/>
          </method>
          <method name='load_state'>
          </method>
          <method name='save_state'>
          </method>
          <method name='set_color_at'>
            <arg type='s' name='device' direction='in'/>
            <arg type='s' name='color'  direction='in'/>
            <arg type='q' name='field'  direction='in'/>
          </method>
          <method name='set_colors'>
            <arg type='s'  name='device' direction='in'/>
            <arg type='as' name='colors' direction='in'/>
          </method>
          <method name='set_breathe'>
            <arg type='s' name='device' direction='in'/>
            <arg type='s' name='color'  direction='in'/>
            <arg type='x' name='speed'  direction='in'/>
            <arg type='x' name='brightness' direction='in'/>
          </method>
          <method name='set_cycle'>
            <arg type='s' name='device' direction='in'/>
            <arg type='x' name='speed'  direction='in'/>
            <arg type='x' name='brightness' direction='in'/>
          </method>
          <method name='echo'>
            <arg type='x' name='s' direction='in'/>
          </method>
          <method name='quit'/>
        </interface>
      </node>
    """

    # see: https://github.com/LEW21/pydbus/blob/master/doc/tutorial.rst

    bus_name = "de.sgdw.linux.glight"
    bus_path = "/" + bus_name.replace(".", "/")

    def __init__(self, state_file=None, verbose=False):
        """"""
        self.state_file = state_file
        self.verbose = verbose

        self.loop = None
        self.bus  = None
        self.lock = Semaphore()

        self.device_registry = None # type: GDeviceRegistry
        self.init_backend()

    def run(self):
        """"""
        self.prepare_run()
        self.loop = GLib.MainLoop()

        self.bus = self.get_bus()
        self.bus.publish(self.bus_name, self)

        self.loop.run()

    def init_backend(self):
        self.device_registry = GDeviceRegistry()

    def prepare_run(self):
        if self.state_file is not None:
            self.load_state()

    def open_device(self, device_name):
        self.lock.acquire()
        device = self.device_registry.get_device(short_name_filter=device_name) # type: GDevice
        if device is not None:
            device.connect()
        return device

    def close_device(self, device):
        """
        :param device: GDevice
        :return:
        """
        if device is not None:
            device.disconnect()

        self.lock.release()

    def unmarshall_num_par(self, num_val, if_not_set=None):
        """None is not allowed over dbus, so a negative value is the None equivalent over the wire"""
        if num_val < 0:
            return if_not_set
        return num_val

    # Public
    def load_state(self):
        if self.state_file is not None:
            try:
                self.device_registry.load_state_of_devices(self.state_file)
                self.device_registry.restore_states_of_devices()
            except Exception as ex:
                print("Failed to restore state '{}'".format(ex.message))
                if self.verbose:
                    print("Exception: {}".format(ex))
                    print(traceback.format_exc())

    # Public
    def save_state(self):
        if self.state_file is not None:
            try:
                self.device_registry.write_state_of_devices(self.state_file)
            except Exception as ex:
                print("Failed to save state '{}'".format(ex.message))
                if self.verbose:
                    print("Exception: {}".format(ex))
                    print(traceback.format_exc())
                raise GDeviceException("Failed to save state")
        else:
            raise GDeviceException("No state file configured")

    # Public
    def list_devices(self):
        devices = list(map((lambda d: d.device_name_short), self.device_registry.find_devices()))
        print("list_devices() := {}".format(devices))
        self.lock.release()
        return devices

    # Public
    def set_color_at(self, device_name, color, field):
        device = self.open_device(device_name)
        try:
            if device is not None:
                print("set_color_at('{}', '{}', {})".format(device_name, color, field))
                device.send_color_command(color, field)
            else:
                print("Device '{}' not found".format(device_name))
        finally:
            self.close_device(device)

    # Public
    def set_colors(self, device_name, colors):
        device = self.open_device(device_name)
        try:
            if device is not None:
                print("set_colors('{}', {})".format(device_name, colors))
                device.send_colors_command(colors)
            else:
                print("Device '{}' not found".format(device_name))
        finally:
            self.close_device(device)

    # Public
    def set_breathe(self, device_name, color, speed, brightness):
        device = self.open_device(device_name)
        try:
            if device is not None:
                print("set_breathe('{}', '{}', {}, {})".format(device_name, color, speed, brightness))
                device.send_breathe_command(
                    color_hex=color,
                    speed=self.unmarshall_num_par(speed),
                    brightness=self.unmarshall_num_par(brightness))
            else:
                print("Device '{}' not found".format(device_name))
        finally:
            self.close_device(device)

    # Public
    def set_cycle(self, device_name, speed, brightness):
        device = self.open_device(device_name)
        try:
            if device is not None:
                print("set_cycle('{}', {}, {})".format(device_name, speed, brightness))
                device.send_cycle_command(
                    speed=self.unmarshall_num_par(speed),
                    brightness=self.unmarshall_num_par(brightness))
            else:
                print("Device '{}' not found".format(device_name))
        finally:
            self.close_device(device)

    # Public
    def echo(self, s):
        """returns whatever is passed to it"""
        self.lock.acquire()
        print("echo('{}')".format(s))
        self.lock.release()
        return s

    # Public
    def quit(self):
        """removes this object from the DBUS connection and exits"""
        self.lock.acquire()
        if self.loop is not None:
            self.loop.quit()
        self.lock.release()


class GlightClient(GlightCommon):

    def __init__(self, verbose=False):
        """"""
        self.verbose=verbose
        self.loop = None
        self.bus  = None
        self.proxy = None # type: GlightCommon

    def connect(self):
        self.bus = self.get_bus()
        self.proxy = self.bus.get(GlightService.bus_name)

    def start_loop(self):
        if self.loop is None:
            self.loop = GLib.MainLoop()
        self.loop.run()

    def stop_loop(self):
        if self.loop is not None:
            self.loop.quit()

    def marshall_num_par(self, num_val, if_none=-1):
        """None is not allowed over dbus, so -1 is the None equivalent over the wire"""
        if num_val is None:
            return if_none
        return num_val

    def load_state(self):
        self.proxy.load_state()

    def save_state(self):
        self.proxy.save_state()

    def list_devices(self):
        return self.proxy.list_devices()

    def set_color_at(self, device, color, field):
        self._log("Setting color at device '{}' to {} at field:{}".format(device, color, field))
        self.proxy.set_color_at(device, color, field)

    def set_colors(self, device, colors):
        self._log("Setting colors at device '{}' to {}".format(device, colors))
        self.proxy.set_colors(device, colors)
        pass

    def set_breathe(self, device, color, speed, brightness):
        self._log("Setting breathe at device '{}' to color:'{}' speed:{} brightness:{}".format(device, color, speed, brightness))
        self.proxy.set_breathe(
            device,
            color,
            self.marshall_num_par(speed),
            self.marshall_num_par(brightness))

    def set_cycle(self, device, speed, brightness):
        self._log("Setting cycle at device '{}' to speed:{} brightness:{}".format(device, speed, brightness))
        self.proxy.set_cycle(
            device,
            self.marshall_num_par(speed),
            self.marshall_num_par(brightness))

    def _log(self, msg):
        if self.verbose:
            print(msg)

    def subscribe(self, dbus_filter, callback):
        """
        :param dbus_filter:
        :param callback:
        :return:

            on_signal_emission(self, *args) -> Data str(args[4][0])
        """
        self.bus.subscribe(object=dbus_filter, signal_fired=callback)

    def do(self):

        print(GlightService.bus_name)
        print(GlightService.bus_path)

        device = "g213"

        print('CALL self.list_devices()')
        print(self.list_devices())

        print('CALL self.set_color_at("FFEEDD", 5)')
        print(self.set_color_at(device, "FFEEDD", 5))

        print('CALL self.set_colors(["DEADBE", "4FDEAD"])')
        print(self.set_colors(device, ["DEADBE", "4FDEAD"]))

        print('CALL self.set_breathe("CCDDEE", 2000)')
        print(self.set_breathe(device, "CCDDEE", 2000))

        print('CALL self.set_cycle(4000)')
        print(self.set_cycle(device, 4000))

        print('CALL self.set_color_at("ddeeff", 0)')
        print(self.set_color_at(device, "ddeeff", 0))


class GlightApp(object):

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
            description='Changes the colors on some Logitech devices (V' + app_version + ')', add_help=False)

        argsparser.add_argument('-d', '--device',  dest='device',  nargs='?', action='store', help='set device', metavar='device_name')
        argsparser.add_argument('-c', '--color',   dest='colors',  nargs='+', action='store', help='set color(s)', metavar='color')
        argsparser.add_argument('-x', '--cycle',   dest='cycle',   nargs='+', action='store', help='set time',  metavar='speed, brightness')
        argsparser.add_argument('-b', '--breathe', dest='breathe', nargs='+', action='store', help='set breathing animation', metavar='color, speed, brightness')
        argsparser.add_argument('--backend',       dest='backend', nargs=1,   action='store', help='set backend (usb1, pyusb)', metavar='(usb1|pyusb)')

        argsparser.add_argument('--state-file',    dest='state_file', nargs='?', action='store', help='file where the state is saved', metavar='filename')
        argsparser.add_argument('--load-state',    dest='load_state', action='store_const', const=True, help='load state from state file')
        argsparser.add_argument('--save-state',    dest='save_state', action='store_const', const=True, help='save state to state file')

        argsparser.add_argument('-C', '--client',  dest='client',  action='store_const', const=True, help='run as client')
        argsparser.add_argument('--service',       dest='service', action='store_const', const=True, help='run as service')
        argsparser.add_argument('-l', '--list',    dest='do_list', action='store_const', const=True, help='list devices')
        argsparser.add_argument('-v', '--verbose', dest='verbose', action='store_const', const=True, help='be verbose')
        argsparser.add_argument('-h', '--help',    dest='help',    action='store_const', const=True, help='show help')

        argsparser.add_argument('--experimental', dest='experimental', nargs='*', action='store',
                                help='experimental features')

        return argsparser

    @staticmethod
    def get_args():
        return GlightApp.get_argsparser().parse_args()

    @staticmethod
    def handle_args(args=None, verbose=None):
        """"""
        if args is None:
            args=GlightApp.get_args()

        if args.help:
            GlightApp.get_argsparser().print_help()
            print()
            sys.exit(0)

        # if args.verbose:
        #     print(args)

        if verbose is None:
            verbose = args.verbose or False

        if args.experimental is not None:
            GlightApp.handle_experimental_features(args=args, verbose=args.verbose)
        else:
            if args.service or args.client:
                GlightApp.handle_client_service(args=args, verbose=args.verbose)
            else:
                GlightApp.handle_device_control(args=args, verbose=args.verbose)

    @staticmethod
    def handle_client_service(args, verbose=False):
        """"""

        if args.service:
            srv = GlightService(state_file=args.state_file, verbose=verbose)
            srv.run()
            sys.exit(0) # Ends here

        elif args.client:
            client = GlightClient(verbose=verbose)
            client.connect()

            # Listing devices
            if args.do_list:
                devices = client.list_devices()
                print("{} devices:".format(len(devices)))
                for i, device in enumerate(devices):
                    print("[{}] {}".format(i, device))

            # Setting colors
            if args.colors is not None:
                client.set_colors(
                            device=args.device,
                            colors=args.colors)

            # Setting breathing
            if args.breathe is not None:
                client.set_breathe(
                    device=args.device,
                    color=GlightApp.get_val_at(args.breathe, 0),
                    speed=GlightApp.get_num_at(args.breathe, 1),
                    brightness=GlightApp.get_num_at(args.breathe, 2))

            # Setting cycle
            if args.cycle is not None:
                client.set_cycle(
                    device=args.device,
                    speed=GlightApp.get_num_at(args.cycle, 0),
                    brightness=GlightApp.get_num_at(args.cycle, 1))

            # Saving state
            if args.save_state:
                if args.state_file is not None:
                    print("Warning: parameter '--state-file' is not supported in client mode. State will be saved by the service.")
                client.save_state()

    @staticmethod
    def handle_device_control(args, verbose=False):
        """"""
        backend_type = UsbBackend.TYPE_DEFAULT
        if args.backend is not None:
            backend_type = args.backend
        if verbose:
            print("Using backend '{}'".format(backend_type))

        gdr = GDeviceRegistry(backend_type, verbose=verbose)
        found_devices = gdr.find_devices()
        device = None # type: GDevice

        if args.load_state and args.state_file is not None:
            gdr.load_state_of_devices(args.state_file)
            gdr.restore_states_of_devices()

        if args.do_list:
            print("{} devices found:".format(len(found_devices)))
            i = 0
            for found_device in found_devices:
                i = i + 1
                print("[{}] {}".format(i, found_device.device_name))

        if args.device is not None:
            for found_device in found_devices:
                if found_device.device_name_short == args.device:
                    device = found_device
                    break

            if device is not None:
                if verbose:
                    print("Using device '{}' ({})".format(device.device_name, device.device_name_short))
            else:
                print("Device '{}' not found".format(args.device))

        if device is not None:
            device.verbose = verbose
            device.backend.verbose = verbose
            try:
                if verbose:
                    print("Connecting to device '{}'".format(device.device_name, device.backend.device))

                # Start communicate to device ...
                device.connect()

                # Setting colors
                if args.colors is not None:
                    device.send_colors_command(args.colors)

                # Setting breathing
                if args.breathe is not None:
                    device.send_breathe_command(
                        color_hex  = GlightApp.get_val_at(args.breathe, 0),
                        speed      = GlightApp.get_num_at(args.breathe, 1),
                        brightness = GlightApp.get_num_at(args.breathe, 2))

                # Setting cycle
                if args.cycle is not None:
                    device.send_cycle_command(
                        speed      = GlightApp.get_num_at(args.cycle, 0),
                        brightness = GlightApp.get_num_at(args.cycle, 1))

            finally:
                if verbose:
                    print("Disconnecting from device '{}'".format(device.device_name))
                device.disconnect()

            # print("State:")
            # print(gdr.get_state_of_devices())

        if args.save_state and args.state_file is not None:
            gdr.write_state_of_devices(args.state_file)


    @staticmethod
    def handle_experimental_features(args, verbose=False):
        """"""
        for experiment in args.experimental:
            if experiment == 'dbus-service':
                srv = GlightService()
                srv.run()
                sys.exit(0)

            elif experiment == 'dbus-client':
                client = GlightClient()
                client.connect()
                client.do()

            else:
                print("Unknown experimental feature '{}'".format(experiment))
                sys.exit(2)


if __name__ == "__main__":

    # App -----------------------------------------
    # here we go ...

    try:

        GlightApp.handle_args()

    except Exception as ex:
        print("Exception: {}".format(ex))
        print(traceback.format_exc())
        sys.exit(1)
    finally:
        pass
