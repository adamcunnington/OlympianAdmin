# <path to game directory>/addons/eventscipts/admin/mods/rpg/
# __init__.py
# by Adam Cunnington

from sqlalchemy import Column, createengine, ForeignKey, Integer, Unicode
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
    __tablename__ = "players"
    players = {}
    
    ID = Column(Integer, primary_key=True, autoincrement=True)
    steam_ID = Column(Unicode)
    name = Column(Unicode)
    experience_points = Column(Integer, default=0)
    level = Column(Integer, default=1)
    credits = Column(Integer, default=DEFAULT_CREDITS)
    
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
    
    player_ID = Column(Integer, ForeignKey(Player.ID)
    perk_ID = Column(Integer, ForeignKey(_Perk.ID)
    level = Column(Integer, default=1)
    players = relationship(Player, backref=Player.__tablename__)
    perks = relationship(_Perk, backref=_Perk.__tablename__)
    
    def __init__(self, player_ID, perk_ID):
        self.player_ID = player_ID
        self.perk_ID = perk_ID
        
class Perk(object):
    _perks = set()
    
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
        if verbose_name = None:
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
        self._perks.add(self)
        
def es_player_validated(event_var):
    es.msg("fires")
    steam_ID = event_var["es_steamid"]
    with SessionWrapper() as session:
        player = session.query(Player).filter(Player.steam_ID == 
                                              steam_ID).first()
        if player is None:
            player = Player(steam_ID, event_var["name"])
            session.add(player)
        else:
            player.name = event_var["name"}
    Player.players[players.get_player_from_steam_ID(steam_ID).user_ID] = record
    
def player_changename(event_var):
    with SessionWrapper() as session:
        player = session.query(Player).filter(Player.steam_ID == 
                                              event_var["es_steamid"]).first()
        player.name = event_var["newname"]
        
def unload():
    for Perk in Perk._perks:
        Perk.unload_callable()
        
_engine = createengine("sqlite:///players.db")
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
        
def _get_description(user_ID):
    return ":: Buy Menu (%s Credits)" % Player.players[user_ID].credits
    
def _get_items(user_ID):
    items = []
    player = Player.players[user_ID]
    with SessionWrapper() as session:
        _perk_records = sesion.query(_Perk).order_by(_Perk.verbose_name).all()
        for ID, basename, verbose_name in _perk_records:
            if basename not in Perk._perks:
                items.append(menus.MenuOption("%s -> [DISABLED]" % 
                                       verbose_name), selectable=False)
            else:
                perk = Perk._perks[basename]
                player_perk = session.query(PlayerPerk).filter(
                                player_ID == player.ID, perk_ID = ID).first()
                if player_perk is None:
                    player_perk = PlayerPerk(player.ID, ID)
                
                if player_perk.level >= perk.max_level:
                    items.append(menus.MenuOption("%s -> %s [MAXED]" %(
                                 verbose_name, player_perk.level), 
                                 selectable=False))
                else:
                    level = player_perk.level += 1
                    cost = perk.cost_calculator(level)
                    selectable = cost <= player.credits:
                    items.append(menus.MenuOption("%s -> %s [%s Credits]" %(
                                 verbose_name, level, cost), (player, perk, 
                                 player_perk, level, cost)), selectable)
                                 
_rpg_menu = menus.Menu(_rpg_menu_callback, get_description=_get_description, 
                       get_items=_get_items)
_rpg_menu.title = "OLYMPIAN# RPG"

def player_say(event_var):
    _rpg_menu.send(int(event_var["userid"]))