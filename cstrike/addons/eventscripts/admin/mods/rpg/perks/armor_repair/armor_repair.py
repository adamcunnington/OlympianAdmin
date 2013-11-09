# <path to game directory>/addons/eventscipts/admin/mods/rpg/perks/
# armor_repair/armor_repair.py
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
    if old_level == 0:
        delay = _delays[user_ID] = delays.Delay(_repair_armor, user_ID, 
                                                rpg.Player.players[user_ID].ID)
        if not players.Player(user_ID).dead:
            delay.start(5, True)


def player_death(event_var):
    delay = _delays.get(int(event_var["userid"]))
    if delay is not None:
        delay.stop()


def player_disconnect(event_var):
    user_ID = int(event_var["userid"])
    if user_ID in _delays:
        delay = _delays.pop(user_ID)
        delay.stop()


def player_spawn(event_var):
    user_ID = int(event_var["userid"])
    if players.Player(user_ID).team_ID not in (players.TERRORIST, 
                                               players.COUNTER_TERRORIST):
        return
    with rpg.SessionWrapper() as session:
        player_ID = rpg.Player.players[user_ID].ID
        if not session.query(rpg.PlayerPerk.level).filter(
                rpg.PlayerPerk.player_ID == player_ID, 
                rpg.PlayerPerk.perk_ID == _armor_repair.record.ID).scalar():
            return
    delay = _delays.get(user_ID)
    if delay is None:
        delay = _delays[user_ID] = delays.Delay(_repair_armor, user_ID, 
                                                player_ID)
        delay.start(5, True)
    elif not delay.running:
        delay.start(5, True)


def _repair_armor(user_ID, player_ID):
    player = players.Player(user_ID)
    if player.armor >= 100:
        return
    with rpg.SessionWrapper() as session:
        armor_repair_level = session.query(rpg.PlayerPerk.level).filter(
                    rpg.PlayerPerk.player_ID == player_ID, 
                    rpg.PlayerPerk.perk_ID == _armor_repair.record.ID).scalar()
    armor_bonus = _armor_repair.perk_calculator(armor_repair_level)
    if 100 - player.armor < armor_bonus:
        player.armor = 100
    else:
        player.armor += armor_bonus


def _unload():
    while _delays:
        user_ID, delay = _delays.popitem()
        delay.stop()


_armor_repair = rpg.Perk("armor_repair", 5, lambda x: x, 
                         lambda x: 5 * 2**(x-1), _unload, _level_change)