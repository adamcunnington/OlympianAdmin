# <path to game directory>/addons/eventscipts/admin/mods/rpg/perks/
# stealth/stealth.py
# by Adam Cunnington

import psyco
psyco.full()

from esutils import players
from rpg import rpg


def _level_change(user_ID, player, player_perk, old_level, new_level):
    _player = players.Player(user_ID)
    if new_level == 0:
        _player.colour = (255, 255, 255, 255)
    else:
        _set_colour(_player, new_level)


def player_spawn(event_var):
    user_ID = int(event_var["userid"])
    player = players.Player(user_ID)
    if players.Player(user_ID).team_ID not in (players.TERRORIST,
                                               players.COUNTER_TERRORIST):
        return
    stealth_level = rpg.get_level(user_ID, _stealth)
    if not stealth_level:
        return
    _set_colour(player, stealth_level)


def _set_colour(player, level):
    player.colour = (255, 255, 255, _stealth.perk_calculator(level))


def unload():
    for player in players.all_players():
        player.colour = (255, 255, 255, 255)


_stealth = rpg.PerkManager("stealth", 5, lambda x: int(255 * (1 - x*0.1)),
                           lambda x: x * 30, _level_change)