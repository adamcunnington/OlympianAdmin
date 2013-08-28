# <path to game directory>/addons/eventscripts/admin/
# modules.py
# by Adam Cunnington

"""Provide a simple way to create custom modules and register them to the 
core. Automatically handle action commands and menu interfaces.

"""

from __future__ import absolute_import

import os

from admin import metadata
from esutils import commands, menus, tools


__all__ = (
    "module_menu", 
    "ModulesError", 
    "Module", 
    "Action", 
    "Parameter", 
    "Menu", 
    "DynamicMenu", 
)


_UNLOADED_PREFIX = "UNLOADED: "


module_menu = menus.Menu()
module_menu.title = metadata.VERBOSE_NAME
module_menu.description = ":: Module Administration"


class _Callback(commands.Callback):
    def __init__(self, action, *args, **kwargs):
        super(_Callback, self).__init__(*args, **kwargs)
        self.action = action
        
class _Command(commands._Command):
    def _invalid_syntax(self, command, args, user_ID=None):
        action = self.callback.action
        parameters = self.callback.parameters
        total_args = len(args)
        if (not action.menu_interface or total_args > 
            len(self.callback.parameters)):
            super(_Command, self)._invalid_syntax(command, args, 
                                                  user_ID=user_ID)
            return
        # Otherwise, the next parameter's menu needs sending.
        self.callback.parameters[total_args].menu.send(user_ID)
        args.insert(0, action.basename)
        menus.Menu.players[user_ID].identifiers.extend(args)
        
class _ClientConsoleCommand(_Command, commands.ClientConsoleCommand):
    pass
    
class _ClientSayCommand(_Command, commands.ClientSayCommand):
    pass
    
class ModulesError(Exception):
    """General error encountered relating to admin.modules"""
    
class Module(object):
    """Create a module that represents a subset of functionality of the admin 
    system core and register appropriate actions to reside in this module.
    
    """
    modules = {}
    
    def __init__(self, basename, verbose_name=None):
        """Instantiate a Module object.
        
        Arguments:
        basename - the basename to identify the module by.
        verbose_name (Keyword Default: None) - the custom verbose name to use 
        in text. If it is not passed, it will be constructed from the basename.
        
        """
        if basename in self.modules:
            module = self.modules[basename]
            if module.loaded:
                raise ModulesError("%s is already loaded." % basename)
            self._option = module.option
            self._option.text = self._option.text.lstrip(_UNLOADED_PREFIX)
            self._option.selectable = True
        else:
            self._option = None
        self.basename = basename
        if verbose_name is None:
            self.verbose_name = tools.format_verbose_name(basename)
        else:
            self.verbose_name = verbose_name
        self._menu = None
        self.actions = set()
        self.modules[basename] = self
        self.loaded = True
        
    @classmethod
    def _menu_select(cls, user_ID, identifiers):
        action = identifiers[-1]
        parameters = action.parameters
        if not parameters:
            # If the action has no parameters, then its callback can be called 
            # straight away.
            action.callback.callable_name(commands.ClientSayCommand.INFORMER, 
                                          user_ID=user_ID, by_menu=True)
            return
        # Otherwise, send the first parameter's menu.
        parameters[0].menu.send(user_ID, reset_navigation=False)
        
    def append(self, action):
        """Register an action to this module. If this is the first action with 
        a menu interface, create a menu for the module.
        
        Arguments:
        action - the action to register.
        
        """
        if action.menu_interface:
            if self._menu is None:
                self._menu = menus.Menu(self._menu_select)
                self._menu.title = self.verbose_name
                self._menu.description = ":: Actions"
                if self._option is None:
                    self._option = menus.Option(self.verbose_name)
                    self._option.set_submenu(self._menu)
                    _module_menu.items.append(self.option)
                else:
                    self._option.text = self.verbose_name
                    self._option.set_submenu = self._menu
                    self._option.selectable = True
            module_menu.items.append(action.option)
        self.actions.add(action)
        
    @property
    def path(self):
        """Compile and return the full path of the module."""
        return os.path.join(os.path.dirname(__file__), "modules", 
                            self.basename)
                            
    def unload(self):
        """Stop the module's administration functionality by unregistering all 
        registered actions and stopping any related menu items from being 
        selectable.
        
        """
        if self._menu is not None:
            self._option.text = _UNLOADED_PREFIX + self.option.text
            self._option.selectable = False
        for action in self.actions:
            action.unload()
        self.loaded = False
        
