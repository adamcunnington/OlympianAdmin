# <path to game directory>/addons/eventscipts/admin/mods/rpg/perks/
# armor_repair/armor_repair.py
# by Adam Cunnington

from __future__ import with_statement

from esutils import delays, players
from rpg import rpg

_delays = {}


def _level_change(user_ID, player_record, player_perk, old_level, new_level):
    if new_level == 0 and user_ID in _delays:
        delay = _delays.pop(user_ID)
        delay.stop()
        return
    if user_ID not in _delays:
        delay = _delays[user_ID] = delays.Delay(_repair_armor, user_ID, 
                                                player_perk)
        delay.start(5, True)


def player_death(event_var):
    _stop_perk(int(event_var["userid"]))


def player_disconnect(event_var):
    _stop_perk(int(event_var["userid"]))


def player_spawn(event_var):
    user_ID = int(event_var["userid"])
    if players.Player(user_ID).team_ID not in (players.TERRORIST, 
                                               players.COUNTER_TERRORIST):
        return
    with rpg.SessionWrapper() as session:
        player_record = rpg.Player.players[user_ID]
        player_perk = session.query(rpg.PlayerPerk).filter(
            rpg.PlayerPerk.player_ID == player_record.ID, 
            rpg.PlayerPerk.perk_ID == armor_repair.record.ID).first()
    if player_perk is None:
        return
    delay = _delays[user_ID] = delays.Delay(_repair_armor, user_ID, 
                                            player_perk)
    delay.start(5, True)


def _repair_armor(user_ID, player_perk):
    player = players.Player(user_ID)
    armor_to_repair = armor_repair.perk_calculator(player_perk.level)
    if 100 - player.armor < armor_to_repair:
        player.armor = max_armor
        return
    player.armor += armor_to_repair


def _stop_perk(user_ID):
    if user_ID in _delays:
        delay = _delays.pop(user_ID)
        delay.stop()


def _unload():
    while _delays:
        user_ID, delay = _delays.popitem()
        delay.stop()


armor_repair = rpg.Perk("armor_repair" 5, lambda x: x, lambda x: 5 * 2**(x-1), 
                        _unload, _level_change)