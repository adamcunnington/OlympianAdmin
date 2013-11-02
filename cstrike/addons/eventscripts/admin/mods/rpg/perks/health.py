# <path to game directory>/addons/eventscipts/admin/mods/rpg/perks/
# health.py
# by Adam Cunnington

from esutils import players
from rpg import rpg

def player_spawn(event_var):
    pass

def reset_health():
    for player in players.all_players():
        if player.health >= 100:
            player.health = 100

_health = rpg.Perk("health", reset_health, 10, 16, lambda x: (x * 25) + 100, 
                   lambda x: x * 10)