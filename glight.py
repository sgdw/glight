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
  * This software is base on:
  *
  * G213Colors by SebiTimeWaster
  * https://github.com/SebiTimeWaster/G213Colors
  *
  * Thank you!
'''

# pylint: disable=C0326

import sys

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

from os import stat

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
        self.context = usb1.USBContext()
        self.interfaces = []
        self.supports_interrupts = True

    def get_usb_device(self):
        """"""
        return self.context.openByVendorIDAndProductID(
            vendor_id=self.vendor_id,
            product_id=self.product_id,
            skip_on_error=True)

    def connect(self, device=None):

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
            self.device.detachKernelDriver(self.w_index)
            self.is_detached = True

        self.claim_interface(1)

        return self.device

    def disconnect(self):
        self._log("Disconnecting device")

        try:
            if self.interfaces is not None:
                # self.interface
                for interface in self.interfaces:
                    self._log("Releasing interface {}".format(self.w_index))
                    self.device.releaseInterface(self.w_index)
        except Exception as ex:
            self._log("Exception while releasing interface: {}".format(ex))
        finally:
            # self._log("Closing device")
            # self.device.close()
            pass

        # reattach kernel driver, otherwise special key will not work
        if self.is_detached:
            self._log("Attaching kernel driver for interface {}".format(self.w_index))
            self.device.attachKernelDriver(self.w_index)

        # self.device.close()
        # self.context.close()

    def claim_interface(self, w_index=None):
        """"""
        if w_index is None:
            w_index = self.w_index

        self.interfaces.append(w_index)
        return self.device.claimInterface(w_index)

    def send_data(self, bm_request_type, bm_request, w_value, data):
        # decode data to binary and send it
        self._log("Send >> '{}'".format(data))
        self.device.controlWrite(bm_request_type, bm_request, w_value, self.w_index, binascii.unhexlify(data), 1000)

    def handle_events(self, timeout=0):
        self.context.handleEventsTimeout(timeout)
        # self.context.handleEvents()

class GDeviceRegistry(object):
    """Enumerates the available G-Devices"""

    def __init__(self, backend_type=UsbBackend.TYPE_DEFAULT):
        """"""
        self.known_devices = [G203(backend_type), G213(backend_type)]

    def find_devices(self):
        """
        :return: GDevice[]
        """

        found_devices = []
        for known_device in self.known_devices:
            if known_device.exists():
                found_devices.append(known_device)

        return found_devices


class GDevice(object):
    """Abstract G-Device"""

    def __init__(self, backend_type=UsbBackend.TYPE_DEFAULT):
        """"""
        self.verbose = False;

        self.backend_type = backend_type
        self.backend = None # type: UsbBackend

        self.device_name_short = ""
        self.device_name = ""

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

        # timings
        self.timeout_after_prepare = 0
        self.timeout_after_cmd = 0

        # mutexes
        self.wait_on_interrupt = False
        self.wait_lock = None

        # binary commands in hex format
        self.cmd_prepare = None
        self.cmd_color   = "{}{}"
        self.cmd_breathe = "{}{}"
        self.cmd_cycle   = "{}"

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

            self.backend.verbose = self.verbose

    def exists(self):
        """"""
        self._init_backend()
        return self.backend.get_usb_device() is not None

    def connect(self, device=None):
        """"""
        self._init_backend()
        self.backend.connect()

    def disconnect(self):
        """"""
        self.backend.disconnect()

    def on_interrupt(self, sender):
        self.wait_on_interrupt = False
        self._log("Received interrupt from sender: {}".format(sender))

    def _can_do_interrupt(self):
        return self.backend.supports_interrupts and self.ep_inter is not None

    def begin_interrupt(self):
        if self._can_do_interrupt():
            self._log("Sending interrupt to endpoint {}".format(hex(self.ep_inter)))
            self.backend.read_interrupt(endpoint=self.ep_inter, length=self.interrupt_length, callback=self.on_interrupt,
                                        user_data=None, timeout=5000)
            self.wait_on_interrupt = True
        else:
            self._log("Not waiting for an interrupt (supports_interrupts={}; ep_inter={})".format(self.backend.supports_interrupts, self.ep_inter))

    def end_interrupt(self): # ChangeMe: stupid busy wait ...
        if self._can_do_interrupt():
            self._log("Waiting for an interrupt")
            max_iter = 100000
            while self.wait_on_interrupt:
                max_iter = max_iter-1
                # self.backend.handle_events()
                if max_iter == 0:
                    self._log("Did not get a interrupt response in time")
                    yield # hack ... works but why?
                    return

            self._log("Finished waiting for an interrupt")

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
                color = args.colors[0]
            else:
                color = "FFFFFF"

            self.send_color_command(color, 0)

        elif len(colors) > 1:
            for i in range(0, min(len(colors), self.max_color_fields)):
                self.send_color_command(colors[i], i + 1)

    def send_color_command(self, color_hex, field=0):
        GDevice.assert_valid_color(color_hex)
        self._log("Set color '{}' at slot {}".format(color_hex, field))
        self.send_data(self.cmd_color.format(str(format(field, '02x')), color_hex))

    def send_breathe_command(self, color_hex, speed):
        GDevice.assert_valid_color(color_hex)
        self.send_data(self.cmd_breathe.format(color_hex, str(format(speed, '04x'))))

    def send_cycle_command(self, speed):
        self.send_data(self.cmd_cycle.format(str(format(speed, '04x'))))

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

        # timings
        self.timeout_after_prepare = 0.01
        self.timeout_after_cmd = 0.01

        # binary commands in hex format
        self.cmd_prepare = "10ff0e0d000000"
        #                   10ff0e0d000000
        #                   10ff0f4d000000 # another prepare command?
        self.cmd_color   = "11ff0e3d{}01{}0200000000000000000000"
        #                   11ff0e3d00018000ff0200000000000000000000 # similar to G213
        #                               RRGGBB
        self.cmd_breathe = "11ff0e3d0003{}{}006400000000000000"
        #                   11ff0e3d00038000ff2af8000100000000000000 # darkest
        #                   11ff0e3d00038000ff2af8006400000000000000 # brightest
        #                               RRGGBB
        self.cmd_cycle   = "11ff0e3d00020000000000{}64000000000000"
        #                   11ff0e3d000200000000002af864000000000000
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

        # timings
        self.timeout_after_prepare = 0.01
        self.timeout_after_cmd = 0.01

        # binary commands in hex format
        self.cmd_prepare = "11ff0c0a00000000000000000000000000000000"
        self.cmd_color   = "11ff0c3a{}01{}0200000000000000000000"
        self.cmd_breathe = "11ff0c3a0002{}{}006400000000000000"
        self.cmd_cycle   = "11ff0c3a0003ffffff0000{}64000000000000"


class GlightService(object):
    """
      <node>
        <interface name='net.lew21.pydbus.ClientServerExample'>
          <method name='EchoString'>
            <arg type='s' name='a' direction='in'/>
            <arg type='s' name='response' direction='out'/>
          </method>
          <method name='Quit'/>
          <property name="SomeProperty" type="s" access="readwrite">
            <annotation name="org.freedesktop.DBus.Property.EmitsChangedSignal" value="true"/>
          </property>
        </interface>
      </node>
    """

    # see: https://github.com/LEW21/pydbus/blob/master/doc/tutorial.rst

    PropertiesChanged = signal()

    bus_name = "net.lew21.pydbus.ClientServerExample"
    bus_path = "/" + bus_name.replace(".", "/")

    def __init__(self):
        """"""
        self._someProperty = "initial value"
        self.loop = None

    def run(self):
        """"""
        self.loop = GLib.MainLoop()

        bus = SessionBus()
        bus.publish(self.bus_name, self)

        self.loop.run()

    # Implementation below
    def EchoString(self, s):
        """returns whatever is passed to it"""
        print("EchoString('{}')".format(s))
        return s

    def Quit(self):
        """removes this object from the DBUS connection and exits"""
        print("Quit()")
        if self.loop is not None:
            self.loop.quit()

    @property
    def SomeProperty(self):
        return self._someProperty

    @SomeProperty.setter
    def SomeProperty(self, value):
        self._someProperty = value
        self.PropertiesChanged(self.bus_name, {"SomeProperty": self.SomeProperty}, [])


class GlightClient(object):

    def __init__(self):
        """"""

        self.loop = None;

    def do(self):

        print(GlightService.bus_name)
        print(GlightService.bus_path)

        # get the session bus
        bus = SessionBus()

        self.loop = GLib.MainLoop()

        # get the object
        the_object = bus.get(GlightService.bus_name)

        reply = the_object.EchoString("test 123")
        print(reply)

        dbus_filter = GlightService.bus_path
        bus.subscribe(object=dbus_filter, signal_fired=self.on_signal_emission)

        the_object.SomeProperty = "Mae was here"

        # the_object.Quit()

        self.loop.run()

    def on_signal_emission(self, *args):
        """
        Callback on emitting signal from server
        """
        print("Message: ", args)
        print("Data: ", str(args[4][0]))

        if self.loop is not None:
            self.loop.quit()

class GlightApp(object):

    @staticmethod
    def handle_device_control(args, verbose=False):
        """"""
        backend_type = UsbBackend.TYPE_DEFAULT
        if args.backend is not None:
            backend_type = args.backend
        if verbose:
            print("Using backend '{}'".format(backend_type))

        gdr = GDeviceRegistry(backend_type)
        found_devices = gdr.find_devices()
        device = None # type: GDevice

        if args.do_list:
            print("{} devices found:".format(len(found_devices)))
            i = 0
            for found_device in found_devices:
                i = i + 1
                print("[{}] {}".format(i, found_device.device_name))

        if args.device is None:
            print("No device selected!")
        else:
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

                # setting breathing
                if args.breathe is not None and len(args.breathe) > 0:
                    speed = default_time
                    if len(args.breathe) > 1:
                        speed = int(args.breathe[1])
                    device.send_breathe_command(args.breathe[0], speed)

                # Set cycle
                if args.cycle is not None and len(args.cycle) > 0:
                    speed = int(args.cycle[0])
                    device.send_cycle_command(speed)

            finally:
                if verbose:
                    print("Disconnecting from device '{}'".format(device.device_name))
                device.disconnect()


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
                client.do()

            else:
                print("Unknown experimental feature '{}'".format(experiment))
                sys.exit(2)


if __name__ == "__main__":

    # Args ----------------------------------------

    argsparser = argparse.ArgumentParser(description='Changes the colors on some Logitech devices (V' + app_version + ')', add_help=False)
    # argsparser.add_argument('arguments',        type=str, nargs='?', help='keywords used to search', metavar='ARGUMENT')
    argsparser.add_argument('-d', '--device',   dest='device',  nargs='?', action='store', help='set device', metavar='device_name')
    argsparser.add_argument('-c', '--color',    dest='colors',  nargs='*', action='store', help='set color(s)', metavar='color')
    argsparser.add_argument('-x', '--cycle',    dest='cycle',   nargs=1,   action='store', help='set time', metavar='speed')
    argsparser.add_argument('-b', '--breathe',  dest='breathe', nargs=2,   action='store', help='set breathing animation', metavar=('color', 'speed'))
    argsparser.add_argument('--backend',        dest='backend', nargs='?', action='store', help='set backend (usb1, pyusb)', metavar='(usb1|pyusb)')
    argsparser.add_argument('-l', '--list',     dest='do_list', action='store_const', const=True, help='list devices')
    argsparser.add_argument('-v', '--verbose',  dest='verbose', action='store_const', const=True, help='be verbose')
    argsparser.add_argument('-h', '--help',     dest='help',    action='store_const', const=True, help='show help')

    argsparser.add_argument('--experimental', dest='experimental', nargs='*', action='store', help='experimental features')

    args = argsparser.parse_args()

    if args.help:
        argsparser.print_help()
        print()
        sys.exit(0)

    if args.verbose:
        print(args)

    try:
        if args.experimental is not None:
            GlightApp.handle_experimental_features(args=args, verbose=args.verbose)
        else:
            GlightApp.handle_device_control(args=args, verbose=args.verbose)

        # ################################################################################################

    except Exception as ex:
        print("Exception: {}".format(ex))
        print(traceback.format_exc())
        sys.exit(1)
    finally:
        pass
