# <path to game directory>/addons/eventscripts/admin/
# metadata.py
# by Adam Cunnington

import es

AUTHOR = "Adam Cunnington"
BASENAME = "olympianadmin"
BOT_NAME = "OLYMPIAN# Bouncer"
CONSOLE_PREFIX = "oa_"
CHAT_PREFIX = "@"
LOG_ERRORS = es.ServerVar("%slog_errors" % CONSOLE_PREFIX, 0)
VERBOSE_NAME = "Team Olympia - Admin"
VERSION = es.ServerVar("%sversion" % CONSOLE_PREFIX, "1.0 ALPHA")