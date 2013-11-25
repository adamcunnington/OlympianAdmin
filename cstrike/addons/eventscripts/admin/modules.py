# <path to game directory>/addons/eventscripts/admin/
# modules.py
# by Adam Cunnington

"""Provides a simple way to create custom modules and register them to the
core. Automatically handle command commands and menu interfaces.

"""

from __future__ import absolute_import

import os

import admin.metadata
from esutils import commands, messages, menus, tools


__all__ = (
    "module_menu",
    "ModulesError",
    "Module",
    "PlayerCommand",
    "AdminCommand",
    "Parameter",
    "Menu",
    "DynamicMenu"
)


module_menu = menus.Menu()
module_menu.title = admin.metadata.VERBOSE_NAME
module_menu.description = ":: Module Administration"


class _CommandInformers(object):
    @classmethod
    def disabled(cls, informer, command_name):
        commands.inform(informer,
                        admin.whisper_text("Command, %s, is currently "
                                           "disabled." % command_name,
                                           informer in
                                           messages.coloured_informers))

    @classmethod
    def invalid_value(cls, informer, command_name, parameter, arg,
                      user_ID=None):
        commands.inform(informer,
                        admin.whisper_text("Invalid value, %s, for "
                                           "parameter, %s." %(arg,
                                           parameter.basename),
                                           informer in
                                           messages.coloured_informers),
                        user_ID)

    @classmethod
    def no_auth(cls, informer, command_name, user_ID=None):
        commands.inform(informer,
                        admin.whisper_text("You are not authorised to use the "
                                           "command, %s." % command_name,
                                           informer in
                                           messages.coloured_informers),
                        user_ID)


class ModulesError(Exception):
    """General error encountered relating to admin.modules"""

class Module(object):
    """Create a module that represents a subset of functionality of the admin
    system core and register appropriate commands to reside in this module.

    """
    modules = {}

    def __init__(self, basename, verbose_name=None):
        """Instantiate a Module object.

        Arguments:
        basename - the basename to identify the module by.
        verbose_name (Keyword Default: None) - the custom verbose name to use
        in text. If it is not passed, it will be constructed from the basename.

        """
        verbose_name = verbose_name or tools.format_verbose_name(basename)
        if basename in self.modules:
            module = self.modules[basename]
            if module.loaded:
                raise ModulesError("%s is already loaded." % basename)
            self._option = module.option
            self._option.text = verbose_name
            self._option.selectable = True
        else:
            self._option = None
        self.basename = basename
        self.verbose_name = verbose_name
        self._menu = None
        self.commands = set()
        self.modules[basename] = self
        self.loaded = True

    def append(self, command):
        """Register a command to this module. If this is the first command
        with a menu interface, create a menu for the module.

        Arguments:
        command - the command to register.

        """
        if command.menu_interface:
            if self._menu is None:
                self._menu = menus.Menu(self._menu_select)
                self._menu.title = self.verbose_name
                self._menu.description = ":: Commands"
                if self._option is None:
                    self._option = menus.Option(self.verbose_name)
                    self._option.set_submenu(self._menu)
                    module_menu.items.append(self.option)
                else:
                    self._option.text = self.verbose_name
                    self._option.set_submenu = self._menu
            module_menu.items.append(command.option)
        self.commands.add(command)

    @classmethod
    def _menu_select(cls, user_ID, identifiers):
        command = identifiers[-1]
        parameters = command.parameters
        if not parameters:
            # If the command has no parameters, then its callback can be called
            # straight away.
            command.callback.callable_name(user_ID=user_ID, by_menu=True)
            return
        # Otherwise, send the first parameter's menu.
        parameters[0].menu.send(user_ID, reset_navigation=False)

    @property
    def path(self):
        """Compile and return the full path of the module."""
        return os.path.join(os.path.dirname(__file__), "modules",
                            self.basename)

    def unload(self):
        """Stop the module's administration functionality by unregistering all
        registered commands and stopping any related menu items from being
        selectable.

        """
        if self._menu is not None:
            self._option.text = "(UNLOADED) %s" % self.option.text
            self._option.selectable = False
        for command in self.commands:
            command.unload()
        self.loaded = False


