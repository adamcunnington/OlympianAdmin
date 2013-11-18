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
from esutils import delays, menus, messages, players, tools


__all__ = (
    "RPGError",
    "Player",
    "PlayerPerk",
    "Perk",
    "get_level"
    )

_Base = declarative_base()

_BOTS_EXP_VS_BOTS_MULTIPLIER = 1
_BOTS_EXP_ATTACKER_MULTIPLIER = 1
_BOTS_EXP_EVENTS_MULTIPLIER = 1
_BOTS_EXP_VICTIM_MULTIPLIER = 1
_BOTS_MAX_LEVEL = 0
_BOTS_RELATIVE_PERKS = True

_CREDITS_INCREMENT = 5
_CREDITS_SELL_MULTIPLIER = 1
_CREDITS_START = 10000
_DATABASE_SAVE_INTERVAL = 300
_EXP_BOMB_DEFUSE = 50
_EXP_BOMB_EXPLODE = 50
_EXP_BOMB_PLANT = 25
_EXP_DAMAGE_MULTIPLIER = 0.01
_EXP_HEADSHOT = 50
_EXP_HOSTAGE_FOLLOW = 25
_EXP_HOSTAGE_RESCUE = 50
_EXP_INCREMENT = 50 # Need to catch any value update and process.
_EXP_KILL = 25
_EXP_LEVEL_ONE = 250 # Need to catch any value update and process.
_EXP_RELATIVE_MULTIPLIER = True
_MIN_LEVEL_TO_RANK = 3


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
    def _load_player(cls, user_ID, steam_ID, name):
        with _QuerySessionWrapper() as session:
            player = session.query(Player).filter(Player.steam_ID ==
                                                  steam_ID).first()
        if player is None:
            player = cls(steam_ID, name)
            with _CommitSessionWrapper() as session:
                session.add(player)
        else:
            if player.steam_ID != players.BOT_STEAM_ID:
                player.name = name.decode("UTF-8").encode("latin-1").decode("UTF-8")  # Fix
        cls.data[user_ID] = player
        for perk_basename in PerkManager.data:
            if PerkManager.data[perk_basename].enabled:
                PlayerPerk._load_player_perk(user_ID, perk_basename)

    @classmethod
    def _get_buy_description(cls, user_ID):
        return ":: Perk Buy Menu (%s Credits)" % cls.data[user_ID].credits

    @classmethod
    def _get_sell_description(cls, user_ID):
        return ":: Perk Sell Menu (%s Credits)" % cls.data[user_ID].credits

    @classmethod
    def _get_stats_description(cls, user_ID):
        return ":: Player Perks: %s" % players.Player(user_ID).name

    @classmethod
    def _get_buy_items(cls, user_ID):
        player = cls.data[user_ID]
        for perk_manager in sorted(PerkManager.data.itervalues(),
                                   key=lambda perk_manager:
                                   perk_manager.perk.verbose_name):
            if not perk_manager.enabled:
                yield menus.MenuOption("%s -> [DISABLED]" %
                                       perk_manager.perk.verbose_name,
                                       selectable=False)
                continue
            else:
                # Declare variable for readable line lengths.
                _basename = perk_manager.perk.basename
                player_perk = PlayerPerk.data[user_ID][_basename]
                if player_perk.level >= perk_manager.max_level:
                    yield menus.MenuOption("%s -> %s [MAXED]" %(
                                           perk_manager.perk.verbose_name,
                                           player_perk.level),
                                           selectable=False)
                    continue
                else:
                    next_level = player_perk.level + 1
                    cost = perk_manager.cost_calculator(next_level)
                    selectable = cost <= player.credits
                    yield menus.MenuOption("%s -> %s [%s Credits]" %(
                                           perk_manager.perk.verbose_name,
                                           next_level, cost), (player,
                                           perk_manager, player_perk,
                                           next_level, -cost), selectable)

    @classmethod
    def _get_sell_items(cls, user_ID):
        for perk_manager in sorted(PerkManager.data.itervalues(),
                                   key=lambda perk_manager:
                                   perk_manager.perk.verbose_name):
            if not perk_manager.enabled:
                yield menus.MenuOption("%s -> [DISABLED]" %
                                       perk_manager.perk.verbose_name,
                                       selectable=False)
                continue
            else:
                # Declare variable for readable line lengths.
                _basename = perk_manager.perk.basename
                player_perk = PlayerPerk.data[user_ID][_basename]
                if player_perk.level == 0:
                    yield menus.MenuOption("%s -> [NO LEVEL]" %
                                           perk_manager.perk.verbose_name,
                                           selectable=False)
                    continue
                else:
                    cost = int(perk_manager.cost_calculator(player_perk.level)
                               * _CREDITS_SELL_MULTIPLIER)
                    yield menus.MenuOption("%s -> %s [%s Credits]" %(
                                           perk_manager.perk.verbose_name,
                                           player_perk.level, cost),
                                           (cls.data[user_ID], perk_manager,
                                           player_perk, player_perk.level - 1,
                                           cost))

    @classmethod
    def _get_stats_items(cls, user_ID):
        for perk_manager in sorted(PerkManager.data.itervalues(),
                                   key=lambda perk_manager:
                                   perk_manager.perk.verbose_name):
            # Declare variable for readable line lengths.
            _basename = perk_manager.perk_basename
            yield menus.MenuOption("%s: Level %s" %(
                                   perk_manager.perk.verbose_name,
                                   PlayerPerk.data[user_ID][_basename]),
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
    def load_perk(cls, basename, verbose_name):
        with _QuerySessionWrapper() as session:
            perk = session.query(_Perk).filter(_Perk.basename ==
                                               basename).first()
        if perk is None:
            perk = cls(basename, verbose_name)
            with _CommitSessionWrapper() as session:
                session.add(perk)
        for player in players.all_players():
            PlayerPerk._load_player_perk(player.user_ID, perk.basename)
        return perk


class PlayerPerk(_Base):
    __tablename__ = "Players Perks"
    data = {}

    player_ID = Column(Integer, ForeignKey(Player.ID), primary_key=True)
    perk_ID = Column(Integer, ForeignKey(_Perk.ID), primary_key=True)
    level = Column(Integer, nullable=False)
    players = relationship(Player, backref=Player.__tablename__)
    perks = relationship(_Perk, backref=_Perk.__tablename__)

    def __init__(self, player_ID, perk_ID, level=0):
        self.player_ID = player_ID
        self.perk_ID = perk_ID
        self.level = level

    @classmethod
    def _load_player_perk(cls, user_ID, perk_basename):
        player_ID = Player.data[user_ID].ID
        perk_ID = PerkManager.data[perk_basename].perk.ID
        with _QuerySessionWrapper() as session:
            player_perk = session.query(PlayerPerk).filter(PlayerPerk.player_ID
                                                           == player_ID,
                                                           PlayerPerk.perk_ID
                                                           == perk_ID).first()
        if player_perk is None:
            player_perk = cls(player_ID, perk_ID)
            with _CommitSessionWrapper() as session:
                session.add(player_perk)
        player_perks = cls.data.get(user_ID)
        if player_perks is None:
            player_perks = cls.data[user_ID] = {}
        player_perks[perk_basename] = player_perk


class PerkManager(object):
    data = {}

    def __init__(self, basename, max_level, perk_calculator, cost_calculator,
                 level_change_callable=None, verbose_name=None):
        if basename in self.data:
            raise RPGError("a perk with basename, %s, is already registered" %
                           basename)
        self.max_level = max_level
        self.perk_calculator = perk_calculator
        self.cost_calculator = cost_calculator
        self.level_change_callable = level_change_callable
        if verbose_name is None:
            verbose_name = tools.format_verbose_name(basename)
        self.perk = _Perk.load_perk(basename, verbose_name)
        with _CommitSessionWrapper() as session:
            session.add(self.perk)
        self.data[basename] = self
        self.enabled = True

    def unload(self):
        es.server.queuecmd("es_xunload rpg/perks/%s" % self.basename)
        self.enabled = False


def get_level(user_ID, perk_manager):
    return PlayerPerk.data[user_ID][perk_manager.perk.basename].level


def _get_top_items(user_ID):
    with _QuerySessionWrapper() as session:
        _players = session.query(Player).filter(Player.steam_ID !=
                                                players.BOT_STEAM_ID,
                                                Player.level >=
                                                _MIN_LEVEL_TO_RANK).order_by(
                                                Player.level).limit(
                                                _rpg_top_menu.max_items).all()
    for player in _players:
        try:
            # Declare variable for readable line lengths.
            _key = players.get_player_from_steam_ID(player.steam_ID).user_ID
            player = Player.data[_key]
        except KeyError:
            pass
        yield menus.MenuOption("%s: Level %s" %(player.name, player.level),
                               selectable=False)


def _level_up(player, levels=1):
    if (player.steam_ID == players.BOT_STEAM_ID and _BOTS_MAX_LEVEL != 0 and
        player.level > _BOTS_MAX_LEVEL):
            return
    player.level += levels
    player.credits += levels * _CREDITS_INCREMENT


def load():
    for player in players.all_players():
        Player._load_player(player.user_ID, player.steam_ID, player.name)
    if _DATABASE_SAVE_INTERVAL > 0:
        _commit_delay.start(_DATABASE_SAVE_INTERVAL, True)


def bomb_defused(event_var):
    user_ID = int(event_var["userid"])
    if players.Player(user_ID).bot:
        if _BOTS_EXP_EVENTS_MULTIPLIER == 0:
            return
        _process_exp(user_ID, _EXP_BOMB_DEFUSE * _BOTS_EXP_EVENTS_MULTIPLIER)
    _process_exp(user_ID, _EXP_BOMB_DEFUSE)


def bomb_exploded(event_var):
    exp = _EXP_BOMB_EXPLODE
    user_ID = int(event_var["userid"])
    if players.Player(user_ID).bot:
        if _BOTS_EXP_EVENTS_MULTIPLIER == 0:
            return
        exp *= _BOTS_EXP_EVENTS_MULTIPLIER
    _process_exp(user_ID, exp)


def bomb_planted(event_var):
    exp = _EXP_BOMB_PLANT
    user_ID = int(event_var["userid"])
    if players.Player(user_ID).bot:
        if _BOTS_EXP_EVENTS_MULTIPLIER == 0:
            return
        exp *= _BOTS_EXP_EVENTS_MULTIPLIER
    _process_exp(user_ID, exp)


def hostage_follows(event_var):
    exp = _EXP_HOSTAGE_FOLLOW
    user_ID = int(event_var["userid"])
    if players.Player(user_ID).bot:
        if _BOTS_EXP_EVENTS_MULTIPLIER == 0:
            return
        exp *= _BOTS_EXP_EVENTS_MULTIPLIER
    _process_exp(user_ID, exp)


def hostage_rescued(event_var):
    exp = _EXP_HOSTAGE_RESCUE
    user_ID = int(event_var["userid"])
    if players.Player(user_ID).bot:
        if _BOTS_EXP_EVENTS_MULTIPLIER == 0:
            return
        exp *= _BOTS_EXP_EVENTS_MULTIPLIER
    _process_exp(user_ID, exp)


def player_connect(event_var):
    user_ID = int(event_var["userid"])
    name = "BOT" if players.Player(user_ID).bot else event_var["name"]
    Player._load_player(user_ID, event_var["networkid"], name)


def player_changename(event_var):
    Player.data[int(event_var["userid"])].name = event_var["newname"]


def player_death(event_var):
    attacker_ID = int(event_var["attacker"])
    if attacker_ID == players.WORLD:
        return
    attacker_is_bot = players.Player(attacker_ID).bot
    victim_ID = int(event_var["userid"])
    victim_is_bot = players.Player(victim_ID).bot
    exp = _EXP_KILL * _EXP_DAMAGE_MULTIPLIER
    if attacker_is_bot:
        if victim_is_bot:
            if _BOTS_EXP_VS_BOTS_MULTIPLIER == 0:
                return
            exp *= _BOTS_EXP_VS_BOTS_MULTIPLIER
        else:
            if _BOTS_EXP_ATTACKER_MULTIPLIER == 0:
                return
            exp *= _BOTS_EXP_ATTACKER_MULTIPLIER
    elif victim_is_bot:
        if _BOTS_EXP_VICTIM_MULTIPLIER == 0:
            return
        exp *= _BOTS_EXP_VICTIM_MULTIPLIER
    _process_exp(attacker_ID, exp)


def player_disconnect(event_var):
    user_ID = int(event_var["userid"])
    with _CommitSessionWrapper() as session:
        session.add(Player.data[user_ID])
        session.add_all(PlayerPerk.data[user_ID].itervalues())
    del Player.data[user_ID]
    del PlayerPerk.data[user_ID]


def player_hurt(event_var):
    attacker_ID = int(event_var["attacker"])
    if attacker_ID == players.WORLD:
        return
    attacker_is_bot = players.Player(attacker_ID).bot
    victim_ID = int(event_var["userid"])
    victim_is_bot = players.Player(victim_ID).bot
    exp = int(event_var["dmg_health"]) * _EXP_DAMAGE_MULTIPLIER
    if attacker_is_bot:
        if victim_is_bot:
            if _BOTS_EXP_VS_BOTS_MULTIPLIER == 0:
                return
            exp *= _BOTS_EXP_VS_BOTS_MULTIPLIER
        else:
            if _BOTS_EXP_ATTACKER_MULTIPLIER == 0:
                return
            exp *= _BOTS_EXP_ATTACKER_MULTIPLIER
    elif victim_is_bot:
        if _BOTS_EXP_VICTIM_MULTIPLIER == 0:
            return
        exp *= _BOTS_EXP_VICTIM_MULTIPLIER
    elif _EXP_RELATIVE_MULTIPLIER:
        with _QuerySessionWrapper() as session:
            # Declare variable for readable line lengths.
            _query = session.query(Player.level).order_by(Player.level)
            top_level = _query.limit(1).scalar()
        attacker_index = Player.data.get(attacker_ID).level/top_level * 100
        victim_index = (Player.data.get(int(event_var["userid"])).level
                        /top_level) * 100
        multiplier = min(1, max(attacker_index / victim_index, 100) ** 0.5)
        exp *= multiplier
    if int(event_var["hitgroup"]) == 1:
        exp += _EXP_HEADSHOT
    _process_exp(attacker_ID, exp)


def player_say(event_var):
    text = event_var["text"]
    user_ID = int(event_var["userid"])
    if text == "rpgmenu":
        _rpg_buy_menu.send(user_ID)
    elif text == "rpgrank":
        player = Player.data[user_ID]
        if player.level < _MIN_LEVEL_TO_RANK:
            messages.whisper(user_ID, "${teamcolour}%s${yellow}, you need to "
                             "reach level %s to rank." %(player.name,
                                                         _MIN_LEVEL_TO_RANK))
            return
        with _QuerySessionWrapper() as session:
            position = session.query(func.count(Player.ID)).filter(
                                     Player.steam_ID != players.BOT_STEAM_ID,
                                     Player.level < player.level,
                                     Player.exp < player.exp).scalar()
            total_ranked = session.query(func.count(Player.ID)).filter(
                                         Player.steam_ID !=
                                         players.BOT_STEAM_ID, Player.level >=
                                         _MIN_LEVEL_TO_RANK).scalar()
        messages.whisper(user_ID, "${teamcolour}%s${yellow}, you are ranked "
                         "${green}%s/%s${yellow}, at level "
                         "${green}%s${yellow} with ${green}%s ${yellow}exp. "
                         "and ${green}%s ${yellow}credits." %(
                         players.Player(user_ID).name, position + 1,
                         total_ranked, player.level, player.exp,
                         player.credits))
    elif text =="rpgsell":
        _rpg_sell_menu.send(user_ID)
    elif text =="rpgstats":
        _rpg_stats_menu.send(user_ID)
    elif text =="rpgtop":
        _rpg_top_menu.send(user_ID)


def _process_exp(target, exp, offline=False):
    exp = int(exp)
    if not offline:
        player = Player.data.get(target)
    else:
        player = target
    exp += player.exp
    surplus_exp = exp-_EXP_LEVEL_ONE + (player.level*_EXP_INCREMENT)
    if surplus_exp > 0:
        level_ups = 0
        while surplus_exp > 0:
            level_ups += 1
            exp = surplus_exp
            surplus_exp -= (_EXP_LEVEL_ONE +
                            ((player.level+level_ups)*_EXP_INCREMENT))
        _level_up(player, level_ups)
    player.exp = exp
    if offline:
        with _CommitSessionWrapper() as session:
            session.add(player)


def round_end(event_var=None):
    objects_to_commit = []
    bot_ID = None
    for player in players.all_players():
        objects_to_commit.append(Player.data[player.user_ID])
        objects_to_commit.extend(PlayerPerk.data[player.user_ID].itervalues())
        if player.bot:
            bot_ID = player.user_ID
    with _CommitSessionWrapper() as session:
        session.add_all(objects_to_commit)
    if bot_ID is not None:
        bot = Player.data[bot_ID]
        if _BOTS_RELATIVE_PERKS:
            player_perk_levels = {}
            for players_perks in PlayerPerk.data.itervalues():
                for perk_basename in players_perks:
                    player_perk = players_perks[perk_basename]
                    if player_perk.player_ID == bot.ID:
                        continue
                    levels = player_perk_levels.get(perk_basename)
                    if levels is None:
                        levels = player_perk_levels[perk_basename] = []
                    levels.append(player_perk.level)
            for perk_basename in player_perk_levels:
                levels = player_perk_levels[perk_basename]
                perk_manager = PerkManager.data[perk_basename]
                if not perk_manager.enabled:
                    continue
                average_level = int(sum(levels) / len(levels))
                player_perk = PlayerPerk.data[bot_ID][perk_basename]
                _set_level(bot_ID, perk_manager, player_perk,
                           player_perk.level, average_level)
        else:
            bot_player_perks = PlayerPerk.data[bot_ID]
            bot_perk_options = {}
            for perk_basename in PerkManager.data:
                perk_manager = PerkManager.data[perk_basename]
                if not perk_manager.enabled:
                    continue
                bot_perk_options[perk_basename] = (bot_player_perks[
                                                   perk_basename].level + 1)
            while True:
                next_perk = PerkManager.data[sorted(bot_perk_options,
                                                    key=lambda perk_basename:
                                                    PerkManager.data[
                                                    perk_basename].
                                                    cost_calculator(
                                                    bot_perk_options[
                                                    perk_basename]))[0]]
                cost = next_perk.cost_calculator(bot_perk_options[
                                                 next_perk.perk.basename])
                if bot.credits < cost:
                    break
                player_perk = bot_player_perks[next_perk.perk.basename]
                bot.credits -= cost
                _set_level(bot_ID, next_perk, player_perk,
                           player_perk.level, player_perk.level + 1)
                bot_perk_options[next_perk.perk.basename] += 1


_commit_delay = delays.Delay(round_end)


def _rpg_menu_callback(user_ID, (player, perk_manager, player_perk, next_level,
                                 cost)):
    player.credits += cost
    _set_level(user_ID, perk_manager, player_perk, player_perk.level,
               next_level)


_rpg_buy_menu = menus.Menu(_rpg_menu_callback,
                           get_description=Player._get_buy_description,
                           get_items=Player._get_buy_items, resend=True)
_rpg_buy_menu.title = "OLYMPIAN# RPG"
_rpg_sell_menu = menus.Menu(_rpg_menu_callback,
                            get_description=Player._get_sell_description,
                            get_items=Player._get_sell_items, resend=True)
_rpg_sell_menu.title = "OLYMPIAN# RPG"


_rpg_stats_menu = menus.Menu(get_description=Player._get_stats_description,
                             get_items=Player._get_stats_items)
_rpg_stats_menu.title = "OLYMPIAN# RPG"


_rpg_top_menu = menus.Menu(get_items=_get_top_items)
_rpg_top_menu.title = "OLYMPIAN# RPG"
_rpg_top_menu.description = "Top Ranked"


def _set_level(user_ID, perk_manager, player_perk, old_level, new_level):
    player_perk.level = new_level
    if perk_manager.level_change_callable is not None:
        perk_manager.level_change_callable(user_ID, player_perk, old_level,
                                           player_perk.level)


def unload():
    if _commit_delay.running:
        _commit_delay.stop()
    objects_to_commit = []
    for player in players.all_players():
        objects_to_commit.append(Player.data[player.user_ID])
        objects_to_commit.extend(PlayerPerk.data[player.user_ID].values())
    with _CommitSessionWrapper() as session:
        session.add_all(objects_to_commit)
    while PerkManager.data:
        basename, perk = PerkManager.data.popitem()
        perk.unload()
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