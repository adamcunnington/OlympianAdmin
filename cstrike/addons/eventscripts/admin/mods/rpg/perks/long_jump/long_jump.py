# <path to game directory>/addons/eventscipts/admin/mods/rpg/perks/
# long_jump/long_jump.py
# by Adam Cunnington

from __future__ import with_statement

from esutils import players
from rpg import rpg


def player_jump(event_var):
    user_ID = int(event_var["userid"])
    with rpg.SessionWrapper() as session:
        player_perk = session.query(rpg.PlayerPerk).filter(
            rpg.PlayerPerk.player_ID == rpg.Player.players[user_ID].ID, 
            rpg.PlayerPerk.perk_ID == _long_jump.record.ID).first()
        if player_perk is None:
            return
    players.Player(user_ID).push(float(player_perk.level * 0.1), 0)


_long_jump = rpg.Perk("long_jump", 5, lambda x: x * 0.1, lambda x: x * 20)