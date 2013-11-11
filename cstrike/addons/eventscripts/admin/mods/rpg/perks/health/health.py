# <path to game directory>/addons/eventscipts/admin/mods/rpg/perks/
# health/health.py
# by Adam Cunnington

import psyco
psyco.full()

from esutils import players
from rpg import rpg


def _level_change(user_ID, player_perk, old_level, new_level):
    if new_level == 0:
        new_max_health = 100
    else:
        new_max_health = _health.perk_calculator(new_level)
    player = players.Player(user_ID)
    if player.health > new_max_health:
        player.health = new_max_health


def player_spawn(event_var):
    user_ID = int(event_var["userid"])
    player = players.Player(user_ID)
    if player.team_ID not in (players.TERRORIST, players.COUNTER_TERRORIST):
        return
    health_level = rpg.get_level(user_ID, _health)
    if not health_level:
        return
    player.health = _health.perk_calculator(health_level)


def unload():
    all_players = players.all_players()
    for player in rpg.all_players(all_players.health > 100):
        player.health = 100


_health = rpg.PerkManager("health", 16, lambda x: (x*25) + 100,
                          lambda x: x * 15, _level_change)