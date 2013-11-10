# <path to game directory>/addons/eventscipts/admin/mods/rpg/
# rpg.py
# by Adam Cunnington

from __future__ import with_statement
import os

import psyco
psyco.full()

from sqlalchemy import (Column, func, create_engine, event, ForeignKey,
                        Integer, String, Unicode)
from sqlalchemy.orm import relationship, sessionmaker
from sqlalchemy.ext.declarative import declarative_base

import es
from esutils import menus, messages, players, tools


__all__ = (
    "RPGError",
    "Player",
    "PlayerPerk",
    "Perk",
    "get_level"
    )

_Base = declarative_base()

### SETTINGS START ###
_EXP_BOMB_DEFUSE = 50
_EXP_BOMB_EXPLODE = 50
_EXP_BOMB_PLANT = 25
_EXP_DAMAGE_MULTIPLIER = 1
_EXP_HEADSHOT = 50
_EXP_HOSTAGE_FOLLOW = 25
_EXP_HOSTAGE_RESCUE = 50
_EXP_INCREMENT = 50 # Need to catch any value update and process.
_EXP_KILL = 50
_EXP_LEVEL_ONE = 250 # Need to catch any value update and process.
_EXP_RELATIVE_MULTIPLIER = True
_CREDITS_INCREMENT = 5
_CREDITS_SELL_MULTIPLIER = 1.0
_CREDITS_START = 10000

_BOTS_EXP_VS_BOTS_MULTIPLIER = 1
_BOTS_EXP_ATTACKER_MULTIPLIER = 1
_BOTS_EXP_EVENTS_MULTIPLIER = 1
_BOTS_EXP_VICTIM_MULTIPLIER = 1
_BOTS_MAX_LEVEL = 0
_BOTS_RANK = False
_BOTS_RELATIVE_PERKS = True


class RPGError(Exception):
    """General error encountered relating to admin.mods.rpg"""
    pass


class Player(_Base):
    __tablename__ = "Players"
    data = {}

    ID = Column(Integer, primary_key=True, autoincrement=True)
    steam_ID = Column(String, nullable=False)
    name = Column(Unicode, nullable=False)
    exp = Column(Integer, default=0, nullable=False)
    level = Column(Integer, default=1, nullable=False)
    credits = Column(Integer, default=_CREDITS_START, nullable=False)

    def __init__(self, steam_ID, name):
        self.steam_ID = steam_ID
        self.name = name

    @classmethod
    def _add_player(cls, user_ID, steam_ID, name):
        with _QuerySessionWrapper() as session:
            player = session.query(Player).filter(Player.steam_ID ==
                                                  steam_ID).first()
        if player is None:
            player = cls(steam_ID, name)
            with _CommitSessionWrapper() as session:
                session.add(player)
        else:
            player.name = name.decode("UTF-8").encode("latin-1").decode("UTF-8")  # Fix
        cls.data[user_ID] = player
        PlayerPerk._load_player_perks(user_ID, player.ID)

    @classmethod
    def _get_buy_description(cls, user_ID):
        return ":: Perk Buy Menu (%s Credits)" % cls.data[user_ID].credits

    @classmethod
    def _get_sell_description(cls, user_ID):
        return ":: Perk sell Menu (%s Credits)" % cls.data[user_ID].credits

    @classmethod
    def _get_stats_description(cls, user_ID):
        return ":: Player Perks: %s" % players.Player(user_ID).name

    @classmethod
    def _get_buy_items(cls, user_ID):
        player = cls.data[user_ID]
        player_perks = PlayerPerk.data[user_ID]
        for perk in sorted(_Perk.data.itervalues(), key=lambda perk:
                           getattr(perk, "verbose_name")):
            perk_manager = PerkManager.data.get(perk.basename)
            if perk_manager is None or not perk_manager.enabled:
                yield menus.MenuOption("%s -> [DISABLED]" % perk.verbose_name,
                                       selectable=False)
                continue
            else:
                player_perk = player_perks.get(perk.basename)
                if player_perk is None:
                    next_level = 1
                else:
                    if player_perk.level >= perk_manager.max_level:
                        yield menus.MenuOption("%s -> %s [MAXED]" %(
                                               perk.verbose_name,
                                               player_perk.level),
                                               selectable=False)
                        continue
                    else:
                        next_level = player_perk.level + 1
                cost = perk_manager.cost_calculator(next_level)
                selectable = cost <= player.credits
                yield menus.MenuOption("%s -> %s [%s Credits]" %(
                                       perk.verbose_name, next_level, cost),
                                       (player, perk_manager, player_perk,
                                       next_level, cost), selectable)

    @classmethod
    def _get_sell_items(cls, user_ID):
        player = cls.data[user_ID]
        player_perks = PlayerPerk.data[user_ID]
        for perk in sorted(_Perk.data.itervalues(), key=lambda perk:
                           getattr(perk, "verbose_name")):
            perk_manager = PerkManager.data.get(perk.basename)
            if perk_manager is None or not perk_manager.enabled:
                yield menus.MenuOption("%s -> [DISABLED]" % perk.verbose_name,
                                       selectable=False)
                continue
            else:
                player_perk = player_perks.get(perk.basename)
                if player_perk is None or player_perk.level == 0:
                    yield menus.MenuOption("%s -> [NO LEVEL]" %
                                           perk.verbose_name, selectable=False)
                    continue
                else:
                    next_level = player_perk.level - 1
                    cost = (perk_manager.cost_calculator(player_perk.level)
                            * _CREDITS_SELL_MULTIPLIER)
                    yield menus.MenuOption("%s -> %s [%s Credits]" %(
                                           perk.verbose_name,
                                           player_perk.level, cost),
                                           (player, perk_manager, player_perk,
                                            next_level, cost))

    @classmethod
    def _get_stats_items(cls, user_ID):
        player_perks = PlayerPerk.data[user_ID]
        for perk in sorted(_Perk.data.itervalues(), key=lambda perk:
                           getattr(perk, "verbose_name")):
            player_perk = player_perks.get(perk.basename)
            yield menus.MenuOption("%s: Level %s"
                                   %(perk.verbose_name, player_perk.level
                                     if player_perk is not None else 0),
                                   selectable=False)


