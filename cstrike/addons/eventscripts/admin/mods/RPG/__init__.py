# <path to game directory>/addons/eventscipts/admin/mods/rpg/
# __init__.py
# by Adam Cunnington

from __future__ import with_statement
import os

from sqlalchemy import Column, create_engine, ForeignKey, Integer, Unicode
from sqlalchemy.orm import relationship, sessionmaker
from sqlalchemy.ext.declarative import declarative_base

import es
from esutils import menus, players, tools

__all__ = ( 
    "Player", 
    "PlayerPerk", 
    "Perk", 
    "SessionWrapper", 
    )

_Base = declarative_base()

class Player(_Base):
    __tablename__ = "players"
    _players = {}

    ID = Column(Integer, primary_key=True, autoincrement=True)
    steam_ID = Column(Unicode)
    name = Column(Unicode)
    experience_points = Column(Integer, default=0)
    level = Column(Integer, default=0)
    credits = Column(Integer, default=50)
    
    def __init__(self, steam_ID, name):
        self.steam_ID = steam_ID
        self.name = name

class _Perk(_Base):
    __tablename__ = "perks"

    ID = Column(Integer, primary_key=True, autoincrement=True)
    basename = Column(Unicode)
    verbose_name = Column(Unicode)

    def __init__(self, basename, verbose_name):
        self.basename = basename
        self.verbose_name = verbose_name

class PlayerPerk(_Base):
    __tablename__ = "player_perks"

    player_ID = Column(Integer, ForeignKey(Player.ID), primary_key=True)
    perk_ID = Column(Integer, ForeignKey(_Perk.ID), primary_key=True)
    level = Column(Integer, default=1)
    players = relationship(Player, backref=Player.__tablename__)
    perks = relationship(_Perk, backref=_Perk.__tablename__)

    def __init__(self, player_ID, perk_ID):
        self.player_ID = player_ID
        self.perk_ID = perk_ID

class Perk(object):
    _perks = {}

    def __init__(self, basename, unload_callable, start_cost, max_level, 
                 perk_calculator, cost_calculator, level_up_callable=None, 
                 verbose_name=None):
        self.basename = basename
        self.unload_callable = unload_callable
        self.start_cost = start_cost
        self.max_level = max_level
        self.perk_calculator = perk_calculator
        self.cost_calculator = cost_calculator
        self.level_up_callable = level_up_callable
        if verbose_name is None:
            verbose_name = tools.format_verbose_name(basename)
        self.verbose_name = verbose_name
        with SessionWrapper() as session:
            record = session.query(_Perk).filter(_Perk.basename == 
                                                  basename).first()
            if record is not None:
                record = record
            else:
                record = _Perk(basename, verbose_name)
                session.add(record)
        self.enabled = True
        self._perks[basename] = self

def player_activate(event_var):
    steam_ID = event_var["es_steamid"]
    with SessionWrapper() as session:
        player = session.query(Player).filter(Player.steam_ID == 
                                              steam_ID).first()
        if player is None:
            player = Player(steam_ID, event_var["name"])
        else:
            player.name = event_var["name"]
        session.add(player)
        session.flush()
        session.expunge(player)
    Player._players[int(event_var["userid"])] = player

def player_changename(event_var):
    with SessionWrapper() as session:
        player = session.query(Player).filter(Player.steam_ID == 
                                              event_var["es_steamid"]).first()
        player.name = event_var["newname"]

def player_disconnect(event_var):
    user_ID = int(event_var["user_ID"])
    if user_ID in Player._players:
        Player._players.remove(user_ID)

def unload():
    for Perk in Perk._perks:
        Perk.unload_callable()

_engine = create_engine("sqlite:///%s" % os.path.join(
                                    os.path.dirname(__file__), "players.db"))
_Base.metadata.create_all(_engine)

class SessionWrapper(object):
    _Session = sessionmaker(bind=_engine)

    def __enter__(self):
        self.session = self._Session()
        return self.session

    def __exit__(self, exc_type, exc_value, traceback):
        if exc_value is None:
            self.session.commit()
        self.session.close()

def _rpg_menu_callback(user_ID, (player, perk, player_perk, level, cost)):
    player.credits -= cost
    player_perk.level += 1
    with SessionWrapper() as session:
        session.add(player)
    if perk.level_up_callable is not None:
        perk.level_up_callable(user_ID, level)
    _rpg_menu.send(user_ID)

def _get_description(user_ID):
    return ":: Buy Menu (%s Credits)" % Player._players[user_ID].credits

def _get_items(user_ID):
    items = []
    player = Player._players[user_ID]
    with SessionWrapper() as session:
        perk_records = session.query(_Perk).order_by(_Perk.verbose_name).all()
        for perk_record in perk_records:
            perk = Perk._perks[perk_record.basename]
            if perk_record.basename not in Perk._perks or not perk.enabled:
                items.append(menus.MenuOption("%s -> [DISABLED]" % 
                                   perk_record.verbose_name, selectable=False))
            else:
                player_perk = session.query(PlayerPerk).filter(
                                PlayerPerk.player_ID == player.ID, 
                                PlayerPerk.perk_ID == perk_record.ID).first()
                if player_perk is None:
                    player_perk = PlayerPerk(player.ID, perk_record.ID)
                    session.add(player_perk)
                    session.flush()
                    session.expunge(player_perk)
                if player_perk.level >= perk.max_level:
                    items.append(menus.MenuOption("%s -> %s [MAXED]" %(
                                 perk_record.verbose_name, player_perk.level), 
                                 selectable=False))
                else:
                    level = max(player_perk.level, 0) + 1
                    cost = perk.cost_calculator(level)
                    selectable = cost <= player.credits
                    items.append(menus.MenuOption("%s -> %s [%s Credits]" %(
                                 perk_record.verbose_name, level, cost), 
                                 (player, perk, player_perk, level, cost), 
                                 selectable))
    return items

_rpg_menu = menus.Menu(_rpg_menu_callback, get_description=_get_description, 
                       get_items=_get_items)
_rpg_menu.title = "OLYMPIAN# RPG"

def player_say(event_var):
    _rpg_menu.send(int(event_var["userid"]))
