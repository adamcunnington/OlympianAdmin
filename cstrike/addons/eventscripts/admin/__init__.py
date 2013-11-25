# <path to game directory>/addons/eventscripts/admin/
# __init__.py
# by Adam Cunnington

from admin import metadata


__all__ = (
    "announce_text",
    "inform_text"
    )


def announce_text(text, action_information=False, colours_supported=True):
    if not colours_supported:
        return "(BOT) %s: %s" %(metadata.BOT_NAME, text)
    if not action_information:
        colour = "yellow"
    else:
        colour = "lightgreen"
    return "${green}(BOT) %s: ${%s}%s" %(metadata.BOT_NAME, colour, text)


def whisper_text(text, colours_supported=True):
    if not colours_supported:
        return "(PRIVATE) %s: %s" %(metadata.BOT_NAME, text)
    else:
        return "${green}(PRIVATE) %s: ${yellow}%s" %(metadata.BOT_NAME, text)