class _Perk(_Base):
    __tablename__ = "Perks"

    ID = Column(Integer, primary_key=True, autoincrement=True)
    basename = Column(String, nullable=False)
    verbose_name = Column(String, nullable=False)

    def __init__(self, basename, verbose_name):
        self.basename = basename
        self.verbose_name = verbose_name

    @classmethod
    def add_perk(cls, basename, verbose_name):
        if basename in cls.data:
            return cls.data[basename]
        with _QuerySessionWrapper() as session:
            perk = session.query(_Perk).filter(_Perk.basename ==
                                               basename).first()
        if perk is None:
            perk = cls(basename, verbose_name)
            with _CommitSessionWrapper() as session:
                session.add(perk)
        cls.data[perk.ID] = perk
        return perk

    @classmethod
    def load_perks(cls):
        with _QuerySessionWrapper() as session:
            cls.data = dict((perk.ID, perk) for perk in
                            session.query(_Perk).all())


class PlayerPerk(_Base):
    __tablename__ = "Players Perks"
    data = {}

    player_ID = Column(Integer, ForeignKey(Player.ID), primary_key=True)
    perk_ID = Column(Integer, ForeignKey(_Perk.ID), primary_key=True)
    level = Column(Integer, nullable=False)
    players = relationship(Player, backref=Player.__tablename__)
    perks = relationship(_Perk, backref=_Perk.__tablename__)

    def __init__(self, user_ID, player_ID, perk_ID, perk_basename):
        self.player_ID = player_ID
        self.perk_ID = perk_ID
        self.level = 1
        self.data[user_ID][perk_basename] = self

    @classmethod
    def _load_player_perks(cls, user_ID, player_ID):
        with _QuerySessionWrapper() as session:
            player_perks = session.query(PlayerPerk).filter(
                                    PlayerPerk.player_ID == player_ID).all()
        cls.data[user_ID] = dict(
                (_Perk.data[player_perk.perk_ID].basename,
                 player_perk) for player_perk in player_perks)


class PerkManager(object):
    data = {}

    def __init__(self, basename, max_level, perk_calculator,
                 cost_calculator, level_change_callable=None,
                 verbose_name=None):
        if basename in self.data:
            raise RPGError("a perk with basename, %s, is already registered"
                           % basename)
        self.max_level = max_level
        self.perk_calculator = perk_calculator
        self.cost_calculator = cost_calculator
        self.level_change_callable = level_change_callable
        if verbose_name is None:
            verbose_name = tools.format_verbose_name(basename)
        self.perk = _Perk.add_perk(basename, verbose_name)
        with _CommitSessionWrapper() as session:
            session.add(self.perk)
        self.data[basename] = self
        self.enabled = True

    def unload(self):
        es.server.queuecmd("es_xunload rpg/perks/%s" % self.basename)
        self.enabled = False


