from trackers.shared import db


class Item(db.Model):

    __tablename__ = 'eve_item'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(500))

    def __init__(self, id, name):
        self.id = id
        self.name = name

    def __repr__(self):
        return '<Item {} {}>'.format(self.id, self.name)


class Participant(db.Model):

    __tablename__ = 'wartracker_participant'

    id = db.Column(db.Integer, primary_key=True)
    kill = db.relationship('Kill', backref='participant', lazy='dynamic')
    role = db.Column(db.String(10))
    corp_id = db.Column(db.Integer)
    corp_name = db.Column(db.String(200))
    alliance_id = db.Column(db.Integer)
    alliance_name = db.Column(db.String(200))
    damage = db.Column(db.Integer)
    ship_id = db.Column(db.Integer)
    ship_name = db.Column(db.String(100))
    final_blow = db.Column(db.Boolean)

    def __init__(self, kill_id='', name='', role='', corp_id='', corp_name='', alliance_id='',
            alliance_name='', damage='', ship_id='', final_blow=False):
        self.kill_id = kill_id
        self.name = name
        self.role = role
        self.corp_id = corp_id
        self.corp_name = corp_name
        self.alliance_id = alliance_id
        self.alliance_name = alliance_name
        self.damage = damage
        self.ship_id = ship_id
        self.final_blow = final_blow

    def __repr__(self):
        return '<Participant {} {} {} {} {}>'.format(self.name, self.role, self.corp_name, 
            self.alliance_name, self.final_blow)


class Kill(db.Model):

    __tablename__ = 'wartracker_kill'

    id = db.Column(db.Integer, primary_key=True)
    kill_id = db.Column(db.Integer)
    victim = db.relationship('Participant', backref='victim_kill', lazy='dynamic')
    attackers = db.relationship('Participant', backref='attackers_kill', lazy='dynamic')
    date = db.Column(db.DateTime)

    def __init__(self, date=''):
        self.victim = None
        self.attackers = []
        self.date = date

    def __repr__(self):
        return '<Kill {} {} {}>'.format(self.victim, len(self.attackers), self.date)
