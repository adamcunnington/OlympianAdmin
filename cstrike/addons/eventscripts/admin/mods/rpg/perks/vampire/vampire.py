# <path to game directory>/addons/eventscipts/admin/mods/rpg/perks/
# vampire/vampire.py
# by Adam Cunnington

import psyco
psyco.full()

from esutils import players
from rpg import rpg


def player_hurt(event_var):
    attacker_ID = int(event_var["attacker"])
    if attacker_ID == players.WORLD:
        return
    vampire_level = rpg.get_level(attacker_ID, _vampire)
    if vampire_level == 0:
        return
    health = rpg.PerkManager.data.get("health")
    if health is None or not health.enabled:
        max_health = 100
    else:
        health_level = rpg.get_level(attacker_ID, health)
        if health_level == 0:
            max_health = 100
        else:
            max_health = health.perk_calculator(health_level)
    health_bonus = int(event_var[
            "dmg_health"]) * _vampire.perk_calculator(vampire_level)
    player = players.Player(attacker_ID)
    if max_health - int(event_var["es_attackerhealth"]) <= health_bonus:
       player.health = max_health
    else:
        player.health += health_bonus


_vampire = rpg.PerkManager("vampire", 8, lambda x: x * 0.1, lambda x: x * 20)
