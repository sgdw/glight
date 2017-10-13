GLight
======

GLight controls LEDs of some Logitech devices.

Included are the following applications:

- **glight.py**    - commandline app for controlling color of the G-devices
- **glight_ui.py** - GTK-UI for glight.py
- **glight_fx.py** - some experiments on changing colors depending on e.g. system load

Supported Devices
=================

- Logitech G203 Prodigy Mouse
- Logitech G213 Prodigy Keyboard

Supported features
==================

- setting a single color for the complete device
- setting different colors for the 5 available segments of the keyboard (G213 only)
- setting a breathing/pulsating color
- setting a color cycle aka. rainbow

How to use
==========

Since communicating with a hid device needs root privileges (at least on my
machine) you will have run these apps either as root, sudoed or run as a
(privileged) service.

Running privileged
------------------

Setting the color of your G203 mouse to red.

    sudo glight.py -d g203 -c ff0000

Running as a service
--------------------

Before running GLight as a service, you will have install a DBUS-policy.
See section "Installing".

Starting the service (privileged).

    sudo glight.py --service

Setting the color in client mode. Look mom no sudo ;)

    glight.py -C -d g203 -c ff0000


Usage glight.py
---------------

Usage::

    glight [-d [device_name]] [-c color [color ...]]
              [-x speed, brightness]
              [-b color, speed, brightness]
              [--backend (usb1|pyusb)] [--state-file [filename]]
              [--load-state] [--save-state] [-C] [--service] [-l] [-v] [-h]
              [--experimental EXPERIMENT]]

    Changes the colors on some Logitech devices (V0.1)

    optional arguments:
      -d [device_name], --device [device_name]
                            set device (e.g. g213, g203)
      -c color [color ...], --color color [color ...]
                            set color(s)
      -x speed [brightness], --cycle speed [brightness]
                            set time
      -b color [speed [brightness]], --breathe color [speed [brightness]]
                            set breathing animation
      --backend (usb1|pyusb)
                            set backend (usb1, pyusb)
      --state-file [filename]
                            file where the state is saved
      --load-state          load state from state file
      --save-state          save state to state file
      -C, --client          run as client
      --service             run as service
      -l, --list            list devices
      -v, --verbose         be verbose
      -h, --help            show help
      --experimental name   experimental features

**Remarks:**

**Argument "-c color"**

If only one color is given, all segments of the keyboard will have the same color.

**Argument "--state-file"**

Only supported in non-client mode.

**Argument "--backend"**

The pyusb backend is only there for legacy reasons. Not recommended,
because the color changes will not be very reliable.

Links and further reading
=========================

Similar projects
----------------

Another project that started all this ;) Thanks!
 https://github.com/SebiTimeWaster/G213Colors

gseries-tools project:
 https://github.com/GSeriesDev/gseries-tools

g500 project by Clément Vuchener:
 https://github.com/cvuchener/g500
 https://github.com/cvuchener/hidpp

Somebody else reverse engineering the Logitech K750
 https://julien.danjou.info/blog/2012/logitech-k750-linux-support

Somebody trying to decode the G-Protocoll:
 https://github.com/GSeriesDev/gseries-tools/issues/3

Specifications
--------------

USB in a NutShell - for the nitty gritty technical details
 http://www.beyondlogic.org/usbnutshell/usb1.shtml

DBUS specification
 https://dbus.freedesktop.org/doc/dbus-specification.html#basic-types

DBUS deamon policies
 https://dbus.freedesktop.org/doc/dbus-daemon.1.html

Libraries
---------

libusb1 - which I ended up using, instead of PyUSB
 https://github.com/vpelletier/python-libusb1

PyUSB Tutorial (PyUSB is not used anymore by GLight, but i started using this Library)
 https://github.com/walac/pyusb/blob/master/docs/tutorial.rst
