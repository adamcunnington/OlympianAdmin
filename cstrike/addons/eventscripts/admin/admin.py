# <path to game directory>/addons/eventscripts/admin/
# admin.py
# by Adam Cunnington

from __future__ import absolute_import

import functools

import admin
from admin import metadata, modules
from esutils import (admins, commands, configurations, exceptions, menus, 
                     messages, tools)
import es


_settings = configurations.Configuration("%s/cfg/admin/settings.cfg" 
                                         % tools.GAME_DIR)
_settings.append_text("Admin Plugin Settings")
_settings.append_text()
_settings.append_variable(metadata.LOG_ERRORS)
_root_admin = es.ServerVar("%sroot_admin" % metadata.CONSOLE_PREFIX, 
                           "STEAM_ID_LAN")
_settings.append_text()
_settings.append_variable(_root_admin)
_settings.write()

_core_actions = set()


def _action_transformer(value, user_ID=None):
    if value in modules.Action.actions:
        return value
    raise commands.ArgumentValueError()
    
_action = modules.Parameter("action", "The basename of an action", None)
_action.set_transformer(_action_transformer)

def _get_loaded_modules(user_ID):
    return [menus.MenuOption(module.verbose_name, module)  
            for module in modules.Module.modules if module.loaded]
            
def _loaded_module_transformer(value, user_ID=None):
    if (value in modules.Module.modules and 
        modules.Module.modules[value].loaded):
        return value
    raise commands.ArgumentValueError()
    
_loaded_module = modules.Parameter("loaded_module", 
                                   "The basename of a loaded module", 
                                   get_items=_get_loaded_modules)
_loaded_module.set_transformer(_loaded_module_transformer)

def _get_unloaded_modules(user_ID):
    items = []
    for module in modules.Module.modules:
        if not module.loaded:
            items.append(menus.MenuOption(module.verbose_name, module))
    items.append(menus.CustomMenuOption("Other Module"))
    return items
    
def _unloaded_module_transformer(value, user_ID=None):
    if (value not in modules.Module.modules or not
        modules.Module.modules[value].loaded):
        return value
    raise commands.ArgumentValueError()
    
_unloaded_module = modules.Parameter("unloaded_module", 
                                     "The basename of an unloaded module", 
                                     get_items=_get_unloaded_modules)
_unloaded_module.set_transformer(_unloaded_module_transformer)

def _help_player(informer, action, user_ID=None, by_menu=False):
    if informer == commands.ClientConsoleCommand.INFORMER:
        informer = functools.partial(informer, user_ID)
    if action is None:
        if informer == commands.ClientSayCommand.INFORMER:
            informer(user_ID, "Outputting to console...")
            informer = functools.partial(commands.ClientConsoleCommand.INFORMER, user_ID)
        informer("%s [v%s]" %(metadata.VERBOSE_NAME, 
                                         metadata.VERSION))
        informer("by %s" % metadata.AUTHOR)
        informer()
        informer("Prefix Settings")
        informer("  Console Prefix: %s" % metadata.CONSOLE_PREFIX)
        informer( "  Chat Prefix: %s" % metadata.CHAT_PREFIX)
        informer()
        informer("Syntax Key")
        informer("  <parameter> is required")
        informer("  [parameter] is optional")
        informer()
        informer("### CORE ACTIONS ###")
        for action in _core_actions:
            message = "  %s %s" %(action.basename.upper(), 
                                  action.callback.syntax)
            message += "  ~ %s" % action.callback.description
            informer(message)
            informer("  Parameters:")
            for parameter in action.callback.parameters:
                informer("    %s: %s" %(parameter.basename, 
                                        parameter.description))
            informer()
        informer()
        informer()
        informer("### MODULES ###")
        for module in modules.Module.modules.itervalues():
            informer("  %s" % module.verbose_name)
            for action in module.actions:
                message = "    %s %s" %(action.basename.upper(), 
                                        action.callback.syntax)
                message += "    ~ %s" % action.callback.description
                informer(message)
                informer("    Parameters:")
                for parameter in action.callback.parameters:
                    informer("      %s: %s" %(parameter.basename, 
                                              parameter.description))
                informer()
            informer()
            informer()
        informer("### END OF HELP ###")
        informer()
    else:
        if informer == commands.ClientSayCommand.INFORMER:
            informer = functools.partial(informer, user_ID)
        action = modules.Action.actions[action]
        message = "%s %s" %(action.basename.upper(), action.callback.syntax)
        if action.callback.description is not None:
            message += "~ %s" % action.callback.description
        informer(message)
        for parameter in action.callback.parameters:
            if parameter.description is not None:
                    informer("  %s: %s" %(parameter.basename, 
                                          parameter.description))
                                          
_help = modules.Action(_help_player, "help", 
                       "View the description and syntax information for an "
                       "action or overview the whole admin system by omitting " 
                       "a value", False)
_help.parameters.append(_action)
_core_actions.add(_help)

def _load_module(informer, module, user_ID=None, by_menu=False):
    es.server.queuecmd("es_xload admin/modules/%s" % module)
    
_load = modules.Action(_load_module, "load", 
                       "Load a module into the admin system")
_load.parameters.append(_unloaded_module)
_core_actions.add(_load)

def _menu(informer, user_ID=None, by_menu=False):
    modules.module_menu.send(user_ID)
    
_menu = modules.Action(_menu, "menu", "Open the admin menu", False, 
                       server_command=False)
_core_actions.add(_menu)

def _unload_module(informer, module, user_ID=None, by_menu=False):
    es.server.queuecmd("es_xunload admin/modules/%s" % module)
    modules.Module.modules[module].unload()
    
_unload = modules.Action(_unload_module, "unload",  
                         "Unload a module from the admin system")
_unload.parameters.append(_loaded_module)
_core_actions.add(_unload)

def load():
    _settings.execute()
    root = admins.Admin(str(_root_admin), "Root")
    root.permissions = modules.Action.permissions
    admin.announce("Loaded.")
    
def player_activate(event_var):
    if admins.is_user_authorised(event_var["es_steamid"]):
        admin.whisper(int(event_var["userid"]), 
                         "Welcome %s. Type %shelp in console or %shelp in "
                         "chat for more information." 
                         %(event_var["es_username"], metadata.CONSOLE_PREFIX, 
                           metadata.CHAT_PREFIX))
                           
def server_cvar(event_var):
    name = event_var["cvarname"]
    if name != metadata.LOG_ERRORS.getName():
        return
    exceptions.exception_manager.log = bool(int(event_var["cvarvalue"]))
    
def unload():
    for action in _core_actions:
        action.unload()
    for module in modules.Module.modules:
        _unload_module(module)
    admin.announce("Unloaded.")