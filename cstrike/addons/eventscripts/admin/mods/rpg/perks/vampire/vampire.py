# <path to game directory>/addons/eventscipts/admin/mods/rpg/perks/
# vampire/vampire.py
# by Adam Cunnington

from __future__ import with_statement

from esutils import players
from rpg import rpg


def player_hurt(event_var):
    attacker = int(event_var["attacker"])
    if attacker = players.WORLD:
        return
    player_record = rpg.Player.players[attacker]
    with rpg.SessionWrapper() as session:
        player_perk = session.query(rpg.PlayerPerk).filter(
            rpg.PlayerPerk.player_ID == player_record.ID, 
            rpg.PlayerPerk.perk_ID == _vampire.record.ID).first()
    if player_perk is None or player_perk.level == 0:
        return
    health_perk = rpg.Perk.perks.get("health")
    if health_perk is None or not health_perk.enabled:
        max_health = 100
    else:
        with rpg.SessionWrapper() as session:
            health_level = session.query(rpg.PlayerPerk.level).filter(
                rpg.PlayerPerk.player_ID == player_record.ID, 
                rpg.PlayerPerk.perk_ID == health_perk.record.ID).scalar()
        if not health_level:
            max_health = 100
        else:
            max_health = health_perk.perk_calculator(health_level)
    health_bonus = int(event_var[
            "dmg_health"]) * _vampire.perk_calculator(player_perk.level)
    player = players.Player(attacker)
    if max_health - int(event_var["es_attackerhealth"]) <= health_bonus:
       player.health = max_health
    else:
        player.health += health_bonus


_vampire = rpg.Perk("vampire", 8, lambda x: x * 0.1, lambda x: x * 20)