class _Command(object):
    def _callback(self, args, informer=None, user_ID=None):
        if not self.menu_interface:
            self.callback(args, informer=informer, user_ID=user_ID,
                          by_menu=False)
            return
        defaults = [parameter.default_value if parameter.default_value
                    is not commands.ABSENT else None
                    for parameter in self.callback.parameters]
        for index, value in enumerate(args[:]):
            if value == defaults[index]:
                args.remove(value)
        self.parameters[len(args)].menu.send(user_ID)
        args.insert(0, self.basename)
        menus.Menu.players[user_ID].identifiers.extend(args)
        if informer == commands.ClientConsoleCommand.INFORMER:
            commands.inform(informer,
                            admin.whisper_text("You have been sent a menu "
                                               "where you can select a value "
                                               "for the next parameter.",
                                               informer in
                                               messages.coloured_informers))
        return

    def _invalid_syntax_callback(self, informer, command_name, parameters,
                                 args, user_ID=None):
        total_args = len(args)
        if not self.menu_interface or total_args > len(parameters):
            commands.inform(informer,
                            admin.whisper_text("Invalid syntax for command, "
                                               "%s." % command_name,
                                               informer in
                                               messages.coloured_informers),
                            user_ID)
        else:
            self.parameters[total_args].menu.send(user_ID)
            args.insert(0, self.basename)
            menus.Menu.players[user_ID].identifiers.extend(args)

    def unload(self):
        """Unregister all registered client and server commands."""
        self.client_console_command.unregister()
        self.client_say_command.unregister()
        if self._server_command is not None:
            self._server_command.disable()
        del self.commands[self.basename]


class PlayerCommand(_Command):
    """Create a command to be used by players. Functionality can vary from
    command handling to a fully functional chained menu interface.

    """
    commands = {}
    def __init__(self, callback, basename, description, menu_interface=True,
                 verbose_name=None):
        """Instantiate a Command object.

        Arguments:
        callback - the name to call when a command is submitted with valid
        syntax and argument values.
        basename - the basename to identify the command by.
        description - a description of the command.
        menu_interface (Keyword Default: True) - whether or not the command
        should have a menu option and utilise the command's parameter's menus.
        verbose_name (Keyword Default: None) - the custom verbose name to use
        in text. If it is not passed, it will be constructed from the basename.

        """
        if basename in self.commands:
            raise ModulesError("the %s command already exists." % basename)
        self.callback = callback
        self.basename = basename
        self._client_callback = commands.Callback(self._callback, description)
        self.parameters = self._client_callback.parameters
        # Declare variable for readable line lengths.
        _callback = self._client_callback
        self._client_console_command = commands.ClientConsoleCommand(_callback)
        self._client_console_command.register("%s%s" %(
                                              admin.metadata.CONSOLE_PREFIX,
                                              basename))
        self._client_say_command = commands.ClientSayCommand(_callback)
        self._client_say_command.register("%s%s" %(admin.metadata.CHAT_PREFIX,
                                                   basename))
        self.verbose_name = verbose_name or tools.format_verbose_name(basename)
        self.commands[basename] = self


