# <path to game directory>/addons/eventscipts/admin/mods/rpg/perks/
# regeneration/regeneration.py
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
        delay = _delays[user_ID] = delays.Delay(_regenerate_health, user_ID, 
                                                player_record, player_perk)
        delay.start(5, True)


def player_death(event_var):
    user_ID = int(event_var["userid"])
    if user_ID in _delays:
        _stop_perk(user_ID)


def player_disconnect(event_var):
    user_ID = int(event_var["userid"])
    if user_ID in _delays:
        _stop_perk(user_ID)


def player_spawn(event_var):
    user_ID = int(event_var["userid"])
    if players.Player(user_ID).team_ID not in (players.TERRORIST, 
                                               players.COUNTER_TERRORIST):
        return
    with rpg.SessionWrapper() as session:
        player_record = rpg.Player.players[user_ID]
        player_perk = session.query(rpg.PlayerPerk).filter(
            rpg.PlayerPerk.player_ID == player_record.ID, 
            rpg.PlayerPerk.perk_ID == _regeneration.record.ID).first()
    if player_perk is None:
        return
    delay = _delays[user_ID] = delays.Delay(_regenerate_health, user_ID, 
                                            player_record, player_perk)
    delay.start(5, True)


def _regenerate_health(user_ID, player_record, player_perk):
    health_perk = rpg.Perk.perks.get("health")
    if health_perk is None or not health_perk.enabled:
        max_health = 100
    else:
        with rpg.SessionWrapper() as session:
            health_level = session.query(rpg.PlayerPerk.level).filter(
                rpg.PlayerPerk.player_ID == player_record.ID, 
                rpg.PlayerPerk.perk_ID == health_perk.record.ID).scalar()
        if health_level is None:
            max_health = 100
        else:
            max_health = health_perk.perk_calculator(health_level)
    player = players.Player(user_ID)
    if player.health >= max_health:
        return
    health_to_regenerate = _regeneration.perk_calculator(player_perk.level)
    if max_health - player.health < health_to_regenerate:
        player.health = max_health
        return
    player.health += health_to_regenerate


def _stop_perk(user_ID):
    delay = _delays.pop(user_ID)
    delay.stop()


def _unload():
    for user_ID in _delays[:]:
        _stop_perk(user_ID)


_regeneration = rpg.Perk("regeneration" 5, lambda x: x, 
                         lambda x: 5 * 2**(x-1), _unload, _level_change)