# <path to game directory>/addons/eventscipts/admin/mods/rpg/perks/
# ammo_replenish_ammo/ammo_replenish_ammo.py
# by Adam Cunnington

from __future__ import with_statement

from esutils import delays, players, weapons
from rpg import rpg

_delays = {}


def _level_change(user_ID, player_record, player_perk, old_level, new_level):
    if new_level == 0:
        if user_ID in _delays:
            delay = _delays.pop(user_ID)
            if delay.running:
                delay.stop()
    elif old_level == 0:
        delay = _delays[user_ID] = delays.Delay(_replenish_ammo, 
                                                players.Player(user_ID))
        if not players.Player(user_ID).dead:
            delay.start(_ammo_replenish.perk_calculator(new_level), True)
    else:
        delay = _delays.get(user_ID)
        if delay is None:
            delay = _delays[user_ID] = delays.Delay(_replenish_ammo, 
                                                players.Player(user_ID))
            if not players.Player(user_ID).dead:
                delay.start(_ammo_replenish.perk_calculator(new_level), True)
        elif delay.running:
            delay.interval = _ammo_replenish.perk_calculator(new_level)


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
    player = players.Player(user_ID)
    if player.team_ID not in (players.TERRORIST, players.COUNTER_TERRORIST):
        return
    with rpg.SessionWrapper() as session:
        player_ID = rpg.Player.players[user_ID].ID
        ammo_replenish_level = session.query(rpg.PlayerPerk.level).filter(
                rpg.PlayerPerk.player_ID == player_ID, 
                rpg.PlayerPerk.perk_ID == _ammo_replenish.record.ID).scalar()
    if not ammo_replenish_level:
        return
    delay = _delays.get(user_ID)
    if delay is None:
        delay = _delays[user_ID] = delays.Delay(_replenish_ammo, player)
        delay.start(_ammo_replenish.perk_calculator(ammo_replenish_level), 
                    True)
    elif not delay.running:
        delay.start(_ammo_replenish.perk_calculator(ammo_replenish_level), 
                    True)


def _replenish_ammo(player):
    active_weapon = player.active_weapon
    if player.active_weapon is None:
        return
    if active_weapon.weapon_type.CATEGORY == weapons.CATEGORY_MELEE:
        active_weapon = player.primary or player.secondary or None
        if active_weapon is None:
            return
    ammo_bonus = max(int(active_weapon.weapon_type.clip_size / 10), 1)
    if active_weapon.weapon_type.max_ammo - active_weapon.ammo <= ammo_bonus:
        active_weapon.ammo = active_weapon.weapon_type.max_ammo
    else:
        active_weapon.ammo += ammo_bonus


def _unload():
    while _delays:
        user_ID, delay = _delays.popitem()
        delay.stop()


_ammo_replenish = rpg.Perk("ammo_replenish_ammo", 5, lambda x: 5 * (7-x), 
                           lambda x: 5 * 2**(x-1), _unload, _level_change)