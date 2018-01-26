# -*- coding: utf-8 -*-
# Copyright 2012,2016 Nick Boultbee
#           2012,2014,2018 Christoph Reiter
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

"""Show directories and files in the default system file browser"""

import os
import subprocess

from gi.repository import Gtk
from senf import fsn2uri, fsnative

try:
    import dbus
except ImportError:
    dbus = None

from quodlibet.util import is_windows, is_osx


def show_files(dirname, entries=[]):
    """Shows the directory in the default file browser and if passed
    a list of directory entries will highlight those.

    Depending on the system/platform this might highlight all files passed,
    or only one of them, or none at all.

    Args:
        dirname (fsnative): Path to the directory
        entries (List[fsnative]): List of (relative) filenames in the directory
        entries (List[fsnative]): List of (relative) filenames in the directory
    Returns:
        bool: if the action was successful or not
    """

    assert isinstance(dirname, fsnative)
    assert all(isinstance(e, fsnative) and os.path.basename(e) == e
               for e in entries)

    dirname = os.path.abspath(dirname)

    if is_windows():
        implementations = [_show_files_win32]
    elif is_osx():
        implementations = [_show_files_finder]
    else:
        implementations = [
            _show_files_fdo,
            _show_files_thunar,
            _show_files_xdg_open,
            _show_files_gnome_open,
        ]

    for impl in implementations:
        try:
            impl(dirname, entries)
        except BrowseError:
            continue
        else:
            return True
    return False


class BrowseError(Exception):
    pass


def _get_startup_id():
    from quodlibet import app
    app_name = type(app.window).__name__
    return "%s_TIME%d" % (app_name, Gtk.get_current_event_time())


def _show_files_fdo(dirname, entries):
    # http://www.freedesktop.org/wiki/Specifications/file-manager-interface
    FDO_PATH = "/org/freedesktop/FileManager1"
    FDO_NAME = "org.freedesktop.FileManager1"
    FDO_IFACE = "org.freedesktop.FileManager1"

    if not dbus:
        raise BrowseError("no dbus")

    try:
        bus = dbus.SessionBus()
        bus_object = bus.get_object(FDO_NAME, FDO_PATH)
        bus_iface = dbus.Interface(bus_object, dbus_interface=FDO_IFACE)

        if not entries:
            bus_iface.ShowFolders([fsn2uri(dirname)], _get_startup_id())
        else:
            item_uri = fsn2uri(os.path.join(dirname, entries[0]))
            bus_iface.ShowItems([item_uri], _get_startup_id())
    except dbus.DBusException as e:
        raise BrowseError(e)


def _show_files_thunar(dirname, entries):
    # http://git.xfce.org/xfce/thunar/tree/thunar/thunar-dbus-service-infos.xml
    XFCE_PATH = "/org/xfce/FileManager"
    XFCE_NAME = "org.xfce.FileManager"
    XFCE_IFACE = "org.xfce.FileManager"

    if not dbus:
        raise BrowseError("no dbus")

    try:
        bus = dbus.SessionBus()
        bus_object = bus.get_object(XFCE_NAME, XFCE_PATH)
        bus_iface = dbus.Interface(bus_object, dbus_interface=XFCE_IFACE)

        if not entries:
            bus_iface.DisplayFolder(fsn2uri(dirname), "", _get_startup_id())
        else:
            item_name = os.path.join(dirname, entries[0])
            bus_iface.DisplayFolderAndSelect(
                fsn2uri(dirname), item_name, "", _get_startup_id())
    except dbus.DBusException as e:
        raise BrowseError(e)


def _show_files_gnome_open(dirname, *args):
    try:
        if subprocess.call(["gnome-open", dirname]) != 0:
            raise EnvironmentError("gnome-open error return status")
    except EnvironmentError as e:
        raise BrowseError(e)


def _show_files_xdg_open(dirname, *args):
    try:
        if subprocess.call(["xdg-open", dirname]) != 0:
            raise EnvironmentError("xdg-open error return status")
    except EnvironmentError as e:
        raise BrowseError(e)


def _show_files_win32(dirname, entries):
    if not is_windows():
        raise BrowseError("windows only")

    if not entries:
        # open_folder_and_select_items will open the parent if no items
        # are passed, so execute explorer directly for that case
        try:
            if subprocess.call(["explorer", dirname]) != 0:
                raise EnvironmentError("explorer error return status")
        except EnvironmentError as e:
            raise BrowseError(e)
    else:
        from quodlibet.util.windows import open_folder_and_select_items

        try:
            open_folder_and_select_items(dirname, [])
        except WindowsError as e:
            raise BrowseError(e)


def _show_files_finder(dirname, *args):
    if not is_osx():
        raise BrowseError("OS X only")

    try:
        if subprocess.call(["open", "-R", dirname]) != 0:
            raise EnvironmentError("open error return status")
    except EnvironmentError as e:
        raise BrowseError(e)
