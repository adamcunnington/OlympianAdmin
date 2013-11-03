# <path to game directory>/addons/eventscipts/admin/mods/rpg/perks/
# health/health.py
# by Adam Cunnington

from __future__ import with_statement

from esutils import players
from rpg import rpg


def _change_max_health(user_ID, player, player_perk, old_level, new_level):
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
        player_perk = session.query(rpg.PlayerPerk).filter(
            rpg.PlayerPerk.player_ID == rpg.Player.players[user_ID].ID, 
            rpg.PlayerPerk.perk_ID == _health.record.ID).first()
        if player_perk is None:
            return
        player.health = _health.perk_calculator(player_perk.level)


def _reset_health():
    for player in players.all_players():
        if player.health > 100:
            player.health = 100


_health = rpg.Perk("health", 16, lambda x: (x * 25) + 100, lambda x: x * 15, 
                   _reset_health, _change_max_health)