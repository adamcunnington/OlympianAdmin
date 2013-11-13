# <path to game directory>/addons/eventscipts/admin/mods/rpg/perks/
# adrenaline/adrenaline.py
# by Adam Cunnington

import psyco
psyco.full()

from esutils import delays, players
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
    if (int(event_var["attacker"]) == players.WORLD or
        int(event_var["hitgroup"]) != 1):
        return
    adrenaline_level = rpg.get_level(victim_ID, _adrenaline)
    if adrenaline_level == 0:
        return
    player = players.Player(victim_ID)
    player.speed = _adrenaline.perk_calculator(adrenaline_level)
    player.colour = (255, 0, 0, 255)
    delay = _delays.get(victim_ID)
    if delay is None:
        delay = _delays[victim_ID] = delays.Delay(_remove_effects, victim_ID)
        delay.start(1.2)
    else:
        if delay.running:
            delay.stop()
        delay.start(1.2)


def _remove_effects(user_ID):
    player = players.Player(user_ID)
    player.speed = 1
    stealth = rpg.PerkManager.data.get("stealth")
    if stealth is None or not stealth.enabled:
        max_alpha = 255
    else:
        stealth_level = rpg.get_level(user_ID, stealth)
        if stealth_level == 0:
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


_adrenaline = rpg.PerkManager("adrenaline", 5, lambda x: 1 + (x*0.2),
                              lambda x: x * 25, _level_change)