class AdminCommand(_Command):
    """Create a command to be listed in the administration system.
    Functionality can vary from command handling to a fully functional chained
    menu interface.

    """
    commands = {}
    permissions = set()

    def __init__(self, callback, basename, description, menu_interface=True,
                 requires_special_permission=True, server_command=True,
                 verbose_name=None):
        """Instantiate a Command object.

        Arguments:
        callback - the name to call when a command is submitted with valid
        syntax and argument values.
        basename - the basename to identify the command by.
        description - a description of the command.
        menu_interface (Keyword Default: True) - whether or not the command
        should have a menu option and utilise the command's parameter's menus.
        requires_special_permission (Keyword Default: True) - whether or not
        there should be a specific permission required to use this command.
        server_command (Keyword Default: True) - whether or not a server
        command should be registered as well as client commands.
        verbose_name (Keyword Default: None) - the custom verbose name to use
        in text. If it is not passed, it will be constructed from the basename.

        """
        if basename in self.commands:
            raise ModulesError("the %s command already exists." % basename)
        self.callback = callback
        self.basename = basename
        self._client_callback = commands.Callback(self._callback, description)
        self.parameters = self._client_callback.parameters
        # Declare variable for readable line lengths.
        _callback = self._client_callback
        self._client_console_command = commands.ClientConsoleCommand(_callback)
        self._client_console_command.register("%s%s" %(
                                              admin.metadata.CONSOLE_PREFIX,
                                              basename))
        self._client_say_command = commands.ClientSayCommand(_callback)
        self._client_say_command.register("%s%s" %(admin.metadata.CHAT_PREFIX,
                                                   basename))
        if not server_command:
            self._server_command = None
        else:
            # Declare variable for readable line lengths.
            _callback = commands.Callback(self.callback, description)
            self._server_command = commands.ServerCommand(_callback)
            self._server_command.parameters = self.parameters
            self._server_command.register("%s%s" %(
                                          admin.metadata.CONSOLE_PREFIX,
                                          basename))
        self.verbose_name = verbose_name or tools.format_verbose_name(basename)
        if menu_interface:
            self._option = menus.MenuOption(self.verbose_name, self)
        self.menu_interface = menu_interface
        if requires_special_permission:
            permission = basename
            self.permissions.add(permission)
        else:
            permission = None
        self._client_console_command.set_permission(basename)
        self._client_say_command.set_permission(basename)
        self._option.set_permission(basename)
        self.commands[basename] = self

    def unload(self):
        """Unregister all registered client and server commands."""
        super(AdminCommand, self).unload()
        self.permissions.discard(self.basename)


class Parameter(commands.Parameter):
    """Create a parameter that can be used across multiple commands."""

    def __init__(self, basename, description, default_value=commands.ABSENT,
                 get_items=None, verbose_name=None):
        """Instantiate a Parameter object.

        Arguments:
        basename - the basename to identify the parameter by.
        description - a description of the values accepted.
        default_value (Keyword Default: commands.ABSENT) - the default value
        the parameter should take. A value other than the default, ABSENT
        object will cause the parameter to be optional.
        get_items (Keyword Default: None) - if the parameter's menu should
        be dynamic, the name to call to dynamically fetch the menu's options.
        verbose_name (Keyword Default: None) - the custom verbose name to use
        in text.

        """
        super(Parameter, self).__init__(basename, description, default_value)
        if default_value is commands.ABSENT:
            self.menu = Menu(get_items)
        else:
            self._get_items = get_items
            self.menu = Menu(self._item_getter)
        self.verbose_name = verbose_name or tools.get_verbose_name(basename)
        self.menu.title = "Parameter: %s" % self.verbose_name

    def _item_getter(self, user_ID):
        if self._get_items is None:
            items = self.menu.items
        else:
            items = self._get_items(user_ID)
        items.insert(0, menus.MenuOption("Default Value (%s)"
                                         % self.default_value,
                                         self.default_value))
        return items

    @classmethod
    def _menu_select(cls, user_ID, *identifiers):
        identifiers = [identifier for identifier in identifiers
                       if identifier is not menus.ABSENT]
        command = identifiers.pop(0)
        command = (PlayerCommand.commands.get(command) or
                   AdminCommand.commands.get(command))
        total_args = len(identifiers)
        if total_args < len(command.parameters):
            # If arguments have been omitted, the next parameter's menu needs
            # sending.
            command.parameters[total_args].menu.send(user_ID,
                                                    reset_navigation=False)
        else:
            # Otherwise, the command's callback can be called.
            command.callback(user_ID=user_ID, by_menu=True, *identifiers)


class Menu(menus.Menu):
    """Create a menu to be used by a parameter, primarily or as a submenu."""

    def __init__(self, get_title=None, get_description=None, get_items=None):
        super(Menu, self).__init__(Parameter._menu_select, get_title=get_title,
                                   get_description=get_description,
                                   get_items=get_items)