def get_level(user_ID, perk_manager):
    perk = PlayerPerk.data[user_ID].get(perk_manager.perk.basename)
    return perk.level if perk is not None else perk


def _get_top_items(user_ID):
    with _QuerySessionWrapper() as session:
        players = session.query(Player).order_by(Player.level).limit(
                                                _rpg_top_menu.max_items).all()
    for player in players:
        yield menus.MenuOption("%s: Level %s" %(player.name, player.level),
                               selectable=False)

def _level_up(player, levels=1):
    player.level += levels
    player.credits += levels * _CREDITS_INCREMENT


def load():
    _Perk.load_perks()
    for player in players.all_players():
        Player._add_player(player.user_ID, player.steam_ID, player.name)


def bomb_defused(event_var):
    _process_exp(int(event_var["userid"]), _EXP_BOMB_DEFUSE)


def bomb_exploded(event_var):
    _process_exp(int(event_var["userid"]), _EXP_BOMB_EXPLODE)


def bomb_planted(event_var):
    _process_exp(int(event_var["userid"]), _EXP_BOMB_PLANT)


def hostage_follows(event_var):
    _process_exp(int(event_var["userid"]), _EXP_HOSTAGE_FOLLOW)


def hostage_rescued(event_var):
    _process_exp(int(event_var["userid"]), _EXP_HOSTAGE_RESCUE)


def player_connect(event_var):
    user_ID = int(event_var["userid"])
    name = "BOT" if players.Player(user_ID).bot else event_var["name"]
    Player._add_player(user_ID, event_var["networkid"], name)


def player_changename(event_var):
    Player.data[int(event_var["userid"])].name = event_var["newname"]


def player_death(event_var):
    attacker_ID = int(event_var["attacker"])
    exp = _EXP_KILL
    if _EXP_RELATIVE_MULTIPLIER:
        with _QuerySessionWrapper() as session:
            top_level = session.query(Player.level).order_by(
                                                Player.level).limit(1).scalar()
        attacker_index = Player.data.get(attacker_ID).level/top_level * 100
        victim_index = (Player.data.get(int(event_var["userid"])).level
                        /top_level) * 100
        multiplier = min(1, max(attacker_index / victim_index, 100) ** 0.5)
        exp = int(exp * multiplier)
    _process_exp(attacker_ID, exp)
    user_ID = int(event_var["userid"])
    with _CommitSessionWrapper() as session:
        session.add(Player.data[user_ID])
        session.add_all(PlayerPerk.data[user_ID].itervalues())


def player_disconnect(event_var):
    user_ID = int(event_var["userid"])
    with _CommitSessionWrapper() as session:
        session.add(Player.data[user_ID])
        session.add_all(PlayerPerk.data[user_ID].itervalues())
    del Player.data[user_ID]
    del PlayerPerk.data[user_ID]


def player_hurt(event_var):
    attacker_ID = int(event_var["attacker"])
    exp = int(event_var["dmg_health"])
    if int(event_var["hitgroup"]) == 1:
        exp += _EXP_HEADSHOT
    exp *= _EXP_DAMAGE_MULTIPLIER
    if _EXP_RELATIVE_MULTIPLIER:
        with _QuerySessionWrapper() as session:
            top_level = session.query(Player.level).order_by(
                                                Player.level).limit(1).scalar()
        attacker_index = Player.data.get(attacker_ID).level/top_level * 100
        victim_index = (Player.data.get(int(event_var["userid"])).level
                        /top_level) * 100
        multiplier = min(1, max(attacker_index / victim_index, 100) ** 0.5)
        exp = int(exp * multiplier)
    _process_exp(attacker_ID, exp)


def player_say(event_var):
    text = event_var["text"]
    user_ID = int(event_var["userid"])
    if text == "rpgmenu":
        _rpg_buy_menu.send(user_ID)
    elif text == "rpgrank":
        player = Player.data[user_ID]
        with _QuerySessionWrapper() as session:
            position = session.query(func.count(Player.ID)).filter(Player.level
                                                < player.level).scalar() + 1
            total_ranked = session.query(func.count(Player.ID)).scalar()
        messages.whisper(user_ID, "${teamcolour}%s${yellow}, you are ranked "
                         "${green}%s/%s${yellow}, at level "
                         "${green}%s${yellow} with ${green}%s ${yellow}exp. "
                         "and ${green}%s ${yellow}credits."
                         %(players.Player(user_ID).name, position,
                           total_ranked, player.level,
                           player.exp, player.credits))
    elif text =="rpgsell":
        _rpg_sell_menu.send(user_ID)
    elif text =="rpgstats":
        _rpg_stats_menu.send(user_ID)
    elif text =="rpgtop":
        _rpg_top_menu.send(user_ID)


