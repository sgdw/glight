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

How to install
==============

Requirements
------------

*Note: The following requirements can also be installed via the installation
script ``support/install-glight``*

Python PIP::

    sudo apt install python-pip

GTK3::

    sudo apt install python-gi python-gi-cairo python3-gi python3-gi-cairo gir1.2-gtk-3.0

libusb1::

    sudo pip install libusb1

PyDBUS::

    sudo pip install pydbus

Yes, you actually need GTK3 even for the commandline use, because glight.py
uses glib.MainLoop() in its libusb1 backend.


**(Optional)** PyUSB::

    sudo pip install pyusb


The actual installation
-----------------------

Use the installation script ``support/install-glight``

You will be either guided through the installation process or get instructions
how to install manually based on your choices. You can also consult the chapter
"Manual installation" in this readme.

How to use
==========

Since communicating with a hid device needs root privileges (at least on my
machine) you will have to run these apps either as root, sudoed or run as a
(privileged) service.

Running glight privileged
-------------------------

Setting the color of your G203 mouse to red.

    sudo glight.py -d g203 -c ff0000

Running glight as a service
---------------------------

Before running GLight as a service, you will have install a DBUS-policy.
See section "Installing".

Starting the service (privileged).

    sudo glight.py --service

Setting the color in client mode. Look mom no sudo ;)

    glight.py -C -d g203 -c ff0000

Running the glight_ui
---------------------

Running the UI using the service.

    glight_ui.py

Running the UI using the device directly.

    sudo glight_ui.py --direct-mode

Running the glight_fx
---------------------

Running the UI using the service.

    glight_fx.py



Usage glight.py
---------------

Usage::

    glight.py [-d [device_name]] [-c color [color ...]]
                     [-x speed [brightness]]
                     [-b color [speed [brightness]] [color [speed [brightness]]
                     ...]] [--backend (usb1|pyusb)] [--state-file [filename]]
                     [--load-state] [--save-state] [-C] [--service] [-l] [-v] [-h]
                     [--experimental [name [name ...]]]

    Changes the colors on some Logitech devices (V0.1)

    optional arguments:
      -d [device_name], --device [device_name]
                            set device
      -c color [color ...], --color color [color ...]
                            set color(s)
      -x speed [brightness], --cycle speed [brightness]
                            set color cycle animation
      -b color [speed [brightness]], --breathe color [speed [brightness]]
                            set breathing animation
      --backend (usb1|pyusb)
                            set backend (usb1, pyusb), usb1 is strongly
                            recommended
      --state-file [filename]
                            file where the state is saved
      --load-state          load state from state file
      --save-state          save state to state file
      -C, --client          run as client
      --service             run as service
      -l, --list            list devices
      -v, --verbose         be verbose
      -h, --help            show help
      --experimental [name [name ...]]
                            experimental features

    Value ranges for each device are:

      G203 Mouse (g203)
          Color segments: 1
          Speed: 1000 .. 20000 (default 11000)
          Brightness: 1 .. 100 (default 100)

      G213 Keyboard (g213)
          Color segments: 6
          Speed: 1000 .. 20000 (default 11000)
          Brightness: 1 .. 100 (default 100)


**Remarks:**

**Argument "-c color"**

If only one color is given, all segments of the keyboard will have the same color.

**Argument "--state-file"**

Only supported in non-client mode.

**Argument "--backend"**

The pyusb backend is only there for legacy reasons. Not recommended,
because the color changes will not be very reliable.

Manual installation
===================

**Moving files around**

Create directory '/usr/local/lib/glight'.

    mkdir "/usr/local/lib/glight"

Setup proper permissions.

    chown root:root "/usr/local/lib/glight" && chmod 755 "/usr/local/lib/glight"

Copy all files from this directory to ''.

    cp ../* "/usr/local/lib/glight/"

Setup proper permissions.

    chown root:root "/usr/local/lib/glight/glight/*.py" && chmod 755 "/usr/local/lib/glight/glight/*.py"

**Setting up DBUS**

The DBUS interface needs a profile, which defines which clients are allowed to connect to it.
Copy the file 'etc-dbus-1/de.sgdw.linux.glight.conf' to '/etc/dbus-1/':

    cp etc-dbus-1/de.sgdw.linux.glight.conf /etc/dbus-1/de.sgdw.linux.glight.conf

**Setting up glight as a service**

Copy the service script from 'etc-init.d/glight' to '/etc/init.d/glight'

    cp etc-init.d/glight /etc/init.d/glight

Setup proper permissions.

    chown root:root "/etc/init.d/glight" && chmod 755 "/etc/init.d/glight"

Copy the default config file to '/etc/glight.conf'.

    cp etc/glight.conf /etc/glight.conf

Setup proper permissions.

    chown root:root "/etc/glight.conf" && chmod 755 "/etc/glight.conf"

**Setup runlevel for glight service**

You want to start the service at system start.

    update-rc.d glight defaults 80 20

The inner workings ...
======================

Before I bought my G203 and G213 I did some research if those devices are supported on linux.
So I stumbled onto SebiTimeWaster's project G213Colors and voila there is some support.

Sadly as SebiTimeWaster mentioned, setting the colors isn't very reliable. So this piqued my interest.

Setting one color at a time worked well. But setting multiple color segments in a quick succession
did not work reliable at all. Only the first few segment would be correctly set. Resubmitting the
color commands would set some more segments, but never in a reliable fashion.

I tried using delays between commands which didn't work either. Only disconnecting the kernel driver
inbetween every command worked, but made it painfully slow.

So I took Wireshark and usbmon to have a look at the underlying protocoll. Thanks to SebiTimeWaster's
work, I had a good idea what to look for. Thanks again ;)

Just sending a color command like ``"11ff0e3d{field}01{color}0200000000000000000000"`` down the line, did
not do the trick. The G-Device seemed to expect a URB_INTERRUPT bracketing the actual color command.

Protocoll::

    HOST > DEVICE : URB_INTERRUPT in "want interrupt"
    HOST > DEVICE : URB_CONTROL out "color command"
    DEVICE > HOST : URB_CONTROL out "response"
    DEVICE > HOST : URB_INTERRUPT out "got interrupt"
    ... now the device is ready for the next command

Since this wasn't possible using the PyUSB lib, I had to switch to the usb1 which is much more expressive
and quite a bit more difficult.

Using this interupt-command structure it was now possible to set the various color effects reliably. If you
are interested in the actual commands, have a look at glight.py and the respective classes G203() and G213().

Links and further reading
=========================

Similar projects
----------------

G213Colors - The project that started all this ;) Thanks!
 https://github.com/SebiTimeWaster/G213Colors

gseries-tools project:
 https://github.com/GSeriesDev/gseries-tools

g500 project by Clément Vuchener:
 https://github.com/cvuchener/g500
 https://github.com/cvuchener/hidpp

Julien Danjou reverse engineering the Logitech K750
 https://julien.danjou.info/blog/2012/logitech-k750-linux-support

'dslul' trying to decode the G-Protocoll:
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
