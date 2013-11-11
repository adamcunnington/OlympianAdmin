# <path to game directory>/addons/eventscipts/admin/mods/rpg/perks/
# ice_stab/ice_stab.py
# by Adam Cunnington

import psyco
psyco.full()

from esutils import delays, players, weapons
from rpg import rpg

_delays = {}


def _level_change(user_ID, player_perk, old_level, new_level):
    if new_level == 0:
        if user_ID in _delays:
            delay = _delays.pop(user_ID)
            if delay.running:
                delay.stop()
        return


def player_death(event_var):
    user_ID = int(event_var["userid"])
    delay = _delays.get(user_ID)
    if delay is not None:
        if delay.running:
            delay.stop()
            _remove_effects(user_ID)


def player_disconnect(event_var):
    user_ID = int(event_var["userid"])
    if user_ID in _delays:
        delay = _delays.pop(user_ID)
        if delay.running:
            delay.stop()


def player_hurt(event_var):
    victim_ID = int(event_var["userid"])
    attacker_ID = int(event_var["attacker"])
    if (attacker_ID == players.WORLD or
        list(weapons.weapon_types_by_names(event_var["weapon"]))[0].CATEGORY
        != weapons.CATEGORY_MELEE):
        return
    ice_stab_level = rpg.get_level(attacker_ID, _ice_stab)
    if not ice_stab_level:
        return
    player = players.Player(victim_ID)
    player.speed = _ice_stab.perk_calculator(ice_stab_level)
    player.colour = (0, 255, 0, 255)
    delay = _delays.get(victim_ID)
    if delay is None:
        delay = _delays[victim_ID] = delays.Delay(_remove_effects, victim_ID)
        delay.start(1.5)
    else:
        if delay.running:
            delay.stop()
        delay.start(1.5)


def _remove_effects(user_ID):
    player = players.Player(user_ID)
    player.speed = 1
    stealth = rpg.PerkManager.data.get("stealth")
    if stealth is None or not stealth.enabled:
        max_alpha = 255
    else:
        stealth_level = rpg.get_level(user_ID, stealth)
        if not stealth_level:
            max_alpha = 255
        else:
            max_alpha = stealth.perk_calculator(stealth_level)
    player.colour = (255, 255, 255, max_alpha)


def unload():
    while _delays:
        user_ID, delay = _delays.popitem()
        delay.stop()
        if delay.running:
            _remove_effects(user_ID)


_ice_stab = rpg.PerkManager("ice_stab", 5, lambda x: 1 - x*0.1,
                            lambda x: x * 30, _level_change)