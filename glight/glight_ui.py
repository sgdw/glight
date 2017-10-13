#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import json
import argparse
import traceback

import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk
from gi.repository import Gdk

import glight

app_version="0.1"

class GlightUiConfig(object):

    def __init__(self):
        """"""
        self.attrs = ["last_chooser_directory"]
        self._config_root = "~/.config/"
        self._config_dir = "glight"
        self._config_filename = "glight_ui.conf"

        self.last_chooser_directory = None

    @property
    def config_dir(self):
        filename = os.path.join(self._config_root, self._config_dir)
        return os.path.expanduser(filename)

    @property
    def config_filename(self):
        filename = os.path.join(self.config_dir, self._config_filename)
        return os.path.expanduser(filename)

    def import_dict(self, values):
        for attr in self.attrs:
            if attr in values:
                self.__setattr__(attr, values[attr])

        return self

    def as_dict(self):
        data = {}
        for attr in self.attrs:
            data[attr] = self.__getattribute__(attr)
        return data

    def load(self):
        """"""
        if os.path.isfile(self.config_filename):
            with open(self.config_filename, "r") as config_file:
                config_json = config_file.read()
                if config_json is not None:
                    config = json.loads(config_json)
                    if isinstance(config, dict):
                        self.import_dict(config)

    def save(self):
        """"""
        if not os.path.isfile(self.config_filename):
            if not os.path.isdir(self.config_dir):
                os.makedirs(self.config_dir)
            with open(self.config_filename, "w") as config_file:
                config_file.write(json.dumps(self.as_dict(), indent=4))

