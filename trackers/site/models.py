from trackers.shared import db
from datetime import datetime
import re

class Site(db.Model):

    __tablename__ = 'sitetracker_site'

    id = db.Column(db.Integer, primary_key=True)
    creator = db.Column(db.String(200))
    date = db.Column(db.DateTime)
    scanid = db.Column(db.String(7))
    name = db.Column(db.String(100))
    type_ = db.Column(db.String(100))
    system = db.Column(db.String(50))
    opened = db.Column(db.Boolean)
    closed = db.Column(db.Boolean)
    notes = db.Column(db.Text)
    snapshots = db.relationship('SiteSnapshot', backref='site', lazy='dynamic')
    
    def __init__(self, creator='__server__', date=None, name='', scanid='?', type_='',
            system='', opened=False, closed=False, notes=''):
        self.creator = creator
        self.date = date if date else datetime.utcnow()
        self.name = name
        self.scanid = scanid
        self.type_ = type_
        self.system = system
        self.opened = opened
        self.closed = closed
        self.notes = notes
    
    def __repr__(self):
        return '<Site {} {} {}>'.format(self.id, self.scanid, self.system)
    
    def is_site_object(self):
        return True

    @property
    def isAnom(self):
        return self.name in ['Common Perimeter Deposit', 'Average Frontier Deposit', \
        'Exceptional Core Deposit', 'Unexceptional Frontier Reservoir', 'Ordinary Permiter Deposit', \
        'Core Garrison', 'Core Stronghold', 'Oruze Osobnyk', 'Quarantine Area', 'Ordinary Perimeter Deposit', \
        'Rarified Core Deposit', 'Unexceptional Frontier Deposit']
    

class SiteSnapshot(db.Model):

    __tablename__ = 'sitetracker_sitesnapshot'

    id = db.Column(db.Integer, primary_key=True)
    site_id = db.Column(db.Integer, db.ForeignKey('sitetracker_site.id'))
    snapper = db.Column(db.String(200))
    changed = db.Column(db.Text)
    date = db.Column(db.DateTime)

    def __init__(self, site_id, snapper, changed, date=None):
        self.site_id = site_id
        self.snapper = snapper
        self.changed = changed
        self.date = date if date else datetime.utcnow()
    
    def __repr__(self):
        return '<SiteSnapshot {} {}>'.format(self.id, self.site)


class Wormhole(db.Model):

    __tablename__ = 'sitetracker_wormhole'

    id = db.Column(db.Integer, primary_key=True)
    creator = db.Column(db.String(200))
    date = db.Column(db.DateTime)
    scanid = db.Column(db.String(7))
    o_scanid = db.Column(db.String(7))
    start = db.Column(db.String(50))
    end = db.Column(db.String(50))
    status = db.Column(db.String(100))
    opened = db.Column(db.Boolean)
    closed = db.Column(db.Boolean)
    mass_taken = db.Column(db.Integer)
    notes = db.Column(db.Text)
    snapshots = db.relationship('WormholeSnapshot', backref='wormhole', lazy='dynamic')

    def __init__(self, creator='__server__', date=None, scanid='?', o_scanid='?',
            start='', end='', status='Undecayed', opened=False, closed=False, mass_taken=0, notes=''):
        self.creator = creator
        self.date = date if date else datetime.utcnow()
        self.scanid = scanid
        self.o_scanid = o_scanid
        self.start = start
        self.end = end
        self.status = status
        self.opened = opened
        self.closed = closed
        self.mass_taken = mass_taken
        self.notes = notes

    def __repr__(self):
        return '<Wormhole {} {} {} {}>'.format(self.id, self.scanid, self.start, self.end)

    def is_site_object(self):
        return False


class WormholeSnapshot(db.Model):

    __tablename__ = 'sitetracker_wormholesnapshot'

    id = db.Column(db.Integer, primary_key=True)
    wormhole_id = db.Column(db.Integer, db.ForeignKey('sitetracker_wormhole.id'))
    snapper = db.Column(db.String(200))
    changed = db.Column(db.Text)
    date = db.Column(db.DateTime)

    def __init__(self, wormhole_id, snapper, changed, date=None):
        self.wormhole_id = wormhole_id
        self.snapper = snapper
        self.changed = changed
        self.date = date if date else datetime.utcnow()

    def __repr__(self):
        return '<WormholeSnapshot {} {}>'.format(self.id, self.wormhole)


