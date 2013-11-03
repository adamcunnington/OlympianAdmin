# <path to game directory>/addons/eventscipts/admin/mods/rpg/
# rpg.py
# by Adam Cunnington

from __future__ import with_statement
import os

from sqlalchemy import (Column, create_engine, ForeignKey, Integer, String, 
                        Unicode)
from sqlalchemy.orm import relationship, sessionmaker
from sqlalchemy.ext.declarative import declarative_base

from esutils import menus, players, tools


__all__ = ( 
    "Player", 
    "PlayerPerk", 
    "Perk", 
    "SessionWrapper", 
    )

_Base = declarative_base()


class Player(_Base):
    __tablename__ = "Players"
    players = {}

    ID = Column(Integer, primary_key=True, autoincrement=True)
    steam_ID = Column(String, nullable=False)
    name = Column(Unicode, nullable=False)
    experience_points = Column(Integer, default=0, nullable=False)
    level = Column(Integer, default=0, nullable=False)
    credits = Column(Integer, default=1500, nullable=False)

    def __init__(self, steam_ID, name):
        self.steam_ID = steam_ID
        self.name = name


class _Perk(_Base):
    __tablename__ = "Perks"

    ID = Column(Integer, primary_key=True, autoincrement=True)
    basename = Column(String, nullable=False)
    verbose_name = Column(String, nullable=False)

    def __init__(self, basename, verbose_name):
        self.basename = basename
        self.verbose_name = verbose_name


class PlayerPerk(_Base):
    __tablename__ = "Players Perks"

    player_ID = Column(Integer, ForeignKey(Player.ID), primary_key=True)
    perk_ID = Column(Integer, ForeignKey(_Perk.ID), primary_key=True)
    level = Column(Integer, default=1, nullable=False)
    players = relationship(Player, backref=Player.__tablename__)
    perks = relationship(_Perk, backref=_Perk.__tablename__)

    def __init__(self, player_ID, perk_ID):
        self.player_ID = player_ID
        self.perk_ID = perk_ID


class Perk(object):
    perks = {}

    def __init__(self, basename, max_level, perk_calculator, 
                 cost_calculator, unload_callable=None, 
                 level_change_callable=None, verbose_name=None):
        self.basename = basename
        self.max_level = max_level
        self.perk_calculator = perk_calculator
        self.cost_calculator = cost_calculator
        self.unload_callable = unload_callable
        self.level_change_callable = level_change_callable
        if verbose_name is None:
            verbose_name = tools.format_verbose_name(basename)
        self.verbose_name = verbose_name
        with SessionWrapper() as session:
            record = session.query(_Perk).filter(_Perk.basename == 
                                                  basename).first()
            if record is not None:
                self.record = record
            else:
                self.record = _Perk(basename, verbose_name)
                session.add(self.record)
        self.enabled = True
        self.perks[basename] = self


def player_activate(event_var):
    steam_ID = event_var["es_steamid"]
    with SessionWrapper() as session:
        player = session.query(Player).filter(Player.steam_ID == 
                                              steam_ID).first()
        name = event_var["es_username"]
        if player is None:
            player = Player(steam_ID, name)
        else:
            player.name = name.decode("UTF-8").encode("latin-1").decode(
                                                                       "UTF-8")
        session.add(player)
    Player.players[int(event_var["userid"])] = player


def player_changename(event_var):
    with SessionWrapper() as session:
        player = session.query(Player).filter(Player.steam_ID == 
                                              event_var["es_steamid"]).first()
        player.name = event_var["newname"]


def player_disconnect(event_var):
    user_ID = int(event_var["userid"])
    if user_ID in Player.players:
        del Player.players[user_ID]


def unload():
    for perk in Perk.perks.itervalues():
        if perk.unload_callable() is not None:
            perk.unload_callable()
        perk.enabled = False


_engine = create_engine("sqlite:///%s" % os.path.join(
                                    os.path.dirname(__file__), "players.db"))
_Base.metadata.create_all(_engine)


class SessionWrapper(object):
    _Session = sessionmaker(bind=_engine, expire_on_commit=False)

    def __enter__(self):
        self.session = self._Session()
        return self.session

    def __exit__(self, exc_type, exc_value, traceback):
        if exc_value is None:
            self.session.commit()
        self.session.close()


def _rpg_menu_callback(user_ID, (player, perk, player_perk, level, cost)):
    with SessionWrapper() as session:
        player.credits -= cost
        if player_perk is None:
            old_level = 0
            player_perk = PlayerPerk(player.ID, perk.record.ID)
            session.add(player_perk)
        else:
            old_level = player_perk.level
            player_perk.level += 1
        session.add_all((player, player_perk))
    if perk.level_change_callable is not None:
        perk.level_change_callable(user_ID, player, player_perk, old_level, 
                                   player_perk.level)
    _rpg_menu.send(user_ID)


def _get_description(user_ID):
    return ":: Buy Menu (%s Credits)" % Player.players[user_ID].credits


def _get_items(user_ID):
    items = []
    player = Player.players[user_ID]
    with SessionWrapper() as session:
        perk_records = session.query(_Perk).order_by(_Perk.verbose_name).all()
        for perk_record in perk_records:
            perk = Perk.perks.get(perk_record.basename)
            if perk is None or not perk.enabled:
                items.append(menus.MenuOption("%s -> [DISABLED]" % 
                                   perk_record.verbose_name, selectable=False))
            else:
                player_perk = session.query(PlayerPerk).filter(
                                PlayerPerk.player_ID == player.ID, 
                                PlayerPerk.perk_ID == perk_record.ID).first()
                if player_perk is None:
                    next_level = 1
                else:
                    if player_perk.level >= perk.max_level:
                        items.append(menus.MenuOption("%s -> %s [MAXED]" %(
                                     perk_record.verbose_name, 
                                     player_perk.level), selectable=False))
                        continue
                    next_level = player_perk.level + 1
                cost = perk.cost_calculator(next_level)
                selectable = cost <= player.credits
                items.append(menus.MenuOption("%s -> %s [%s Credits]" %(
                             perk_record.verbose_name, next_level, cost), 
                             (player, perk, player_perk, next_level, cost), 
                             selectable))
    return items


_rpg_menu = menus.Menu(_rpg_menu_callback, get_description=_get_description, 
                       get_items=_get_items)
_rpg_menu.title = "OLYMPIAN# RPG"


def player_say(event_var):
    _rpg_menu.send(int(event_var["userid"]))