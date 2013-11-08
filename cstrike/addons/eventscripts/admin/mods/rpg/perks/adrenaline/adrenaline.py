# <path to game directory>/addons/eventscipts/admin/mods/rpg/perks/
# adrenaline/adrenaline.py
# by Adam Cunnington

from __future__ import with_statement

from esutils import delays, players, weapons
from rpg import rpg

_delays = {}


def player_death(event_var):
    user_ID = int(event_var["userid"])
    if user_ID in _delays:
        _stop_perk(user_ID)
        _remove_effects(players.Player(user_ID)


def player_disconnect(event_var):
    user_ID = int(event_var["userid"])
    if user_ID in _delays:
        _stop_perk(user_ID)


def player_hurt(event_var):
    user_ID = int(event_var["userid"])
    if (not int(event_var["attacker"]) or 
        weapons.transform_weapon_name(event_var["weapon"]) == "weapon_knife"):
        return
    with rpg.SessionWrapper() as session:
        player_perk = session.query(rpg.PlayerPerk).filter(
            rpg.PlayerPerk.player_ID == rpg.Player.players[user_ID].ID, 
            rpg.PlayerPerk.perk_ID == _adrenaline.record.ID).first()
    if player_perk is None:
        return
    player = players.Player(user_ID)
    player.speed = _adrenaline.perk_calculator(player_perk.level)
    player.colour = (255, 0, 0, 255)
    delay = _delays[user_ID] = delays.Delay(_remove_effects, player)
    delay.start(1.5)


def _remove_effects(player):
    player.speed = 1
    player.colour = (255, 255, 255, 255)


def _stop_perk(user_ID):
    delay = _delays.pop(user_ID)
    delay.stop()


def _unload():
    for user_ID in _delays[:]:
        _stop_perk(user_ID)
        _remove_effects(players.Player(user_ID)


_adrenaline = rpg.Perk("adrenaline", 5, lambda x: 1 + (x * 0.2), 
                       lambda x: x * 25, _unload)