class GlightUi:

    def __init__(self, backend_type=None):
        self.state_file_extension = "gstate"
        self.config = GlightUiConfig()
        self.config.load()

        self.gladefile = "glight_ui.glade"
        self.builder = Gtk.Builder()

        self.registry = None # type: glight.GDeviceRegistry
        self.proxy = None # type: glight.GlightController

        self.backend_type = glight.GlightController.BACKEND_DBUS
        if backend_type is not None:
            self.backend_type = backend_type

        self.device_states = None

        self.selected_device = None
        self.devices = None
        self.device_store = None
        self.window = None

        self.device_store = None
        self.device_tree = None
        self.btn_color_field = None
        self.btn_color_complete = None
        self.btn_color_breathe = None

        self.btn_set = None
        self.lbl_not_supported = None

        self.adj_speed_breathe = None
        self.adj_brightness_breathe = None
        self.adj_speed_cycle = None
        self.adj_brightness_cycle = None

        self.pages = ["complete", "fields", "breathe", "cycle"]

        self.setup_backend()
        self.init_ui()

    def init_ui(self):
        base = os.path.dirname(os.path.realpath(__file__))
        self.builder.add_from_file(os.path.join(base, self.gladefile))

        self.window = self.builder.get_object("window")
        self.window.set_title("GLight-UI")

        self.device_store = self.builder.get_object("devices")  # type: ListStore
        self.device_tree = self.builder.get_object("device_tree")

        self.btn_color_complete = self.builder.get_object("btn_color_complete")
        self.btn_color_complete.set_rgba(self.get_rgba_from_hex("ffffff"))
        self.btn_color_breathe = self.builder.get_object("btn_color_breathe")
        self.btn_color_breathe.set_rgba(self.get_rgba_from_hex("ffffff"))

        self.btn_set = {}
        self.lbl_not_supported = {}
        for page in self.pages:
            self.btn_set[page] = self.builder.get_object("btn_{0}_set".format(page))
            self.lbl_not_supported[page] = self.builder.get_object("lbl_not_supported_{0}".format(page))

        self.btn_color_field = []
        for i in range(1, 6):
            self.btn_color_field.append(self.builder.get_object("btn_color_field_{0}".format(i)))

        self.adj_speed_breathe = self.builder.get_object("adj_speed_breathe")
        self.adj_brightness_breathe = self.builder.get_object("adj_brightness_breathe")
        self.adj_speed_cycle = self.builder.get_object("adj_speed_cycle")
        self.adj_brightness_cycle = self.builder.get_object("adj_brightness_cycle")

        self.sync_ui()

        self.builder.connect_signals(self)
        self.window.show()

    def setup_backend(self):
        self.proxy = glight.GlightController(self.backend_type)
        self.registry = glight.GDeviceRegistry()

    def sync_ui(self):
        self.device_store.clear()
        self.devices = self.proxy.list_devices()
        for device_name_short, device_name in self.devices.iteritems():
            print "Added '{0}' ({1})".format(device_name_short, device_name)
            self.device_store.append([device_name, device_name_short])

    def get_device_base(self, device_name_short):
        """
        :param device_name_short: str
        :return: glight.GDevice
        """
        return self.registry.get_known_device(device_name_short)

    def update_ui(self):
        """"""

        if self.selected_device is None:
            pass
        else:
            device = self.get_device_base(self.selected_device) # type: glight.GDevice

            self.adj_brightness_breathe.set_lower(device.bright_spec.min_value)
            self.adj_brightness_breathe.set_upper(device.bright_spec.max_value)
            self.adj_brightness_breathe.set_value(device.bright_spec.max_value)

            self.adj_speed_breathe.set_lower(device.speed_spec.min_value)
            self.adj_speed_breathe.set_upper(device.speed_spec.max_value)
            self.adj_speed_breathe.set_value(device.speed_spec.min_value)

            self.adj_brightness_cycle.set_lower(device.bright_spec.min_value)
            self.adj_brightness_cycle.set_upper(device.bright_spec.max_value)
            self.adj_brightness_cycle.set_value(device.bright_spec.max_value)

            self.adj_speed_cycle.set_lower(device.speed_spec.min_value)
            self.adj_speed_cycle.set_upper(device.speed_spec.max_value)
            self.adj_speed_cycle.set_value(device.speed_spec.min_value)

            fields_supported = device.field_spec.max_value > 1
            self.btn_set["fields"].set_sensitive(fields_supported)
            self.lbl_not_supported["fields"].set_visible(not fields_supported)

            # print device.speed_spec.min_value
            # print device.speed_spec.max_value

            if self.selected_device in self.device_states:
                state = self.device_states[self.selected_device] # type: glight.GDeviceState

                for i in range(0, len(self.btn_color_field)+1):
                    if state.colors is not None and len(state.colors) > i:
                        color = state.colors[i]
                    else:
                        color = "ffffff"
                    c = self.get_rgba_from_hex(color)
                    print "[{0}] {1}".format(i, color)

                    if i == 0:
                        self.btn_color_complete.set_rgba(c)
                        self.btn_color_breathe.set_rgba(c)
                    else:
                        if len(self.btn_color_field) > i-1:
                            self.btn_color_field[i-1].set_rgba(c)

                if state.speed is not None:
                    if state.breathing:
                        self.adj_speed_breathe.set_value(state.speed)
                    elif state.cycling:
                        self.adj_speed_cycle.set_value(state.speed)

                if state.brightness is not None:
                    if state.breathing:
                        self.adj_brightness_breathe.set_value(state.brightness)
                    elif state.cycling:
                        self.adj_brightness_cycle.set_value(state.brightness)


    def get_rgba_from_hex(self, col_hex):
        """"""
        # rgb = tuple(int(col_hex[i:i + 2], 16) for i in (0, 2, 4))
        # return Gdk.Color(rgb[0], rgb[1], rgb[2])

        rgba = Gdk.RGBA()
        if col_hex is None:
            rgba.parse("#ffffff")
        else:
            rgba.parse("#"+col_hex)
        return rgba

    def get_color_hex_from_button(self, col_btn):
        """"""
        return self.convert_gdk_col_to_string(col_btn.get_rgba())

    def convert_gdk_col_to_string(self, gdk_col):
        """"""
        return "{:02x}{:02x}{:02x}".format(
            int(round(gdk_col.red   * 255)),
            int(round(gdk_col.green * 255)),
            int(round(gdk_col.blue  * 255)))

    def on_window_destroy(self, object, data=None):
        Gtk.main_quit()

    def on_store_settings(self, *args, **kwargs):
        """"""
        self.proxy.save_state()

    def on_restore_settings(self, *args, **kwargs):
        """"""
        state = self.proxy.get_state()
        print state
        self.proxy.load_state()

    def on_load_state(self, widget):
        # http://python-gtk-3-tutorial.readthedocs.io/en/latest/dialogs.html#filechooserdialog
        dialog = Gtk.FileChooserDialog(
            "Please choose a file",
            self.window,
            Gtk.FileChooserAction.OPEN,
            (Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL, Gtk.STOCK_OPEN, Gtk.ResponseType.OK))

        if self.config.last_chooser_directory is not None \
                and os.path.isdir(self.config.last_chooser_directory):
            dialog.set_current_folder(os.path.expanduser(self.config.last_chooser_directory))
        else:
            dialog.set_current_folder(os.path.expanduser("~"))  # Home

        self.add_filters(dialog)

        response = dialog.run()
        if response == Gtk.ResponseType.OK:
            print("File selected: " + dialog.get_filename())

            state_json = None
            filename = dialog.get_filename()
            with open(filename, "r") as state_file:
                state_json = state_file.read()

            if state_json is not None:
                self.proxy.set_state(state_json)

        elif response == Gtk.ResponseType.CANCEL:
            print("Cancel clicked")

        dialog.destroy()

    def on_save_state(self, widget):
        dialog = Gtk.FileChooserDialog(
            "Please choose a file",
            self.window,
            Gtk.FileChooserAction.SAVE,
            (Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL, Gtk.STOCK_SAVE, Gtk.ResponseType.OK))

        dialog.set_current_folder(os.path.expanduser("~"))  # HACK

        self.add_filters(dialog)

        response = dialog.run()
        if response == Gtk.ResponseType.OK:
            print("File selected: " + dialog.get_filename())

            state = self.proxy.get_state()
            state_json = self.proxy.convert_state_to_json(state)

            filename = dialog.get_filename()
            dirname = os.path.dirname(filename)
            self.config.last_chooser_directory = dirname
            self.config.save()

            if not filename.endswith(".{0}".format(self.state_file_extension)):
                filename = filename + "." + self.state_file_extension

            with open(filename, "w") as state_file:
                state_json = state_file.write(state_json)

        elif response == Gtk.ResponseType.CANCEL:
            print("Cancel clicked")

        dialog.destroy()

    def add_filters(self, dialog):
        filter_text = Gtk.FileFilter()
        filter_text.set_name("GLight state file")
        filter_text.add_mime_type("text/plain")
        filter_text.add_pattern("*.{0}".format(self.state_file_extension))
        dialog.add_filter(filter_text)

        filter_any = Gtk.FileFilter()
        filter_any.set_name("Any files")
        filter_any.add_pattern("*")
        dialog.add_filter(filter_any)

    def on_device_selected(self, tree_selection):
        """"""
        selection = tree_selection.get_selection()
        model, treeiter = selection.get_selected()
        if treeiter is not None:
            print("You selected '{0}' ({1})".format(model[treeiter][0], model[treeiter][1]))
            self.selected_device = model[treeiter][1]
        else:
            self.selected_device = None

        self.device_states = self.proxy.get_state()

        self.update_ui()

    def on_color_change(self, btn):
        """
        :param btn: Gtk.ColorButton
        :return:
        """
        print btn.get_name()
        print btn.get_color()
        print self.get_color_hex_from_button(btn)

    def on_complete_set(self, *args, **kwargs):
        """"""
        col = self.get_color_hex_from_button(self.btn_color_complete)
        self.proxy.set_colors(self.selected_device, [col])

    def on_fields_set(self, *args, **kwargs):
        """"""
        cols = []
        for btn in self.btn_color_field:
            cols.append(self.get_color_hex_from_button(btn))

        self.proxy.set_colors(self.selected_device, cols)

    def on_breathe_set(self, *args, **kwargs):
        """"""
        col = self.get_color_hex_from_button(self.btn_color_breathe)
        speed = int(self.adj_speed_breathe.get_value())
        brightness = int(self.adj_brightness_breathe.get_value())

        self.proxy.set_breathe(self.selected_device, col, speed, brightness)

    def on_cycle_set(self, *args, **kwargs):
        """"""
        speed = int(self.adj_speed_cycle.get_value())
        brightness = int(self.adj_brightness_cycle.get_value())

        self.proxy.set_cycle(self.selected_device, speed, brightness)


