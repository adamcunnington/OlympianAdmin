# <path to game directory>/addons/eventscipts/admin/mods/rpg/perks/
# ice_stab/ice_stab.py
# by Adam Cunnington

from __future__ import with_statement

from esutils import delays, players, weapons
from rpg import rpg

_delays = {}


def player_death(event_var):
    user_ID = int(event_var["userid"])
    if user_ID in _delays:
        _stop_perk(user_ID)


def player_disconnect(event_var):
    user_ID = int(event_var["userid"])
    if user_ID in _delays:
        _stop_perk(user_ID)


def player_hurt(event_var):
    user_ID = int(event_var["userid"])
    attacker = int(event_var["attacker"])
    if (not attacker or 
        weapons.transform_weapon_name(event_var["weapon"]) != "weapon_knife"):
        return
    with rpg.SessionWrapper() as session:
        player_perk = session.query(rpg.PlayerPerk).filter(
            rpg.PlayerPerk.player_ID == rpg.Player.players[attacker].ID, 
            rpg.PlayerPerk.perk_ID == _freeze_stab.record.ID).first()
    if player_perk is None:
        return
    player = players.Player(user_ID)
    player.speed = _freeze_stab.perk_calculator(player_perk.level)
    player.colour = (0, 255, 0, 255)
    delay = _delays[user_ID] = delays.Delay(_remove_effects, player)
    delay.start(1.5)


def _remove_effects(player):
    player.speed = 1
    player.colour = (255, 255, 255, 255)


def _stop_perk(user_ID):
    delay = _delays.pop(user_ID)
    delay.stop()
    _remove_effects(players.Player(user_ID)


def _unload():
    for user_ID in _delays[:]:
        _stop_perk(user_ID)


_freeze_stab = rpg.Perk("freeze_stab", 5, lambda x: 1 - (x * 0.15), 
                        lambda x: x * 30, _unload)