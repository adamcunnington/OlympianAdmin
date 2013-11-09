# <path to game directory>/addons/eventscipts/admin/mods/rpg/perks/
# stealth/stealth.py
# by Adam Cunnington

from __future__ import with_statement

from esutils import players
from rpg import rpg


def _level_change(user_ID, player, player_perk, old_level, new_level):
    player = players.Player(user_ID)
    if new_level == 0:
        player.colour = (255, 255, 255, 255)
    else:
        _set_colour(player, new_level)


def player_spawn(event_var):
    user_ID = int(event_var["userid"])
    player = players.Player(user_ID)
    if players.Player(user_ID).team_ID not in (players.TERRORIST, 
                                               players.COUNTER_TERRORIST):
        return
    with rpg.SessionWrapper() as session:
        player_perk = session.query(rpg.PlayerPerk).filter(
                rpg.PlayerPerk.player_ID == rpg.Player.players[user_ID].ID, 
                rpg.PlayerPerk.perk_ID == _stealth.record.ID).first()
    if player_perk is None or player_perk.level == 0:
        return
    _set_colour(player, player_perk.level)


def _set_colour(player, level):
    player.colour = (255, 255, 255, 
                     int(255 * (1 - _stealth.perk_calculator(level))))


def _unload():
    for player in players.all_players():
        player.colour = (255, 255, 255, 255)


_stealth = rpg.Perk("stealth", 5, lambda x: x * 0.1, lambda x: x * 30, 
                    _unload, _level_change)