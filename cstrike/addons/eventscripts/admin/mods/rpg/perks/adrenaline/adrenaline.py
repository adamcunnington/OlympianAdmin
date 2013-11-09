# <path to game directory>/addons/eventscipts/admin/mods/rpg/perks/
# adrenaline/adrenaline.py
# by Adam Cunnington

from __future__ import with_statement

from esutils import delays, players
from rpg import rpg

_delays = {}

def _level_change(user_ID, player_record, player_perk, old_level, new_level):
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
    user_ID = int(event_var["userid"])
    if (int(event_var["attacker"]) == players.WORLD or 
        int(event_var["hitgroup"]) != 1):
        return
    with rpg.SessionWrapper() as session:
        adrenaline_level = session.query(rpg.PlayerPerk.level).filter(
                rpg.PlayerPerk.player_ID == rpg.Player.players[user_ID].ID, 
                rpg.PlayerPerk.perk_ID == _adrenaline.record.ID).scalar()
    if not adrenaline_level:
        return
    player = players.Player(user_ID)
    player.speed = _adrenaline.perk_calculator(adrenaline_level)
    player.colour = (255, 0, 0, 255)
    delay = _delays.get(user_ID)
    if delay is None:
        delay = _delays[user_ID] = delays.Delay(_remove_effects, user_ID)
        delay.start(1.2)
    else:
        if delay.running:
            delay.stop()
        delay.start(1.2)


def _remove_effects(user_ID):
    player = players.Player(user_ID)
    player.speed = 1
    stealth_perk = rpg.Perk.perks.get("stealth")
    if stealth_perk is None or not stealth_perk.enabled:
        max_alpha = 255
    else:
        with rpg.SessionWrapper() as session:
            stealth_level = session.query(rpg.PlayerPerk.level).filter(
                rpg.PlayerPerk.player_ID == rpg.Player.players[user_ID].ID, 
                rpg.PlayerPerk.perk_ID == stealth_perk.record.ID).scalar()
        if not stealth_level:
            max_alpha = 255
        else:
            max_alpha = stealth_perk.perk_calculator(stealth_level)
    player.colour = (255, 255, 255, max_alpha)


def _unload():
    while _delays:
        user_ID, delay = _delays.popitem()
        delay.stop()
        _remove_effects(user_ID)


_adrenaline = rpg.Perk("adrenaline", 5, lambda x: 1 + (x * 0.2), 
                       lambda x: x * 25, _unload, _level_change)