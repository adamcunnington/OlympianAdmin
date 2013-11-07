# <path to game directory>/addons/eventscipts/admin/mods/rpg/perks/
# long_jump/freeze_stab.py
# by Adam Cunnington

from __future__ import with_statement

import es
from esutils import delays, players, weapons
from rpg import rpg

_delays = {}


def player_death(event_var):
    user_ID = int(event_var["userid"])
    _stop_delay(user_ID)
    _remove_effects(players.Player(user_ID))


def player_disconnect(event_var):
    _stop_delay(int(event_var["userid"]))


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


def _reset_effects():
    all_players = players.all_players()
    for player in all_players.filter(~all_players.dead):
        _remove_effects(player)
    _delays.clear()


def _stop_delay(user_ID):
    if user_ID in _delays:
        delay = _delays.pop(user_ID)
        delay.stop()


_freeze_stab = rpg.Perk("freeze_stab", 5, lambda x: 1 - (x * 0.15), 
                        lambda x: x * 30, _reset_effects())