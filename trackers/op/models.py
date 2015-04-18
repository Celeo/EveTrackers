from trackers.shared import db, app_settings
from datetime import datetime
from collections import Counter


class Operation(db.Model):

    __tablename__ = 'optracker_operation'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(500))
    date = db.Column(db.DateTime)
    state = db.Column(db.String(15))
    leader = db.Column(db.String(200))
    location = db.Column(db.String(200))
    description = db.Column(db.Text)
    last_edited = db.Column(db.DateTime)
    loot = db.Column(db.BigInteger)
    key = db.Column(db.String(10))
    locked = db.Column(db.Boolean)
    tax = db.Column(db.Float)
    players = db.relationship('Player', backref='operation', lazy='dynamic')

    def __init__(self, name, date=None, state='Not started', leader='', location='', description='',
            last_edited=None, loot=0, key=None, locked=False, tax=.1):
        self.name = name
        self.date = date or datetime.utcnow()
        self.state = state
        self.leader = leader
        self.location = location
        self.description = description
        self.last_edited = last_edited or datetime.utcnow()
        self.loot = loot
        self.key = key or datetime.utcnow().strftime('%Y%m%d%S')
        self.locked = locked
        self.tax = tax

    def __repr__(self):
        return '<Operation {} {}>'.format(self.name, self.state)

    def get_state_label(self):
        if self.state == 'Not started':
            return 'yellow'
        elif self.state == 'In progress':
            return 'green'
        elif self.state == 'Loot collected' or self.state == 'Loot sold':
            return 'blue'
        elif self.state == 'Paid':
            return 'white'

    def get_all_players(self):
        return Player.query.filter_by(operation_id=self.id).all()

    def total_shares(self):
        count = 0
        for player in self.get_all_players():
            count += player.sites
        return count

    def get_share_for(self, player):
        try:
            usable = self.loot - (self.loot * self.tax)
            corp_presence = Counter()
            for player in self.get_players():
                corp_presence[player.corporation] += 1
            corp_share = corp_presence[player.corporation] / sum(corp_presence.values())
            corp_allotment = corp_share * usable
            corp_tax = corp_allotment * (app_settings['CORP_TAXES'][player.corporation] if player.corporation in app_settings['CORP_TAXES'] else 1)
            corp_member_allotment = usable - corp_tax
            share = corp_member_allotment / player.sites
            return round(share)
        except:
            return -1

    def get_alliance_share(self):
        # TODO
        offset = 0
        for player in self.get_all_players():
            offset += self.get_share_for(player)
        return self.loot - offset

    def get_players(self):
        return [p for p in self.get_all_players() if not p.name == 'SRP']

    def get_player_count(self):
        return len(self.get_all_players())

    def tax_as_percentage(self):
        return "{}%".format(self.tax * 100)


class Player(db.Model):

    __tablename__ = 'optracker_player'

    id = db.Column(db.Integer, primary_key=True)
    operation_id = db.Column(db.Integer, db.ForeignKey('optracker_operation.id'))
    name = db.Column(db.String(200))
    corporation = db.Column(db.String(200))
    sites = db.Column(db.Float)
    paid = db.Column(db.Integer)
    complete = db.Column(db.Boolean)
    
    def __init__(self, operation_id, name, corporation, sites=0, paid=0.0, complete=False):
        self.operation_id = operation_id
        self.name = name
        self.corporation = corporation
        self.sites = sites
        self.paid = paid
        self.complete = complete

    def __repr__(self):
        return '<Player {} {} {}>'.format(self.name, self.sites, self.complete)

    def get_share(self):
        return self.operation.get_share_for(self)

    def get_share_formatted(self):
        return '{:,}'.format(self.get_share())

    def get_paid_formatted(self):
        return '{:,}'.format(self.paid)


class LogStatement(db.Model):

    __tablename__ = 'optracker_logstatement'

    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.DateTime)
    user = db.Column(db.String(200))
    message = db.Column(db.Text)

    def __init__(self, date=None, user='', message=''):
        self.date = date if date else datetime.utcnow()
        self.user = user
        self.message = message