class Action(object):
    """Create an action to be listed in the administration system. 
    Functionality can vary from command handling to a fully functional chained 
    menu interface.
    
    """
    actions = {}
    permissions = set()
    
    def __init__(self, callback, basename, description, 
                 requires_permission=True, menu_interface=True, 
                 server_command=True, verbose_name=None):
        """Instantiate an Action object.
        
        Arguments:
        callback - the name to call when an action is submitted with valid 
        syntax and argument values.
        basename - the basename to identify the action by.
        description - a description of the action.
        requires_permission (Keyword Default: True) - whether or not there 
        should be a specific permission required to use this action.
        menu_interface (Keyword Default: True) - whether or not the action 
        should have a menu option and utilise the action's parameter's menus.  
        server_command (Keyword Default: True) - whether or not a server 
        command should be registered as well as client commands.
        verbose_name (Keyword Default: None) - the custom verbose name to use 
        in text. If it is not passed, it will be constructed from the basename.
        
        """
        if basename in self.actions:
            raise ModulesError("the %s action already exists." % basename)
        self.callable_name = callback
        self.basename = basename
        self.menu_interface = menu_interface
        self.callback = _Callback(self, self._callback, description)
        self.parameters = self.callback.parameters
        client_console_command = _ClientConsoleCommand(self.callback)
        client_console_command.register("%s%s" %(metadata.CONSOLE_PREFIX, 
                                                 basename))
        client_say_command = _ClientSayCommand(self.callback)
        client_say_command.register("%s%s" %(metadata.CHAT_PREFIX, 
                                             basename))
        self._client_commands = (client_console_command, client_say_command)
        if not server_command:
            self._server_command = None
        else:
            self._server_command = commands.ServerCommand(self.callback)
            self._server_command.register("%s%s" %(metadata.CONSOLE_PREFIX, 
                                                  basename))
        if verbose_name is None:
            self.verbose_name = tools.format_verbose_name(basename)
        else:
            self.verbose_name = verbose_name
        if menu_interface:
            self._option = menus.MenuOption(self.verbose_name, self)
        if requires_permission:
            client_console_command.set_permission(basename)
            client_say_command.set_permission(basename)
            self._option.set_permission(basename)
            self.permissions.add(basename)
        else:
            client_console_command.set_permission()
            client_say_command.set_permission()
            self._option.set_permission()
        self.actions[basename] = self
        
    def _callback(self, informer, args, user_ID=None):
        defaults = [parameter.default_value 
                    if parameter.default_value is not commands.ABSENT
                    else None for parameter in self.parameters]
        if (self.menu_interface and defaults and 
            informer is not commands.ServerCommand.INFORMER):
            _args = list(args)
            for index, value in enumerate(_args):
                if value == defaults[index]:
                    args.remove(value)
            self.parameters[len(args)].menu.send(user_ID)
            args.insert(0, self.basename)
            menus.Menu.players[user_ID].identifiers.extend(args)
            return
        self.callable_name(informer, user_ID=user_ID, by_menu=False, *args)
        
    def resend_menu(self, user_ID, parameter):
        """Resend the menu for the parameter to the user.
        
        Arguments:
        user_ID - the unique session ID of the user who's menu should be 
        closed.
        parameter - the parameter object to use.
        
        """
        player = menus.Menu.players[user_ID]
        identifiers = player.identifiers
        del identifiers[self.parameters.index(parameter): ]
        parameter.menu.send(user_ID)
        player.identifiers.extend(identifiers)
        
    def unload(self):
        """Unregister all registered client and server commands."""
        for command in self._client_commands:
            command.unregister()
        if self._server_command is not None:
            self._server_command.unregister()
        self.permissions.discard(self.basename)
        del self.actions[self.basename]
        
class Parameter(commands.Parameter):
    """Create a parameter that can be used across multiple actions."""
    
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
        if verbose_name is None:
            self.verbose_name = tools.format_verbose_name(self.basename)
        else:
            self.verbose_name = verbose_name
        self.menu.title = "Parameter: %s" % self.verbose_name
        
    def _item_getter(self, user_ID):
        if self._get_items is None:
            items = []
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
        action = Action.actions[identifiers.pop(0)]
        total_args = len(identifiers)
        if total_args < len(action.parameters):
            # If arguments have been omitted, the next parameter's menu needs 
            # sending.
            action.parameters[total_args].menu.send(user_ID, 
                                                    reset_navigation=False)
        else:
            # Otherwise, the action's callback can be called.
            action.callable_name(commands.ClientSayCommand.INFORMER, 
                                 user_ID=user_ID, by_menu=True, *identifiers)
                                 
class Menu(menus.Menu):
    """Create a menu to be used by a parameter, primarily or as a submenu."""
    
    def __init__(self, get_items=None):
        super(Menu, self).__init__(Parameter._menu_select, get_items=get_items)