def _process_exp(target, exp, offline=False):
    if offline is False:
        player = Player.data.get(user_ID)
    else:
        player = target
    player_exp = player.exp + exp
    surplus_exp = player_exp-_EXP_LEVEL_ONE + (player.level*_EXP_INCREMENT)
    if surplus_exp > 0:
        level_ups = 0
        while player_exp > 0:
            level_ups += 1
            player_exp -= (_EXP_LEVEL_ONE +
                           ((player.level+level_ups)*_EXP_INCREMENT))
        _level_up(player, level_ups)
    player.exp = player_exp
    if offline is True:
        with _CommitSessionWrapper() as session:
            session.add(player)


def round_end(event_var):
    objects_to_commit = []
    for player in players.all_players():
        objects_to_commit.append(Player.data[player.user_ID])
        objects_to_commit.extend(PlayerPerk.data[player.user_ID].itervalues())
    with _CommitSessionWrapper() as session:
        session.add_all(objects_to_commit)


def _rpg_buy_menu_callback(user_ID, (player, perk_manager, player_perk, level,
                                 cost)):
    player.credits -= cost
    if player_perk is None:
        old_level = 0
        player_perk = PlayerPerk(user_ID, player.ID, perk_manager.perk.ID,
                                 perk_manager.perk.basename)
    else:
        old_level = player_perk.level
        player_perk.level += 1
    if perk_manager.level_change_callable is not None:
        perk_manager.level_change_callable(user_ID, player, player_perk,
                                           old_level, player_perk.level)


_rpg_buy_menu = menus.Menu(_rpg_buy_menu_callback,
                           get_description=Player._get_buy_description,
                           get_items=Player._get_buy_items, resend=True)
_rpg_buy_menu.title = "OLYMPIAN# RPG"


def _rpg_sell_menu_callback(user_ID, (player, perk_manager, player_perk, level,
                                 cost)):
    player.credits += cost
    old_level = player_perk.level
    player_perk.level -= 1
    if perk_manager.level_change_callable is not None:
        perk_manager.level_change_callable(user_ID, player, player_perk,
                                           old_level, player_perk.level)


_rpg_sell_menu = menus.Menu(_rpg_sell_menu_callback,
                            get_description=Player._get_sell_description,
                            get_items=Player._get_sell_items, resend=True)
_rpg_sell_menu.title = "OLYMPIAN# RPG"


_rpg_stats_menu = menus.Menu(get_description=Player._get_stats_description,
                             get_items=Player._get_stats_items)
_rpg_stats_menu.title = "OLYMPIAN# RPG"


_rpg_top_menu = menus.Menu(get_items=_get_top_items)
_rpg_top_menu.title = "OLYMPIAN# RPG"
_rpg_top_menu.description = "Top Ranked"


def unload():
    objects_to_commit = []
    for player in players.all_players():
        objects_to_commit.append(Player.data[player.user_ID])
        objects_to_commit.extend(PlayerPerk.data[player.user_ID].values())
    with _CommitSessionWrapper() as session:
        session.add_all(objects_to_commit)
    while PerkManager.data:
        basename, perk = PerkManager.data.popitem()
        perk.unload()
    _Perk.data.clear()
    Player.data.clear()
    PlayerPerk.data.clear()


_engine = create_engine("sqlite:///%s" %
                        os.path.join(os.path.dirname(__file__), "players.db"))
_Base.metadata.create_all(_engine)

@event.listens_for(_engine, "connect")
def receive_connect(connection, connection_record):
    connection.execute("PRAGMA JOURNAL_MODE = WAL")
    connection.execute("PRAGMA SYNCHRONOUS = OFF")
    connection.execute("PRAGMA FOREIGN_KEYS = ON")


class _QuerySessionWrapper(object):
    Session = sessionmaker(bind=_engine, expire_on_commit=False)

    def __enter__(self):
        self.session = self.Session()
        return self.session

    def __exit__(self, exc_type, exc_value, traceback):
        self.session.close()


class _CommitSessionWrapper(_QuerySessionWrapper):
    def __exit__(self, exc_type, exc_value, traceback):
        try:
            if exc_value is None:
                self.session.commit()
        finally:
            self.session.close()