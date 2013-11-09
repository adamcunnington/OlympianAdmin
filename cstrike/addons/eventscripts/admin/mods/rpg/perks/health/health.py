# <path to game directory>/addons/eventscipts/admin/mods/rpg/perks/
# health/health.py
# by Adam Cunnington

from __future__ import with_statement

from esutils import players
from rpg import rpg


def _level_change(user_ID, player, player_perk, old_level, new_level):
    if new_level == 0:
        new_max_health = 100
    else:
        new_max_health = _health.perk_calculator(new_level)
    player = players.Player(user_ID)
    if player.health > new_max_health:
        player.health = new_max_health


def player_spawn(event_var):
    user_ID = int(event_var["userid"])
    player = players.Player(user_ID)
    if player.team_ID not in (players.TERRORIST, players.COUNTER_TERRORIST):
        return
    with rpg.SessionWrapper() as session:
        health_level = session.query(rpg.PlayerPerk.level).filter(
                rpg.PlayerPerk.player_ID == rpg.Player.players[user_ID].ID,
                rpg.PlayerPerk.perk_ID == _health.record.ID).scalar()
    if not health_level:
        return
    player.health = _health.perk_calculator(health_level)


def _unload():
    all_players = players.all_players()
    for player in all_players(all_players.health > 100):
        player.health = 100


_health = rpg.Perk("health", 16, lambda x: (x * 25) + 100, lambda x: x * 15,
                   _unload, _level_change)