class Settings(db.Model):

    __tablename__ = 'sitetracker_settings'

    id = db.Column(db.Integer, primary_key=True)
    user = db.Column(db.String(200))
    edits_in_new_tabs = db.Column(db.Boolean)
    store_multiple = db.Column(db.Boolean)
    auto_expand_graph = db.Column(db.Boolean)
    edits_made = db.Column(db.Integer)

    def __init__(self, user, edits_in_new_tabs=True, store_multiple=True, auto_expand_graph=True, edits_made=0):
        self.user = user
        self.edits_in_new_tabs = edits_in_new_tabs
        self.store_multiple = store_multiple
        self.auto_expand_graph = auto_expand_graph
        self.edits_made = edits_made

    def __repr__(self):
        return '<Settings {}>'.format(self.user)


class System(db.Model):

    __tablename__ = 'sitetracker_system'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100))
    map_id = db.Column(db.Integer)
    class_ = db.Column(db.Integer)
    security_level = db.Column(db.Float)
    note = db.Column(db.Text)
    jumps_amarr = db.Column(db.Integer)
    jumps_dodixie = db.Column(db.Integer)
    jumps_hek = db.Column(db.Integer)
    jumps_jita = db.Column(db.Integer)
    jumps_rens = db.Column(db.Integer)
    static = db.Column(db.String(50))
    effect = db.Column(db.String(20))
    is_stub = db.Column(db.Boolean)

    def __init__(self, name, map_id=0, class_=0, security_level=0.0, note='', jumps_amarr=0,
            jumps_dodixie=0, jumps_hek=0, jumps_jita=0, jumps_rens=0, static='', effect='', is_stub=False):
        self.name = name
        self.map_id = map_id
        self.class_ = class_
        self.security_level = security_level
        self.note = note
        self.jumps_amarr = jumps_amarr
        self.jumps_dodixie = jumps_dodixie
        self.jumps_hek = jumps_hek
        self.jumps_jita = jumps_jita
        self.jumps_rens = jumps_rens
        self.static = static
        self.effect = effect
        self.is_stub = is_stub

    def __repr__(self):
        return '<System {}>'.format(self.name)

    def is_kspace(self):
        return not re.match(r'^J\d{6}$', self.name)


class WormholeType(db.Model):

    __tablename__ = 'sitetracker_wormholetype'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(4))
    start = db.Column(db.String(10))
    end = db.Column(db.String(10))
    duration = db.Column(db.Integer)
    mass_per_jump = db.Column(db.Integer)
    mass_total = db.Column(db.Integer)

    def __init__(self, name, start, end, duration, mass_per_jump, mass_total):
        self.name = name
        self.start = start
        self.end = end
        self.duration = duration
        self.mass_per_jump = mass_per_jump
        self.mass_total = mass_total

    def __repr__(self):
        return '<WormholeType {}>'.format(self.name)


class PasteUpdated(db.Model):

    __tablename__ = 'sitetracker_pasteupdated'

    id = db.Column(db.Integer, primary_key=True)
    user = db.Column(db.String(200))
    date = db.Column(db.DateTime)

    def __init__(self, user, date=None):
        self.user = user
        self.date = date if date else datetime.utcnow()

    def __repr__(self):
        return '<PasteUpdated {}>'.format(self.user)


class ShipMass(db.Model):

    __tablename__ = 'sitetracker_shipmass'

    id = db.Column(db.Integer, primary_key=True)
    ship = db.Column(db.String(50))
    mass = db.Column(db.Integer)

    def __init__(self, ship, mass):
        self.ship = ship
        self.mass = mass

    def __repr__(self):
        return '<ShipMass {} {}>'.format(self.ship, self.mass)


class InGameBrowser(dict):

    alliance_name = ''

    def __init__(self, request):
        self.request = request

    def __getitem__(self, key):
        return self.request.headers[str(key)]

    def is_igb(self):
        return 'Eve-Trusted' in self.request.headers and self.request.headers['Eve-Trusted'] in ['No', 'Yes']

    def is_trusted(self):
        return 'Eve-Trusted' in self.request.headers and self.request.headers['Eve-Trusted'] == 'Yes'

    def is_valid(self):
        return self.is_trusted() and 'Eve-Alliancename' in self.request.headers and \
            self.request.headers['Eve-Alliancename'] == self.alliance_name

    def all(self):
        ret = {}
        for key, value in self.request.headers:
            if not key.startswith('Eve-'):
                continue
            ret[key] = value
        return ret

    def __repr__(self):
        return '<InGameBrowser {} {} {}>'.format(self.is_igb(), self.is_trusted(), self.is_valid())
