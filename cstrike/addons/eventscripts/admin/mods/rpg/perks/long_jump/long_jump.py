# <path to game directory>/addons/eventscipts/admin/mods/rpg/perks/
# long_jump/long_jump.py
# by Adam Cunnington

import psyco
psyco.full()

from esutils import players
from rpg import rpg


def player_jump(event_var):
    user_ID = int(event_var["userid"])
    long_jump_level = rpg.get_level(user_ID, _long_jump)
    if long_jump_level == 0:
        return
    players.Player(user_ID).push(float(long_jump_level * 0.1), 0)


_long_jump = rpg.PerkManager("long_jump", 5, lambda x: x * 0.1,
                             lambda x: x * 20)