if __name__ == "__main__":
    argsparser = argparse.ArgumentParser(
        description='UI to change the colors on some Logitech devices (V' + app_version + ')', add_help=False)
    argsparser.add_argument('--direct-mode', dest='direct_mode', action='store_const', const=True,
                            help='run directly against usb interface; might be necessary to run as root')
    argsparser.add_argument('-h', '--help', dest='help', action='store_const', const=True, help='show help')
    args = argsparser.parse_args()

    if args.help:
        argsparser.print_help()
        print
        exit()


    try:

        if args.direct_mode:
            main = GlightUi(glight.GlightController.BACKEND_LOCAL)
        else:
            main = GlightUi()
        Gtk.main()

    except Exception as ex:

        print("Exception: {}".format(ex))
        print(traceback.format_exc())

        msg = "Exception '{0}' [{1}]".format(ex.message, type(ex).__name__)

        user_msg=None
        if "org.freedesktop.DBus.Error.ServiceUnknown" in ex.message:
            user_msg = "Could not connect to the glight service!\n\nIs the service running?"
        elif "USBErrorAccess" in type(ex).__name__:
            user_msg = "Could not access device directly via usb!\n\nYou might want to try running the application as root."

        if user_msg is not None:
            msg = user_msg + "\n\n" + msg

        md = Gtk.MessageDialog(None,
                               Gtk.DialogFlags.DESTROY_WITH_PARENT,
                               Gtk.MessageType.ERROR,
                               Gtk.ButtonsType.CLOSE,
                               msg)
        md.run()