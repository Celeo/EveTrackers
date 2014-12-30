from trackers.shared import db
from datetime import datetime


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
    loot = db.Column(db.Integer)
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
            return 'label-warning'
        elif self.state == 'In progress':
            return 'label-success'
        elif self.state == 'Loot collected' or self.state == 'Loot sold':
            return 'label-info'
        elif self.state == 'Paid':
            return 'label-default'

    def get_all_players(self):
        return Player.query.filter_by(operation_id=self.id).all()

    def total_shares(self):
        count = 0
        for player in self.get_all_players():
            count += player.sites
        return count

    def get_share_for(self, player):
        try:
            share = self.loot * (float(player.sites) / float(self.total_shares()))
            share -= float(self.tax) * float(share)
            return share
        except:
            return -1

    def get_alliance_share(self):
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
    sites = db.Column(db.Float)
    paid = db.Column(db.Integer)
    api_paid = db.Column(db.Integer)
    complete = db.Column(db.Boolean)
    
    def __init__(self, operation_id, name, sites=0, paid=0.0, api_paid=0.0, complete=False):
        self.operation_id = operation_id
        self.name = name
        self.sites = sites
        self.paid = paid
        self.api_paid = api_paid
        self.complete = complete

    def __repr__(self):
        return '<Player {} {} {}>'.format(self.name, self.sites, self.complete)

    def get_share(self):
        return self.operation.get_share_for(self)

    def get_share_formatted(self):
        return '{:,}'.format(self.get_share())

    def get_paid_formatted(self):
        return '{:,}'.format(self.paid)

    def get_api_paid_formatted(self):
        return '{:,}'.format(self.api_paid)


class ApiKey(db.Model):

    __tablename__ = 'optracker_apikey'

    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.Integer)
    code = db.Column(db.String(200))
    wallet = db.Column(db.Integer)
    added = db.Column(db.DateTime)
    note = db.Column(db.Text)

    def __init__(self, key='', code='', wallet=1001, added=None, note=''):
        self.key = key
        self.code = code
        self.wallet = wallet
        self.added = added if added else datetime.utcnow()
        self.note = note

    def __repr__(self):
        return '<ApiKey {} {}'.format(self.key, self.code)


class PlayerAuthName(db.Model):

    __tablename__ = 'optracker_playerauthname'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(200))
    character_name = db.Column(db.String(200))
    corp = db.Column(db.String(200))
    bursar = db.Column(db.Boolean)

    def __init__(self, username='', character_name='', corp='', bursar=False):
        self.username = username
        self.character_name = character_name
        self.corp = corp
        self.bursar = bursar

    def __repr__(self):
        return '<PlayerAuthName {} {} {}>'.format(self.username, self.character_name, self.bursar)


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
