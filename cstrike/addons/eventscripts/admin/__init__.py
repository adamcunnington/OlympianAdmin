# <path to game directory>/addons/eventscripts/admin/
# __init__.py
# by Adam Cunnington

from admin import metadata
from esutils import messages

class CommandsError(Exception):
    """General error encountered relating to esutils.commands"""

def announce(text, action_information=False):
    if not action_information:
        colour = "yellow"
    else:
        colour = "lightgreen"
    messages.announce("${green}(BOT) %s: ${%s}%s" %(metadata.BOT_NAME, colour,
                                                text))

def whisper(user_ID, text, index=None):
    messages.whisper(user_ID, "${green}(PRIVATE) %s: ${yellow}%s"
                              %(metadata.BOT_NAME, text), index)